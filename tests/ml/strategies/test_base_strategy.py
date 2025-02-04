import pytest
import numpy as np
from traid.ml.strategies.base_strategy import TradingStrategy
from traid.ml.features.technical_indicators import (
    RSIParameters,
    MACDParameters,
    BBParameters
)


@pytest.fixture
def sample_prices():
    """Generate sample price data for strategy testing."""
    return np.array([10, 11, 12, 13, 14, 15, 14, 13, 12, 11,
                    10, 9, 8, 7, 6, 7, 8, 9, 10, 11])


@pytest.fixture
def strategy():
    """Create strategy instance with test parameters."""
    return TradingStrategy(
        rsi_params=RSIParameters(period=5),
        macd_params=MACDParameters(fast_period=3, slow_period=6, signal_period=2),
        bb_params=BBParameters(period=5, num_std=2)
    )


@pytest.fixture
def uptrend_prices():
    """Generate uptrend price data."""
    return np.array([10, 12, 15, 17, 20, 25, 30, 35, 40, 45])


@pytest.fixture
def downtrend_prices():
    """Generate downtrend price data."""
    return np.array([50, 45, 40, 35, 30, 25, 20, 15, 12, 10])


@pytest.fixture
def sideways_prices():
    """Generate sideways price data."""
    return np.array([10, 11, 10, 12, 11, 10, 11, 12, 11, 10])


def test_strategy_basic_signals(sample_prices, strategy):
    """Test basic strategy signal generation."""
    signals = strategy.generate_signals(sample_prices)

    assert len(signals) == len(sample_prices), "Signal length should match price data"
    assert all(s in [-1, 0, 1] for s in signals), "Signals should be -1 (sell), 0 (hold), or 1 (buy)"


def test_strategy_uptrend_signals(strategy, uptrend_prices):
    """Test strategy signals in uptrend market."""
    signals = strategy.generate_signals(uptrend_prices)

    valid_signals = signals[5:]
    buy_count = np.sum(valid_signals == 1)
    sell_count = np.sum(valid_signals == -1)

    assert buy_count > sell_count, "Should generate more buy signals in uptrend"


def test_strategy_downtrend_signals(strategy, downtrend_prices):
    """Test strategy signals in downtrend market."""
    signals = strategy.generate_signals(downtrend_prices)

    # After warmup period, should have more sell than buy signals
    valid_signals = signals[5:]  # After warmup
    buy_count = np.sum(valid_signals == 1)
    sell_count = np.sum(valid_signals == -1)

    assert sell_count > buy_count, "Should generate more sell signals in downtrend"

    # Verify we don't have consecutive buy signals in downtrend
    for i in range(len(valid_signals) - 1):
        if valid_signals[i] == 1:
            assert valid_signals[i + 1] != 1, "Should not have consecutive buys in downtrend"


def test_strategy_sideways_signals(strategy, sideways_prices):
    """Test strategy signals in sideways market."""
    signals = strategy.generate_signals(sideways_prices)

    valid_signals = signals[5:]

    hold_count = np.sum(valid_signals == 0)
    action_count = np.sum(valid_signals != 0)

    assert hold_count > action_count, "Should generate more hold signals in sideways market"

    buy_count = np.sum(valid_signals == 1)
    sell_count = np.sum(valid_signals == -1)

    assert abs(buy_count - sell_count) <= 1, "Buy and sell signals should be balanced in sideways market"