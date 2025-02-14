"""Trading execution coordinator."""
from decimal import Decimal
from typing import Dict, Any
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
        self._last_execution_time = 0

    def execute_cycle(self) -> Dict[str, Any]:
        """Execute one complete trading cycle.

        Returns:
            Dict containing execution results:
                - timestamp: Execution timestamp
                - action: Trading action taken ('buy', 'sell', or 'hold')
                - balance: Current balance
                - portfolio_value: Total portfolio value
        """
        try:
            # Get latest market data
            ohlcv_data = self.market_data.get_ohlcv()
            if not ohlcv_data:
                return self._create_cycle_result('hold', "No market data available")

            # Convert to numpy array for technical analysis
            prices = np.array([candle['close'] for candle in ohlcv_data])

            # Generate trading signals
            signals = self.strategy.generate_signals(prices)

            # Get latest signal
            current_signal = signals[-1]
            latest_price = Decimal(str(prices[-1]))

            # Update market price in simulator
            self.simulator.update_market_price(self.symbol, latest_price)

            # Execute trade based on signal
            action = 'hold'
            if current_signal == 1:  # Buy signal
                volume = self._calculate_position_size(latest_price)
                if self.simulator.execute_buy(self.symbol, latest_price, volume):
                    action = 'buy'
            elif current_signal == -1:  # Sell signal
                current_position = self.simulator.positions.get(self.symbol, Decimal("0"))
                if current_position > 0:
                    if self.simulator.execute_sell(self.symbol, latest_price, current_position):
                        action = 'sell'

            return self._create_cycle_result(action)

        except Exception as e:
            return self._create_cycle_result('hold', str(e))

    def _calculate_position_size(self, price: Decimal) -> Decimal:
        """Calculate appropriate position size based on current balance.

        Args:
            price: Current market price

        Returns:
            Position size to trade
        """
        # Simple position sizing: use 10% of available balance
        position_value = self.simulator.balance.available * Decimal("0.1")
        return position_value / price

    def _create_cycle_result(self, action: str, error: str = None) -> Dict[str, Any]:
        """Create standardized cycle execution result.

        Args:
            action: Trading action taken
            error: Error message if any

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
            "portfolio_value": float(portfolio_value)
        }

        if error:
            result["error"] = error

        return result