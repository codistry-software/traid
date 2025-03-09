"""
Refactored tests for Kraken WebSocket client.
Matches the current KrakenClient implementation.
"""
import json
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from traid.kraken_client import KrakenClient


@pytest.fixture
def client():
    """Create KrakenClient instance for tests."""
    return KrakenClient()


@pytest.fixture
def test_symbol():
    """Return test symbol."""
    return "BTC/USDT"


class MockWebSocket:
    """Mock WebSocket class for testing."""

    def __init__(self):
        self.open = True
        self.sent_messages = []

    async def send(self, message):
        """Record sent messages."""
        self.sent_messages.append(message)

    async def recv(self):
        """Simulate a simple recv if needed."""
        # Could simulate incoming messages here if you want to test _process_message
        await asyncio.sleep(0.01)
        return ""

    async def close(self):
        self.open = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


@pytest.mark.asyncio
async def test_connect(client, monkeypatch):
    """Test WebSocket connection establishment."""
    mock_ws = MockWebSocket()

    async def mock_connect(*args, **kwargs):
        return mock_ws

    monkeypatch.setattr('websockets.connect', mock_connect)

    # Test connect method
    result = await client.connect()

    # Assertions
    assert result is True
    assert client.running is True
    assert client.ws == mock_ws


@pytest.mark.asyncio
async def test_subscribe_prices(client, test_symbol, monkeypatch):
    """
    Test subscribing to price updates for multiple symbols.
    The client code no longer has `subscribe_price()`,
    so we test `subscribe_prices()` instead.
    """
    mock_ws = MockWebSocket()

    async def mock_connect(*args, **kwargs):
        return mock_ws

    monkeypatch.setattr('websockets.connect', mock_connect)

    # Connect and subscribe
    await client.connect()
    await client.subscribe_prices([test_symbol])

    # Assertions
    formatted_symbol = client._format_symbol(test_symbol)
    assert formatted_symbol in client.subscriptions, "Symbol should be in subscriptions."
    assert len(mock_ws.sent_messages) == 1, "Should have sent one subscription message."

    sent_message = json.loads(mock_ws.sent_messages[0])
    assert sent_message.get('subscription', {}).get('name') == 'ticker'
    assert formatted_symbol in sent_message.get('pair', [])


@pytest.mark.asyncio
async def test_process_message_ticker_update(client, test_symbol, monkeypatch):
    """Test processing a ticker WebSocket message."""
    mock_ws = MockWebSocket()

    async def mock_connect(*args, **kwargs):
        return mock_ws

    monkeypatch.setattr('websockets.connect', mock_connect)

    # Setup a callback
    callback_called = False
    callback_data = None

    def on_price_update(data):
        nonlocal callback_called, callback_data
        callback_called = True
        callback_data = data

    client.on_price_update = on_price_update

    # Connect
    await client.connect()
    # Simulate a ticker message
    ticker_message = (
        '[42,'
        '{"c":["50000.00000","0.00100000"],'
        '"v":["1.00000000","10.00000000"],'
        '"p":["50000.00000","50000.00000"],'
        '"t":[10,100],'
        '"l":["49000.00000","49000.00000"],'
        '"h":["51000.00000","51000.00000"],'
        '"o":["50000.00000","50000.00000"]},'
        '"ticker",'
        '"XBT/USDT"]'
    )

    await client._process_message(ticker_message)

    # Assertions
    assert callback_called is True, "on_price_update should have been called."
    assert callback_data["symbol"] == "BTC/USDT"
    assert callback_data["data"]["price"] == Decimal("50000.00000")


def test_format_symbol(client):
    """Test symbol formatting for Kraken API."""
    # Test BTC/USDT mapping
    formatted = client._format_symbol("BTC/USDT")
    assert formatted == "XBT/USDT"

    # Test ETH/USDT (no special mapping needed)
    formatted = client._format_symbol("ETH/USDT")
    assert formatted == "ETH/USDT"


def test_reverse_format_symbol(client):
    """Test reverse symbol formatting from Kraken API."""
    # Test XBT/USDT -> BTC/USDT
    standard = client._reverse_format_symbol("XBT/USDT")
    assert standard == "BTC/USDT"

    # Test ETH/USDT (no special mapping)
    standard = client._reverse_format_symbol("ETH/USDT")
    assert standard == "ETH/USDT"


import pytest
import asyncio

