"""Simplified Kraken WebSocket client for real-time market data."""
import json
import ssl
import websockets
import asyncio
import aiohttp
from typing import Dict, List, Optional, Callable, Set
from decimal import Decimal
import time

class KrakenClient:
    """Client for interacting with Kraken's WebSocket and REST API."""

    WS_URL = "wss://ws.kraken.com"
    REST_API_URL = "https://api.kraken.com/0/public"
    ASSET_MAPPING = {
        "BTC": "XBT",
        "USDT": "USDT",
        "USD": "USD",
        "EUR": "EUR"
    }

    def __init__(self):
        """Initialize WebSocket client."""
        self.ws = None
        self.running = False
        self.subscriptions: Set[str] = set()
        self.price_data: Dict[str, Dict] = {}
        self.on_price_update: Optional[Callable] = None
        self._message_handler_task = None

    async def connect(self) -> bool:
        """Establish WebSocket connection."""
        try:
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

            self.ws = await websockets.connect(self.WS_URL, ssl=ssl_context)
            self.running = True

            # Resubscribe to previous subscriptions
            for symbol in self.subscriptions:
                await self._subscribe_to_symbol(symbol)

            # Start message handler task
            if not self._message_handler_task or self._message_handler_task.done():
                self._message_handler_task = asyncio.create_task(self._message_handler())

            return True
        except Exception as e:
            print(f"Connection failed: {e}")
            return False

    async def subscribe_prices(self, symbols: List[str]) -> None:
        """Subscribe to price updates for multiple symbols."""
        if not self.ws:
            success = await self.connect()
            if not success:
                print("Failed to connect to WebSocket API")
                return

        for symbol in symbols:
            await self._subscribe_to_symbol(symbol)

    async def _subscribe_to_symbol(self, symbol: str) -> None:
        """Subscribe to ticker data for a symbol."""
        formatted_symbol = self._format_symbol(symbol)
        if formatted_symbol not in self.subscriptions:
            message = {
                "event": "subscribe",
                "pair": [formatted_symbol],
                "subscription": {"name": "ticker"}
            }
            await self.ws.send(json.dumps(message))
            self.subscriptions.add(formatted_symbol)

    async def _message_handler(self) -> None:
        """Handle incoming WebSocket messages."""
        while self.running:
            if not self.ws:
                success = await self.connect()
                if not success:
                    print("Failed to reconnect, stopping message handler.")
                    self.running = False
                    break

            try:
                message = await self.ws.recv()
                await self._process_message(message)
            except websockets.exceptions.ConnectionClosed:
                print("WebSocket connection closed. Attempting to reconnect...")
                await asyncio.sleep(2)
                await self.connect()
            except Exception as e:
                print(f"Error processing message: {e}")
                await asyncio.sleep(1)

    async def _process_message(self, message: str) -> None:
        """Process incoming WebSocket message."""
        if not message:
            return

        try:
            data = json.loads(message)

            # Handle ticker updates (price data)
            if isinstance(data, list) and len(data) > 2 and data[2] == "ticker":
                symbol = data[3]
                price_data = data[1]

                if "c" in price_data:
                    standard_symbol = self._reverse_format_symbol(symbol)

                    # Update price cache
                    self.price_data[standard_symbol] = {
                        "price": Decimal(price_data["c"][0]),
                        "timestamp": int(time.time() * 1000),
                        "volume": Decimal(price_data["v"][1]),
                        "low": Decimal(price_data["l"][1]),
                        "high": Decimal(price_data["h"][1]),
                    }

                    # Call the callback if registered
                    if self.on_price_update:
                        update = {
                            "symbol": standard_symbol,
                            "data": self.price_data[standard_symbol]
                        }
                        self.on_price_update(update)

        except Exception as e:
            print(f"Error processing message: {e}")

    def get_latest_price(self, symbol: str) -> Optional[Decimal]:
        """Get the latest price for a symbol."""
        if symbol in self.price_data:
            return self.price_data[symbol]["price"]
        return None

    def get_multi_coin_data(self) -> Dict[str, Dict]:
        """Get latest data for all subscribed coins."""
        return self.price_data

    async def fetch_historical_data(self, symbols, interval=5, limit=200):
        """Fetch historical OHLCV data from Kraken REST API."""
        interval_map = {1: 1, 5: 5, 15: 15, 30: 30, 60: 60, 240: 240, 1440: 1440}
        if interval not in interval_map:
            interval = 5

        kraken_interval = interval_map[interval]
        historical_data = {}

        for symbol in symbols:
            try:
                formatted_symbol = self._format_symbol(symbol)
                endpoint = f"{self.REST_API_URL}/OHLC"
                params = {
                    "pair": formatted_symbol.replace("/", ""),
                    "interval": kraken_interval
                }

                async with aiohttp.ClientSession() as session:
                    ssl_context = ssl.create_default_context()
                    ssl_context.check_hostname = False
                    ssl_context.verify_mode = ssl.CERT_NONE

                    async with session.get(endpoint, params=params, ssl=ssl_context) as response:
                        if response.status == 200:
                            data = await response.json()
                            if "result" in data and data["error"] == [] and data["result"]:
                                pair_data = list(data["result"].keys())[0]
                                ohlc_data = data["result"][pair_data]

                                historical_data[symbol] = []
                                for candle in ohlc_data[-limit:]:
                                    timestamp, open_price, high, low, close, vwap, vol, count = candle
                                    historical_data[symbol].append({
                                        "timestamp": int(timestamp),
                                        "open": float(open_price),
                                        "high": float(high),
                                        "low": float(low),
                                        "close": float(close),
                                        "volume": float(vol)
                                    })
            except Exception as e:
                print(f"Error fetching data for {symbol}: {e}")

        return historical_data

    def _format_symbol(self, symbol: str) -> str:
        """Format trading pair symbol for Kraken API."""
        if not symbol or '/' not in symbol:
            return symbol

        base, quote = symbol.split('/')
        base = self.ASSET_MAPPING.get(base, base)
        quote = self.ASSET_MAPPING.get(quote, quote)
        return f"{base}/{quote}"

    def _reverse_format_symbol(self, symbol: str) -> str:
        """Convert Kraken symbol format back to standard format."""
        if not symbol or '/' not in symbol:
            return symbol

        base, quote = symbol.split('/')

        # Reverse mapping
        for standard, kraken in self.ASSET_MAPPING.items():
            if kraken == base:
                base = standard
                break
        for standard, kraken in self.ASSET_MAPPING.items():
            if kraken == quote:
                quote = standard
                break

        return f"{base}/{quote}"

    async def close(self) -> None:
        """Close WebSocket connection gracefully."""
        self.running = False
        if self.ws:
            await self.ws.close()
            self.ws = None

        if self._message_handler_task:
            await asyncio.sleep(0.1)
            if not self._message_handler_task.done():
                self._message_handler_task.cancel()
            self._message_handler_task = None