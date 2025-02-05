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