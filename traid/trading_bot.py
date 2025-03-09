from decimal import Decimal
from typing import Dict, List, Optional
import asyncio
import time
import numpy as np


class TradingBot:
    """Unified trading bot supporting single-coin or multi-coin trading."""

    STABLE_COINS = {'USDT', 'USDC', 'DAI', 'BUSD', 'UST', 'EURT', 'TUSD', 'GUSD', 'PAX', 'HUSD', 'EURS'}

    def __init__(
        self,
        symbols: List[str],
        timeframe: str,
        initial_balance: Decimal,
        client,
        single_coin_mode: bool = False
    ):
        # Filter out stablecoins or invalid symbols
        self.symbols = [
            s for s in symbols
            if '/' in s and s.split('/')[0] not in self.STABLE_COINS
        ]

        self.timeframe = timeframe
        self.initial_balance = initial_balance
        self.available_balance = initial_balance
        self.client = client
        self.single_coin_mode = single_coin_mode

        self.last_trade_time = 0

        # Trading state
        self.active_symbol = self.symbols[0] if self.single_coin_mode and self.symbols else None
        self.positions: Dict[str, Decimal] = {}
        self.execution_history: Dict[str, List[Dict]] = {symbol: [] for symbol in self.symbols}
        self.current_prices: Dict[str, Decimal] = {}

        # Each symbol’s allocated balance, if single coin mode,
        # we allocate the entire initial balance to the first symbol.
        self.allocated_balances: Dict[str, Decimal] = {
            symbol: (initial_balance if symbol == self.active_symbol and single_coin_mode else Decimal('0'))
            for symbol in self.symbols
        }

        # Data for technical analysis
        self.coin_data: Dict[str, Dict] = {}
        self.opportunity_scores: Dict[str, int] = {}

        # Flags and tasks
        self.is_running = False
        self._stop_event = asyncio.Event()
        self._tasks = []

        # Performance metrics
        self.total_trades = 0
        self.profitable_trades = 0
        self.total_profit_loss = Decimal('0')
        self.start_time = None

        # Set price update callback
        self.client.on_price_update = self._handle_price_update

        print(f"🚀 Trading Bot initialized in {'SINGLE' if single_coin_mode else 'MULTI'}-coin mode")
        print(f"👀 Monitoring {len(self.symbols)} trading pairs (stablecoins excluded)")
        print(f"💰 Initial balance: {self.initial_balance} USDT")

    def _handle_price_update(self, update: Dict) -> None:
        """Handle live price updates from the client."""
        symbol = update["symbol"]
        price = update["data"]["price"]
        volume = update["data"]["volume"]

        self.current_prices[symbol] = price
        self._update_coin_data(symbol, price, volume)

    def _update_coin_data(self, symbol: str, price: Decimal, volume: Decimal) -> None:
        """Maintain a rolling history of prices/volumes/timestamps for analysis."""
        if symbol not in self.coin_data:
            self.coin_data[symbol] = {'prices': [], 'volumes': [], 'timestamps': []}

        self.coin_data[symbol]['prices'].append(float(price))
        self.coin_data[symbol]['volumes'].append(float(volume))
        self.coin_data[symbol]['timestamps'].append(int(time.time()))

        # Keep only the last 50 data points
        max_len = 50
        for key in ['prices', 'volumes', 'timestamps']:
            if len(self.coin_data[symbol][key]) > max_len:
                self.coin_data[symbol][key] = self.coin_data[symbol][key][-max_len:]

    async def start(self) -> None:
        """Begin trading: connect to client, fetch history, start loops."""
        if self.is_running:
            return
        self.is_running = True
        self._stop_event.clear()
        self.start_time = int(time.time())

        print("📡 Connecting to Kraken WebSocket API...")
        await self.client.connect()

        print(f"🔔 Subscribing to {len(self.symbols)} trading pairs...")
        await self.client.subscribe_prices(self.symbols)

        print("📊 Fetching historical data...")
        historical_data = await self.client.fetch_historical_data(
            symbols=self.symbols, interval=5, limit=50
        )

        # Load historical data
        for symbol, ohlcv_data in historical_data.items():
            self.coin_data[symbol] = {
                'prices': [candle['close'] for candle in ohlcv_data],
                'volumes': [candle['volume'] for candle in ohlcv_data],
                'timestamps': [candle['timestamp'] for candle in ohlcv_data]
            }

        # Calculate initial scores and choose an active symbol (multi-coin mode)
        self._calculate_opportunity_scores()
        top_opportunities = self._get_top_opportunities(5)
        print("\n🔥 Initial Top Trading Opportunities:")
        for sym, score in top_opportunities:
            print(f"  {sym}: Score {score}/100")

        if not self.single_coin_mode:
            best_coin = self._get_best_opportunity()
            if best_coin:
                print(f"\n🎯 Selected {best_coin} as initial trading target")
                await self._switch_active_coin(best_coin)
        else:
            print(f"\n🎯 Trading single coin: {self.active_symbol}")

        # Create and run loops
        self._tasks = [
            asyncio.create_task(self._analysis_loop()),
            asyncio.create_task(self._trading_loop())
        ]

        print("\n✅ Trading bot is now active")
        print(f"💪 Strategy: {'SINGLE-COIN FOCUS' if self.single_coin_mode else 'AGGRESSIVE MULTI-COIN'}")
        self._print_portfolio_status()

    async def stop(self) -> None:
        """Cleanly stop the bot and close connections."""
        if not self.is_running:
            return
        print("🛑 Stopping trading bot...")
        self._stop_event.set()

        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)

        await self.client.close()
        self.is_running = False

        print("\n⏹️ Trading bot stopped")
        self._print_summary()

    async def _analysis_loop(self) -> None:
        """Periodic analysis for multi-coin mode (every 5 minutes)."""
        while not self._stop_event.is_set():
            try:
                if self.single_coin_mode:
                    await asyncio.sleep(300)
                    continue

                self._calculate_opportunity_scores()
                top_opportunities = self._get_top_opportunities(3)
                if top_opportunities:
                    print("\n📊 MARKET ANALYSIS UPDATE 📊")
                    print("Top Trading Opportunities:")
                    for sym, score in top_opportunities:
                        print(f"  {sym}: Score {score}/100")

                    if self.active_symbol:
                        better_coin = self._should_change_coin()
                        if better_coin and better_coin != self.active_symbol:
                            print(f"\n🔄 Switching target from {self.active_symbol} to {better_coin}")
                            await self._switch_active_coin(better_coin)
                    else:
                        best_coin = self._get_best_opportunity()
                        if best_coin:
                            print(f"\n🎯 Selecting {best_coin} for trading")
                            await self._switch_active_coin(best_coin)

                self._print_portfolio_status()
                await asyncio.sleep(300)  # 5 minutes

            except Exception as e:
                print(f"❌ Error in market analysis: {e}")
                await asyncio.sleep(60)

    async def _trading_loop(self) -> None:
        """Check signals and trade continuously (every second)."""
        while not self._stop_event.is_set():
            try:
                if self.active_symbol and self.allocated_balances.get(self.active_symbol, Decimal('0')) > 0:
                    price = self.client.get_latest_price(self.active_symbol)
                    if not price or price <= 0:
                        await asyncio.sleep(1)
                        continue

                    signal = self._generate_trading_signal(self.active_symbol)
                    if signal == 1:  # Buy
                        if self._execute_buy(self.active_symbol, price):
                            self._print_portfolio_status()
                    elif signal == -1:  # Sell
                        if self._execute_sell(self.active_symbol, price):
                            self._print_portfolio_status()

                await asyncio.sleep(1)

            except Exception as e:
                print(f"❌ Error in trading execution: {e}")
                await asyncio.sleep(5)

    def _calculate_opportunity_scores(self) -> Dict[str, int]:
        """Calculate and store opportunity scores for all symbols."""
        for symbol, data in self.coin_data.items():
            if len(data['prices']) < 10:
                self.opportunity_scores[symbol] = 50
                continue

            prices = np.array(data['prices'])
            volumes = np.array(data['volumes'])

            try:
                score = self._calculate_coin_score(symbol, prices, volumes)
            except Exception as e:
                print(f"Error calculating score for {symbol}: {e}")
                score = 50

            self.opportunity_scores[symbol] = score

        return self.opportunity_scores

    def _calculate_coin_score(self, symbol: str, prices: np.ndarray, volumes: np.ndarray) -> int:
        """Compute a simple integer score (0-100) based on recent price and volume action."""
        score = 50  # start neutral

        # Recent price change
        if len(prices) >= 2:
            recent_change = (prices[-1] / prices[-2] - 1) * 100
            if recent_change > 1:
                score += recent_change * 2
            elif recent_change < -1:
                score -= abs(recent_change)

        # RSI
        rsi = self._calculate_rsi(prices)
        if rsi < 30:
            score += (30 - rsi) * 1.5
        elif rsi > 70:
            score -= (rsi - 70) * 1.5

        # Short and long MAs
        if len(prices) >= 6:
            short_ma = np.mean(prices[-3:])
            long_ma = np.mean(prices[-6:])
            if short_ma > long_ma:
                trend_strength = (short_ma / long_ma - 1) * 100
                score += 10 + trend_strength
            else:
                trend_weakness = (1 - short_ma / long_ma) * 100
                score -= 10 + trend_weakness

        # Volume spike
        if len(volumes) >= 3:
            avg_volume = np.mean(volumes[-4:-1])
            current_volume = volumes[-1]
            if avg_volume > 0 and current_volume > avg_volume * 1.5:
                volume_increase = (current_volume / avg_volume - 1) * 10
                score += 10 + volume_increase

        return max(0, min(100, int(score)))

    def _calculate_rsi(self, prices: np.ndarray, period: int = 14) -> float:
        """Calculate RSI over the given period."""
        if len(prices) < period + 1:
            return 50

        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)

        avg_gain = np.mean(gains[:period])
        avg_loss = np.mean(losses[:period])
        if avg_loss == 0:
            return 100

        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    def _get_top_opportunities(self, top_n: int = 3) -> List:
        """Return a sorted list of the highest scoring symbols."""
        return sorted(self.opportunity_scores.items(), key=lambda x: x[1], reverse=True)[:top_n]

    def _get_best_opportunity(self) -> Optional[str]:
        """Return the single best coin according to current scores."""
        top = self._get_top_opportunities(1)
        return top[0][0] if top else None

    def _should_change_coin(self) -> Optional[str]:
        """Check whether a different coin's score is sufficiently higher than the current."""
        if not self.active_symbol or self.active_symbol not in self.opportunity_scores:
            return self._get_best_opportunity()

        best_coin = self._get_best_opportunity()
        if not best_coin:
            return None

        current_score = self.opportunity_scores[self.active_symbol]
        best_score = self.opportunity_scores[best_coin]
        if best_coin != self.active_symbol and best_score > current_score + 10:
            return best_coin
        return None

    async def _switch_active_coin(self, new_symbol: str) -> None:
        """Switch all trading operations to a new symbol, liquidating old positions."""
        if new_symbol not in self.symbols:
            print(f"Cannot switch to {new_symbol}: not monitored")
            return

        # Sell out of old symbol
        if self.active_symbol:
            if self.active_symbol in self.positions and self.positions[self.active_symbol] > 0:
                price = self.client.get_latest_price(self.active_symbol)
                if price:
                    self._execute_sell(self.active_symbol, price, self.positions[self.active_symbol])
                else:
                    print(f"⚠️ No price for {self.active_symbol}; positions not liquidated")

            self.available_balance += self.allocated_balances[self.active_symbol]
            self.allocated_balances[self.active_symbol] = Decimal('0')

        old_symbol = self.active_symbol
        self.active_symbol = new_symbol

        # Allocate 80% of available balance to new symbol
        allocation = self.available_balance * Decimal('0.8')
        self.allocated_balances[new_symbol] = allocation
        self.available_balance -= allocation

        print(f"🔄 SWITCHED from {old_symbol or 'none'} to {new_symbol}")
        print(f"💰 Allocated {allocation:.2f} USDT to {new_symbol}")

    def _generate_trading_signal(self, symbol: str) -> int:
        """Generate a buy (1), sell (-1), or hold (0) signal."""
        data = self.coin_data.get(symbol)
        if not data or len(data['prices']) < 14:
            return 0

        prices = np.array(data['prices'])
        rsi = self._calculate_rsi(prices)

        if len(prices) >= 10:
            short_ma = np.mean(prices[-3:])
            long_ma = np.mean(prices[-8:])

            # Buy conditions
            if rsi < 35 or (short_ma > long_ma and rsi < 65):
                if symbol not in self.positions or self.positions[symbol] == 0:
                    return 1

            # Sell conditions
            if rsi > 65 or (short_ma < long_ma and rsi > 35):
                if symbol in self.positions and self.positions[symbol] > 0:
                    return -1

        return 0

    def _execute_buy(self, symbol: str, price: Decimal, volume: Optional[Decimal] = None) -> bool:
        """Perform a buy order using allocated balance."""
        if price <= 0:
            print(f"Invalid price for {symbol}: {price}")
            return False

        bal = self.allocated_balances.get(symbol, Decimal('0'))
        if bal <= 0:
            print(f"No balance allocated for {symbol}")
            return False

        # Use up to 95% of allocated balance if volume not specified
        if volume is None:
            position_value = bal * Decimal('0.95')
            volume = position_value / price

        if volume < Decimal('0.0001'):
            print(f"Volume too small for {symbol}: {volume}")
            return False

        cost = price * volume
        if cost > bal:
            volume = bal / price
            cost = price * volume

        self.allocated_balances[symbol] -= cost
        self.positions[symbol] = self.positions.get(symbol, Decimal('0')) + volume

        details = {
            "timestamp": int(time.time()),
            "action": "buy",
            "symbol": symbol,
            "price": float(price),
            "volume": float(volume),
            "cost": float(cost),
            "balance_after": float(self.allocated_balances[symbol])
        }
        self.execution_history[symbol].append(details)
        self.total_trades += 1

        print(f"🔵 BOUGHT {volume:.6f} {symbol} at {price} USDT (Total: {cost:.2f} USDT)")
        return True

    def _execute_sell(self, symbol: str, price: Decimal, volume: Optional[Decimal] = None) -> bool:
        """Perform a sell order of either specified or all current position."""
        if price <= 0:
            print(f"Invalid price for {symbol}: {price}")
            return False

        if symbol not in self.positions or self.positions[symbol] <= 0:
            print(f"No position to sell for {symbol}")
            return False

        if volume is None or volume > self.positions[symbol]:
            volume = self.positions[symbol]

        revenue = price * volume
        self.allocated_balances[symbol] += revenue
        self.positions[symbol] -= volume
        if self.positions[symbol] == 0:
            del self.positions[symbol]

        details = {
            "timestamp": int(time.time()),
            "action": "sell",
            "symbol": symbol,
            "price": float(price),
            "volume": float(volume),
            "revenue": float(revenue),
            "balance_after": float(self.allocated_balances[symbol])
        }
        self.execution_history[symbol].append(details)
        self.total_trades += 1

        avg_buy_price = self._get_average_buy_price(symbol)
        if avg_buy_price:
            profit = volume * (price - avg_buy_price)
            profit_percent = (price / avg_buy_price - 1) * 100
            if price > avg_buy_price:
                self.profitable_trades += 1
                self.total_profit_loss += profit
                print(
                    f"🟢 SOLD {volume:.6f} {symbol} at {price} USDT "
                    f"- PROFIT: {profit:.2f} USDT (+{profit_percent:.2f}%)"
                )
            else:
                self.total_profit_loss += profit
                print(
                    f"🔴 SOLD {volume:.6f} {symbol} at {price} USDT "
                    f"- LOSS: {profit:.2f} USDT ({profit_percent:.2f}%)"
                )
        else:
            print(f"🟡 SOLD {volume:.6f} {symbol} at {price} USDT (Total: {revenue:.2f} USDT)")
        return True

    def _get_average_buy_price(self, symbol: str) -> Optional[Decimal]:
        """Compute the average buy price for a symbol from recorded trades."""
        buy_trades = [t for t in self.execution_history.get(symbol, []) if t['action'] == 'buy']
        if not buy_trades:
            return None

        total_cost = sum(t['cost'] for t in buy_trades)
        total_volume = sum(t['volume'] for t in buy_trades)
        if total_volume == 0:
            return None

        return Decimal(str(total_cost)) / Decimal(str(total_volume))

    def _calculate_total_portfolio_value(self) -> Decimal:
        """Sum up all cash + allocated balances + open positions."""
        total_value = self.available_balance
        for sym, bal in self.allocated_balances.items():
            total_value += bal
        for sym, vol in self.positions.items():
            price = self.client.get_latest_price(sym)
            if price:
                total_value += vol * price
        return total_value

    def _elapsed_time_str(self) -> str:
        """Return elapsed time since start in Xh Ym Zs format or 'N/A'."""
        if not self.start_time:
            return "N/A"
        elapsed = int(time.time()) - self.start_time
        h = elapsed // 3600
        m = (elapsed % 3600) // 60
        s = elapsed % 60
        return f"{h}h {m}m {s}s"

    def _print_portfolio_status(self) -> None:
        """Print current time, active symbol, open positions, and P/L."""
        portfolio_value = self._calculate_total_portfolio_value()
        profit = portfolio_value - self.initial_balance
        profit_percent = (profit / self.initial_balance * 100) if self.initial_balance > 0 else Decimal('0')

        print("\n📈 PORTFOLIO STATUS 📈")
        print(f"⏱️ Session Duration: {self._elapsed_time_str()}")
        print(f"🎯 Active Symbol: {self.active_symbol or 'None'}")
        print(f"💵 Available Balance: {self.available_balance:.2f} USDT")

        if self.positions:
            print("\n📊 Active Positions:")
            for sym, vol in self.positions.items():
                price = self.client.get_latest_price(sym) or Decimal('0')
                value = vol * price
                avg_buy = self._get_average_buy_price(sym)
                if avg_buy:
                    pos_pl_percent = ((price / avg_buy) - 1) * 100 if avg_buy else Decimal('0')
                    indicator = "🟢" if pos_pl_percent > 0 else "🔴"
                    print(f"  {indicator} {sym}: {vol:.6f} @ avg {avg_buy:.4f} "
                          f"(Current: {price:.4f}, P/L: {pos_pl_percent:.2f}%, Value: {value:.2f} USDT)")
                else:
                    print(f"  {sym}: {vol:.6f} (Value: {value:.2f} USDT)")

        print(f"\n💰 Total Portfolio Value: {portfolio_value:.2f} USDT")
        if profit > 0:
            print(f"📊 Profit/Loss: 🟢 +{profit:.2f} USDT (+{profit_percent:.2f}%)")
        elif profit < 0:
            print(f"📊 Profit/Loss: 🔴 {profit:.2f} USDT ({profit_percent:.2f}%)")
        else:
            print(f"📊 Profit/Loss: {profit:.2f} USDT ({profit_percent:.2f}%)")

        if self.total_trades > 0:
            win_rate = (self.profitable_trades / self.total_trades) * 100
            print(f"🔄 Trades: {self.total_trades} (Win Rate: {win_rate:.2f}%)")
        else:
            print("🔄 Trades: 0")

        print("-" * 40)

    def _print_summary(self) -> None:
        """Print a final summary of the session."""
        portfolio_value = self._calculate_total_portfolio_value()
        profit = portfolio_value - self.initial_balance
        profit_percent = (profit / self.initial_balance * 100) if self.initial_balance > 0 else Decimal('0')

        print("\n" + "=" * 50)
        print("               TRADING SESSION SUMMARY               ")
        print("=" * 50)
        print(f"\n⏱️ Session Duration: {self._elapsed_time_str()}")
        print(f"🤖 Trading Mode: {'Single-coin' if self.single_coin_mode else 'Multi-coin'}")
        print(f"👀 Coins Monitored: {len(self.symbols)}")
        print(f"\n💰 Initial Portfolio: {self.initial_balance:.2f} USDT")
        print(f"💰 Final Portfolio: {portfolio_value:.2f} USDT")

        if profit > 0:
            print(f"📊 Total Profit/Loss: 🟢 +{profit:.2f} USDT (+{profit_percent:.2f}%)")
        elif profit < 0:
            print(f"📊 Total Profit/Loss: 🔴 {profit:.2f} USDT ({profit_percent:.2f}%)")
        else:
            print(f"📊 Total Profit/Loss: {profit:.2f} USDT ({profit_percent:.2f}%)")

        print(f"\n🔄 Total Trades: {self.total_trades}")
        if self.total_trades > 0:
            win_rate = (self.profitable_trades / self.total_trades) * 100
            print(f"✅ Profitable Trades: {self.profitable_trades} ({win_rate:.2f}%)")

        if self.positions:
            print("\n📊 Remaining Positions:")
            for sym, vol in self.positions.items():
                price = self.client.get_latest_price(sym) or Decimal('0')
                val = vol * price
                print(f"  {sym}: {vol:.6f} (Value: {val:.2f} USDT)")

        print("\n" + "=" * 50)
