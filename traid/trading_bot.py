from decimal import Decimal
from typing import Dict, List, Optional
import asyncio
import time
import numpy as np


class TradingBot:
    # List of stable coins to exclude from trading
    STABLE_COINS = {'USDT', 'USDC', 'DAI', 'BUSD', 'UST', 'EURT', 'TUSD', 'GUSD', 'PAX', 'HUSD', 'EURS'}

    def __init__(
            self,
            symbols: List[str],
            timeframe: str,
            initial_balance: Decimal,
            client,
            single_coin_mode: bool = False
    ):
        """Initialize trading bot."""
        # Filter out stablecoins from symbols list
        self.symbols = []
        for s in symbols:
            # Expect a format like "BTC/USDT"
            try:
                base, quote = s.split('/')
            except ValueError:
                # If the symbol doesn't have '/', skip or handle differently
                continue

            # We only skip if the BASE is a stable coin
            if base not in self.STABLE_COINS:
                self.symbols.append(s)

        self.timeframe = timeframe
        self.initial_balance = initial_balance
        self.available_balance = initial_balance
        self.client = client
        self.single_coin_mode = single_coin_mode

        # Trading parameters - more aggressive settings
        self.max_trade_count = 10  # Increased from 5 to be more aggressive
        self.trade_cooldown = 60  # Reduced from 300 to be more aggressive (1 minute)
        self.last_trade_time = 0  # Timestamp of last trade

        # Set on_price_update callback
        self.client.on_price_update = self._handle_price_update

        # Trading state
        self.active_symbol = self.symbols[0] if single_coin_mode else None
        self.positions: Dict[str, Decimal] = {}
        self.execution_history: Dict[str, List[Dict]] = {symbol: [] for symbol in self.symbols}
        self.current_prices: Dict[str, Decimal] = {}
        self.allocated_balances: Dict[str, Decimal] = {
            symbol: (initial_balance if symbol == self.active_symbol and single_coin_mode else Decimal('0'))
            for symbol in self.symbols
        }

        # Technical analysis data
        self.coin_data: Dict[str, Dict] = {}
        self.opportunity_scores: Dict[str, int] = {}

        # Control flags
        self.is_running = False
        self._stop_event = asyncio.Event()
        self._tasks = []

        # Performance metrics
        self.total_trades = 0
        self.profitable_trades = 0
        self.total_profit_loss = Decimal('0')
        self.start_time = None

        # Print initialization message
        print(f"🚀 Trading Bot initialized in {'SINGLE' if single_coin_mode else 'MULTI'}-coin mode")
        print(f"👀 Monitoring {len(self.symbols)} trading pairs (stablecoins excluded)")
        print(f"💰 Initial balance: {self.initial_balance} USDT")

    def _handle_price_update(self, update: Dict) -> None:
        """Handle price updates from WebSocket."""
        symbol = update["symbol"]
        price = update["data"]["price"]
        volume = update["data"]["volume"]

        # Update current prices
        self.current_prices[symbol] = price

        # Update coin data for analysis
        self._update_coin_data(symbol, price, volume)

    def _update_coin_data(self, symbol: str, price: Decimal, volume: Decimal) -> None:
        """Update historical data for a coin."""
        if symbol not in self.coin_data:
            self.coin_data[symbol] = {
                'prices': [],
                'volumes': [],
                'timestamps': []
            }

        timestamp = int(time.time())

        # Add new data point
        self.coin_data[symbol]['prices'].append(float(price))
        self.coin_data[symbol]['volumes'].append(float(volume))
        self.coin_data[symbol]['timestamps'].append(timestamp)

        # Limit the history length
        max_history = 50
        if len(self.coin_data[symbol]['prices']) > max_history:
            self.coin_data[symbol]['prices'] = self.coin_data[symbol]['prices'][-max_history:]
            self.coin_data[symbol]['volumes'] = self.coin_data[symbol]['volumes'][-max_history:]
            self.coin_data[symbol]['timestamps'] = self.coin_data[symbol]['timestamps'][-max_history:]

    async def start(self) -> None:
        """Start the trading bot."""
        if self.is_running:
            return

        self.is_running = True
        self._stop_event.clear()
        self.start_time = int(time.time())

        # Connect to WebSocket and subscribe to symbols
        print("📡 Connecting to Kraken WebSocket API...")
        await self.client.connect()

        print(f"🔔 Subscribing to {len(self.symbols)} trading pairs...")
        await self.client.subscribe_prices(self.symbols)

        # Fetch historical data
        print("📊 Fetching historical data...")
        historical_data = await self.client.fetch_historical_data(
            symbols=self.symbols,
            interval=5,
            limit=50
        )

        # Load historical data
        for symbol, ohlcv_data in historical_data.items():
            self.coin_data[symbol] = {
                'prices': [candle['close'] for candle in ohlcv_data],
                'volumes': [candle['volume'] for candle in ohlcv_data],
                'timestamps': [candle['timestamp'] for candle in ohlcv_data]
            }

        # Calculate initial opportunity scores
        self._calculate_opportunity_scores()

        # Print top opportunities
        top_opportunities = self._get_top_opportunities(5)
        print("\n🔥 Initial Top Trading Opportunities:")
        for symbol, score in top_opportunities:
            print(f"  {symbol}: Score {score}/100")

        # Set initial active symbol
        if not self.single_coin_mode:
            top_coin = self._get_best_opportunity()
            if top_coin:
                print(f"\n🎯 Selected {top_coin} as initial trading target")
                await self._switch_active_coin(top_coin)
        else:
            print(f"\n🎯 Trading single coin: {self.active_symbol}")

        # Start the trading loops
        self._tasks = [
            asyncio.create_task(self._analysis_loop()),
            asyncio.create_task(self._trading_loop())
        ]

        print("\n✅ Trading bot is now active")
        print(f"💪 Strategy: {'AGGRESSIVE' if not self.single_coin_mode else 'SINGLE-COIN FOCUS'}")
        self._print_portfolio_status()

    async def stop(self) -> None:
        """Stop the trading bot."""
        if not self.is_running:
            return

        print("🛑 Stopping trading bot...")
        self._stop_event.set()

        # Wait for tasks to complete
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)

        # Close WebSocket connection
        await self.client.close()

        self.is_running = False
        print("\n⏹️ Trading bot stopped")
        self._print_summary()

    async def _analysis_loop(self) -> None:
        """Analyze market data and update opportunity scores every 5 minutes."""
        while not self._stop_event.is_set():
            try:
                # Skip analysis in single-coin mode
                if self.single_coin_mode:
                    await asyncio.sleep(300)  # 5 minutes
                    continue

                # Calculate opportunity scores
                self._calculate_opportunity_scores()

                # Get best opportunities
                top_opportunities = self._get_top_opportunities(3)

                if top_opportunities:
                    print("\n📊 MARKET ANALYSIS UPDATE 📊")
                    print("Top Trading Opportunities:")
                    for symbol, score in top_opportunities:
                        print(f"  {symbol}: Score {score}/100")

                    # Check if we should switch coins
                    if self.active_symbol:
                        better_coin = self._should_change_coin()
                        if better_coin and better_coin != self.active_symbol:
                            print(f"\n🔄 Switching target from {self.active_symbol} to {better_coin}")
                            await self._switch_active_coin(better_coin)
                    else:
                        # No active coin yet, select the best one
                        best_coin = self._get_best_opportunity()
                        if best_coin:
                            print(f"\n🎯 Selecting {best_coin} for trading")
                            await self._switch_active_coin(best_coin)

                # Print current portfolio status
                self._print_portfolio_status()

                # Wait 5 minutes before next analysis
                await asyncio.sleep(300)  # 5 minutes between market checks

            except Exception as e:
                print(f"❌ Error in market analysis: {e}")
                await asyncio.sleep(60)  # Shorter recovery time for errors

    async def _trading_loop(self) -> None:
        """Execute trading actions every second."""
        while not self._stop_event.is_set():
            try:
                # Only trade if we have an active symbol with allocated balance
                if self.active_symbol and self.allocated_balances.get(self.active_symbol, Decimal('0')) > Decimal('0'):

                    # Get latest price
                    price = self.client.get_latest_price(self.active_symbol)

                    if not price or price <= 0:
                        await asyncio.sleep(1)
                        continue

                    # Generate signal
                    signal = self._generate_trading_signal(self.active_symbol)

                    # Execute trade based on signal
                    if signal == 1:  # Buy signal
                        success = self._execute_buy(self.active_symbol, price)
                        if success:
                            self._print_portfolio_status()

                    elif signal == -1:  # Sell signal
                        success = self._execute_sell(self.active_symbol, price)
                        if success:
                            self._print_portfolio_status()

                # Wait before next check (every second)
                await asyncio.sleep(1)

            except Exception as e:
                print(f"❌ Error in trading execution: {e}")
                await asyncio.sleep(5)  # Shorter recovery time for errors

    def _calculate_opportunity_scores(self) -> Dict[str, int]:
        """Calculate opportunity scores for all coins."""
        for symbol, data in self.coin_data.items():
            # Skip if not enough data
            if len(data['prices']) < 10:
                self.opportunity_scores[symbol] = 50  # Neutral score
                continue

            try:
                # Convert to numpy arrays
                prices = np.array(data['prices'])
                volumes = np.array(data['volumes'])

                # Calculate score
                score = self._calculate_coin_score(symbol, prices, volumes)
                self.opportunity_scores[symbol] = score

            except Exception as e:
                print(f"Error calculating score for {symbol}: {e}")
                self.opportunity_scores[symbol] = 50

        return self.opportunity_scores

    def _calculate_rsi(self, prices: np.ndarray, period: int = 14) -> float:
        """Calculate Relative Strength Index."""
        if len(prices) < period + 1:
            return 50

        # Calculate price changes
        deltas = np.diff(prices)

        # Split gains and losses
        gains = deltas.copy()
        losses = deltas.copy()
        gains[gains < 0] = 0
        losses[losses > 0] = 0
        losses = abs(losses)

        # Calculate average gains and losses
        avg_gain = np.mean(gains[:period])
        avg_loss = np.mean(losses[:period])

        # Calculate RS and RSI
        if avg_loss == 0:
            return 100

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return rsi

    def _get_top_opportunities(self, top_n: int = 3) -> List:
        """Get top N coins with highest opportunity scores."""
        sorted_opportunities = sorted(
            self.opportunity_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )

        return sorted_opportunities[:top_n]

    def _get_best_opportunity(self) -> Optional[str]:
        """Get the best opportunity coin."""
        top_opportunities = self._get_top_opportunities(1)
        return top_opportunities[0][0] if top_opportunities else None

    def _should_change_coin(self) -> Optional[str]:
        """Determine if bot should switch to a different coin (more aggressive)."""
        if not self.opportunity_scores or self.active_symbol not in self.opportunity_scores:
            return self._get_best_opportunity()

        best_coin = self._get_best_opportunity()
        if not best_coin:
            return None

        current_score = self.opportunity_scores[self.active_symbol]
        best_score = self.opportunity_scores[best_coin]

        # More aggressive coin switching: 10+ points difference instead of 15
        if best_coin != self.active_symbol and best_score > current_score + 10:
            return best_coin

        return None

    async def _switch_active_coin(self, new_symbol: str) -> None:
        """Switch trading to a different coin."""
        if new_symbol not in self.symbols:
            print(f"Cannot switch to {new_symbol}: not in monitored symbols")
            return

        # If we have an active symbol, liquidate positions
        if self.active_symbol:
            # Sell all positions
            if self.active_symbol in self.positions and self.positions[self.active_symbol] > 0:
                price = self.client.get_latest_price(self.active_symbol)
                if price:
                    self._execute_sell(self.active_symbol, price, self.positions[self.active_symbol])
                else:
                    print(f"⚠️ Warning: Could not get price for {self.active_symbol}, positions not liquidated")

            # Update available balance
            self.available_balance += self.allocated_balances[self.active_symbol]
            self.allocated_balances[self.active_symbol] = Decimal('0')

        # Set new active symbol
        old_symbol = self.active_symbol
        self.active_symbol = new_symbol

        # Allocate balance to new symbol (80% of available - more aggressive than before)
        allocation = self.available_balance * Decimal('0.8')  # Was 70% before
        self.allocated_balances[new_symbol] = allocation
        self.available_balance -= allocation

        print(f"🔄 SWITCHED from {old_symbol if old_symbol else 'none'} to {new_symbol}")
        print(f"💰 Allocated {allocation:.2f} USDT to {new_symbol}")

    def _generate_trading_signal(self, symbol: str) -> int:
        """Generate trading signal for a symbol (more aggressive).

        Returns:
            int: 1 for buy, -1 for sell, 0 for hold
        """
        if symbol not in self.coin_data or len(self.coin_data[symbol]['prices']) < 14:
            return 0

        prices = np.array(self.coin_data[symbol]['prices'])

        # Calculate RSI
        rsi = self._calculate_rsi(prices)

        # Calculate moving averages
        if len(prices) >= 10:
            short_ma = np.mean(prices[-3:])  # Shorter window (was 5)
            long_ma = np.mean(prices[-8:])  # Shorter window (was 10)

            # Buy signal: More aggressive parameters
            # Buy when RSI < 35 (was 30) or when short MA > long MA with RSI < 65 (was 60)
            if rsi < 35 or (short_ma > long_ma and rsi < 65):
                # Check if we already have a position
                if symbol not in self.positions or self.positions.get(symbol, Decimal('0')) == Decimal('0'):
                    return 1

            # Sell signal: More aggressive parameters
            # Sell when RSI > 65 (was 70) or when short MA < long MA with RSI > 35 (was 40)
            elif rsi > 65 or (short_ma < long_ma and rsi > 35):
                # Check if we have a position to sell
                if symbol in self.positions and self.positions.get(symbol, Decimal('0')) > 0:
                    return -1

        return 0

    def _execute_buy(self, symbol: str, price: Decimal, volume: Optional[Decimal] = None) -> bool:
        """Execute a buy order (more aggressive)."""
        if price <= 0:
            print(f"Invalid price for {symbol}: {price}")
            return False

        available_balance = self.allocated_balances.get(symbol, Decimal('0'))

        if available_balance <= 0:
            print(f"No balance allocated for {symbol}")
            return False

        # Calculate volume if not provided - use 95% of available balance (was 90%)
        if volume is None:
            position_value = available_balance * Decimal('0.95')  # More aggressive allocation
            volume = position_value / price

        # Minimum volume check
        if volume < Decimal('0.0001'):
            print(f"Volume too small for {symbol}: {volume}")
            return False

        cost = price * volume

        # Check if we have enough balance
        if cost > available_balance:
            # Use all available balance instead of failing
            volume = available_balance / price
            cost = price * volume

        # Update balance
        self.allocated_balances[symbol] -= cost

        # Update position
        if symbol not in self.positions:
            self.positions[symbol] = Decimal('0')
        self.positions[symbol] += volume

        # Record trade
        timestamp = int(time.time())
        trade_details = {
            "timestamp": timestamp,
            "action": "buy",
            "symbol": symbol,
            "price": float(price),
            "volume": float(volume),
            "cost": float(cost),
            "balance_after": float(self.allocated_balances[symbol])
        }

        self.execution_history[symbol].append(trade_details)
        self.total_trades += 1

        print(f"🔵 BOUGHT {volume:.6f} {symbol} at {price} USDT (Total: {cost:.2f} USDT)")
        return True

