from typing import List, Dict, Optional
import requests


class MarketData:
    """Class for handling market data operations.

    Attributes:
        symbol: Trading pair symbol (e.g. 'BTC/USDT')
        timeframe: Timeframe for the market data (e.g. '1h', '15m')
    """
    BASE_URL = "https://api.kraken.com/0/public"

    def __init__(
            self,
            symbol: str,
            timeframe: str
    ) -> None:
        self.symbol = symbol
        self.timeframe = timeframe

    def get_ohlcv(self) -> List[Dict]:
        """Fetch OHLCV (Open, High, Low, Close, Volume) data.

        Returns:
            List[Dict]: List of OHLCV candles with keys:
                - timestamp: int (Unix timestamp)
                - open: float
                - high: float
                - low: float
                - close: float
                - volume: float
        """
        endpoint = f"{self.BASE_URL}/OHLC"
        params = {
            "pair": self.symbol,
            "interval": self.timeframe
        }

        response = requests.get(endpoint, params=params)
        return self._parse_ohlcv_response(response.json())

    def _parse_ohlcv_response(self, response: Dict) -> List[Dict]:
        """Parse Kraken OHLCV response into standardized format.

        Args:
            response: Raw Kraken API response

        Returns:
            List of parsed OHLCV candles
        """
        # TODO: Implement actual parsing
        return []