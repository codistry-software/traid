from decimal import Decimal
from typing import Dict, List
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

    def execute_buy(self, symbol: str, price: Decimal, volume: Decimal) -> bool:
        """Execute a buy order.

        Args:
            symbol: Trading pair symbol (e.g. 'BTC/USD')
            price: Current market price
            volume: Amount to buy

        Returns:
            bool: True if order executed successfully, False otherwise
        """
        cost = price * volume

        # Check if we have enough balance
        if not self.balance.decrease(cost):
            return False

        # Update position
        self.positions[symbol] = self.positions.get(symbol, Decimal("0")) + volume

        # Record trade
        self.trades_history.append({
            "symbol": symbol,
            "side": "buy",
            "price": price,
            "volume": volume,
            "cost": cost
        })

        return True