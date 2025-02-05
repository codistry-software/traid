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


def test_balance_negative_validation():
    """Test balance validation rejects negative values."""
    with pytest.raises(ValueError, match="Initial balance must be positive"):
        Balance(Decimal("-100"))


def test_balance_operations(balance):
    """Test balance increase and decrease operations."""
    initial = balance.available

    # Test increase
    balance.increase(Decimal("500"))
    assert balance.available == initial + Decimal("500")

    # Test decrease
    assert balance.decrease(Decimal("200")) is True
    assert balance.available == initial + Decimal("300")

    # Test insufficient funds
    assert balance.decrease(Decimal("2000")) is False
    assert balance.available == initial + Decimal("300")


def test_balance_pnl(balance, initial_balance):
    """Test profit/loss calculation."""
    # No trades yet
    assert balance.pnl == Decimal("0")

    # After profitable trades
    balance.increase(Decimal("500"))
    assert balance.pnl == Decimal("500")

    # After losses
    balance.decrease(Decimal("300"))
    assert balance.pnl == Decimal("200")


def test_operation_amount_validation(balance):
    """Test validation of operation amounts."""
    with pytest.raises(ValueError, match="Amount must be positive"):
        balance.increase(Decimal("-100"))

    with pytest.raises(ValueError, match="Amount must be positive"):
        balance.decrease(Decimal("-50"))

    with pytest.raises(ValueError, match="Amount must be positive"):
        balance.increase(Decimal("0"))

    with pytest.raises(ValueError, match="Amount must be positive"):
        balance.decrease(Decimal("0"))