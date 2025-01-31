import pytest
from unittest.mock import patch, Mock
from traid.data.clients.kraken_client import KrakenClient


def test_kraken_client_initialization():
    """Test if KrakenClient initializes with correct base URL."""
    client = KrakenClient()
    assert isinstance(client, KrakenClient)
    assert client.BASE_URL == "https://api.kraken.com/0/public"

