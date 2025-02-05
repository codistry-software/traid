"""Test trading simulator functionality."""
from decimal import Decimal
import pytest
from traid.trading.simulator import TradingSimulator
from traid.portfolio.balance import Balance

@pytest.fixture
def initial_balance() -> Decimal:
    """Provide test initial balance."""
    return Decimal("10000")

@pytest.fixture
def simulator(initial_balance) -> TradingSimulator:
    """Provide test simulator instance."""
    return TradingSimulator(initial_balance)

def test_simulator_initialization(simulator, initial_balance):
    """Test simulator creation and initial state."""
    assert isinstance(simulator.balance, Balance)
    assert simulator.balance.available == initial_balance
    assert len(simulator.positions) == 0
    assert len(simulator.trades_history) == 0