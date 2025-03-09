from typing import List, Dict
from ..clients.kraken_client import KrakenClient
from ..models.ohlcv import OHLCV


class MarketData:
    """Handles market data operations and transformations.

    Attributes:
        symbol: Trading pair symbol (e.g. 'BTC/USDT')
        timeframe: Timeframe for the market data (e.g. '1h', '15m')
    """

    def __init__(self, symbol: str, timeframe: str) -> None:
        self.symbol = symbol
        self.timeframe = timeframe
        self._client = KrakenClient()

    def get_ohlcv(self) -> List[Dict]:
        """Fetch OHLCV data from Kraken API.

        Returns:
            List[Dict]: List of OHLCV candles with standardized format
        """
        data = self._client.get_ohlcv(self.symbol, 1)
        return data if data is not None else []

    def _parse_ohlcv_response(self, response: Dict) -> List[Dict]:
        """Parse Kraken OHLCV response into standardized format.

        Args:
            response: Raw Kraken API response

        Returns:
            List[Dict]: List of parsed OHLCV candles
        """
        ohlcv_list = OHLCV.parse_kraken_response(response)
        return [candle.to_dict() for candle in ohlcv_list]