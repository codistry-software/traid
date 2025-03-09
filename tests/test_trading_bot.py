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

    def test_calculate_opportunity_scores(self, trading_bot):
        """Test opportunity score calculation."""
        # Setup coin data
        trading_bot.coin_data = {
            'BTC/USDT': {
                'prices': [90, 95, 100, 105, 110, 115, 120],
                'volumes': [10, 12, 15, 18, 20, 25, 30],
                'timestamps': [1000, 1060, 1120, 1180, 1240, 1300, 1360]
            },
            'ETH/USDT': {
                'prices': [18, 19, 20, 21, 22, 23, 24],
                'volumes': [100, 110, 120, 130, 140, 150, 160],
                'timestamps': [1000, 1060, 1120, 1180, 1240, 1300, 1360]
            }
        }

        # Use monkeypatch to override the method for the test duration
        original_score_method = trading_bot._calculate_coin_score

        def mock_score_method(symbol, prices, volumes):
            return 75 if symbol == 'BTC/USDT' else 65

        trading_bot._calculate_coin_score = mock_score_method

        try:
            scores = trading_bot._calculate_opportunity_scores()
            assert scores['BTC/USDT'] == 75
            assert scores['ETH/USDT'] == 65
        finally:
            # Restore the original method
            trading_bot._calculate_coin_score = original_score_method

    def test_calculate_rsi(self, trading_bot):
        """Test RSI calculation."""
        prices = np.array([100, 102, 104, 103, 105, 107, 109, 108, 110, 112,
                           111, 113, 115, 114, 116, 118, 120])
        rsi = trading_bot._calculate_rsi(prices)
        assert 0 <= rsi <= 100  # RSI must be between 0 and 100

    def test_get_top_opportunities(self, trading_bot):
        """Test getting top trading opportunities."""
        trading_bot.opportunity_scores = {
            'BTC/USDT': 75,
            'ETH/USDT': 85,
            'XRP/USDT': 65,
            'LTC/USDT': 70
        }

        top_2 = trading_bot._get_top_opportunities(2)
        assert len(top_2) == 2
        assert top_2[0][0] == 'ETH/USDT'
        assert top_2[0][1] == 85
        assert top_2[1][0] == 'BTC/USDT'
        assert top_2[1][1] == 75

    def test_get_best_opportunity(self, trading_bot):
        """Test getting the single best opportunity."""
        with patch.object(trading_bot, '_get_top_opportunities', return_value=[('ETH/USDT', 85)]):
            best = trading_bot._get_best_opportunity()
            assert best == 'ETH/USDT'
            trading_bot._get_top_opportunities.assert_called_once_with(1)

    def test_should_change_coin(self, trading_bot):
        """Test coin change determination logic."""
        trading_bot.active_symbol = 'BTC/USDT'
        trading_bot.opportunity_scores = {'BTC/USDT': 70, 'ETH/USDT': 85}

        # ETH score is 15 higher than BTC, should change
        better_coin = trading_bot._should_change_coin()
        assert better_coin == 'ETH/USDT'

        # If difference is less than 10, should not change
        trading_bot.opportunity_scores = {'BTC/USDT': 76, 'ETH/USDT': 85}
        better_coin = trading_bot._should_change_coin()
        assert better_coin is None

    @pytest.mark.asyncio
    async def test_switch_active_coin(self, trading_bot):
        """Test switching to a different trading coin."""
        trading_bot.active_symbol = 'BTC/USDT'
        trading_bot.positions['BTC/USDT'] = Decimal('0.5')
        trading_bot.allocated_balances['BTC/USDT'] = Decimal('200')
        trading_bot.available_balance = Decimal('300')

        with patch.object(trading_bot, '_execute_sell', return_value=True):
            await trading_bot._switch_active_coin('ETH/USDT')
            trading_bot._execute_sell.assert_called_once_with('BTC/USDT', Decimal('100'), Decimal('0.5'))
            assert trading_bot.active_symbol == 'ETH/USDT'
            assert trading_bot.allocated_balances['ETH/USDT'] > 0
            assert trading_bot.allocated_balances['BTC/USDT'] == 0

    def test_generate_trading_signal(self, trading_bot):
        """Test trading signal generation."""
        trading_bot.coin_data['BTC/USDT'] = {
            'prices': [100, 102, 104, 106, 108, 110, 112, 114, 116, 118, 120, 122, 124, 126, 128],
            'volumes': [10] * 15,
            'timestamps': [1000 + 60 * i for i in range(15)]
        }

        with patch.object(trading_bot, '_calculate_rsi', return_value=30):  # Oversold condition
            signal = trading_bot._generate_trading_signal('BTC/USDT')
            assert signal == 1  # Should generate a buy signal

        with patch.object(trading_bot, '_calculate_rsi', return_value=70):  # Overbought condition
            trading_bot.positions['BTC/USDT'] = Decimal('0.5')  # Need a position to sell
            signal = trading_bot._generate_trading_signal('BTC/USDT')
            assert signal == -1  # Should generate a sell signal

    def test_execute_buy(self, trading_bot):
        """Test buy execution."""
        trading_bot.allocated_balances['BTC/USDT'] = Decimal('500')
        result = trading_bot._execute_buy('BTC/USDT', Decimal('100'))

        assert result is True
        assert trading_bot.positions['BTC/USDT'] > 0
        assert trading_bot.allocated_balances['BTC/USDT'] < Decimal('500')
        assert len(trading_bot.execution_history['BTC/USDT']) == 1
        assert trading_bot.execution_history['BTC/USDT'][0]['action'] == 'buy'
        assert trading_bot.total_trades == 1

    def test_execute_sell(self, trading_bot):
        """Test sell execution."""
        trading_bot.positions['BTC/USDT'] = Decimal('0.5')
        trading_bot.allocated_balances['BTC/USDT'] = Decimal('200')

        # Add a previous buy to history for P/L calculation
        trading_bot.execution_history['BTC/USDT'] = [{
            "timestamp": 1000,
            "action": "buy",
            "symbol": "BTC/USDT",
            "price": 90.0,
            "volume": 0.5,
            "cost": 45.0,
            "balance_after": 155.0
        }]

        result = trading_bot._execute_sell('BTC/USDT', Decimal('100'))

        assert result is True
        assert 'BTC/USDT' not in trading_bot.positions  # Position should be closed
        assert trading_bot.allocated_balances['BTC/USDT'] > Decimal('200')  # Balance should increase
        assert len(trading_bot.execution_history['BTC/USDT']) == 2
        assert trading_bot.execution_history['BTC/USDT'][1]['action'] == 'sell'
        assert trading_bot.total_trades == 1
        assert trading_bot.profitable_trades == 1  # Sold at 100, bought at 90 -> profit

