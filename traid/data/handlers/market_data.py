from typing import List, Dict
from ..clients.kraken_client import KrakenClient
from ..models.ohlcv import OHLCV

class MarketData:
    def __init__(self, symbol: str, timeframe: str) -> None:
        self.symbol = symbol
        self.timeframe = timeframe
        self._client = KrakenClient()

    def get_ohlcv(self) -> List[Dict]:
        """Fetch OHLCV data.
        Returns:
            List[Dict]: List of OHLCV candles
        """
        response = self._client.get_ohlcv(self.symbol, self.timeframe)
        return self._parse_ohlcv_response(response)

    def _parse_ohlcv_response(self, response: Dict) -> List[Dict]:
        return []