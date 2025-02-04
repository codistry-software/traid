from decimal import Decimal
import pytest
from traid.portfolio.balance import Balance

@pytest.fixture
def initial_balance() -> Decimal:
    """Provide test initial balance."""
    return Decimal("1000")

@pytest.fixture
def balance(initial_balance) -> Balance:
    """Provide test balance instance."""
    return Balance(initial_balance)

def test_balance_initialization(balance, initial_balance):
    """Test balance creation with valid amount."""
    assert balance.available == initial_balance
    assert balance.initial == initial_balance

def test_balance_negative_validation():
    """Test balance validation rejects negative values."""
    with pytest.raises(ValueError, match="Initial balance must be positive"):
        Balance(Decimal("-100"))