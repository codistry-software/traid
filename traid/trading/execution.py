"""Trading execution coordinator."""
from decimal import Decimal
from typing import Dict, Any, List
import time
import numpy as np

from ..ml.strategies.base_strategy import TradingStrategy
from ..trading.simulator import TradingSimulator
from ..data.handlers.market_data import MarketData


class TradingExecutor:
    """Coordinates market data, strategy signals, and trade execution.

    Attributes:
        symbol: Trading pair symbol
        timeframe: Trading timeframe
        strategy: Trading strategy instance
        simulator: Trading simulator instance
        market_data: Market data handler
        trades: List of executed trades
    """

    def __init__(
            self,
            symbol: str,
            timeframe: str,
            initial_balance: Decimal
    ) -> None:
        """Initialize trading executor.

        Args:
            symbol: Trading pair symbol (e.g. 'BTC/USDT')
            timeframe: Candle timeframe (e.g. '1h', '15m')
            initial_balance: Starting balance for simulation
        """
        self.symbol = symbol
        self.timeframe = timeframe
        self.strategy = TradingStrategy()
        self.simulator = TradingSimulator(initial_balance)
        self.market_data = MarketData(symbol, timeframe)
        self.trades: List[Dict] = []
        self._last_execution_time = 0
        self._consecutive_trades = 0
        self._last_trade_time = 0
        self._min_trade_interval = 3600  # Minimum 1 hour between trades

    def execute_cycle(self) -> Dict[str, Any]:
        """Execute one complete trading cycle.

        Returns:
            Dict containing execution results:
                - timestamp: Execution timestamp
                - action: Trading action taken ('buy', 'sell', or 'hold')
                - balance: Current balance
                - portfolio_value: Total portfolio value
                - trade_details: Details of executed trade (if any)
        """
        try:
            # Get latest market data
            ohlcv_data = self.market_data.get_ohlcv()
            if not ohlcv_data:
                return self._create_cycle_result('hold', "No market data available")

            # Convert to numpy array for technical analysis
            prices = np.array([candle['close'] for candle in ohlcv_data])
            timestamps = np.array([candle['timestamp'] for candle in ohlcv_data])

            # Generate trading signals
            signals = self.strategy.generate_signals(prices)

            # Get latest signal and price
            current_signal = signals[-1]
            latest_price = Decimal(str(prices[-1]))
            latest_timestamp = timestamps[-1]

            # Update market price in simulator
            self.simulator.update_market_price(self.symbol, latest_price)

            # Execute trade based on signal
            action = 'hold'
            trade_details = None
            message = None

            if current_signal == 1 and self._can_buy(latest_timestamp):  # Buy signal
                volume = self._calculate_position_size(latest_price)
                if self.simulator.execute_buy(self.symbol, latest_price, volume):
                    action = 'buy'
                    trade_details = self._record_trade('buy', latest_price, volume, latest_timestamp)
                    message = f"Bought {volume} {self.symbol} at {latest_price}"

            elif current_signal == -1 and self._can_sell(latest_timestamp):  # Sell signal
                current_position = self.simulator.positions.get(self.symbol, Decimal("0"))
                if current_position > 0:
                    if self.simulator.execute_sell(self.symbol, latest_price, current_position):
                        action = 'sell'
                        trade_details = self._record_trade('sell', latest_price, current_position, latest_timestamp)
                        message = f"Sold {current_position} {self.symbol} at {latest_price}"

            result = self._create_cycle_result(action, message)
            if trade_details:
                result['trade_details'] = trade_details
                self._update_trade_state(action, latest_timestamp)

            return result

        except Exception as e:
            return self._create_cycle_result('hold', str(e))

    def _can_buy(self, timestamp: int) -> bool:
        """Check if buy conditions are met.

        Args:
            timestamp: Current timestamp

        Returns:
            bool: True if buy conditions are met
        """
        # Calculate total portfolio value currently in positions
        total_position_value = Decimal("0")
        for symbol, volume in self.simulator.positions.items():
            if symbol in self.simulator.current_prices:
                total_position_value += volume * self.simulator.current_prices[symbol]

        # Don't use more than 80% of total available balance
        available_portfolio = self.simulator.balance.available * Decimal("0.8")
        if total_position_value >= available_portfolio:
            return False

        # Maximum 20% of portfolio per position
        position_size = self._calculate_position_size(self.simulator.current_prices[self.symbol])
        max_position_value = self.simulator.balance.available * Decimal("0.2")
        if position_size * self.simulator.current_prices[self.symbol] > max_position_value:
            return False

        return True

    def _can_sell(self, timestamp: int) -> bool:
        """Check if sell conditions are met.

        Args:
            timestamp: Current timestamp

        Returns:
            bool: True if sell conditions are met
        """
        # Can sell if we have a position
        current_position = self.simulator.positions.get(self.symbol, Decimal("0"))
        if current_position <= 0:
            return False

        # Calculate current position value
        position_value = current_position * self.simulator.current_prices[self.symbol]

        # Calculate profit/loss percentage
        buy_trades = [t for t in self.trades if t['type'] == 'buy' and t['symbol'] == self.symbol]
        if not buy_trades:
            return True

        avg_buy_price = sum(Decimal(str(t['price'])) * Decimal(str(t['volume'])) for t in buy_trades) / \
                        sum(Decimal(str(t['volume'])) for t in buy_trades)

        profit_percentage = (self.simulator.current_prices[self.symbol] - avg_buy_price) / avg_buy_price * 100

        # Sell if profit is above 5% or loss is more than 2%
        return profit_percentage >= 5 or profit_percentage <= -2

    def _calculate_position_size(self, price: Decimal) -> Decimal:
        """Calculate appropriate position size based on current balance.

        Args:
            price: Current market price

        Returns:
            Position size to trade
        """
        # Risk-adjusted position sizing: use 10% of available balance
        position_value = self.simulator.balance.available * Decimal("0.1")

        # Add minimum position size check
        min_position = Decimal("0.001")  # Minimum 0.001 BTC
        calculated_position = position_value / price

        return max(calculated_position, min_position)

    def _record_trade(self, trade_type: str, price: Decimal, volume: Decimal, timestamp: int) -> Dict:
        """Record trade details.

        Args:
            trade_type: Type of trade ('buy' or 'sell')
            price: Trade price
            volume: Trade volume
            timestamp: Trade timestamp

        Returns:
            Dict containing trade details
        """
        trade_details = {
            'type': trade_type,
            'price': float(price),
            'volume': float(volume),
            'value': float(price * volume),
            'timestamp': timestamp,
            'balance_after': float(self.simulator.balance.available)
        }
        self.trades.append(trade_details)
        return trade_details

    def _update_trade_state(self, action: str, timestamp: int) -> None:
        """Update trading state after execution.

        Args:
            action: Executed action
            timestamp: Current timestamp
        """
        if action in ['buy', 'sell']:
            self._consecutive_trades += 1
            self._last_trade_time = timestamp
        else:
            self._consecutive_trades = 0

    def _create_cycle_result(self, action: str, message: str = None) -> Dict[str, Any]:
        """Create standardized cycle execution result.

        Args:
            action: Trading action taken
            message: Result message

        Returns:
            Execution result dictionary
        """
        current_time = int(time.time())
        self._last_execution_time = current_time

        portfolio_value = self.simulator.balance.available
        for symbol, volume in self.simulator.positions.items():
            if symbol in self.simulator.current_prices:
                portfolio_value += volume * self.simulator.current_prices[symbol]

        result = {
            "timestamp": current_time,
            "action": action,
            "balance": float(self.simulator.balance.available),
            "portfolio_value": float(portfolio_value),
            "positions": {
                symbol: float(volume)
                for symbol, volume in self.simulator.positions.items()
            }
        }

        if message:
            result["message"] = message

        return result

    def get_trading_stats(self) -> Dict[str, Any]:
        """Calculate trading statistics.

        Returns:
            Dict containing trading statistics
        """
        if not self.trades:
            return {
                "total_trades": 0,
                "successful_trades": 0,
                "win_rate": 0.0,
                "average_profit": 0.0
            }

        successful_trades = 0
        total_profit = Decimal("0")

        for trade in self.trades:
            if trade['type'] == 'sell':
                if trade['value'] > trade['price'] * trade['volume']:
                    successful_trades += 1
                total_profit += Decimal(str(trade['value'])) - Decimal(str(trade['price'])) * Decimal(str(trade['volume']))

        return {
            "total_trades": len(self.trades),
            "successful_trades": successful_trades,
            "win_rate": float(successful_trades) / len(self.trades) if self.trades else 0.0,
            "average_profit": float(total_profit / Decimal(str(len(self.trades)))) if self.trades else 0.0
        }