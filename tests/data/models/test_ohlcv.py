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

