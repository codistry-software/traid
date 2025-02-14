"""Tests for main trading bot runner."""
import pytest
from decimal import Decimal
from traid.runner import TradingBotRunner
from traid.trading.execution import TradingExecutor


@pytest.fixture
def runner():
    """Create trading bot runner with test configuration."""
    return TradingBotRunner(
        symbol="BTC/USDT",
        timeframe="1h",
        initial_balance=Decimal("10000"),
        update_interval=60  # 1 minute for testing
    )


def test_runner_initialization(runner):
    """Test runner initialization."""
    assert isinstance(runner.executor, TradingExecutor)
    assert runner.update_interval == 60
    assert runner.is_running is False


def test_start_stop(runner, mocker):
    """Test bot start and stop functionality."""
    # Mock execute_cycle to avoid actual execution
    mocker.patch.object(runner.executor, 'execute_cycle', return_value={
        'timestamp': 1000,
        'action': 'hold',
        'balance': 10000,
        'portfolio_value': 10000
    })

    # Mock sleep to avoid waiting
    mocker.patch('time.sleep')

    # Start bot in separate thread
    runner.start()
    assert runner.is_running is True

    # Stop bot
    runner.stop()
    assert runner.is_running is False


def test_execution_results_logging(runner, mocker):
    """Test that execution results are properly logged."""
    mock_result = {
        'timestamp': 1000,
        'action': 'buy',
        'balance': 9000,
        'portfolio_value': 10000
    }
    mocker.patch.object(runner.executor, 'execute_cycle', return_value=mock_result)
    mocker.patch('time.sleep')

    # Start bot and let it run one cycle
    runner.start()
    runner.stop()

    # Verify results were logged
    assert len(runner.execution_history) > 0
    last_result = runner.execution_history[-1]
    assert last_result['action'] == 'buy'
    assert last_result['balance'] == 9000