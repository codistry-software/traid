"""Kraken WebSocket client for real-time market data."""
import json
import websockets
import asyncio
from typing import Dict, Optional, Callable
from decimal import Decimal
import time


class KrakenClient:
    """Client for interacting with Kraken's WebSocket API."""

    WS_URL = "wss://ws.kraken.com"
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
        self.subscriptions = set()
        self.on_price_update: Optional[Callable] = None
        self._last_update = 0
        self._message_queue = asyncio.Queue()

    async def connect(self):
        """Establish WebSocket connection."""
        if not self.ws:
            self.ws = await websockets.connect(self.WS_URL)
            self.running = True
            asyncio.create_task(self._message_handler())

    async def subscribe_price(self, symbol: str):
        """Subscribe to price updates for a symbol.

        Args:
            symbol: Trading pair symbol (e.g. 'BTC/USD')
        """
        if not self.ws:
            await self.connect()

        formatted_symbol = self._format_symbol(symbol)
        if formatted_symbol not in self.subscriptions:
            message = {
                "event": "subscribe",
                "pair": [formatted_symbol],
                "subscription": {"name": "ticker"}
            }
            await self.ws.send(json.dumps(message))
            self.subscriptions.add(formatted_symbol)

    async def _message_handler(self):
        """Handle incoming WebSocket messages."""
        while self.running:
            try:
                if self.ws:
                    message = await self.ws.recv()
                    await self._process_message(message)
            except websockets.exceptions.ConnectionClosed:
                print("WebSocket connection closed. Reconnecting...")
                await self.connect()
            except Exception as e:
                print(f"Error processing message: {e}")
                await asyncio.sleep(1)

    async def _process_message(self, message: str = None):
        """Process incoming WebSocket message.

        Args:
            message: Raw WebSocket message
        """
        if not message:
            return

        data = json.loads(message)
        if isinstance(data, list) and len(data) > 2:
            # Price update message
            if data[2] == "ticker":
                symbol = data[3]
                price_data = data[1]

                if "c" in price_data:  # "c" contains last trade price
                    update = {
                        "symbol": self._reverse_format_symbol(symbol),
                        "price": price_data["c"][0],
                        "timestamp": int(time.time() * 1000)
                    }

                    if self.on_price_update:
                        self.on_price_update(update)

    def _format_symbol(self, symbol: str) -> str:
        """Format trading pair symbol for Kraken API."""
        base, quote = symbol.split('/')
        base = self.ASSET_MAPPING.get(base, base)
        return f"{base}/{quote}"

    def _reverse_format_symbol(self, symbol: str) -> str:
        """Convert Kraken symbol format back to standard format."""
        base, quote = symbol.split('/')
        for standard, kraken in self.ASSET_MAPPING.items():
            if kraken == base:
                return f"{standard}/{quote}"
        return symbol

    async def close(self):
        """Close WebSocket connection."""
        self.running = False
        if self.ws:
            await self.ws.close()
            self.ws = None