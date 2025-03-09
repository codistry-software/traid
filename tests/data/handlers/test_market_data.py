from traid.data.handlers.market_data import MarketData


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


def test_fetch_ohlcv_data():
    """Test if OHLCV data structure and method exists."""
    market_data = MarketData(
        symbol="BTC/USD",
        timeframe="1h"
    )

    data = market_data.get_ohlcv()
    assert isinstance(data, list)

    if data:
        first_candle = data[0]
        assert 'timestamp' in first_candle
        assert 'open' in first_candle
        assert 'high' in first_candle
        assert 'low' in first_candle
        assert 'close' in first_candle
        assert 'volume' in first_candle
