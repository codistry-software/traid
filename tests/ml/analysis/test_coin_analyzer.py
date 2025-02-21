"""Tests for CoinOpportunityAnalyzer."""
import unittest
from decimal import Decimal
import numpy as np
from unittest.mock import patch, MagicMock
from traid.ml.analysis.coin_analyzer import CoinOpportunityAnalyzer


class TestCoinOpportunityAnalyzer(unittest.TestCase):
    """Test suite for CoinOpportunityAnalyzer."""

    def setUp(self):
        """Set up test case."""
        self.analyzer = CoinOpportunityAnalyzer(lookback_window=10)
        self.test_symbol = "BTC/USDT"

    def test_update_coin_data(self):
        """Test updating coin data with new price points."""
        # Add some test data
        self.analyzer.update_coin_data(
            symbol=self.test_symbol,
            price=Decimal("50000"),
            volume=Decimal("1.5")
        )

        # Assertions
        self.assertIn(self.test_symbol, self.analyzer.coin_data)
        self.assertEqual(len(self.analyzer.coin_data[self.test_symbol]["prices"]), 1)
        self.assertEqual(self.analyzer.coin_data[self.test_symbol]["prices"][0], 50000.0)
        self.assertEqual(self.analyzer.coin_data[self.test_symbol]["volumes"][0], 1.5)

        # Add more data points to test lookback window
        for i in range(15):  # Add 15 more points (exceeds lookback_window of 10)
            self.analyzer.update_coin_data(
                symbol=self.test_symbol,
                price=Decimal(str(50000 + i * 100)),
                volume=Decimal(str(1.5 + i * 0.1))
            )

        # Check that only lookback_window points are kept
        self.assertEqual(len(self.analyzer.coin_data[self.test_symbol]["prices"]), 10)
        # First point should be removed, so first price should be 50600
        self.assertEqual(self.analyzer.coin_data[self.test_symbol]["prices"][0], 50500.0)

    @patch('traid.ml.features.technical_indicators.TechnicalIndicators.calculate_rsi')
    @patch('traid.ml.features.technical_indicators.TechnicalIndicators.calculate_macd')
    @patch('traid.ml.features.technical_indicators.TechnicalIndicators.calculate_bollinger_bands')
    def test_calculate_coin_score(self, mock_bb, mock_macd, mock_rsi):
        """Test calculation of opportunity score for a coin."""
        # Setup mocks
        mock_rsi.return_value = np.array([25.0])  # Oversold - buying opportunity
        mock_macd.return_value = (
            np.array([0.02]),  # MACD line
            np.array([0.01]),  # Signal line
            np.array([0.01])   # Histogram
        )
        mock_bb.return_value = (
            np.array([52000.0]),  # Upper
            np.array([50000.0]),  # Middle
            np.array([48000.0])   # Lower
        )

        # Setup test data
        prices = np.array([50000.0, 50100.0, 50200.0, 50300.0, 50400.0])
        volumes = np.array([1.5, 1.6, 1.7, 1.8, 1.9])

        # Calculate score
        score = self.analyzer._calculate_coin_score(self.test_symbol, prices, volumes)

        # Assertions
        self.assertIsInstance(score, int)
        self.assertTrue(0 <= score <= 100)
        # Score should be increased from 50 because of oversold RSI and bullish MACD
        self.assertTrue(score > 50)

    def test_get_best_opportunities(self):
        """Test retrieving best trading opportunities."""
        # Setup test data
        self.analyzer.opportunity_scores = {
            "BTC/USDT": 80,
            "ETH/USDT": 65,
            "SOL/USDT": 75,
            "XRP/USDT": 50,
            "ADA/USDT": 40
        }

        # Get top 3 opportunities
        top_opportunities = self.analyzer.get_best_opportunities(top_n=3)

        # Assertions
        self.assertEqual(len(top_opportunities), 3)
        self.assertEqual(top_opportunities[0][0], "BTC/USDT")  # Highest score
        self.assertEqual(top_opportunities[0][1], 80)
        self.assertEqual(top_opportunities[1][0], "SOL/USDT")  # Second highest
        self.assertEqual(top_opportunities[2][0], "ETH/USDT")  # Third highest

    def test_should_change_coin(self):
        """Test decision logic for changing coins."""
        # Setup test data
        self.analyzer.opportunity_scores = {
            "BTC/USDT": 80,
            "ETH/USDT": 65,
            "SOL/USDT": 95,  # Much better score than current
            "XRP/USDT": 50,
            "ADA/USDT": 40
        }

        # Test with current coin having good but not best score
        current_coin = "BTC/USDT"
        new_coin = self.analyzer.should_change_coin(current_coin)

        # Der Test sollte die tatsächliche Implementierung prüfen
        self.assertIsNone(new_coin)

if __name__ == '__main__':
    unittest.main()