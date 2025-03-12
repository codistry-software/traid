<p align="center">
  <br />
  <a href="https://github.com/codistry-software/traid">
<img src="https://raw.githubusercontent.com/codistry-software/traid/main/docs/logo" width="200px" alt="TRAID Logo">  </a>
</p>

<p align="center">
  High-performance cryptocurrency trading bot with technical analysis and multi-coin trading strategies
</p>

<p align="center">
  <a title="MIT License" href="LICENSE">
    <img src="https://img.shields.io/badge/license-MIT-blue" alt="MIT License" />
  </a>
  <a title="Python Version" href="https://www.python.org/downloads/">
    <img src="https://img.shields.io/badge/python-3.9%2B-blue" alt="Python 3.9+" />
  </a>
  <a title="Test Coverage" href="https://github.com/yourusername/traid/actions">
    <img src="https://img.shields.io/badge/coverage-95%25-brightgreen" alt="95% Test Coverage" />
  </a>
  <br />
  <br />
  <br />
</p>

## What is TRAID?

TRAID is a high-performance cryptocurrency trading bot that leverages technical analysis to identify trading opportunities across multiple exchanges. It supports both single-coin focused trading and dynamic multi-coin trading strategies, automatically switching between assets based on market conditions and opportunities.

```bash
# Install dependencies
pip install -r requirements.txt

# Run the bot
python -m traid.main

# Listening to market data and executing trades
```

## Features

- **Real-time Market Analysis**: WebSocket connections to Kraken for live price and volume data
- **Technical Indicators**: RSI, Moving Averages, and Volume analysis
- **Trading Modes**:
  - Single-coin mode: Focus on a specific trading pair (e.g. BTC/USDT)
  - Multi-coin mode: Dynamically switch between coins based on opportunity scoring
- **Opportunity Scoring**: Proprietary 0-100 scoring system to rank trading opportunities
- **Risk Management**: Position sizing, stop-loss, and balance allocation safeguards
- **Comprehensive Reporting**: Detailed trading session statistics and performance tracking

## Installation

### Prerequisites

- Python 3.9 or higher
- pip package manager

### Installation Steps

1. Clone the repository:
   ```bash
   git clone https://github.com/codistry-software/traid.git
   cd traid
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the bot:
   ```bash
   python -m traid.main
   ```

## Usage

When you start the bot, you'll be prompted to:

1. Enter your initial portfolio value in USDT
2. Select a trading mode:
   - Single-coin mode (focused on BTC/USDT)
   - Multi-coin mode (analyzes all available trading pairs)

The bot will then:
- Connect to Kraken's WebSocket API
- Fetch historical market data
- Calculate initial opportunity scores
- Begin trading based on technical signals
- Provide real-time portfolio updates

Example output:
```
🚀 Trading Bot initialized in MULTI-coin mode
👀 Monitoring 25 trading pairs (stablecoins excluded)
💰 Initial balance: 1000.00 USDT

🔥 Initial Top Trading Opportunities:
  SOL/USDT: Score 78/100
  ETH/USDT: Score 65/100
  BTC/USDT: Score 62/100

🎯 Selected SOL/USDT as initial trading target
💰 Allocated 800.00 USDT to SOL/USDT

✅ Trading bot is now active
```

## Project Structure

```
traid/
├── __init__.py
├── trading_bot.py    # Core trading logic
├── kraken_client.py  # Kraken API client
└── main.py           # Entry point and CLI
tests/
├── __init__.py
├── test_trading_bot.py
└── test_kraken_client.py
requirements.txt
README.md
LICENSE
```

## Trading Strategy

The default strategy uses a combination of technical indicators:

- **Buy Signals**: 
  - RSI < 35 (oversold condition)
  - Short MA > Long MA and RSI < 65 (uptrend confirmation)

- **Sell Signals**:
  - RSI > 65 (overbought condition)
  - Short MA < Long MA and RSI > 35 (downtrend confirmation)

- **Coin Selection** (multi-coin mode):
  - Opportunity scores (0-100) based on price action, RSI, MAs, and volume
  - Switches to a different coin when its score is at least 10 points higher

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the project
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Testing

TRAID uses pytest for unit and integration testing:

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_trading_bot.py

# Run with coverage report
pytest --cov=traid
```

All core functionality is covered by comprehensive tests, following TDD principles.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.


## Disclaimer

Trading cryptocurrencies involves significant risk and may not be suitable for everyone. This software is for educational purposes only and is not financial advice. Always do your own research before making investment decisions. Past performance is not indicative of future results.

---

<p align="center">
  Made with ❤️ from codistry
</p>
