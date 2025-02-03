"""Technical indicators for trading analysis."""
from dataclasses import dataclass
from typing import Optional
import numpy as np

@dataclass
class RSIParameters:
    """Parameters for RSI calculation.

    Attributes:
        period: Length of lookback period
        min_periods: Minimum periods required for calculation
    """
    period: int = 14
    min_periods: Optional[int] = None

    def __post_init__(self):
        """Validate parameters after initialization."""
        if self.period <= 0:
            raise ValueError("Period must be positive")
        if self.min_periods is None:
            self.min_periods = self.period


@dataclass
class MACDParameters:
    """Parameters for MACD calculation.

    Attributes:
        fast_period: Short-term EMA period
        slow_period: Long-term EMA period
        signal_period: Signal line EMA period
    """
    fast_period: int = 12
    slow_period: int = 26
    signal_period: int = 9

    def __post_init__(self):
        """Validate parameters after initialization."""
        if self.fast_period <= 0 or self.slow_period <= 0 or self.signal_period <= 0:
            raise ValueError("All periods must be positive")
        if self.fast_period >= self.slow_period:
            raise ValueError("Fast period must be less than slow period")


class TechnicalIndicators:
    """Calculate technical indicators for trading analysis."""

    @staticmethod
    def calculate_rsi(
        prices: np.ndarray,
        params: Optional[RSIParameters] = None
    ) -> np.ndarray:
        """Calculate Relative Strength Index.

        Args:
            prices: Array of price values
            params: RSI calculation parameters

        Returns:
            Array of RSI values corresponding to input prices.
            Values before warmup period are set to 0.

        Raises:
            ValueError: If prices array is empty or contains invalid values
        """
        if len(prices) == 0:
            raise ValueError("Price array cannot be empty")

        if np.any(np.isnan(prices)):
            raise ValueError("Price array contains NaN values")

        params = params or RSIParameters()

        # Initialize output array
        rsi = np.zeros_like(prices, dtype=np.float64)

        # Calculate price changes
        changes = np.diff(prices)
        gains = np.zeros_like(prices)
        losses = np.zeros_like(prices)

        # Separate gains and losses
        gains[1:] = np.where(changes > 0, changes, 0)
        losses[1:] = np.where(changes < 0, -changes, 0)

        # Calculate RSI using EMA of gains and losses
        for i in range(params.period, len(prices)):
            avg_gain = np.mean(gains[i-params.period+1:i+1])
            avg_loss = np.mean(losses[i-params.period+1:i+1])

            if avg_loss == 0:
                rsi[i] = 100
            else:
                rs = avg_gain / avg_loss
                rsi[i] = 100 - (100 / (1 + rs))

        return rsi