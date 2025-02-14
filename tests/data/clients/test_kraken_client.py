import pytest
from unittest.mock import patch, Mock
from traid.data.clients.kraken_client import KrakenClient


def test_kraken_client_initialization():
    """Test if KrakenClient initializes with correct base URL."""
    client = KrakenClient()
    assert isinstance(client, KrakenClient)
    assert client.BASE_URL == "https://api.kraken.com/0/public"


def test_get_ohlcv_request():
    """Test if get_ohlcv makes correct API request."""
    with patch('requests.get') as mock_get:
        # Setup mock response
        mock_response = Mock()
        mock_response.json.return_value = {"result": {}}
        mock_get.return_value = mock_response

        client = KrakenClient()
        response = client.get_ohlcv("BTC/USD", "1h")

        # Verify the request
        mock_get.assert_called_once()
        call_args = mock_get.call_args

        # Check URL
        assert call_args[0][0] == f"{client.BASE_URL}/OHLC"

        # Check parameters
        params = call_args[1]['params']
        assert params['pair'] == "XBTUSD"
        assert params['interval'] == "60"


def test_get_ohlcv_error_handling():
    """Test if get_ohlcv properly handles API errors."""
    with patch('requests.get') as mock_get:
        # Setup mock error response
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.json.return_value = {
            "error": ["EAPI:Invalid arguments"]
        }
        mock_get.return_value = mock_response

        client = KrakenClient()
        response = client.get_ohlcv("INVALID/PAIR", "1h")

        assert "error" in response
        assert response["error"][0] == "EAPI:Invalid arguments"


def test_timeframe_conversion():
    """Test timeframe conversion to minutes."""
    client = KrakenClient()

    assert client._convert_timeframe("1m") == "1"
    assert client._convert_timeframe("15m") == "15"
    assert client._convert_timeframe("1h") == "60"
    assert client._convert_timeframe("4h") == "240"
    assert client._convert_timeframe("1d") == "1440"


def test_symbol_formatting():
    """Test trading pair symbol formatting."""
    client = KrakenClient()

    assert client._format_symbol("BTC/USD") == "XBTUSD"
    assert client._format_symbol("ETH/USD") == "ETHUSD"
    assert client._format_symbol("BTC/USDT") == "XBTUSDT"
