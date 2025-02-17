"""Tests for Kraken WebSocket client."""
import pytest
from unittest.mock import patch, Mock, AsyncMock
import json
from traid.data.clients.kraken_client import KrakenClient


def test_kraken_client_initialization():
    """Test if KrakenClient initializes correctly."""
    client = KrakenClient()
    assert isinstance(client, KrakenClient)
    assert client.WS_URL == "wss://ws.kraken.com"


@pytest.mark.asyncio
async def test_websocket_connection():
    """Test WebSocket connection establishment."""
    client = KrakenClient()

    mock_ws = AsyncMock()
    with patch('websockets.connect', return_value=mock_ws):
        await client.connect()
        assert client.ws == mock_ws


@pytest.mark.asyncio
async def test_price_subscription():
    """Test price update subscription."""
    client = KrakenClient()
    mock_ws = AsyncMock()

    with patch('websockets.connect', return_value=mock_ws):
        await client.connect()
        await client.subscribe_price("BTC/USD")

        expected_message = {
            "event": "subscribe",
            "pair": ["XBT/USD"],
            "subscription": {"name": "ticker"}
        }

        mock_ws.send.assert_called_with(json.dumps(expected_message))


@pytest.mark.asyncio
async def test_price_update_handling():
    """Test handling of price updates."""
    client = KrakenClient()
    received_prices = []

    def on_price_update(price):
        received_prices.append(price)

    client.on_price_update = on_price_update
    mock_ws = AsyncMock()

    # Mock a price update message
    mock_message = [
        0,
        {"c": ["50000.0"]},
        "ticker",
        "XBT/USD"
    ]

    with patch('websockets.connect', return_value=mock_ws):
        await client.connect()
        mock_ws.recv.return_value = json.dumps(mock_message)
        await client._process_message()

        assert len(received_prices) == 1
        assert received_prices[0]["price"] == "50000.0"
        assert received_prices[0]["symbol"] == "BTC/USD"


def test_symbol_formatting():
    """Test trading pair symbol formatting."""
    client = KrakenClient()
    assert client._format_symbol("BTC/USD") == "XBT/USD"
    assert client._format_symbol("ETH/USD") == "ETH/USD"
    assert client._format_symbol("BTC/USDT") == "XBT/USDT"