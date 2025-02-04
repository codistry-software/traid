"""Base trading strategy implementation."""
from dataclasses import dataclass
from typing import Optional
import numpy as np

from ..features.technical_indicators import (
    TechnicalIndicators,
    RSIParameters,
    MACDParameters,
    BBParameters
)


@dataclass
class StrategyParameters:
    """Parameters for trading strategy."""
    rsi_params: RSIParameters = RSIParameters(period=5)
    macd_params: MACDParameters = MACDParameters(
        fast_period=3,
        slow_period=6,
        signal_period=2
    )
    bb_params: BBParameters = BBParameters(period=5)


class TradingStrategy:
    """Base trading strategy using technical indicators."""

    def __init__(self, **params):
        """Initialize strategy with parameters."""
        self.rsi_params = params.get('rsi_params', RSIParameters(period=5))
        self.macd_params = params.get('macd_params', MACDParameters(
            fast_period=3,
            slow_period=6,
            signal_period=2
        ))
        self.bb_params = params.get('bb_params', BBParameters(period=5))

    def generate_signals(self, prices: np.ndarray) -> np.ndarray:
        """Generate trading signals from price data.

        Args:
            prices: Array of price values

        Returns:
            Array of signals: 1 (buy), 0 (hold), -1 (sell)
        """
        # Calculate all indicators
        rsi = TechnicalIndicators.calculate_rsi(prices, self.rsi_params)
        macd_line, signal_line, _ = TechnicalIndicators.calculate_macd(
            prices, self.macd_params
        )
        upper, _, lower = TechnicalIndicators.calculate_bollinger_bands(
            prices, self.bb_params
        )

        signals = np.zeros(len(prices))

        # Generate signals after warmup period
        warmup = max(self.rsi_params.period, self.macd_params.slow_period,
                     self.bb_params.period)

        for i in range(warmup, len(prices)):
            if self._is_buy_signal(prices[i], rsi[i], macd_line[i],
                                   signal_line[i], lower[i]):
                signals[i] = 1
            elif self._is_sell_signal(prices[i], rsi[i], macd_line[i],
                                      signal_line[i], upper[i]):
                signals[i] = -1

        return signals

    def _is_buy_signal(self, price: float, rsi: float, macd: float,
                       signal: float, bb_lower: float) -> bool:
        """Check if current indicators suggest a buy signal."""
        return (
                rsi < 30 and  # Oversold
                macd > signal and  # MACD crossover
                price <= bb_lower  # Price at/below lower band
        )

    def _is_sell_signal(self, price: float, rsi: float, macd: float,
                        signal: float, bb_upper: float) -> bool:
        """Check if current indicators suggest a sell signal."""
        return (
                rsi > 70 and  # Overbought
                macd < signal and  # MACD crossunder
                price >= bb_upper  # Price at/above upper band
        )