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
        assert call_args[1]['params']['pair'] == "BTC/USD"
        assert call_args[1]['params']['interval'] == "1h"


def test_get_ohlcv_error_handling():
    """Test if get_ohlcv properly handles API errors."""
    with patch('requests.get') as mock_get:
        # Setup mock error response
        mock_response = Mock()
        mock_response.json.return_value = {
            "error": ["EAPI:Invalid arguments"]
        }
        mock_get.return_value = mock_response

        client = KrakenClient()
        response = client.get_ohlcv("INVALID/PAIR", "1h")

        assert "error" in response
        assert response["error"][0] == "EAPI:Invalid arguments"