@pytest.mark.asyncio
async def test_fetch_historical_data(client, monkeypatch):
    """
    Test fetching historical data from the REST API.
    The current client returns a dictionary of lists of OHLCV data.
    """

    ################################################################################
    # 1) Define a mock response class that supports `async with`.
    ################################################################################
    class MockResponse:
        def __init__(self, status=200, data=None):
            self.status = status
            self._data = data or {}

        async def json(self):
            return self._data

        async def __aenter__(self):
            # This is called by: `async with session.get(...) as response:`
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    # This is the data we want the client to see
    mock_data = {
        "error": [],
        "result": {
            # e.g. if `BTC/USDT` is formatted to `XBTUSDT`
            "XBTUSDT": [
                [
                    1617592800, "50000.1", "51000.2", "49500.3",
                    "50500.4", "50250.5", "10.12345678", 100
                ],
                [
                    1617596400, "50500.4", "52000.5", "50400.6",
                    "51800.7", "51200.8", "15.87654321", 150
                ],
            ]
        }
    }
    # Create a MockResponse instance
    mock_response = MockResponse(status=200, data=mock_data)

    ################################################################################
    # 2) Define a mock session that returns our mock response as an async context.
    ################################################################################
    class MockSession:
        """Pretend aiohttp.ClientSession that yields `mock_response` on session.get(...)."""

        async def __aenter__(self):
            # This is called by: `async with aiohttp.ClientSession() as session:`
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

        def get(self, url, params=None, ssl=None):
            """
            Called by:
              async with session.get(endpoint, params=params, ssl=ssl_context) as response:
                  data = await response.json()
            Must return an object that supports `async with ...`.
            """
            return mock_response

    ################################################################################
    # 3) Patch the aiohttp.ClientSession constructor to return our MockSession.
    ################################################################################
    def mock_client_session_constructor(*args, **kwargs):
        return MockSession()

    monkeypatch.setattr("aiohttp.ClientSession", mock_client_session_constructor)

    ################################################################################
    # 4) Finally, run your production code as normal.
    ################################################################################
    symbols = ["BTC/USDT"]
    interval = 5
    data = await client.fetch_historical_data(symbols, interval=interval)

    ################################################################################
    # 5) Assertions - we should see "BTC/USDT" in the returned dictionary.
    ################################################################################
    assert isinstance(data, dict), "Expected a dictionary from fetch_historical_data."
    assert "BTC/USDT" in data, "Expected 'BTC/USDT' key in returned data."
    assert len(data["BTC/USDT"]) == 2, "Expected two OHLCV candles in result."

    # Check one candle's fields
    candle0 = data["BTC/USDT"][0]
    assert candle0["timestamp"] == 1617592800
    assert candle0["open"] == 50000.1
    assert candle0["high"] == 51000.2
    assert candle0["low"] == 49500.3
    assert candle0["close"] == 50500.4
    assert candle0["volume"] == 10.12345678

@pytest.mark.asyncio
async def test_fetch_historical_data_http_error(client, monkeypatch):
    """Test handling of HTTP error status when fetching historical data."""
    class MockResponse:
        def __init__(self, status=500, data=None):
            self.status = status
            self._data = data or {}

        async def json(self):
            return self._data

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    mock_response = MockResponse(status=500)
    mock_session = AsyncMock()
    mock_session.get.return_value.__aenter__.return_value = mock_response

    mock_client_session = AsyncMock()
    mock_client_session.__aenter__.return_value = mock_session

    monkeypatch.setattr('aiohttp.ClientSession', lambda: mock_client_session)

    symbols = ["BTC/USDT"]
    data = await client.fetch_historical_data(symbols, interval=5)
    # The client returns an empty dictionary on error
    assert isinstance(data, dict)
    assert not data, "Data should be empty when HTTP error occurs."


@pytest.mark.asyncio
async def test_fetch_historical_data_api_error(client, monkeypatch):
    """Test handling of an API-level error response from Kraken."""
    class MockResponse:
        def __init__(self, status=200, data=None):
            self.status = status
            self._data = data or {}

        async def json(self):
            return self._data

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    # Simulate an API error in the "error" field
    mock_data = {
        "error": ["EGeneral:Invalid arguments"],
        "result": {}
    }
    mock_response = MockResponse(data=mock_data)
    mock_session = AsyncMock()
    mock_session.get.return_value.__aenter__.return_value = mock_response

    mock_client_session = AsyncMock()
    mock_client_session.__aenter__.return_value = mock_session

    monkeypatch.setattr('aiohttp.ClientSession', lambda: mock_client_session)

    symbols = ["BTC/USDT"]
    data = await client.fetch_historical_data(symbols, interval=5)
    assert isinstance(data, dict)
    assert not data, "Expect empty data when Kraken returns API-level error."


@pytest.mark.asyncio
async def test_fetch_historical_data_exception(client, monkeypatch):
    """Test handling of network/other exceptions when fetching historical data."""
    async def mock_get(*args, **kwargs):
        raise Exception("Network error")

    mock_session = AsyncMock()
    mock_session.get.side_effect = mock_get

    mock_client_session = AsyncMock()
    mock_client_session.__aenter__.return_value = mock_session

    monkeypatch.setattr('aiohttp.ClientSession', lambda: mock_client_session)

    symbols = ["BTC/USDT"]
    data = await client.fetch_historical_data(symbols, interval=5)
    assert isinstance(data, dict)
    assert not data, "Expect empty data on exception."
