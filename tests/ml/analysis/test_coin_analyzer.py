"""Tests for CoinOpportunityAnalyzer."""
from decimal import Decimal
import numpy as np
import pytest
from unittest.mock import patch, MagicMock
from traid.ml.analysis.coin_analyzer import CoinOpportunityAnalyzer


class TestCoinOpportunityAnalyzer:
    """Test suite for CoinOpportunityAnalyzer."""

    @pytest.fixture
    def analyzer(self):
        """Return a CoinOpportunityAnalyzer instance."""
        return CoinOpportunityAnalyzer(lookback_window=10)

    @pytest.fixture
    def test_symbol(self):
        """Return a test symbol."""
        return "BTC/USDT"

    def test_update_coin_data(self, analyzer, test_symbol):
        """Test updating coin data with new price points."""
        # Add some test data
        analyzer.update_coin_data(
            symbol=test_symbol,
            price=Decimal("50000"),
            volume=Decimal("1.5")
        )

        # Assertions
        assert test_symbol in analyzer.coin_data
        assert len(analyzer.coin_data[test_symbol]["prices"]) == 1
        assert analyzer.coin_data[test_symbol]["prices"][0] == 50000.0
        assert analyzer.coin_data[test_symbol]["volumes"][0] == 1.5

        # Add more data points to test lookback window
        for i in range(15):  # Add 15 more points (exceeds lookback_window of 10)
            analyzer.update_coin_data(
                symbol=test_symbol,
                price=Decimal(str(50000 + i * 100)),
                volume=Decimal(str(1.5 + i * 0.1))
            )

        # Check that only lookback_window points are kept
        assert len(analyzer.coin_data[test_symbol]["prices"]) == 10
        # First point should be removed, so first price should be 50600
        assert analyzer.coin_data[test_symbol]["prices"][0] == 50500.0

    @patch('traid.ml.features.technical_indicators.TechnicalIndicators.calculate_rsi')
    @patch('traid.ml.features.technical_indicators.TechnicalIndicators.calculate_macd')
    @patch('traid.ml.features.technical_indicators.TechnicalIndicators.calculate_bollinger_bands')
    def test_calculate_coin_score(self, mock_bb, mock_macd, mock_rsi, analyzer, test_symbol):
        """Test calculation of opportunity score for a coin."""
        # Setup mocks
        mock_rsi.return_value = np.array([25.0])  # Oversold - buying opportunity
        mock_macd.return_value = (
            np.array([0.02]),  # MACD line
            np.array([0.01]),  # Signal line
            np.array([0.01])  # Histogram
        )
        mock_bb.return_value = (
            np.array([52000.0]),  # Upper
            np.array([50000.0]),  # Middle
            np.array([48000.0])  # Lower
        )

        # Setup test data
        prices = np.array([50000.0, 50100.0, 50200.0, 50300.0, 50400.0])
        volumes = np.array([1.5, 1.6, 1.7, 1.8, 1.9])

        # Calculate score
        score = analyzer._calculate_coin_score(test_symbol, prices, volumes)

        # Assertions
        assert isinstance(score, int)
        assert 0 <= score <= 100
        # Score should be increased from 50 because of oversold RSI and bullish MACD
        assert score > 50

    def test_get_best_opportunities(self, analyzer):
        """Test retrieving best trading opportunities."""
        # Setup test data
        analyzer.opportunity_scores = {
            "BTC/USDT": 80,
            "ETH/USDT": 65,
            "SOL/USDT": 75,
            "XRP/USDT": 50,
            "ADA/USDT": 40
        }

        # Get top 3 opportunities
        top_opportunities = analyzer.get_best_opportunities(top_n=3)

        # Assertions
        assert len(top_opportunities) == 3
        assert top_opportunities[0][0] == "BTC/USDT"  # Highest score
        assert top_opportunities[0][1] == 80
        assert top_opportunities[1][0] == "SOL/USDT"  # Second highest
        assert top_opportunities[2][0] == "ETH/USDT"  # Third highest

    def test_should_change_coin(self, analyzer, test_symbol):
        """Test decision logic for changing coins."""
        # Setup test data
        analyzer.opportunity_scores = {
            "BTC/USDT": 80,
            "ETH/USDT": 65,
            "SOL/USDT": 95,  # Much better score than current
            "XRP/USDT": 50,
            "ADA/USDT": 40
        }

        # Test with current coin having good but not best score
        current_coin = "BTC/USDT"
        new_coin = analyzer.should_change_coin(current_coin)

        # Test should check the actual implementation
        assert new_coin is None
