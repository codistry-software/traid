from decimal import Decimal
from typing import Optional


class Balance:
    """Manages trading account balance.

    Attributes:
        available: Current available balance
        initial: Initial deposit amount
    """

    def __init__(self, initial: Decimal):
        """Initialize balance with initial deposit.

        Args:
            initial: Initial balance amount

        Raises:
            ValueError: If initial balance is not positive
        """
        if initial <= 0:
            raise ValueError("Initial balance must be positive")
        self.available = initial
        self.initial = initial

    def increase(self, amount: Decimal) -> None:
        """Increase available balance.

        Args:
            amount: Amount to add to balance
        """
        self.available += amount

    def decrease(self, amount: Decimal) -> bool:
        """Decrease available balance if sufficient funds.

        Args:
            amount: Amount to subtract from balance

        Returns:
            bool: True if decrease successful, False if insufficient funds
        """
        if amount > self.available:
            return False
        self.available -= amount
        return True

    @property
    def pnl(self) -> Decimal:
        """Calculate current profit/loss.

        Returns:
            Decimal: Current PnL (positive for profit, negative for loss)
        """
        return self.available - self.initial