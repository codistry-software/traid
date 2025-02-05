from dataclasses import dataclass
from typing import Optional, List
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
    max_consecutive_trades: int = 2
    volatility_threshold: float = 0.1  # 10% price change


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
        self.max_consecutive_trades = params.get('max_consecutive_trades', 2)
        self.volatility_threshold = params.get('volatility_threshold', 0.1)
        self.previous_signals: List[int] = []

    def generate_signals(self, prices: np.ndarray) -> np.ndarray:
        """Generate trading signals from price data."""
        # Calculate indicators
        rsi = TechnicalIndicators.calculate_rsi(prices, self.rsi_params)
        macd_line, signal_line, _ = TechnicalIndicators.calculate_macd(
            prices, self.macd_params
        )
        upper, middle, lower = TechnicalIndicators.calculate_bollinger_bands(
            prices, self.bb_params
        )

        signals = np.zeros(len(prices))
        self.previous_signals = []  # Reset for new data

        # Calculate volatility
        returns = np.diff(prices) / prices[:-1]
        volatility = np.zeros_like(prices)
        volatility[1:] = np.abs(returns)

        # Generate signals after warmup period
        warmup = max(self.rsi_params.period, self.macd_params.slow_period,
                    self.bb_params.period)

        for i in range(warmup, len(prices)):
            if self._should_skip_trade(volatility[i], signals[max(0, i-3):i]):
                signals[i] = 0
                continue

            if self._is_buy_signal(prices[i], rsi[i], macd_line[i],
                                 signal_line[i], lower[i]):
                signals[i] = 1
            elif self._is_sell_signal(prices[i], rsi[i], macd_line[i],
                                    signal_line[i], upper[i]):
                signals[i] = -1

            self.previous_signals.append(int(signals[i]))

        return signals

    def _should_skip_trade(self, current_volatility: float,
                          recent_signals: np.ndarray) -> bool:
        """Determine if we should skip trading based on conditions."""
        # Skip if volatility is too high
        if current_volatility > self.volatility_threshold:
            return True

        # Skip if we have too many consecutive trades
        if len(recent_signals) >= self.max_consecutive_trades:
            consecutive_trades = np.sum(recent_signals != 0)
            if consecutive_trades >= self.max_consecutive_trades:
                return True

        return False

    def _is_buy_signal(self, price: float, rsi: float, macd: float,
                       signal: float, bb_lower: float) -> bool:
        """Check if current indicators suggest a buy signal."""
        momentum = (price - bb_lower) / bb_lower
        macd_trend = macd - signal

        print(f"\nBuy Debug - RSI: {rsi:.2f}, MACD trend: {macd_trend:.2f}, Momentum: {momentum:.2f}")

        return (
                (macd > signal or
                 (rsi < 30 and momentum > 0)) and
                momentum > -0.1
        )

    def _is_sell_signal(self, price: float, rsi: float, macd: float,
                        signal: float, bb_upper: float) -> bool:
        """Check if current indicators suggest a sell signal."""
        momentum = (bb_upper - price) / price
        macd_trend = signal - macd

        print(f"\nSell Debug - RSI: {rsi:.2f}, MACD trend: {macd_trend:.2f}, Momentum: {momentum:.2f}")

        return (
                (macd < signal or
                 (rsi > 70 and momentum < 0)) and
                momentum > -0.1
        )