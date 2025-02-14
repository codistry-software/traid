"""Tests for trading execution coordinator."""
import pytest
from decimal import Decimal
import numpy as np
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
    mock_data = [
        {'timestamp': 1000, 'open': 100, 'high': 101, 'low': 99, 'close': 100, 'volume': 1000},
        {'timestamp': 2000, 'open': 101, 'high': 102, 'low': 100, 'close': 101, 'volume': 1100}
    ]
    mocker.patch.object(executor.market_data, 'get_ohlcv', return_value=mock_data)

    result = executor.execute_cycle()

    assert isinstance(result, dict)
    assert 'timestamp' in result
    assert 'action' in result
    assert 'balance' in result
    assert 'portfolio_value' in result
