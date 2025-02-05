from typing import Dict
import requests


class KrakenClient:
    BASE_URL = "https://api.kraken.com/0/public"

    def get_ohlcv(self, symbol: str, timeframe: str) -> Dict:
        endpoint = f"{self.BASE_URL}/OHLC"
        params = {
            "pair": symbol,
            "interval": timeframe
        }
        response = requests.get(endpoint, params=params)
        return response.json()