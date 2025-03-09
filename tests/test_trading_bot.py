import pytest
from decimal import Decimal
import numpy as np
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from traid.trading_bot import TradingBot  # Using the correct module path


class TestTradingBot: