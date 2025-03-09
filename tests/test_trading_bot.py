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

    @pytest.fixture
    def trading_bot(self, mock_client):
        symbols = ['BTC/USDT', 'ETH/USDT', 'XRP/USDT']
        bot = TradingBot(
            symbols=symbols,
            timeframe='1h',
            initial_balance=Decimal('1000'),
            client=mock_client,
            single_coin_mode=False
        )
        return bot

    @pytest.fixture
    def single_coin_bot(self, mock_client):
        symbols = ['BTC/USDT']
        bot = TradingBot(
            symbols=symbols,
            timeframe='1h',
            initial_balance=Decimal('1000'),
            client=mock_client,
            single_coin_mode=True
        )
        return bot

    def test_init(self, trading_bot):
        """Test initialization of trading bot."""
        assert trading_bot.symbols == ['BTC/USDT', 'ETH/USDT', 'XRP/USDT']
        assert trading_bot.initial_balance == Decimal('1000')
        assert trading_bot.available_balance == Decimal('1000')
        assert trading_bot.single_coin_mode is False
        assert trading_bot.active_symbol is None
        assert trading_bot.positions == {}
        assert 'BTC/USDT' in trading_bot.execution_history

    def test_init_single_coin(self, single_coin_bot):
        """Test initialization in single coin mode."""
        assert single_coin_bot.symbols == ['BTC/USDT']
        assert single_coin_bot.active_symbol == 'BTC/USDT'
        assert single_coin_bot.allocated_balances['BTC/USDT'] == Decimal('1000')
        assert single_coin_bot.single_coin_mode is True

    def test_handle_price_update(self, trading_bot):
        """Test price update handling."""
        update = {
            "symbol": "BTC/USDT",
            "data": {"price": Decimal('110'), "volume": Decimal('20')}
        }
        trading_bot._handle_price_update(update)
        assert trading_bot.current_prices["BTC/USDT"] == Decimal('110')
        assert 110 in trading_bot.coin_data["BTC/USDT"]["prices"]
        assert 20 in trading_bot.coin_data["BTC/USDT"]["volumes"]