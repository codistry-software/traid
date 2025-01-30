from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class OHLCV:
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float

    def to_dict(self) -> Dict:
        """Convert OHLCV data to dictionary format.

        Returns:
            Dict containing OHLCV data with string keys
        """
        return {
            'timestamp': self.timestamp,
            'open': self.open,
            'high': self.high,
            'low': self.low,
            'close': self.close,
            'volume': self.volume
        }

    @staticmethod
    def parse_kraken_response(response: Dict) -> List['OHLCV']:
        """Parse complete Kraken API response into list of OHLCV objects.

        Args:
            response: Raw Kraken API response dictionary

        Returns:
            List of OHLCV objects

        Raises:
            ValueError: If response format is invalid
        """
        if not response or 'result' not in response:
            return []

        try:
            pair_data = next(iter(response['result'].values()))
            return [OHLCV.from_kraken_data(candle) for candle in pair_data]
        except (StopIteration, KeyError) as e:
            raise ValueError(f"Invalid Kraken response format: {e}")