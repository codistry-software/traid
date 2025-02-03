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
