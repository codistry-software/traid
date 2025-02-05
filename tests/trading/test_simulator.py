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


def test_simulator_buy(simulator, initial_balance):
    """Test basic buy operation."""
    symbol = "BTC/USD"
    price = Decimal("30000")
    volume = Decimal("0.1")

    # Execute buy
    success = simulator.execute_buy(symbol, price, volume)

    # Verify success
    assert success is True
    assert simulator.positions[symbol] == volume
    assert simulator.balance.available == initial_balance - (price * volume)
    assert len(simulator.trades_history) == 1

    # Verify trade record
    trade = simulator.trades_history[0]
    assert trade["symbol"] == symbol
    assert trade["side"] == "buy"
    assert trade["price"] == price
    assert trade["volume"] == volume


def test_simulator_sell(simulator, initial_balance):
    """Test basic sell operation."""
    symbol = "BTC/USD"
    buy_price = Decimal("30000")
    sell_price = Decimal("31000")
    volume = Decimal("0.1")

    # First buy some crypto
    simulator.execute_buy(symbol, buy_price, volume)
    initial_balance_after_buy = simulator.balance.available

    # Execute sell
    success = simulator.execute_sell(symbol, sell_price, volume)

    # Verify success
    assert success is True
    assert symbol not in simulator.positions or simulator.positions[symbol] == Decimal("0")
    assert simulator.balance.available == initial_balance_after_buy + (sell_price * volume)
    assert len(simulator.trades_history) == 2

    # Verify trade record
    trade = simulator.trades_history[-1]
    assert trade["symbol"] == symbol
    assert trade["side"] == "sell"
    assert trade["price"] == sell_price
    assert trade["volume"] == volume