"""Technical indicators for trading analysis."""
from dataclasses import dataclass
from typing import Optional, Tuple
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


@dataclass
class BBParameters:
    """Parameters for Bollinger Bands calculation.

    Attributes:
        period: Moving average period
        num_std: Number of standard deviations for bands
    """
    period: int = 20
    num_std: float = 2.0

    def __post_init__(self):
        """Validate parameters after initialization."""
        if self.period <= 0:
            raise ValueError("Period must be positive")
        if self.num_std <= 0:
            raise ValueError("Number of standard deviations must be positive")


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

    @staticmethod
    def calculate_macd(
            prices: np.ndarray,
            params: Optional[MACDParameters] = None
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Calculate MACD (Moving Average Convergence Divergence).

        Args:
            prices: Array of price values
            params: MACD calculation parameters

        Returns:
            Tuple of (MACD line, Signal line, Histogram)

        Raises:
            ValueError: If prices array is empty or contains invalid values
        """
        if len(prices) == 0:
            raise ValueError("Price array cannot be empty")

        if np.any(np.isnan(prices)):
            raise ValueError("Price array contains NaN values")

        params = params or MACDParameters()

        # Calculate EMAs
        ema_fast = TechnicalIndicators._calculate_ema(prices, params.fast_period)
        ema_slow = TechnicalIndicators._calculate_ema(prices, params.slow_period)

        # Calculate MACD line
        macd_line = ema_fast - ema_slow

        # Calculate signal line
        signal_line = TechnicalIndicators._calculate_ema(macd_line, params.signal_period)

        # Calculate histogram
        histogram = macd_line - signal_line

        return macd_line, signal_line, histogram

    @staticmethod
    def _calculate_ema(data: np.ndarray, period: int) -> np.ndarray:
        """Calculate Exponential Moving Average.

        Args:
            data: Input data array
            period: EMA period

        Returns:
            Array of EMA values
        """
        alpha = 2.0 / (period + 1)
        ema = np.zeros_like(data)
        ema[period - 1] = np.mean(data[:period])

        for i in range(period, len(data)):
            ema[i] = data[i] * alpha + ema[i - 1] * (1 - alpha)

        return ema

    @staticmethod
    def calculate_bollinger_bands(
            prices: np.ndarray,
            params: Optional[BBParameters] = None
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Calculate Bollinger Bands.

        Args:
            prices: Array of price values
            params: Bollinger Bands parameters

        Returns:
            Tuple of (Upper band, Middle band, Lower band)

        Raises:
            ValueError: If prices array is empty or contains invalid values
        """
        if len(prices) == 0:
            raise ValueError("Price array cannot be empty")

        if np.any(np.isnan(prices)):
            raise ValueError("Price array contains NaN values")

        params = params or BBParameters()

        # Calculate middle band (simple moving average)
        middle_band = np.zeros_like(prices)
        for i in range(params.period, len(prices)):
            middle_band[i] = np.mean(prices[i - params.period:i])

        # Calculate standard deviation
        std = np.zeros_like(prices)
        for i in range(params.period, len(prices)):
            std[i] = np.std(prices[i - params.period:i])

        # Calculate upper and lower bands
        upper_band = middle_band + (std * params.num_std)
        lower_band = middle_band - (std * params.num_std)

        return upper_band, middle_band, lower_band