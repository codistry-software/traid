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


def test_sell_without_position(simulator):
    """Test selling without having a position."""
    symbol = "BTC/USD"
    price = Decimal("30000")
    volume = Decimal("0.1")

    # Try to sell without position
    success = simulator.execute_sell(symbol, price, volume)

    assert success is False
    assert len(simulator.trades_history) == 0


def test_sell_more_than_owned(simulator):
    """Test selling more volume than owned."""
    symbol = "BTC/USD"
    price = Decimal("30000")
    buy_volume = Decimal("0.1")
    sell_volume = Decimal("0.2")

    # First buy some crypto
    simulator.execute_buy(symbol, price, buy_volume)
    initial_position = simulator.positions[symbol]
    initial_balance = simulator.balance.available

    # Try to sell more than owned
    success = simulator.execute_sell(symbol, price, sell_volume)

    assert success is False
    assert simulator.positions[symbol] == initial_position
    assert simulator.balance.available == initial_balance
    assert len(simulator.trades_history) == 1


def test_invalid_trade_volumes(simulator):
    """Test validation of trade volumes."""
    symbol = "BTC/USD"
    price = Decimal("30000")

    # Test zero volume
    with pytest.raises(ValueError, match="Volume must be positive"):
        simulator.execute_buy(symbol, price, Decimal("0"))

    with pytest.raises(ValueError, match="Volume must be positive"):
        simulator.execute_sell(symbol, price, Decimal("0"))

    # Test negative volume
    with pytest.raises(ValueError, match="Volume must be positive"):
        simulator.execute_buy(symbol, price, Decimal("-0.1"))

    with pytest.raises(ValueError, match="Volume must be positive"):
        simulator.execute_sell(symbol, price, Decimal("-0.1"))


def test_invalid_trade_prices(simulator):
    """Test validation of trade prices."""
    symbol = "BTC/USD"
    volume = Decimal("0.1")

    # Test zero price
    with pytest.raises(ValueError, match="Price must be positive"):
        simulator.execute_buy(symbol, Decimal("0"), volume)

    with pytest.raises(ValueError, match="Price must be positive"):
        simulator.execute_sell(symbol, Decimal("0"), volume)

    # Test negative price
    with pytest.raises(ValueError, match="Price must be positive"):
        simulator.execute_buy(symbol, Decimal("-100"), volume)

    with pytest.raises(ValueError, match="Price must be positive"):
        simulator.execute_sell(symbol, Decimal("-100"), volume)


def test_invalid_symbols(simulator):
    """Test validation of trading symbols."""
    price = Decimal("30000")
    volume = Decimal("0.1")

    # Test empty symbol
    with pytest.raises(ValueError, match="Symbol must not be empty"):
        simulator.execute_buy("", price, volume)

    with pytest.raises(ValueError, match="Symbol must not be empty"):
        simulator.execute_sell("", price, volume)

    # Test invalid format (must contain '/')
    with pytest.raises(ValueError, match="Invalid symbol format"):
        simulator.execute_buy("BTCUSD", price, volume)

    with pytest.raises(ValueError, match="Invalid symbol format"):
        simulator.execute_sell("BTCUSD", price, volume)


def test_trade_timestamps(simulator):
    """Test that trades are recorded with timestamps."""
    symbol = "BTC/USD"
    price = Decimal("30000")
    volume = Decimal("0.1")

    # Execute buy and sell
    simulator.execute_buy(symbol, price, volume)
    simulator.execute_sell(symbol, price, volume)

    # Verify timestamps
    for trade in simulator.trades_history:
        assert "timestamp" in trade
        assert isinstance(trade["timestamp"], int)
        assert trade["timestamp"] > 0  # Unix timestamp should be positive


def test_get_current_position_value(simulator):
    """Test calculation of current position value."""
    symbol = "BTC/USD"
    price = Decimal("30000")
    volume = Decimal("0.1")

    # Execute buy and update current price
    simulator.execute_buy(symbol, price, volume)
    simulator.update_market_price(symbol, Decimal("31000"))

    position_value = simulator.get_position_value(symbol)
    assert position_value == Decimal("31000") * Decimal("0.1")
