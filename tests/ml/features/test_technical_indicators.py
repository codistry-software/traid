"""Tests for technical indicators calculations."""
import pytest
import numpy as np
from traid.ml.features.technical_indicators import (
    TechnicalIndicators,
    RSIParameters,
    MACDParameters
)


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

def test_macd_input_validation():
    """Test MACD input validation."""
    with pytest.raises(ValueError, match="Price array cannot be empty"):
        TechnicalIndicators.calculate_macd(np.array([]))

    with pytest.raises(ValueError, match="Price array contains NaN"):
        TechnicalIndicators.calculate_macd(np.array([1, np.nan, 3]))


def test_macd_parameter_validation():
    """Test MACD parameter validation."""
    prices = np.array([1, 2, 3])

    with pytest.raises(ValueError, match="All periods must be positive"):
        params = MACDParameters(fast_period=0)
        TechnicalIndicators.calculate_macd(prices, params)

    with pytest.raises(ValueError, match="Fast period must be less than slow period"):
        params = MACDParameters(fast_period=26, slow_period=12)
        TechnicalIndicators.calculate_macd(prices, params)


def test_macd_basic_calculation(trend_prices):
    """Test basic MACD calculation properties."""
    params = MACDParameters(
        fast_period=3,  # Using smaller periods for testing
        slow_period=6,
        signal_period=2
    )

    macd_line, signal_line, histogram = TechnicalIndicators.calculate_macd(
        trend_prices, params
    )

    # Test output lengths
    assert len(macd_line) == len(trend_prices), "MACD line length should match input"
    assert len(signal_line) == len(trend_prices), "Signal line length should match input"
    assert len(histogram) == len(trend_prices), "Histogram length should match input"

    # Verify histogram calculation
    expected_histogram = macd_line - signal_line
    np.testing.assert_array_almost_equal(
        histogram, expected_histogram,
        decimal=8,
        err_msg="Histogram should be MACD line minus signal line"
    )