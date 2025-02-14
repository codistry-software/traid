"""Kraken API client for market data fetching."""
from typing import Dict
import requests
from requests.exceptions import RequestException


class KrakenClient:
    """Client for interacting with Kraken's public API."""

    BASE_URL = "https://api.kraken.com/0/public"

    # Mapping for asset names to Kraken's format
    ASSET_MAPPING = {
        "BTC": "XBT",
        "USDT": "USDT",
        "USD": "USD",
        "EUR": "EUR"
    }

    def get_ohlcv(self, symbol: str, timeframe: str) -> Dict:
        """Fetch OHLCV (candle) data from Kraken.

        Args:
            symbol: Trading pair symbol (e.g. 'BTC/USD')
            timeframe: Time interval (e.g. '1h', '15m', '1d')

        Returns:
            Dict containing OHLCV data or error message

        Raises:
            RequestException: If API request fails
        """
        try:
            endpoint = f"{self.BASE_URL}/OHLC"
            params = {
                "pair": self._format_symbol(symbol),
                "interval": self._convert_timeframe(timeframe)
            }

            response = requests.get(endpoint, params=params, timeout=10)
            response.raise_for_status()
            return response.json()

        except RequestException as e:
            return {
                "error": [f"API request failed: {str(e)}"]
            }
        except Exception as e:
            return {
                "error": [f"Unexpected error: {str(e)}"]
            }

    def _format_symbol(self, symbol: str) -> str:
        """Format trading pair symbol for Kraken API.

        Args:
            symbol: Standard symbol format (e.g. 'BTC/USD')

        Returns:
            Kraken-formatted symbol (e.g. 'XBTUSD')
        """
        base, quote = symbol.split('/')

        # Convert to Kraken's symbol format
        base = self.ASSET_MAPPING.get(base, base)
        quote = self.ASSET_MAPPING.get(quote, quote)

        return f"{base}{quote}"

    def _convert_timeframe(self, timeframe: str) -> str:
        """Convert timeframe to minutes for Kraken API.

        Args:
            timeframe: Human readable timeframe (e.g. '1h', '15m', '1d')

        Returns:
            Timeframe in minutes as string
        """
        if timeframe.endswith('m'):
            return timeframe[:-1]
        elif timeframe.endswith('h'):
            return str(int(timeframe[:-1]) * 60)
        elif timeframe.endswith('d'):
            return str(int(timeframe[:-1]) * 1440)
        return timeframe