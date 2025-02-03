"""Tests for technical indicators calculations."""
import pytest
import numpy as np
from traid.ml.features.technical_indicators import TechnicalIndicators, RSIParameters


@pytest.fixture
def uptrend_prices():
    """Generate price data with clear uptrend."""
    return np.array([10, 11, 12, 13, 14, 15, 16, 17, 18, 19])


@pytest.fixture
def downtrend_prices():
    """Generate price data with clear downtrend."""
    return np.array([20, 19, 18, 17, 16, 15, 14, 13, 12, 11])

@pytest.fixture
def trend_prices():
    """Generate price data with clear trend patterns for MACD testing."""
    up = np.array([100, 102, 104, 106, 108, 110])
    sideways = np.array([110, 109, 111, 110, 109, 111])
    down = np.array([109, 107, 105, 103, 101, 99])
    return np.concatenate([up, sideways, down])

def test_rsi_basic_validation():
    """Test RSI input validation."""
    with pytest.raises(ValueError, match="Price array cannot be empty"):
        TechnicalIndicators.calculate_rsi(np.array([]))

    with pytest.raises(ValueError, match="Price array contains NaN"):
        TechnicalIndicators.calculate_rsi(np.array([1, np.nan, 3]))


def test_rsi_period_validation():
    """Test RSI period parameter validation."""
    prices = np.array([1, 2, 3])
    with pytest.raises(ValueError, match="Period must be positive"):
        TechnicalIndicators.calculate_rsi(prices, RSIParameters(period=0))


def test_rsi_trend_detection(uptrend_prices, downtrend_prices):
    """Test RSI calculation with known trends."""
    params = RSIParameters(period=5)

    # Calculate RSI for both trends
    rsi_up = TechnicalIndicators.calculate_rsi(uptrend_prices, params)
    rsi_down = TechnicalIndicators.calculate_rsi(downtrend_prices, params)

    # Check only valid values (after warmup)
    valid_idx = params.period

    # Uptrend should have higher RSI values
    assert np.mean(rsi_up[valid_idx:]) > np.mean(rsi_down[valid_idx:]), \
           "RSI failed to detect trend difference"

    # All values should be in valid range
    assert np.all((rsi_up[valid_idx:] >= 0) & (rsi_up[valid_idx:] <= 100)), \
           "RSI values out of valid range"
