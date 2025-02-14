"""Tests for trading execution coordinator."""
import pytest
from decimal import Decimal
import numpy as np
import time
from traid.trading.execution import TradingExecutor
from traid.ml.strategies.base_strategy import TradingStrategy
from traid.trading.simulator import TradingSimulator
from traid.data.handlers.market_data import MarketData


@pytest.fixture
def executor():
    """Create trading executor with test configuration."""
    return TradingExecutor(
        symbol="BTC/USDT",
        timeframe="1h",
        initial_balance=Decimal("10000")
    )


def test_executor_initialization(executor):
    """Test executor initialization."""
    assert executor.symbol == "BTC/USDT"
    assert executor.timeframe == "1h"
    assert isinstance(executor.strategy, TradingStrategy)
    assert isinstance(executor.simulator, TradingSimulator)
    assert isinstance(executor.market_data, MarketData)


def test_execute_trading_cycle(executor, mocker):
    """Test single trading cycle execution."""
    # Mock market data
    current_time = int(time.time())
    mock_data = [
        {'timestamp': current_time - 3600, 'open': 100, 'high': 101, 'low': 99, 'close': 100, 'volume': 1000},
        {'timestamp': current_time, 'open': 101, 'high': 102, 'low': 100, 'close': 101, 'volume': 1100}
    ]
    mocker.patch.object(executor.market_data, 'get_ohlcv', return_value=mock_data)

    result = executor.execute_cycle()

    assert isinstance(result, dict)
    assert 'timestamp' in result
    assert 'action' in result
    assert 'balance' in result
    assert 'portfolio_value' in result


def test_trade_execution_success(executor, mocker):
    """Test successful trade execution and tracking."""
    # Mock market data with proper timestamps
    current_time = int(time.time())
    mock_data = [
        {'timestamp': current_time - 3600, 'open': 100, 'high': 101, 'low': 99, 'close': 100, 'volume': 1000},
        {'timestamp': current_time, 'open': 101, 'high': 102, 'low': 100, 'close': 101, 'volume': 1100}
    ]
    mocker.patch.object(executor.market_data, 'get_ohlcv', return_value=mock_data)

    # Mock strategy to return buy signal
    mock_signals = np.array([0, 1])  # Buy signal at last candle
    mocker.patch.object(executor.strategy, 'generate_signals', return_value=mock_signals)

    # Reset executor state
    executor._last_trade_time = 0
    executor._consecutive_trades = 0

    # Execute buy cycle
    result = executor.execute_cycle()

    assert result['action'] == 'buy'
    assert hasattr(executor, 'trades')
    assert len(executor.trades) > 0
    assert 'trade_details' in result
    assert result['trade_details']['price'] == 101


def test_trade_size_calculation(executor):
    """Test position size calculation."""
    price = Decimal("50000")  # BTC at 50k
    size = executor._calculate_position_size(price)

    # Should use 10% of balance (10000 * 0.1 = 1000)
    expected_size = Decimal("1000") / price
    expected_min = Decimal("0.001")  # Minimum position size
    assert size == max(expected_size, expected_min)


def test_portfolio_tracking(executor, mocker):
    """Test portfolio value tracking across trades."""
    initial_value = float(executor.simulator.balance.available)

    # Mock data for price increase with timestamps
    current_time = int(time.time())
    mock_data = [
        {'timestamp': current_time - 3600, 'open': 100, 'high': 101, 'low': 99, 'close': 100, 'volume': 1000},
        {'timestamp': current_time, 'open': 101, 'high': 102, 'low': 100, 'close': 110, 'volume': 1100}
    ]
    mocker.patch.object(executor.market_data, 'get_ohlcv', return_value=mock_data)

    # Mock buy signal
    mocker.patch.object(executor.strategy, 'generate_signals', return_value=np.array([0, 1]))

    # Reset executor state
    executor._last_trade_time = 0
    executor._consecutive_trades = 0

    result = executor.execute_cycle()
    assert float(result['portfolio_value']) >= initial_value


def test_consecutive_trades_limit(executor, mocker):
    """Test consecutive trades limiting."""
    current_time = int(time.time())

    # Execute multiple trades
    for i in range(5):  # Try to execute 5 trades
        mock_data = [
            {'timestamp': current_time + (i * 3600) - 3600, 'close': 100 + i, 'open': 100, 'high': 101, 'low': 99, 'volume': 1000},
            {'timestamp': current_time + (i * 3600), 'close': 101 + i, 'open': 101, 'high': 102, 'low': 100, 'volume': 1100}
        ]
        mocker.patch.object(executor.market_data, 'get_ohlcv', return_value=mock_data)
        mocker.patch.object(executor.strategy, 'generate_signals', return_value=np.array([0, 1]))

        result = executor.execute_cycle()
        if i >= 3:  # After 3 consecutive trades
            assert result['action'] == 'hold'