"""Tests for MultiCoinTradingBot."""
import asyncio
from decimal import Decimal
from unittest.mock import patch, MagicMock, AsyncMock

import pytest

from traid.trading.multi_coin_bot import MultiCoinTradingBot


class TestMultiCoinTradingBot:
    """Test suite for MultiCoinTradingBot."""

    @pytest.fixture
    def symbols(self):
        """Return symbols fixture."""
        return ["BTC/USDT", "ETH/USDT", "SOL/USDT"]

    @pytest.fixture
    def timeframe(self):
        """Return timeframe fixture."""
        return "1m"

    @pytest.fixture
    def initial_balance(self):
        """Return initial balance fixture."""
        return Decimal("1000")

    @pytest.fixture
    def bot_components(self):
        """Return mocked bot components."""
        with patch('traid.trading.multi_coin_bot.KrakenClient') as mock_client, \
                patch('traid.trading.multi_coin_bot.CoinOpportunityAnalyzer') as mock_analyzer, \
                patch('traid.trading.multi_coin_bot.TradingExecutor') as mock_executor:
            mock_client_instance = MagicMock()
            mock_analyzer_instance = MagicMock()
            mock_executor_instance = MagicMock()

            mock_client.return_value = mock_client_instance
            mock_analyzer.return_value = mock_analyzer_instance
            mock_executor.return_value = mock_executor_instance

            yield {
                'client': mock_client_instance,
                'analyzer': mock_analyzer_instance,
                'executor': mock_executor_instance
            }

    @pytest.fixture
    def bot(self, symbols, timeframe, initial_balance, bot_components):
        """Return MultiCoinTradingBot instance with mocked components."""
        bot = MultiCoinTradingBot(
            symbols=symbols,
            timeframe=timeframe,
            initial_balance=initial_balance,
            update_interval=1  # Fast updates for testing
        )
        return bot

    @pytest.mark.asyncio
    async def test_initialization(self, bot, symbols, timeframe, initial_balance):
        """Test bot initialization."""
        # Check basic properties
        assert bot.symbols == symbols
        assert bot.timeframe == timeframe
        assert bot.initial_balance == initial_balance
        assert bot.available_balance == initial_balance

        # Check component initialization
        assert len(bot.executors) == len(symbols)
        assert bot.active_symbol is None
        assert len(bot.allocated_balances) == len(symbols)

        # All balances should start at zero
        for balance in bot.allocated_balances.values():
            assert balance == Decimal('0')

    @patch('traid.trading.multi_coin_bot.KrakenClient')
    @patch('traid.trading.multi_coin_bot.CoinOpportunityAnalyzer')
    @patch('traid.trading.multi_coin_bot.TradingExecutor')
    @pytest.mark.asyncio
    async def test_start_stop(self, mock_executor, mock_analyzer, mock_client, symbols, timeframe, initial_balance):
        """Test bot start and stop."""
        # Setup mocks
        mock_client_instance = AsyncMock()
        mock_client_instance.connect = AsyncMock(return_value=True)
        mock_client_instance.subscribe_prices = AsyncMock()
        mock_client_instance.close = AsyncMock()

        mock_client.return_value = mock_client_instance
        mock_analyzer.return_value = MagicMock()
        mock_executor.return_value = MagicMock()

        # Create bot with mocks
        bot = MultiCoinTradingBot(
            symbols=symbols,
            timeframe=timeframe,
            initial_balance=initial_balance,
            update_interval=1
        )

        # Test start
        await bot.start()
        assert bot.is_running
        mock_client_instance.connect.assert_called_once()
        mock_client_instance.subscribe_prices.assert_called_once_with(symbols)
        assert len(bot._tasks) == 2  # Should have 2 tasks running

        # Test stop
        await bot.stop()
        assert not bot.is_running
        mock_client_instance.close.assert_called_once()

    @pytest.mark.asyncio
    @patch('traid.trading.multi_coin_bot.asyncio.sleep', new_callable=AsyncMock)
    async def test_market_analysis_loop(self, mock_sleep, bot, bot_components):
        """Test market analysis loop."""
        # Setup mocks
        analyzer = bot_components['analyzer']
        analyzer.calculate_opportunity_scores.return_value = {
            "BTC/USDT": 80,
            "ETH/USDT": 65,
            "SOL/USDT": 75
        }
        analyzer.get_best_opportunities.return_value = [
            ("BTC/USDT", 80),
            ("SOL/USDT", 75),
            ("ETH/USDT", 65)
        ]
        analyzer.should_change_coin.return_value = None

        # Replace _switch_active_coin with mock
        bot._switch_active_coin = AsyncMock()

        # Mock _stop_event to run the loop once
        bot._stop_event = MagicMock()
        bot._stop_event.wait = AsyncMock()
        bot._stop_event.is_set = MagicMock(side_effect=[False, True])

        # Run the analysis loop
        await bot._market_analysis_loop()

        # Assertions
        analyzer.calculate_opportunity_scores.assert_called_once()
        analyzer.get_best_opportunities.assert_called_once_with(3)
        bot._switch_active_coin.assert_called_once_with("BTC/USDT")

    @pytest.mark.asyncio
    async def test_handle_price_update(self, bot, bot_components):
        """Test handling of price updates."""
        # Setup test data
        update = {
            "symbol": "BTC/USDT",
            "data": {
                "price": Decimal("50000"),
                "volume": Decimal("1.5"),
                "timestamp": 1634567890000
            }
        }

        executor = bot_components['executor']
        analyzer = bot_components['analyzer']

        # Call the handler
        bot._handle_price_update(update)

        # Assertions
        executor.simulator.update_market_price.assert_called_once_with(
            "BTC/USDT", Decimal("50000")
        )
        analyzer.update_coin_data.assert_called_once_with(
            "BTC/USDT", Decimal("50000"), Decimal("1.5")
        )

    @pytest.mark.asyncio
    @patch('traid.trading.multi_coin_bot.time.time')
    async def test_switch_active_coin(self, mock_time, bot):
        """Test switching between coins."""
        # Setup mocks
        mock_time.return_value = 1634567890
        bot.active_symbol = "ETH/USDT"
        bot.allocated_balances["ETH/USDT"] = Decimal("300")
        bot.available_balance = Decimal("700")

        # Mock executor for active coin
        mock_eth_executor = MagicMock()
        mock_eth_executor.simulator.positions = {}
        bot.executors["ETH/USDT"] = mock_eth_executor

        # Switch to a new coin
        await bot._switch_active_coin("BTC/USDT")

        # Assertions
        assert bot.active_symbol == "BTC/USDT"
        assert bot.active_since == 1634567890

        # ETH balance should be returned to available
        assert bot.allocated_balances["ETH/USDT"] == Decimal("0")

        # BTC should be allocated 70% of available (now 1000)
        assert bot.allocated_balances["BTC/USDT"] == Decimal("700")
        assert bot.available_balance == Decimal("300")
