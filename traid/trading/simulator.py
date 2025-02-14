from decimal import Decimal
from typing import Dict, List
import time
from ..portfolio.balance import Balance


class TradingSimulator:
    """Simulates trading activities with virtual balance.

    Attributes:
        balance: Current account balance
        positions: Dictionary of current positions {symbol: volume}
        trades_history: List of executed trades
    """

    def __init__(self, initial_balance: Decimal):
        """Initialize trading simulator.

        Args:
            initial_balance: Starting balance for paper trading
        """
        self.balance = Balance(initial_balance)
        self.positions: Dict[str, Decimal] = {}
        self.trades_history: List[dict] = []

    def _validate_symbol(self, symbol: str) -> None:
        """Validate trading symbol format.

        Args:
            symbol: Trading pair symbol

        Raises:
            ValueError: If symbol is empty or has invalid format
        """
        if not symbol:
            raise ValueError("Symbol must not be empty")
        if '/' not in symbol:
            raise ValueError("Invalid symbol format")

    def execute_buy(self, symbol: str, price: Decimal, volume: Decimal) -> bool:
        """Execute a buy order."""
        self._validate_symbol(symbol)

        if volume <= 0:
            raise ValueError("Volume must be positive")

        if price <= 0:
            raise ValueError("Price must be positive")

        cost = price * volume

        # Check if we have enough balance
        if not self.balance.decrease(cost):
            return False

        # Update position
        self.positions[symbol] = self.positions.get(symbol, Decimal("0")) + volume

        # Record trade with timestamp
        self.trades_history.append({
            "symbol": symbol,
            "side": "buy",
            "price": price,
            "volume": volume,
            "cost": cost,
            "timestamp": int(time.time())
        })

        return True

    def execute_sell(self, symbol: str, price: Decimal, volume: Decimal) -> bool:
        """Execute a sell order.

        Args:
            symbol: Trading pair symbol (e.g. 'BTC/USD')
            price: Current market price
            volume: Amount to sell

        Returns:
            bool: True if order executed successfully, False otherwise

        Raises:
            ValueError: If volume or price is not positive, or symbol is invalid
        """
        self._validate_symbol(symbol)

        if volume <= 0:
            raise ValueError("Volume must be positive")

        if price <= 0:
            raise ValueError("Price must be positive")

        # Check if we have enough volume to sell
        if symbol not in self.positions or self.positions[symbol] < volume:
            return False

        revenue = price * volume

        # Update balance
        self.balance.increase(revenue)

        # Update position
        self.positions[symbol] -= volume
        if self.positions[symbol] == Decimal("0"):
            del self.positions[symbol]

        # Record trade with timestamp
        self.trades_history.append({
            "symbol": symbol,
            "side": "sell",
            "price": price,
            "volume": volume,
            "revenue": revenue,
            "timestamp": int(time.time())
        })

        return True

    def update_market_price(self, symbol: str, price: Decimal) -> None:
        """Update current market price for a symbol."""
        self._validate_symbol(symbol)
        if price <= 0:
            raise ValueError("Price must be positive")
        if not hasattr(self, 'current_prices'):
            self.current_prices = {}
        self.current_prices[symbol] = price

    def get_position_value(self, symbol: str) -> Decimal:
        """Calculate current value of position."""
        self._validate_symbol(symbol)
        if symbol not in self.positions:
            return Decimal("0")
        if not hasattr(self, 'current_prices') or symbol not in self.current_prices:
            raise ValueError(f"No current price available for {symbol}")
        return self.positions[symbol] * self.current_prices[symbol]

    def get_position_pnl(self, symbol: str) -> Decimal:
        """Calculate unrealized P&L for a position."""
        self._validate_symbol(symbol)
        buy_trades = [trade for trade in self.trades_history
                      if trade["symbol"] == symbol and trade["side"] == "buy"]
        if not buy_trades:
            return Decimal("0")

        avg_price = sum(t["cost"] for t in buy_trades) / sum(t["volume"] for t in buy_trades)
        current_value = self.get_position_value(symbol)
        position_cost = self.positions.get(symbol, Decimal("0")) * avg_price
        return current_value - position_cost

    def get_trading_summary(self) -> Dict:
        """Generate summary of trading activity."""
        total_trades = len(self.trades_history)
        if total_trades == 0:
            return {
                "total_trades": 0,
                "profitable_trades": 0,
                "total_profit_loss": Decimal("0")
            }

        profitable_trades = 0
        total_pnl = Decimal("0")

        for trade in self.trades_history:
            if trade["side"] == "sell":
                profit = trade["revenue"] - trade["price"] * trade["volume"]
                if profit > 0:
                    profitable_trades += 1
                total_pnl += profit

        return {
            "total_trades": total_trades,
            "profitable_trades": profitable_trades,
            "total_profit_loss": total_pnl
        }
