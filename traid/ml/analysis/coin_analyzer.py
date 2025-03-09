"""Coin opportunity analyzer for multi-coin trading."""
from typing import Dict, List, Optional, Tuple
from decimal import Decimal
import numpy as np
import time

from ..features.technical_indicators import TechnicalIndicators


class CoinOpportunityAnalyzer:
    """Analyzes trading opportunities across multiple coins.

    Provides scoring and ranking for different coins based on
    technical indicators and market conditions.
    """

    def __init__(self, lookback_window: int = 20,
                 rsi_oversold: float = 30,
                 rsi_overbought: float = 70,
                 switch_threshold: int = 15,
                 update_interval: int = 60,
                 min_data_points=30,
                 rsi_period=14):
        """Initialize coin opportunity analyzer.

        Args:
            lookback_window: Number of historical data points to analyze
            rsi_oversold: RSI threshold for oversold condition
            rsi_overbought: RSI threshold for overbought condition
            switch_threshold: Score difference required to switch coins
            update_interval: Seconds between score calculations
        """
        self.lookback_window = lookback_window
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought
        self.switch_threshold = switch_threshold
        self.coin_data: Dict[str, Dict] = {}  # Historical data for each coin
        self.opportunity_scores: Dict[str, int] = {}  # Latest scores
        self.last_update_time = 0
        self.update_interval = update_interval
        self.min_data_points = min_data_points
        self.rsi_period = rsi_period
        self.coin_data = {}

    def update_coin_data(self, symbol: str, price: Decimal, volume: Decimal) -> None:
        """Update historical data for a coin.

        Args:
            symbol: Trading pair symbol
            price: Current price
            volume: Current trading volume
        """
        if price <= 0 or volume < 0:
            raise ValueError(f"Invalid price or volume for {symbol}: price={price}, volume={volume}")

        timestamp = int(time.time())

        if symbol not in self.coin_data:
            self.coin_data[symbol] = {
                'prices': [],
                'volumes': [],
                'timestamps': []
            }

        # Add new data point
        self.coin_data[symbol]['prices'].append(float(price))
        self.coin_data[symbol]['volumes'].append(float(volume))
        self.coin_data[symbol]['timestamps'].append(timestamp)

        # Keep only the lookback window
        if len(self.coin_data[symbol]['prices']) > self.lookback_window:
            self.coin_data[symbol]['prices'] = self.coin_data[symbol]['prices'][-self.lookback_window:]
            self.coin_data[symbol]['volumes'] = self.coin_data[symbol]['volumes'][-self.lookback_window:]
            self.coin_data[symbol]['timestamps'] = self.coin_data[symbol]['timestamps'][-self.lookback_window:]

    def calculate_opportunity_scores(self) -> Dict[str, int]:
        """Calculate opportunity scores for all tracked coins.

        Returns:
            Dictionary mapping coin symbols to opportunity scores (0-100)
        """
        current_time = time.time()

        # Only recalculate scores if enough time has passed
        if current_time - self.last_update_time < self.update_interval:
            return self.opportunity_scores

        self.last_update_time = current_time

        for symbol, data in self.coin_data.items():
            # Skip if not enough data
            if len(data['prices']) < 10:
                self.opportunity_scores[symbol] = 50  # Neutral score
                continue

            try:
                # Convert to numpy arrays for technical indicators
                prices = np.array(data['prices'])
                volumes = np.array(data['volumes'])

                # Calculate opportunity score
                score = self._calculate_coin_score(symbol, prices, volumes)
                self.opportunity_scores[symbol] = score

            except Exception as e:
                self.opportunity_scores[symbol] = 50  # Neutral on error

        return self.opportunity_scores

    def _calculate_coin_score(self, symbol: str, prices: np.ndarray, volumes: np.ndarray) -> int:
        """Calculate opportunity score for a single coin.

        Args:
            symbol: Trading pair symbol
            prices: Array of historical prices
            volumes: Array of historical volumes

        Returns:
            Opportunity score from 0 (worst) to 100 (best)
        """
        # Base score starts at 50 (neutral)
        score = 50

        try:
            # Calculate technical indicators
            rsi = TechnicalIndicators.calculate_rsi(prices)[-1]  # Get latest RSI
            macd, signal, hist = TechnicalIndicators.calculate_macd(prices)
            macd_latest, signal_latest = macd[-1], signal[-1]
            upper, middle, lower = TechnicalIndicators.calculate_bollinger_bands(prices)
            upper_latest, lower_latest = upper[-1], lower[-1]

            # RSI component (0-30 points)
            if rsi < 30:  # Oversold - buying opportunity
                rsi_score = (30 - rsi)
                score += rsi_score
            elif rsi > 70:  # Overbought - reduce score
                rsi_score = (rsi - 70)
                score -= rsi_score

            # MACD component (0-40 points)
            if macd_latest > signal_latest:  # Bullish crossover
                # Strength based on the distance
                macd_score = min(20, (macd_latest - signal_latest) * 100)
                score += macd_score

                # Check if histogram is positive and increasing
                if len(hist) >= 3 and hist[-1] > 0 and hist[-1] > hist[-2] > hist[-3]:
                    score += 20  # Strong bullish momentum
            elif macd_latest < signal_latest:  # Bearish crossover
                # Strength based on the distance
                macd_score = min(20, (signal_latest - macd_latest) * 100)
                score -= macd_score

            # Price relative to Bollinger Bands (0-30 points)
            current_price = prices[-1]
            if current_price < lower_latest:  # Below lower band - potential bounce
                band_score = min(30, (lower_latest - current_price) / lower_latest * 100)
                score += band_score
            elif current_price > upper_latest:  # Above upper band - potential drop
                band_score = min(30, (current_price - upper_latest) / upper_latest * 100)
                score -= band_score

            # Volume analysis (0-10 points)
            if len(volumes) > 5:
                avg_volume = np.mean(volumes[:-5])
                current_volume = volumes[-1]

                # Higher than average volume is good for momentum
                if current_volume > avg_volume * 1.5:
                    volume_score = min(10, (current_volume / avg_volume - 1) * 10)
                    score += volume_score

        except Exception as e:
            print(f"Error calculating score for {symbol}: {e}")
            return 50  # Return neutral score on error

        # Ensure score is within 0-100 range
        return max(0, min(100, int(score)))

    def get_best_opportunities(self, top_n: int = 3) -> List[Tuple[str, int]]:
        """Get top N coins with the highest opportunity scores.

        Args:
            top_n: Number of top coins to return

        Returns:
            List of (symbol, score) tuples, sorted by descending score
        """
        # Update scores
        self.calculate_opportunity_scores()

        # Sort by score descending
        sorted_opportunities = sorted(
            self.opportunity_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )

        return sorted_opportunities[:top_n]

    def should_change_coin(self, current_coin: str) -> Optional[str]:
        """Determine if the bot should switch to a different coin.

        Args:
            current_coin: Currently traded coin

        Returns:
            Symbol of coin to switch to, or None if should stay
        """
        # Only consider switching if we have scores for at least 2 coins
        if len(self.opportunity_scores) < 2:
            return None

        # Get best opportunity
        best_coin, best_score = self.get_best_opportunities(1)[0]

        if current_coin not in self.opportunity_scores:
            return best_coin

        current_score = self.opportunity_scores[current_coin]

        # Only switch if the new coin has a significantly better score
        # (at least 15 points higher)
        if best_coin != current_coin and best_score > current_score + 15:
            return best_coin

        return None