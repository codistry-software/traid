# TRAID Project Checklist & Architecture Decisions

## 1. Project Setup
- [x] Initialize Git repository
- [x] Create virtual environment
- [x] Setup basic project structure
- [x] Create requirements.txt
- [x] Setup basic CI/CD pipeline
- [x] Create initial test framework

## 2. Data Architecture
### ADR 1: Data Sources

- [x] Define which cryptocurrency data to use
    - All trading pairs available on Kraken
    - Focus on USDT pairs (e.g., BTC/USDT, ETH/USDT)
    - Include all market cap sizes for comprehensive testing
    - Filter out stablecoin pairs (USDT, USDC, DAI, etc.)

- [x] Choose data provider/API
    - Selected Kraken API
    - Using REST API for historical data
    - Using WebSocket for real-time data

- [x] Define data structure
    - Using standard OHLCV format:
        - timestamp: int (Unix timestamp)
        - open: float
        - high: float
        - low: float
        - close: float
        - volume: float
    - Additional data for real-time updates:
        - price: Decimal (current price)
        - volume: Decimal (24h volume)
        - timestamp: int (millisecond timestamp)

- [x] Implement data fetching
    - Implemented WebSocket connection for real-time data
    - Implemented REST API calls for historical OHLCV data
    - Created asset mapping for Kraken's symbol format (BTC→XBT)

- [x] Setup data storage
    - In-memory storage for real-time price data
    - Rolling window storage for technical analysis (50 data points)
    - Trade execution history for performance analysis

## 3. Trading Bot Architecture
### ADR 2: Trading Modes

- [x] Define trading modes
    - Single-coin mode: Focus on a single trading pair (BTC/USDT)
    - Multi-coin mode: Dynamically switch between coins based on opportunity scores

- [x] Design allocation strategy
    - Single-coin: Allocate entire portfolio to one symbol
    - Multi-coin: 80% allocation to best opportunity, able to switch between coins

### ADR 3: Core Components

- [x] Define bot architecture
    - Modular design with separate client and trading logic
    - Event-driven price updates via callbacks
    - Asynchronous execution using asyncio

- [x] Implement basic trading logic
    - Technical analysis based signal generation
    - RSI, moving averages, and volume analysis
    - Opportunity scoring system (0-100) for coin selection

- [x] Setup risk management
    - Position size limits (95% of allocated balance)
    - Minimum order size checks
    - Error handling in trading and analysis loops

- [x] Create position sizing logic
    - Dynamic sizing based on allocated balance
    - Support for partial position exits
    - Automatic balance reallocation on coin switching

- [x] Implement order execution
    - Buy execution with price validation
    - Sell execution with P&L tracking
    - Order execution history tracking

## 4. Technical Analysis Implementation
### ADR 4: Analysis Strategy

- [x] Choose technical indicators
    - RSI (Relative Strength Index) for overbought/oversold conditions
    - Short and long moving averages for trend detection
    - Volume analysis for momentum confirmation

- [x] Implement signal generation
    - Buy signals: RSI < 35 or (short MA > long MA and RSI < 65)
    - Sell signals: RSI > 65 or (short MA < long MA and RSI > 35)
    - Neutral signals when conditions aren't met

- [x] Create opportunity scoring system
    - Base score of 50 (neutral)
    - Adjust based on recent price changes
    - Adjust based on RSI values
    - Adjust based on MA trends
    - Adjust based on volume spikes
    - Clamped to 0-100 range

## 5. Testing Strategy
### ADR 5: Testing Framework

- [x] Unit tests
    - Created test fixtures for client and bot
    - Test individual methods in isolation
    - Mocking of external dependencies

- [ ] Integration tests
    - Test interaction between client and trading bot
    - Validate end-to-end functionality

- [ ] Backtesting framework
    - Historical data processing
    - Strategy performance evaluation

- [x] Performance metrics
    - Implemented tracking of:
      - Total trades
      - Win rate
      - Profit/loss tracking
      - Position P&L calculations
      - Portfolio value calculation

- [ ] Paper trading tests
    - Live testing without real money

## 6. User Interface
### ADR 6: Command Line Interface

- [x] User configuration
    - Initial balance input
    - Trading mode selection
    - Symbol selection (automatic or manual)

- [x] Status display
    - Real-time portfolio status updates
    - Position tracking with P&L
    - Trading opportunity scores
    - Session duration tracking

- [x] Performance reporting
    - Session summary on exit
    - Comprehensive P&L breakdown
    - Win rate calculation
    - Remaining position reporting

## 7. Project Structure
- [x] Implemented code organization
    - `traid/trading_bot.py`: Core trading bot implementation
    - `traid/kraken_client.py`: Kraken API client implementation
    - `traid/main.py`: User interface and entry point
    - `tests/`: Test directory for pytest test files

## Directory Structure
```
TRAID/
├── traid/
│   ├── __init__.py
│   ├── trading_bot.py    # Trading bot implementation
│   ├── kraken_client.py  # Kraken API client
│   └── main.py           # Entry point and CLI
├── tests/
│   ├── __init__.py
│   ├── test_trading_bot.py
│   └── test_kraken_client.py
├── requirements.txt
└── README.md
```

## Implementation Details

### main.py:
- Command-line interface for user configuration
- Fetches available trading pairs from Kraken
- Handles startup, execution, and graceful shutdown
- Error handling and user interruption

### trading_bot.py:
- Core trading logic implementation
- Technical analysis and signal generation
- Trade execution and position management
- Portfolio tracking and performance metrics
- Asynchronous operation with two main loops:
  - Analysis loop (5-minute interval)
  - Trading loop (1-second interval)

### kraken_client.py:
- WebSocket connection for real-time data
- REST API for historical data
- Symbol formatting and mapping
- Message handling and callback system

## Future Enhancements
- [ ] Implement machine learning models for improved signal generation
- [ ] Add database storage for historical trades and performance
- [ ] Create web dashboard for monitoring
- [ ] Implement additional trading strategies
- [ ] Add support for more exchanges