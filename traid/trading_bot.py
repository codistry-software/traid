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

    def _handle_price_update(self, update: Dict) -> None:
        """Handle price updates from WebSocket."""
        symbol = update["symbol"]
        price = update["data"]["price"]
        volume = update["data"]["volume"]

        # Update current prices
        self.current_prices[symbol] = price

        # Update coin data for analysis
        self._update_coin_data(symbol, price, volume)

    def _update_coin_data(self, symbol: str, price: Decimal, volume: Decimal) -> None:
        """Update historical data for a coin."""
        if symbol not in self.coin_data:
            self.coin_data[symbol] = {
                'prices': [],
                'volumes': [],
                'timestamps': []
            }

        timestamp = int(time.time())

        # Add new data point
        self.coin_data[symbol]['prices'].append(float(price))
        self.coin_data[symbol]['volumes'].append(float(volume))
        self.coin_data[symbol]['timestamps'].append(timestamp)

        # Limit the history length
        max_history = 50
        if len(self.coin_data[symbol]['prices']) > max_history:
            self.coin_data[symbol]['prices'] = self.coin_data[symbol]['prices'][-max_history:]
            self.coin_data[symbol]['volumes'] = self.coin_data[symbol]['volumes'][-max_history:]
            self.coin_data[symbol]['timestamps'] = self.coin_data[symbol]['timestamps'][-max_history:]

    async def start(self) -> None:
        """Start the trading bot."""
        if self.is_running:
            return

        self.is_running = True
        self._stop_event.clear()
        self.start_time = int(time.time())

        # Connect to WebSocket and subscribe to symbols
        print("📡 Connecting to Kraken WebSocket API...")
        await self.client.connect()

        print(f"🔔 Subscribing to {len(self.symbols)} trading pairs...")
        await self.client.subscribe_prices(self.symbols)

        # Fetch historical data
        print("📊 Fetching historical data...")
        historical_data = await self.client.fetch_historical_data(
            symbols=self.symbols,
            interval=5,
            limit=50
        )

        # Load historical data
        for symbol, ohlcv_data in historical_data.items():
            self.coin_data[symbol] = {
                'prices': [candle['close'] for candle in ohlcv_data],
                'volumes': [candle['volume'] for candle in ohlcv_data],
                'timestamps': [candle['timestamp'] for candle in ohlcv_data]
            }

        # Calculate initial opportunity scores
        self._calculate_opportunity_scores()

        # Print top opportunities
        top_opportunities = self._get_top_opportunities(5)
        print("\n🔥 Initial Top Trading Opportunities:")
        for symbol, score in top_opportunities:
            print(f"  {symbol}: Score {score}/100")

        # Set initial active symbol
        if not self.single_coin_mode:
            top_coin = self._get_best_opportunity()
            if top_coin:
                print(f"\n🎯 Selected {top_coin} as initial trading target")
                await self._switch_active_coin(top_coin)
        else:
            print(f"\n🎯 Trading single coin: {self.active_symbol}")

        # Start the trading loops
        self._tasks = [
            asyncio.create_task(self._analysis_loop()),
            asyncio.create_task(self._trading_loop())
        ]

        print("\n✅ Trading bot is now active")
        print(f"💪 Strategy: {'AGGRESSIVE' if not self.single_coin_mode else 'SINGLE-COIN FOCUS'}")
        self._print_portfolio_status()