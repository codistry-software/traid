"""Balance management for trading account."""
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