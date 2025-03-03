"""Tests for Kraken WebSocket client."""
import unittest
import asyncio
from unittest.mock import patch, MagicMock
from decimal import Decimal
from traid.data.clients.kraken_client import KrakenClient


class TestKrakenClient(unittest.TestCase):
    """Test suite for KrakenClient."""

    def setUp(self):
        """Set up test case."""
        self.client = KrakenClient()
        self.test_symbol = "BTC/USDT"

    @patch('websockets.connect')
    async def test_connect(self, mock_connect):
        """Test WebSocket connection establishment."""
        # Setup mock
        mock_ws = MagicMock()
        mock_ws.open = True
        mock_connect.return_value = mock_ws

        # Test connect method
        result = await self.client.connect()

        # Assertions
        self.assertTrue(result)
        self.assertTrue(self.client.running)
        self.assertEqual(self.client.ws, mock_ws)
        mock_connect.assert_called_once_with(self.client.WS_URL)

    @patch('websockets.connect')
    async def test_subscribe_price(self, mock_connect):
        """Test subscribing to price updates."""
        # Setup mock
        mock_ws = MagicMock()
        mock_ws.open = True
        mock_connect.return_value = mock_ws

        # Connect and subscribe
        await self.client.connect()
        await self.client.subscribe_price(self.test_symbol)

        # Assertions
        formatted_symbol = self.client._format_symbol(self.test_symbol)
        self.assertIn(formatted_symbol, self.client.subscriptions)
        mock_ws.send.assert_called_once()

    @patch('websockets.connect')
    async def test_process_message(self, mock_connect):
        """Test processing WebSocket messages."""
        # Setup mock
        mock_ws = MagicMock()
        mock_ws.open = True
        mock_connect.return_value = mock_ws

        # Setup callback
        callback_called = False
        callback_data = None

        def on_price_update(data):
            nonlocal callback_called, callback_data
            callback_called = True
            callback_data = data

        self.client.on_price_update = on_price_update

        # Connect
        await self.client.connect()

        # Test ticker message
        ticker_message = '[1,{"c":["50000.00000","0.00100000"],"v":["1.00000000","10.00000000"],"p":["50000.00000","50000.00000"],"t":[10,100],"l":["49000.00000","49000.00000"],"h":["51000.00000","51000.00000"],"o":["50000.00000","50000.00000"]},"ticker","XBT/USDT"]'
        await self.client._process_message(ticker_message)

        # Assertions
        self.assertTrue(callback_called)
        self.assertEqual(callback_data["symbol"], "BTC/USDT")
        self.assertEqual(callback_data["data"]["price"], Decimal("50000.00000"))

    def test_format_symbol(self):
        """Test symbol formatting for Kraken API."""
        # Test BTC/USDT mapping
        formatted = self.client._format_symbol("BTC/USDT")
        self.assertEqual(formatted, "XBT/USDT")

        # Test ETH/USDT (no mapping needed)
        formatted = self.client._format_symbol("ETH/USDT")
        self.assertEqual(formatted, "ETH/USDT")

    def test_reverse_format_symbol(self):
        """Test reverse symbol formatting from Kraken API."""
        # Test XBT/USDT mapping back to BTC/USDT
        standard = self.client._reverse_format_symbol("XBT/USDT")
        self.assertEqual(standard, "BTC/USDT")

        # Test ETH/USDT (no mapping needed)
        standard = self.client._reverse_format_symbol("ETH/USDT")
        self.assertEqual(standard, "ETH/USDT")


if __name__ == '__main__':
    # Run async tests using asyncio
    loop = asyncio.get_event_loop()
    unittest.main()