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
        """Establish WebSocket connection with retry logic.

        Returns:
            bool: True if connection successful, False otherwise
        """
        if self.ws:
            try:
                # Try to send a ping to check if connection is still alive
                pong = await asyncio.wait_for(self.ws.ping(), timeout=2.0)
                return True  # Connection is still good
            except Exception:
                # Connection is not usable, continue to create a new one
                pass

        try:
            # Create SSL context with verification disabled
            import ssl
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

            self.ws = await websockets.connect(self.WS_URL, ssl=ssl_context)
            self.running = True
            self._reconnect_attempts = 0

            # Resubscribe to all previous subscriptions
            for symbol in self.subscriptions:
                await self._subscribe_to_symbol(symbol)

            # Start message handler
            asyncio.create_task(self._message_handler())
            return True

        except Exception as e:
            self._reconnect_attempts += 1
            print(f"Connection attempt {self._reconnect_attempts} failed: {e}")

            if self._reconnect_attempts >= self._max_reconnect_attempts:
                print("Maximum reconnection attempts reached")
                return False

            # Exponential backoff
            wait_time = 2 ** self._reconnect_attempts
            print(f"Retrying in {wait_time} seconds...")
            await asyncio.sleep(wait_time)
            return await self.connect()  # Recursive retry

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
            interval: Candle interval in minutes (1, 5, 15, 30, 60, 240, 1440, 10080, 21600)
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
        """Internal method to send subscription message for a symbol."""
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
            try:
                if self.ws:
                    message = await self.ws.recv()
                    await self._process_message(message)
            except websockets.exceptions.ConnectionClosed:
                print("WebSocket connection closed. Reconnecting...")
                success = await self.connect()
                if not success:
                    print("Failed to reconnect. Stopping message handler.")
                    self.running = False
            except Exception as e:
                print(f"Error processing message: {e}")
                await asyncio.sleep(1)

    async def _process_message(self, message: str) -> None:
        """Process incoming WebSocket message.

        Args:
            message: Raw WebSocket message
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

                    if "c" in price_data:  # "c" contains last trade price
                        standard_symbol = self._reverse_format_symbol(symbol)

                        # Update our price cache
                        self.price_data[standard_symbol] = {
                            "price": Decimal(price_data["c"][0]),
                            "timestamp": int(time.time() * 1000),
                            "volume": Decimal(price_data["v"][1]),  # 24h volume
                            "low": Decimal(price_data["l"][1]),  # 24h low
                            "high": Decimal(price_data["h"][1]),  # 24h high
                        }

                        # Call the callback if registered
                        if self.on_price_update:
                            update = {
                                "symbol": standard_symbol,
                                "data": self.price_data[standard_symbol]
                            }
                            self.on_price_update(update)

                # Add handling for OHLCV data
                elif data[2] == "ohlc":
                    symbol = data[3]
                    ohlc_data = data[1]

                    # Convert symbol to standard format if necessary
                    standard_symbol = self._reverse_format_symbol(symbol)

                    # Initialize the dictionary for this symbol if it doesn't exist
                    if standard_symbol not in self.ohlcv_data:
                        self.ohlcv_data[standard_symbol] = []

                    # Parse the OHLCV data and add to our cache
                    candle = {
                        "timestamp": int(ohlc_data[0]),
                        "open": Decimal(ohlc_data[1]),
                        "high": Decimal(ohlc_data[2]),
                        "low": Decimal(ohlc_data[3]),
                        "close": Decimal(ohlc_data[4]),
                        "volume": Decimal(ohlc_data[6])  # Assuming position 6 is volume based on your test
                    }

                    # Check if a candle with this timestamp already exists
                    timestamp = int(ohlc_data[0])
                    updated_existing = False

                    for i, existing_candle in enumerate(self.ohlcv_data[standard_symbol]):
                        if existing_candle["timestamp"] == timestamp:
                            # Update the existing candle instead of adding a new one
                            self.ohlcv_data[standard_symbol][i] = candle
                            updated_existing = True
                            break

                    # Only append if we didn't update an existing candle
                    if not updated_existing:
                        self.ohlcv_data[standard_symbol].append(candle)

                    # Call the callback if registered
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
        """Fetch historical OHLCV data from Kraken API.

        Args:
            symbols: List of trading pair symbols
            interval: Candle interval in minutes
            limit: Number of candles to fetch per symbol

        Returns:
            Dict mapping symbols to lists of OHLCV data
        """
        # Map minutes to Kraken interval format
        interval_map = {
            1: 1, 5: 5, 15: 15, 30: 30,
            60: 60, 240: 240, 1440: 1440,
            10080: 10080, 21600: 21600
        }

        if interval not in interval_map:
            interval = 5  # Default to 5 minutes if invalid interval

        kraken_interval = interval_map[interval]
        historical_data = {}
        failed_symbols = []

        for symbol in symbols:
            try:
                formatted_symbol = self._format_symbol(symbol)
                endpoint = f"{self.REST_API_URL}/OHLC"

                # Prepare request parameters
                params = {
                    "pair": formatted_symbol.replace("/", ""),
                    "interval": kraken_interval
                }

                async with aiohttp.ClientSession() as session:
                    ssl_context = ssl.create_default_context()
                    ssl_context.check_hostname = False
                    ssl_context.verify_mode = ssl.CERT_NONE

                    try:
                        # Make API request
                        async with session.get(endpoint, params=params, ssl=ssl_context) as response:
                            if response.status == 200:
                                data = await response.json()

                                if "result" in data and data["error"] == [] and data["result"]:
                                    pair_data = list(data["result"].keys())[0]
                                    ohlc_data = data["result"][pair_data]

                                    if len(ohlc_data) == 0:
                                        failed_symbols.append((symbol, "Empty OHLC data returned"))
                                        continue

                                    # Initialize data array for this symbol
                                    historical_data[symbol] = []

                                    # Process all candles (up to limit)
                                    for candle in ohlc_data[-limit:]:
                                        timestamp, open_price, high, low, close, vwap, volume, count = candle

                                        # Store normalized data
                                        historical_data[symbol].append({
                                            "timestamp": int(timestamp),
                                            "open": float(open_price),
                                            "high": float(high),
                                            "low": float(low),
                                            "close": float(close),
                                            "volume": float(volume)
                                        })
                                else:
                                    error_msg = "API error"
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

        # Print summary
        print(f"Fetched historical data: {len(historical_data)}/{len(symbols)} symbols successful")
        if failed_symbols:
            print(f"Failed to fetch data for {len(failed_symbols)} symbols")

        # If all symbols failed, return False to indicate complete failure
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
        """Close WebSocket connection."""
        self.running = False
        if self.ws:
            await self.ws.close()
            self.ws = None
