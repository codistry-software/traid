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

    def test_update_coin_data(self, trading_bot):
        """Test coin data update functionality."""
        trading_bot._update_coin_data("BTC/USDT", Decimal('120'), Decimal('30'))
        assert 120 in trading_bot.coin_data["BTC/USDT"]["prices"]
        assert 30 in trading_bot.coin_data["BTC/USDT"]["volumes"]

        # Test max length constraint
        for i in range(60):  # Add more than max_len=50 items
            trading_bot._update_coin_data("BTC/USDT", Decimal(i), Decimal(i))

        assert len(trading_bot.coin_data["BTC/USDT"]["prices"]) == 50
        assert trading_bot.coin_data["BTC/USDT"]["prices"][-1] == 59  # Should have the latest value

    @pytest.mark.asyncio
    async def test_start(self, trading_bot):
        """Test bot startup process."""
        with patch.object(trading_bot, '_calculate_opportunity_scores', return_value={}), \
                patch.object(trading_bot, '_get_top_opportunities', return_value=[('BTC/USDT', 80)]), \
                patch.object(trading_bot, '_print_portfolio_status'), \
                patch.object(asyncio, 'create_task', return_value=MagicMock()):
            await trading_bot.start()
            assert trading_bot.is_running is True
            assert trading_bot.start_time is not None
            trading_bot.client.connect.assert_called_once()
            trading_bot.client.subscribe_prices.assert_called_once_with(['BTC/USDT', 'ETH/USDT', 'XRP/USDT'])
            trading_bot.client.fetch_historical_data.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop(self, trading_bot):
        """Test bot shutdown process."""
        trading_bot.is_running = True

        # Create actual coroutines instead of MagicMocks
        async def dummy_coro():
            pass

        task1 = asyncio.create_task(dummy_coro())
        task2 = asyncio.create_task(dummy_coro())
        trading_bot._tasks = [task1, task2]

        with patch.object(trading_bot, '_print_summary'):
            await trading_bot.stop()
            assert trading_bot.is_running is False
            trading_bot.client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_analysis_loop(self, trading_bot):
        """Test the analysis loop functionality."""
        # Setup for single iteration of the loop
        trading_bot.is_running = True
        trading_bot._stop_event = MagicMock()
        trading_bot._stop_event.is_set.side_effect = [False, True]  # Run once then stop

        with patch.object(trading_bot, '_calculate_opportunity_scores'), \
                patch.object(trading_bot, '_get_top_opportunities', return_value=[('ETH/USDT', 90)]), \
                patch.object(trading_bot, '_should_change_coin', return_value='ETH/USDT'), \
                patch.object(trading_bot, '_switch_active_coin', new_callable=AsyncMock), \
                patch.object(trading_bot, '_print_portfolio_status'), \
                patch.object(asyncio, 'sleep', new_callable=AsyncMock):
            await trading_bot._analysis_loop()
            trading_bot._calculate_opportunity_scores.assert_called_once()
            trading_bot._switch_active_coin.assert_called_once_with('ETH/USDT')

    @pytest.mark.asyncio
    async def test_trading_loop(self, trading_bot):
        """Test the trading loop functionality."""
        trading_bot.is_running = True
        trading_bot.active_symbol = 'BTC/USDT'
        trading_bot.allocated_balances['BTC/USDT'] = Decimal('500')
        trading_bot._stop_event = MagicMock()
        trading_bot._stop_event.is_set.side_effect = [False, True]  # Run once then stop

        with patch.object(trading_bot, '_generate_trading_signal', return_value=1), \
                patch.object(trading_bot, '_execute_buy', return_value=True), \
                patch.object(trading_bot, '_print_portfolio_status'), \
                patch.object(asyncio, 'sleep', new_callable=AsyncMock):
            await trading_bot._trading_loop()
            trading_bot._generate_trading_signal.assert_called_once_with('BTC/USDT')
            trading_bot._execute_buy.assert_called_once_with('BTC/USDT', Decimal('100'))