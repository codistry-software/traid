"""Tests for MultiCoinTradingBot."""
import unittest
import asyncio
from decimal import Decimal
from unittest.mock import patch, MagicMock, AsyncMock
from traid.trading.multi_coin_bot import MultiCoinTradingBot


class TestMultiCoinTradingBot(unittest.TestCase):
    """Test suite for MultiCoinTradingBot."""

    def setUp(self):
        """Set up test case."""
        self.symbols = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
        self.timeframe = "1m"
        self.initial_balance = Decimal("1000")

        # Create bot with patched components
        with patch('traid.trading.multi_coin_bot.KrakenClient') as mock_client, \
                patch('traid.trading.multi_coin_bot.CoinOpportunityAnalyzer') as mock_analyzer, \
                patch('traid.trading.multi_coin_bot.TradingExecutor') as mock_executor:
            self.mock_client = MagicMock()
            self.mock_analyzer = MagicMock()
            self.mock_executor = MagicMock()

            mock_client.return_value = self.mock_client
            mock_analyzer.return_value = self.mock_analyzer
            mock_executor.return_value = self.mock_executor

            self.bot = MultiCoinTradingBot(
                symbols=self.symbols,
                timeframe=self.timeframe,
                initial_balance=self.initial_balance,
                update_interval=1  # Fast updates for testing
            )

    async def test_initialization(self):
        """Test bot initialization."""
        # Check basic properties
        self.assertEqual(self.bot.symbols, self.symbols)
        self.assertEqual(self.bot.timeframe, self.timeframe)
        self.assertEqual(self.bot.initial_balance, self.initial_balance)
        self.assertEqual(self.bot.available_balance, self.initial_balance)

        # Check component initialization
        self.assertEqual(len(self.bot.executors), len(self.symbols))
        self.assertEqual(self.bot.active_symbol, None)
        self.assertEqual(len(self.bot.allocated_balances), len(self.symbols))

        # All balances should start at zero
        for balance in self.bot.allocated_balances.values():
            self.assertEqual(balance, Decimal('0'))

    @patch('traid.trading.multi_coin_bot.KrakenClient')
    @patch('traid.trading.multi_coin_bot.CoinOpportunityAnalyzer')
    @patch('traid.trading.multi_coin_bot.TradingExecutor')
    async def test_start_stop(self, mock_executor, mock_analyzer, mock_client):
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
            symbols=self.symbols,
            timeframe=self.timeframe,
            initial_balance=self.initial_balance,
            update_interval=1
        )

        # Test start
        await bot.start()
        self.assertTrue(bot.is_running)
        mock_client_instance.connect.assert_called_once()
        mock_client_instance.subscribe_prices.assert_called_once_with(self.symbols)
        self.assertEqual(len(bot._tasks), 2)  # Should have 2 tasks running

        # Test stop
        await bot.stop()
        self.assertFalse(bot.is_running)
        mock_client_instance.close.assert_called_once()

    @patch('traid.trading.multi_coin_bot.asyncio.sleep', new_callable=AsyncMock)
    async def test_market_analysis_loop(self, mock_sleep):
        """Test market analysis loop."""
        # Setup mocks
        self.mock_analyzer.calculate_opportunity_scores.return_value = {
            "BTC/USDT": 80,
            "ETH/USDT": 65,
            "SOL/USDT": 75
        }
        self.mock_analyzer.get_best_opportunities.return_value = [
            ("BTC/USDT", 80),
            ("SOL/USDT", 75),
            ("ETH/USDT", 65)
        ]
        self.mock_analyzer.should_change_coin.return_value = None

        # Replace _switch_active_coin with mock
        self.bot._switch_active_coin = AsyncMock()

        # Mock _stop_event to run the loop once
        self.bot._stop_event = MagicMock()
        self.bot._stop_event.wait = AsyncMock()
        self.bot._stop_event.is_set = MagicMock(side_effect=[False, True])

        # Run the analysis loop
        await self.bot._market_analysis_loop()

        # Assertions
        self.mock_analyzer.calculate_opportunity_scores.assert_called_once()
        self.mock_analyzer.get_best_opportunities.assert_called_once_with(3)
        self.bot._switch_active_coin.assert_called_once_with("BTC/USDT")

    async def test_handle_price_update(self):
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

        # Call the handler
        self.bot._handle_price_update(update)

        # Assertions
        self.mock_executor.simulator.update_market_price.assert_called_once_with(
            "BTC/USDT", Decimal("50000")
        )
        self.mock_analyzer.update_coin_data.assert_called_once_with(
            "BTC/USDT", Decimal("50000"), Decimal("1.5")
        )

    @patch('traid.trading.multi_coin_bot.time.time')
    async def test_switch_active_coin(self, mock_time):
        """Test switching between coins."""
        # Setup mocks
        mock_time.return_value = 1634567890
        self.bot.active_symbol = "ETH/USDT"
        self.bot.allocated_balances["ETH/USDT"] = Decimal("300")
        self.bot.available_balance = Decimal("700")

        # Mock executor for active coin
        mock_eth_executor = MagicMock()
        mock_eth_executor.simulator.positions = {}
        self.bot.executors["ETH/USDT"] = mock_eth_executor

        # Switch to a new coin
        await self.bot._switch_active_coin("BTC/USDT")

        # Assertions
        self.assertEqual(self.bot.active_symbol, "BTC/USDT")
        self.assertEqual(self.bot.active_since, 1634567890)

        # ETH balance should be returned to available
        self.assertEqual(self.bot.allocated_balances["ETH/USDT"], Decimal("0"))

        # BTC should be allocated 70% of available (now 1000)
        self.assertEqual(self.bot.allocated_balances["BTC/USDT"], Decimal("700"))
        self.assertEqual(self.bot.available_balance, Decimal("300"))


if __name__ == '__main__':
    # Run async tests using asyncio
    loop = asyncio.get_event_loop()
    unittest.main()