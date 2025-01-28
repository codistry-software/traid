from typing import Optional


class MarketData:
    """Class for handling market data operations.

    Attributes:
        symbol: Trading pair symbol (e.g. 'BTC/USDT')
        timeframe: Timeframe for the market data (e.g. '1h', '15m')
    """

    def __init__(
            self,
            symbol: str,
            timeframe: str
    ) -> None:
        self.symbol = symbol
        self.timeframe = timeframe

    def get_ohlcv(self) -> None:
        """Fetch OHLCV (Open, High, Low, Close, Volume) data.

        Not implemented yet.
        """
        pass