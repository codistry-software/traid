from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class OHLCV:
    """Represents OHLCV (Open, High, Low, Close, Volume) candlestick data.

    Attributes:
        timestamp: Unix timestamp of the candle
        open: Opening price
        high: Highest price during period
        low: Lowest price during period
        close: Closing price
        volume: Trading volume
    """
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float

    @staticmethod
    def from_kraken_data(raw_candle: list) -> 'OHLCV':
        """Create OHLCV object from Kraken API response format.

        Args:
            raw_candle: List containing [timestamp, open, high, low, close, vwap, volume, count]

        Returns:
            OHLCV: Parsed candlestick data
        """
        try:
            return OHLCV(
                timestamp=int(raw_candle[0]),
                open=float(raw_candle[1]),
                high=float(raw_candle[2]),
                low=float(raw_candle[3]),
                close=float(raw_candle[4]),
                volume=float(raw_candle[6])
            )
        except (IndexError, ValueError) as e:
            raise ValueError(f"Invalid Kraken candle data format: {e}")

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