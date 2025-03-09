from decimal import Decimal
from typing import Dict, List, Optional
import asyncio
import time
import numpy as np


class TradingBot:
    # List of stable coins to exclude from trading
    STABLE_COINS = {'USDT', 'USDC', 'DAI', 'BUSD', 'UST', 'EURT', 'TUSD', 'GUSD', 'PAX', 'HUSD', 'EURS'}

    def __init__(
            self,
            symbols: List[str],
            timeframe: str,
            initial_balance: Decimal,
            client,
            single_coin_mode: bool = False
    ):
        """Initialize trading bot."""
        # Filter out stablecoins from symbols list
        self.symbols = []
        for s in symbols:
            # Expect a format like "BTC/USDT"
            try:
                base, quote = s.split('/')
            except ValueError:
                # If the symbol doesn't have '/', skip or handle differently
                continue

            # We only skip if the BASE is a stable coin
            if base not in self.STABLE_COINS:
                self.symbols.append(s)

        self.timeframe = timeframe
        self.initial_balance = initial_balance
        self.available_balance = initial_balance
        self.client = client
        self.single_coin_mode = single_coin_mode

        # Trading parameters - more aggressive settings
        self.max_trade_count = 10  # Increased from 5 to be more aggressive
        self.trade_cooldown = 60  # Reduced from 300 to be more aggressive (1 minute)
        self.last_trade_time = 0  # Timestamp of last trade

        # Set on_price_update callback
        self.client.on_price_update = self._handle_price_update

        # Trading state
        self.active_symbol = self.symbols[0] if single_coin_mode else None
        self.positions: Dict[str, Decimal] = {}
        self.execution_history: Dict[str, List[Dict]] = {symbol: [] for symbol in self.symbols}
        self.current_prices: Dict[str, Decimal] = {}
        self.allocated_balances: Dict[str, Decimal] = {
            symbol: (initial_balance if symbol == self.active_symbol and single_coin_mode else Decimal('0'))
            for symbol in self.symbols
        }

        # Technical analysis data
        self.coin_data: Dict[str, Dict] = {}
        self.opportunity_scores: Dict[str, int] = {}

        # Control flags
        self.is_running = False
        self._stop_event = asyncio.Event()
        self._tasks = []

        # Performance metrics
        self.total_trades = 0
        self.profitable_trades = 0
        self.total_profit_loss = Decimal('0')
        self.start_time = None

        # Print initialization message
        print(f"🚀 Trading Bot initialized in {'SINGLE' if single_coin_mode else 'MULTI'}-coin mode")
        print(f"👀 Monitoring {len(self.symbols)} trading pairs (stablecoins excluded)")
        print(f"💰 Initial balance: {self.initial_balance} USDT")