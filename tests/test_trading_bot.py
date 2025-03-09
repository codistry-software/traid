import pytest
from decimal import Decimal
import numpy as np
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from traid.trading_bot import TradingBot  # Using the correct module path


class TestTradingBot:
    @pytest.fixture
    def mock_client(self):
        client = MagicMock()
        client.get_latest_price = MagicMock(return_value=Decimal('100'))
        client.connect = AsyncMock()
        client.subscribe_prices = AsyncMock()
        client.fetch_historical_data = AsyncMock(return_value={
            'BTC/USDT': [
                {'close': 100, 'volume': 10, 'timestamp': 1000},
                {'close': 105, 'volume': 12, 'timestamp': 1060},
            ],
            'ETH/USDT': [
                {'close': 20, 'volume': 100, 'timestamp': 1000},
                {'close': 22, 'volume': 120, 'timestamp': 1060},
            ]
        })
        client.close = AsyncMock()
        return client