"""Multi-coin trading bot runner with dynamic coin selection."""
from decimal import Decimal
from typing import Dict, List, Set, Optional
import asyncio
import time

from ..trading.execution import TradingExecutor
from ..data.clients.kraken_client import KrakenClient
from ..ml.analysis.coin_analyzer import CoinOpportunityAnalyzer


class MultiCoinTradingBot:
    """Multi-coin trading bot with dynamic coin selection.

    Monitors multiple cryptocurrencies and allocates trading capital
    to the most promising opportunities.
    """

    def __init__(
            self,
            symbols: List[str],
            timeframe: str,
            initial_balance: Decimal,
            update_interval: int = 60
    ) -> None:
        """Initialize multi-coin trading bot.

        Args:
            symbols: List of trading pair symbols to monitor
            timeframe: Trading timeframe
            initial_balance: Starting balance in USDT
            update_interval: Seconds between updates
        """
        self.symbols = symbols
        self.timeframe = timeframe
        self.initial_balance = initial_balance
        self.available_balance = initial_balance
        self.update_interval = update_interval

        # Initialize components
        self.client = KrakenClient()
        self.analyzer = CoinOpportunityAnalyzer()

        # Create executors for each symbol
        self.executors: Dict[str, TradingExecutor] = {}
        for symbol in symbols:
            self.executors[symbol] = TradingExecutor(
                symbol=symbol,
                timeframe=timeframe,
                initial_balance=Decimal('0')  # Initially allocate no balance
            )

        # Trading state
        self.active_symbol: Optional[str] = None
        self.active_since: int = 0
        self.allocated_balances: Dict[str, Decimal] = {symbol: Decimal('0') for symbol in symbols}
        self.positions: Dict[str, Dict] = {}
        self.execution_history: Dict[str, List[Dict]] = {symbol: [] for symbol in symbols}

        # Control flags
        self.is_running = False
        self._stop_event = asyncio.Event()
        self._tasks = []

        # Add initialization state flags
        self._data_initialized = False
        self._analysis_complete = False

        # Performance metrics
        self.total_trades = 0
        self.profitable_trades = 0
        self.total_profit_loss = Decimal('0')

    async def start(self) -> None:
        """Start the multi-coin trading bot."""
        if self.is_running:
            return

        self.is_running = True
        self._stop_event.clear()

        # STEP 1: Fetch historical data
        print(f"Fetching historical data for {len(self.symbols)} trading pairs...")
        historical_data = await self.client.fetch_historical_data(
            symbols=self.symbols,
            interval=5,
            limit=200  # Fetch plenty of historical data
        )

        # STEP 2: Load data directly into the analyzer
        print("Loading historical data into analyzer...")
        for symbol, ohlcv_data in historical_data.items():
            self.analyzer.load_market_data(symbol, ohlcv_data)

        # STEP 3: Connect to WebSocket for real-time data
        print("Connecting to Kraken WebSocket API...")
        await self.client.connect()

        # Subscribe to all symbols
        print(f"Subscribing to {len(self.symbols)} trading pairs...")
        await self.client.subscribe_prices(self.symbols)

        # Set price update callback
        self.client.on_price_update = self._handle_price_update

        # STEP 4: Perform initial market analysis
        print("Performing initial market analysis...")
        scores = self.analyzer.calculate_opportunity_scores()

        # STEP 5: Select initial trading pair based on analysis
        if scores and any(score != 50 for score in scores.values()):
            top_opportunities = self.analyzer.get_best_opportunities(3)

            print("\nTop Trading Opportunities from initial analysis:")
            for symbol, score in top_opportunities:
                print(f"{symbol}: Score {score}/100")

            # Select best coin to start trading immediately
            if top_opportunities:
                best_symbol, _ = top_opportunities[0]
                print(f"Selecting {best_symbol} for immediate trading based on analysis...")
                await self._switch_active_coin(best_symbol)
                self._analysis_complete = True
        else:
            print("No conclusive analysis available yet. Trading will start once analysis is complete.")

        # STEP 6: Start the monitoring and trading loops
        self._tasks = [
            asyncio.create_task(self._market_analysis_loop()),
            asyncio.create_task(self._trading_execution_loop())
        ]

        symbols_str = ', '.join(self.symbols)
        print(f"Multi-coin trading bot started - Monitoring: {symbols_str}")

    async def stop(self) -> None:
        """Stop the multi-coin trading bot."""
        if not self.is_running:
            return

        print("Stopping multi-coin trading bot...")
        self._stop_event.set()

        # Wait for all tasks to complete
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)

        # Close WebSocket connection
        await self.client.close()

        self.is_running = False
        print("\nMulti-coin trading bot stopped")
        self._print_final_summary()

    def _handle_price_update(self, update: Dict) -> None:
        """Handle price updates from WebSocket.

        Args:
            update: Price update data
        """
        symbol = update["symbol"]
        price = update["data"]["price"]
        volume = update["data"]["volume"]

        # Update price in executor
        if symbol in self.executors:
            self.executors[symbol].simulator.update_market_price(symbol, price)

        # Update analyzer data
        self.analyzer.update_coin_data(symbol, price, volume)

    async def _market_analysis_loop(self) -> None:
        """Continuously analyze market data and update opportunity scores."""
        print("Starting market analysis loop...")

        while not self._stop_event.is_set():
            try:
                # Calculate opportunity scores
                scores = self.analyzer.calculate_opportunity_scores()

                if scores and any(score != 50 for score in scores.values()):
                    # Mark analysis as complete if it wasn't already
                    if not self._analysis_complete:
                        print("Market analysis now has meaningful scores. Trading can begin.")
                        self._analysis_complete = True

                    # Log current opportunities
                    top_opportunities = self.analyzer.get_best_opportunities(3)

                    print("\nTop Trading Opportunities:")
                    for symbol, score in top_opportunities:
                        print(f"{symbol}: Score {score}/100")

                    # Check if we should switch to a better coin
                    if self.active_symbol:
                        better_symbol = self.analyzer.should_change_coin(self.active_symbol)

                        if better_symbol and better_symbol != self.active_symbol:
                            # Time to switch coins
                            print(
                                f"\nSwitching from {self.active_symbol} to {better_symbol} based on opportunity analysis")
                            await self._switch_active_coin(better_symbol)
                    else:
                        # No active coin yet, select the best one
                        if top_opportunities:
                            best_symbol, _ = top_opportunities[0]
                            print(f"Selecting {best_symbol} for trading based on analysis...")
                            await self._switch_active_coin(best_symbol)

                # Wait before next analysis
                try:
                    await asyncio.wait_for(self._stop_event.wait(), timeout=self.update_interval)
                except asyncio.TimeoutError:
                    pass

            except Exception as e:
                print(f"Error in market analysis: {e}")
                await asyncio.sleep(self.update_interval)

    async def _trading_execution_loop(self) -> None:
        """Execute trading actions on the active coin."""
        print("Starting trading execution loop...")

        # Wait until we have proper analysis before attempting any trades
        while not self._stop_event.is_set() and not self._analysis_complete:
            print("Waiting for market analysis to complete before trading...")
            await asyncio.sleep(10)
            continue

        print("Trading execution loop is now active and will execute trades.")

        while not self._stop_event.is_set():
            all_prices = self.client.get_multi_coin_data()
            print(f"DEBUG: Available price data for {len(all_prices)} symbols: {list(all_prices.keys())}")
            print(f"DEBUG: Looking for price data for {self.active_symbol}")

            # Check if symbol exists but with different case
            if self.active_symbol not in all_prices:
                for key in all_prices.keys():
                    if key.upper() == self.active_symbol.upper():
                        print(f"DEBUG: Symbol case mismatch! Found {key} instead of {self.active_symbol}")

            # Print the actual price data for the symbol
            if self.active_symbol in all_prices:
                price_data = all_prices[self.active_symbol]
                print(f"DEBUG: Price data for {self.active_symbol}: {price_data}")
            try:
                # Only trade if we have an active symbol with allocated balance
                if self.active_symbol and self.allocated_balances.get(self.active_symbol, Decimal('0')) > Decimal('0'):
                    executor = self.executors[self.active_symbol]

                    # Verify we have market data
                    latest_price = self.client.get_latest_price(self.active_symbol)

                    print(latest_price)
                    if latest_price is None or latest_price <= 0:
                        print(f"No market data available for {self.active_symbol}, waiting...")
                        await asyncio.sleep(5)
                        continue

                    # Update executor's balance
                    executor.simulator.balance.available = self.allocated_balances[self.active_symbol]

                    # Execute trading cycle
                    result = executor.execute_cycle()
                    self.execution_history[self.active_symbol].append(result)

                    # Update allocated balance based on result
                    self.allocated_balances[self.active_symbol] = Decimal(str(result['portfolio_value']))

                    # Check if trade was executed
                    if result['action'] in ['buy', 'sell']:
                        self.total_trades += 1

                        # Update positions
                        self.positions = {
                            symbol: float(volume)
                            for symbol, volume in executor.simulator.positions.items()
                        }

                        # If it was a sell, check for profit
                        if result['action'] == 'sell' and 'trade_details' in result:
                            trade = result['trade_details']
                            if trade['value'] > trade['price'] * trade['volume']:
                                self.profitable_trades += 1
                                profit = Decimal(str(trade['value'])) - (
                                        Decimal(str(trade['price'])) * Decimal(str(trade['volume'])))
                                self.total_profit_loss += profit

                    self._print_cycle_result(self.active_symbol, result)
                else:
                    # No active symbol yet
                    if not self.active_symbol:
                        print("Waiting for market analysis to select trading pair...")
                    else:
                        print(f"Active symbol {self.active_symbol} has no allocated balance yet...")
                    await asyncio.sleep(5)

                # Wait before next execution
                try:
                    await asyncio.wait_for(self._stop_event.wait(), timeout=10)
                except asyncio.TimeoutError:
                    pass

            except Exception as e:
                print(f"Error in trading execution: {e}")
                await asyncio.sleep(10)

    async def _switch_active_coin(self, new_symbol: str) -> None:
        """Switch trading to a different coin.

        Args:
            new_symbol: Symbol to switch to
        """
        if new_symbol not in self.symbols:
            print(f"Cannot switch to {new_symbol}: not in monitored symbols")
            return

        # If we already have an active symbol, liquidate positions
        if self.active_symbol:
            executor = self.executors[self.active_symbol]

            # Sell all positions
            for position_symbol, volume in list(executor.simulator.positions.items()):
                if volume > Decimal('0'):
                    price = self.client.get_latest_price(position_symbol)
                    if price:
                        executor.simulator.execute_sell(position_symbol, price, volume)
                        print(f"Liquidated position: {volume} {position_symbol} at {price}")

            # Update available balance
            self.available_balance += self.allocated_balances[self.active_symbol]
            self.allocated_balances[self.active_symbol] = Decimal('0')

        # Set new active symbol
        self.active_symbol = new_symbol
        self.active_since = int(time.time())

        # Allocate balance to new symbol (70% of available)
        allocation = self.available_balance * Decimal('0.7')
        self.allocated_balances[new_symbol] = allocation
        self.available_balance -= allocation

        print(f"Allocated {allocation} USDT to {new_symbol}")

    def _print_cycle_result(self, symbol: str, result: Dict) -> None:
        """Print execution cycle result.

        Args:
            symbol: Trading pair symbol
            result: Execution result
        """
        print(f"\n{symbol} Execution:")
        print(f"Action: {result['action']}")
        print(f"Balance: {result['balance']:.2f}")
        print(f"Portfolio Value: {result['portfolio_value']:.2f}")
        if 'message' in result:
            print(f"Message: {result['message']}")

    def _print_final_summary(self) -> None:
        """Print trading session summary."""
        print("\nTrading Session Summary")
        print("=" * 50)

        # Calculate final portfolio value
        final_value = self.available_balance
        for symbol, balance in self.allocated_balances.items():
            final_value += balance

        # Print overall performance
        profit = final_value - self.initial_balance
        profit_percent = (profit / self.initial_balance * 100) if self.initial_balance > 0 else Decimal('0')

        print(f"Initial Portfolio: {self.initial_balance:.2f} USDT")
        print(f"Final Portfolio: {final_value:.2f} USDT")
        print(f"Total Profit/Loss: {profit:.2f} USDT ({profit_percent:.2f}%)")
        print(f"Total Trades: {self.total_trades}")

        if self.total_trades > 0:
            win_rate = (self.profitable_trades / self.total_trades) * 100
            print(f"Win Rate: {win_rate:.2f}%")

        # Print coin-specific stats
        print("\nCoin Performance:")
        for symbol in self.symbols:
            history = self.execution_history[symbol]
            if not history:
                continue

            trades_count = sum(1 for r in history if r['action'] in ['buy', 'sell'])

            print(f"\n{symbol}:")
            print(f"  Trades: {trades_count}")
            print(f"  Final Allocation: {self.allocated_balances[symbol]:.2f} USDT")

            if history:
                first = history[0]
                last = history[-1]
                symbol_profit = Decimal(str(last['portfolio_value'])) - Decimal(str(first['portfolio_value']))
                symbol_percent = (symbol_profit / Decimal(str(first['portfolio_value'])) * 100) if Decimal(
                    str(first['portfolio_value'])) > 0 else Decimal('0')
                print(f"  Profit/Loss: {symbol_profit:.2f} USDT ({symbol_percent:.2f}%)")