import pytest
from traid.data.market_data import MarketData


def test_market_data_initialization():
    """Test if MarketData class properly initializes with basic attributes."""
    market_data = MarketData(
        symbol="BTC/USDT",
        timeframe="1h"
    )

    assert isinstance(market_data, MarketData)
    assert market_data.symbol == "BTC/USDT"
    assert market_data.timeframe == "1h"
    assert hasattr(market_data, 'get_ohlcv')
