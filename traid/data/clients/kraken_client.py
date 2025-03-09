"""Kraken WebSocket client with multi-coin support for real-time market data."""
import json
import ssl

import websockets
import asyncio
import aiohttp
from typing import Dict, Optional, Callable, List, Set
from decimal import Decimal
import time


class KrakenClient:
    """Enhanced client for interacting with Kraken's WebSocket API with multi-coin support."""

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
        self.price_data: Dict[str, Dict] = {}  # Store latest price data for each symbol
        self.ohlcv_data: Dict[str, List[Dict]] = {}  # Store OHLCV data for each symbol
        self.on_price_update: Optional[Callable] = None

        # Track message handler task so we don't spawn duplicates
        self._message_handler_task: Optional[asyncio.Task] = None

        # Internal flags for reconnection/backoff
        self._last_update = 0
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = 5

    async def connect(self) -> bool:
        """Establish or verify WebSocket connection with retry logic.

        Returns:
            bool: True if connection is successful/active, False otherwise.
        """
        # If we already have a socket, ping to verify it's alive
        if self.ws:
            try:
                pong = await asyncio.wait_for(self.ws.ping(), timeout=2.0)
                # If it doesn't raise, it means the connection is alive
                return True
            except Exception:
                # If ping fails, we'll try to reconnect below
                pass

        try:
            # Create SSL context with verification disabled
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

            # Actually connect to Kraken's WS
            self.ws = await websockets.connect(self.WS_URL, ssl=ssl_context)
            self.running = True
            self._reconnect_attempts = 0

            # Resubscribe to all previous subscriptions
            for symbol in self.subscriptions:
                await self._subscribe_to_symbol(symbol)

            # Only start the message handler if not already started or if it's done
            if not self._message_handler_task or self._message_handler_task.done():
                self._message_handler_task = asyncio.create_task(self._message_handler())

            return True

        except Exception as e:
            self._reconnect_attempts += 1
            print(f"Connection attempt {self._reconnect_attempts} failed: {e}")

            if self._reconnect_attempts >= self._max_reconnect_attempts:
                print("Maximum reconnection attempts reached. Giving up.")
                return False

            # Exponential backoff
            wait_time = 2 ** self._reconnect_attempts
            print(f"Retrying WebSocket connection in {wait_time} seconds...")
            await asyncio.sleep(wait_time)
            return await self.connect()  # Recursive retry with backoff

    async def _reconnect_once(self) -> bool:
        """Attempt a single reconnect operation with backoff limits."""
        # We'll close the current ws to ensure a fresh connection
        if self.ws:
            await self.ws.close()
        self.ws = None

        self._reconnect_attempts += 1
        if self._reconnect_attempts > self._max_reconnect_attempts:
            print("Exceeded max reconnection attempts in _reconnect_once()")
            return False

        wait_time = 2 ** self._reconnect_attempts
        print(f"WebSocket disconnected. Retrying in {wait_time} seconds...")
        await asyncio.sleep(wait_time)
        return await self.connect()

    async def subscribe_prices(self, symbols: List[str]) -> None:
        """Subscribe to price updates for multiple symbols.

        Args:
            symbols: List of trading pair symbols (e.g. ['BTC/USD', 'ETH/USD'])
        """
        if not self.ws:
            success = await self.connect()
            if not success:
                print("Failed to connect to WebSocket API")
                return

        for symbol in symbols:
            await self.subscribe_price(symbol)

    async def subscribe_price(self, symbol: str) -> None:
        """Subscribe to price updates for a symbol.

        Args:
            symbol: Trading pair symbol (e.g. 'BTC/USD')
        """
        if not self.ws:
            success = await self.connect()
            if not success:
                print(f"Failed to subscribe to {symbol}: connection failed")
                return

        await self._subscribe_to_symbol(symbol)

    async def subscribe_ohlcv(self, symbol: str, interval: int = 1) -> None:
        """Subscribe to OHLCV (candle) data for a symbol.

        Args:
            symbol: Trading pair symbol (e.g. 'BTC/USD')
            interval: Candle interval in minutes
        """
        if not self.ws:
            success = await self.connect()
            if not success:
                print(f"Failed to subscribe to {symbol} OHLCV: connection failed")
                return

        formatted_symbol = self._format_symbol(symbol)
        message = {
            "event": "subscribe",
            "pair": [formatted_symbol],
            "subscription": {"name": "ohlc", "interval": interval}
        }
        await self.ws.send(json.dumps(message))
        print(f"Subscribed to {symbol} OHLCV data, interval {interval}")

    async def _subscribe_to_symbol(self, symbol: str) -> None:
        """Internal helper to subscribe a single symbol to ticker data."""
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
        """Single task that continuously reads messages from WebSocket."""
        while self.running:
            # Ensure we have an active connection
            if not self.ws:
                success = await self.connect()
                if not success:
                    print("Failed to reconnect, stopping _message_handler.")
                    self.running = False
                    break

            try:
                # Read one message from the WS
                message = await self.ws.recv()
                await self._process_message(message)

            except websockets.exceptions.ConnectionClosed:
                print("WebSocket connection closed. Trying a single reconnect...")
                success = await self._reconnect_once()
                if not success:
                    print("Failed to reconnect. Stopping message handler.")
                    self.running = False

            except Exception as e:
                print(f"Error processing message: {e}")
                # A short sleep to prevent busy-loop if repeated errors occur
                await asyncio.sleep(1)

        print("Exiting _message_handler loop.")

    async def _process_message(self, message: str) -> None:
        """Process incoming WebSocket message.

        Args:
            message: Raw JSON string from WebSocket.
        """
        if not message:
            return

        try:
            data = json.loads(message)

            # Handle ticker updates (price data)
            if isinstance(data, list) and len(data) > 2:
                if data[2] == "ticker":
                    symbol = data[3]
                    price_data = data[1]

                    if "c" in price_data:
                        standard_symbol = self._reverse_format_symbol(symbol)

                        # Update our price cache
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

                # Handle OHLCV updates
                elif data[2] == "ohlc":
                    symbol = data[3]
                    ohlc_data = data[1]
                    standard_symbol = self._reverse_format_symbol(symbol)

                    if standard_symbol not in self.ohlcv_data:
                        self.ohlcv_data[standard_symbol] = []

                    candle = {
                        "timestamp": int(ohlc_data[0]),
                        "open": Decimal(ohlc_data[1]),
                        "high": Decimal(ohlc_data[2]),
                        "low": Decimal(ohlc_data[3]),
                        "close": Decimal(ohlc_data[4]),
                        "volume": Decimal(ohlc_data[6])
                    }

                    timestamp = candle["timestamp"]
                    updated_existing = False

                    for i, existing_candle in enumerate(self.ohlcv_data[standard_symbol]):
                        if existing_candle["timestamp"] == timestamp:
                            self.ohlcv_data[standard_symbol][i] = candle
                            updated_existing = True
                            break

                    if not updated_existing:
                        self.ohlcv_data[standard_symbol].append(candle)

                    # If you had an OHLCV callback, call it here
                    if hasattr(self, 'on_ohlcv_update') and self.on_ohlcv_update:
                        update = {
                            "symbol": standard_symbol,
                            "data": candle
                        }
                        self.on_ohlcv_update(update)

            # Handle subscription status messages
            elif isinstance(data, dict) and "event" in data:
                if data["event"] == "subscriptionStatus":
                    status = data.get("status")
                    pair = data.get("pair")
                    if status == "error":
                        print(f"Subscription error for {pair}: {data.get('errorMessage')}")

        except json.JSONDecodeError:
            print(f"Invalid JSON message: {message[:100]}...")
        except Exception as e:
            print(f"Error processing message: {e}")

    def get_latest_price(self, symbol: str) -> Optional[Decimal]:
        """Get the latest price for a symbol.

        Args:
            symbol: Trading pair symbol

        Returns:
            Latest price or None if not available
        """
        if symbol in self.price_data:
            return self.price_data[symbol]["price"]
        return None

    def get_multi_coin_data(self) -> Dict[str, Dict]:
        """Get latest data for all subscribed coins.

        Returns:
            Dictionary with price data for all coins
        """
        return self.price_data

    def get_ohlcv(self, symbol: str, limit: int = 100) -> Optional[List[Dict]]:
        """Get OHLCV data for a symbol.

        Args:
            symbol: Trading pair symbol
            limit: Maximum number of candles to return

        Returns:
            List of OHLCV candles or None if not available
        """
        if symbol in self.ohlcv_data:
            # Return the latest 'limit' candles
            return self.ohlcv_data[symbol][-limit:]
        return None

    async def fetch_historical_data(self, symbols, interval=5, limit=200):
        """Fetch historical OHLCV data from Kraken REST API.

        Args:
            symbols: List of trading pair symbols
            interval: Candle interval in minutes
            limit: Number of candles to fetch per symbol

        Returns:
            Dict mapping symbols to lists of OHLCV data (or False on complete failure).
        """
        interval_map = {
            1: 1, 5: 5, 15: 15, 30: 30,
            60: 60, 240: 240, 1440: 1440,
            10080: 10080, 21600: 21600
        }
        if interval not in interval_map:
            interval = 5

        kraken_interval = interval_map[interval]
        historical_data = {}
        failed_symbols = []

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

                    try:
                        async with session.get(endpoint, params=params, ssl=ssl_context) as response:
                            if response.status == 200:
                                data = await response.json()
                                if "result" in data and data["error"] == [] and data["result"]:
                                    pair_data = list(data["result"].keys())[0]
                                    ohlc_data = data["result"][pair_data]

                                    if len(ohlc_data) == 0:
                                        failed_symbols.append((symbol, "Empty OHLC data returned"))
                                        continue

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
                                else:
                                    error_msg = "Unknown API error"
                                    if "error" in data and data["error"]:
                                        error_msg = f"API error: {data['error']}"
                                    failed_symbols.append((symbol, error_msg))
                            else:
                                response_text = await response.text()
                                failed_symbols.append((symbol, f"HTTP {response.status}: {response_text[:100]}"))
                    except aiohttp.ClientError as ce:
                        failed_symbols.append((symbol, f"Connection error: {str(ce)}"))
            except Exception as e:
                import traceback
                failed_symbols.append((symbol, f"Exception: {str(e)[:100]}"))
                print(f"Error processing {symbol}: {str(e)}")
                print(traceback.format_exc())

        print(f"Fetched historical data: {len(historical_data)}/{len(symbols)} symbols successful")
        if failed_symbols:
            print(f"Failed to fetch data for {len(failed_symbols)} symbols: {failed_symbols}")

        if len(failed_symbols) == len(symbols):
            return False

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

        # Reverse mapping for base currency
        for standard, kraken in self.ASSET_MAPPING.items():
            if kraken == base:
                base = standard
                break

        # Reverse mapping for quote currency
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
            # Wait for handler to exit
            await asyncio.sleep(0.1)
            if not self._message_handler_task.done():
                self._message_handler_task.cancel()
            self._message_handler_task = None

        print("WebSocket and message handler closed.")
