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


def test_parse_ohlcv_response():
    """Test if OHLCV response is correctly parsed"""
    market_data = MarketData(
        symbol="BTC/USD",
        timeframe="1h"
    )

    # Mock Kraken API response format
    mock_response = {
        "result": {
            "XXBTZUSD": [
                # timestamp, open, high, low, close, vwap, volume, count
                [1707566400, "48200.1", "48300.2", "48100.3", "48250.4", "48225.5", "10.5", 100]
            ]
        }
    }

    result = market_data._parse_ohlcv_response(mock_response)

    assert len(result) == 1
    candle = result[0]
    assert candle['timestamp'] == 1707566400
    assert candle['open'] == 48200.1
    assert candle['high'] == 48300.2
    assert candle['low'] == 48100.3
    assert candle['close'] == 48250.4
    assert candle['volume'] == 10.5
