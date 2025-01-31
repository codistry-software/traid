import pytest
from traid.data.models.ohlcv import OHLCV


def test_ohlcv_initialization():
    """Test if OHLCV class properly initializes with correct attributes."""
    ohlcv = OHLCV(
        timestamp=1707566400,
        open=48200.1,
        high=48300.2,
        low=48100.3,
        close=48250.4,
        volume=10.5
    )

    assert isinstance(ohlcv, OHLCV)
    assert ohlcv.timestamp == 1707566400
    assert ohlcv.open == 48200.1
    assert ohlcv.high == 48300.2
    assert ohlcv.low == 48100.3
    assert ohlcv.close == 48250.4
    assert ohlcv.volume == 10.5


def test_from_kraken_data():
    """Test if OHLCV correctly parses Kraken data format."""
    raw_data = [1707566400, "48200.1", "48300.2", "48100.3", "48250.4", "48225.5", "10.5", 100]

    ohlcv = OHLCV.from_kraken_data(raw_data)

    assert isinstance(ohlcv, OHLCV)
    assert ohlcv.timestamp == 1707566400
    assert ohlcv.open == 48200.1
    assert ohlcv.high == 48300.2
    assert ohlcv.low == 48100.3
    assert ohlcv.close == 48250.4
    assert ohlcv.volume == 10.5


def test_from_kraken_data_invalid():
    """Test if from_kraken_data properly handles invalid data."""
    invalid_data = [1707566400, "48200.1"]  # Missing required fields

    with pytest.raises(ValueError) as exc_info:
        OHLCV.from_kraken_data(invalid_data)

    assert "Invalid Kraken candle data format" in str(exc_info.value)


def test_to_dict():
    """Test if to_dict returns correct dictionary format."""
    ohlcv = OHLCV(
        timestamp=1707566400,
        open=48200.1,
        high=48300.2,
        low=48100.3,
        close=48250.4,
        volume=10.5
    )

    result = ohlcv.to_dict()

    assert isinstance(result, dict)
    assert result['timestamp'] == 1707566400
    assert result['open'] == 48200.1
    assert result['high'] == 48300.2
    assert result['low'] == 48100.3
    assert result['close'] == 48250.4
    assert result['volume'] == 10.5


def test_parse_kraken_response():
    """Test if parse_kraken_response correctly handles full API response."""
    response = {
        "result": {
            "XXBTZUSD": [
                [1707566400, "48200.1", "48300.2", "48100.3", "48250.4", "48225.5", "10.5", 100],
                [1707570000, "48250.4", "48400.5", "48200.6", "48350.7", "48325.8", "11.2", 120]
            ]
        }
    }

    result = OHLCV.parse_kraken_response(response)

    assert isinstance(result, list)
    assert len(result) == 2
    assert all(isinstance(item, OHLCV) for item in result)


def test_parse_kraken_response_empty():
    """Test if parse_kraken_response handles empty or invalid responses."""
    empty_response = {}
    result = OHLCV.parse_kraken_response(empty_response)
    assert result == []

    invalid_response = {"result": {}}
    result = OHLCV.parse_kraken_response(invalid_response)
    assert result == []