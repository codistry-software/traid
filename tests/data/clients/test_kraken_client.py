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
    async def test_subscribe_ohlcv(self, mock_connect):
        """Test subscribing to OHLCV updates."""
        # Setup mock
        mock_ws = MagicMock()
        mock_ws.open = True
        mock_connect.return_value = mock_ws

        # Connect and subscribe to OHLCV
        await self.client.connect()
        await self.client.subscribe_ohlcv(self.test_symbol, interval=5)

        # Assertions
        formatted_symbol = self.client._format_symbol(self.test_symbol)
        mock_ws.send.assert_called_once()
        # Check if the correct message was sent
        call_args = mock_ws.send.call_args[0][0]
        self.assertIn('"event":"subscribe"', call_args)
        self.assertIn('"name":"ohlc"', call_args)
        self.assertIn('"interval":5', call_args)
        self.assertIn(formatted_symbol, call_args)

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

    def test_get_ohlcv_no_data(self):
        """Test getting OHLCV data when no data exists for the symbol."""
        # Setup - ensure no data for test symbol
        self.client.ohlcv_data = {}

        # Act
        result = self.client.get_ohlcv(self.test_symbol)

        # Assert
        self.assertIsNone(result)

    def test_get_ohlcv_with_data(self):
        """Test getting OHLCV data when data exists."""
        # Setup test data
        self.client.ohlcv_data = {
            "BTC/USDT": [
                {"timestamp": 1000, "open": Decimal("30000"), "high": Decimal("31000"),
                 "low": Decimal("29500"), "close": Decimal("30500"), "volume": Decimal("100")},
                {"timestamp": 2000, "open": Decimal("30500"), "high": Decimal("32000"),
                 "low": Decimal("30400"), "close": Decimal("31500"), "volume": Decimal("150")},
                {"timestamp": 3000, "open": Decimal("31500"), "high": Decimal("33000"),
                 "low": Decimal("31000"), "close": Decimal("32500"), "volume": Decimal("200")},
            ]
        }

        # Test with default limit (all data)
        result = self.client.get_ohlcv(self.test_symbol)

        # Assertions
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0]["timestamp"], 1000)
        self.assertEqual(result[-1]["close"], Decimal("32500"))

        # Test with specific limit
        result_limited = self.client.get_ohlcv(self.test_symbol, limit=2)

        # Assertions for limited result
        self.assertEqual(len(result_limited), 2)
        self.assertEqual(result_limited[0]["timestamp"], 2000)
        self.assertEqual(result_limited[1]["timestamp"], 3000)

    @patch('websockets.connect')
    async def test_process_ohlcv_message(self, mock_connect):
        """Test processing OHLCV WebSocket messages."""
        # Setup mock
        mock_ws = MagicMock()
        mock_ws.open = True
        mock_connect.return_value = mock_ws

        # Connect
        await self.client.connect()

        # Test OHLCV message
        ohlc_message = '[42,["1617592800","59000.1","59100.8","58900.0","59050.5","0.0","10.12345678",100],"ohlc","XBT/USDT"]'
        await self.client._process_message(ohlc_message)

        # Assertions
        self.assertIn("BTC/USDT", self.client.ohlcv_data)
        candle = self.client.ohlcv_data["BTC/USDT"][0]
        self.assertEqual(candle["timestamp"], 1617592800)
        self.assertEqual(candle["open"], Decimal("59000.1"))
        self.assertEqual(candle["high"], Decimal("59100.8"))
        self.assertEqual(candle["low"], Decimal("58900.0"))
        self.assertEqual(candle["close"], Decimal("59050.5"))
        self.assertEqual(candle["volume"], Decimal("10.12345678"))


if __name__ == '__main__':
    # Run async tests using asyncio
    loop = asyncio.get_event_loop()
    unittest.main()
