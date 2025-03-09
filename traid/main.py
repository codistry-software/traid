"""Main entry point for trading bot."""
from decimal import Decimal
import asyncio
import requests
from kraken_client import KrakenClient
from trading_bot import TradingBot

async def get_all_kraken_pairs():
    """Fetch all available trading pairs from Kraken."""
    # Define stable coins to exclude from fetched pairs
    STABLE_COINS = {'USDT', 'USDC', 'DAI', 'BUSD', 'UST', 'EURT', 'TUSD', 'GUSD', 'PAX', 'HUSD', 'EURS'}

    try:
        print("Fetching available trading pairs from Kraken...")

        # Use REST API to get available asset pairs
        response = requests.get("https://api.kraken.com/0/public/AssetPairs")
        if response.status_code != 200:
            print("Warning: Failed to fetch trading pairs. Using default set.")
            return ["BTC/USDT", "ETH/USDT", "SOL/USDT", "XRP/USDT", "ADA/USDT"]

        data = response.json()

        if not data.get('result'):
            print("Warning: Invalid response from Kraken API. Using default set.")
            return ["BTC/USDT", "ETH/USDT", "SOL/USDT", "XRP/USDT", "ADA/USDT"]

        # Filter for USDT pairs, excluding stable/stable pairs
        usdt_pairs = []

        for pair_name, pair_data in data['result'].items():
            if 'USDT' in pair_name:
                base = pair_data.get('base', '')
                quote = pair_data.get('quote', '')

                if base and quote and len(base) < 10 and len(quote) < 10:
                    if quote == 'USDT' and base not in STABLE_COINS:
                        standard_pair = f"{base}/{quote}"
                        usdt_pairs.append(standard_pair)

        # If no USDT pairs found, return default set
        if not usdt_pairs:
            print("Warning: No USDT pairs found. Using default set.")
            return ["BTC/USDT", "ETH/USDT", "SOL/USDT", "XRP/USDT", "ADA/USDT"]

        print(f"Found {len(usdt_pairs)} USDT trading pairs on Kraken")
        return usdt_pairs

    except Exception as e:
        print(f"Error fetching trading pairs: {e}")
        print("Using default set of trading pairs...")
        return ["BTC/USDT", "ETH/USDT", "SOL/USDT", "XRP/USDT", "ADA/USDT"]

def get_user_config():
    """Get trading configuration from user."""
    while True:
        try:
            portfolio = input("Enter your initial portfolio value in USDT: ")
            initial_balance = Decimal(portfolio)
            if initial_balance <= 0:
                print("Portfolio value must be positive!")
                continue

            # Ask if user wants single or multi-coin trading
            print("\nTrading modes:")
            print("1. Single coin trading (BTC/USDT only)")
            print("2. Multi-coin trading (analyzes all available coins)")

            while True:
                mode = input("\nSelect trading mode (default: 2): ").strip()
                if mode == "" or mode == "2" or mode == "1":
                    break
                print("Invalid option. Please select 1 or 2.")

            return initial_balance, "1" if mode == "1" else "2"
        except:
            print("Invalid input! Please enter a valid number.")

async def run_bot():
    """Run trading bot with WebSocket connection."""
    # Get user configuration
    INITIAL_BALANCE, MODE = get_user_config()
    TIMEFRAME = "1m"  # 1 minute for more frequent updates

    if MODE == "1":
        # Single coin mode (original functionality)
        SYMBOL = "BTC/USDT"

        print(f"\nStarting bot with:")
        print(f"Initial Portfolio: {INITIAL_BALANCE} USDT")
        print(f"Trading Pair: {SYMBOL}")
        print(f"Timeframe: {TIMEFRAME}")
        print(f"Mode: Single coin trading")

        # Create and start bot
        bot = TradingBotRunner(
            symbol=SYMBOL,
            timeframe=TIMEFRAME,
            initial_balance=INITIAL_BALANCE
        )
    else:
        # Multi-coin mode (new functionality)
        all_pairs = await get_all_kraken_pairs()

        print(f"\nStarting bot with:")
        print(f"Initial Portfolio: {INITIAL_BALANCE} USDT")
        print(f"Monitoring: {len(all_pairs)} cryptocurrencies")
        print(f"Timeframe: {TIMEFRAME}")
        print(f"Mode: Multi-coin trading")
        print("\nThe bot will automatically analyze all coins and select the best trading opportunities.")

        # Create and start multi-coin bot
        bot = MultiCoinTradingBot(
            symbols=all_pairs,
            timeframe=TIMEFRAME,
            initial_balance=INITIAL_BALANCE,
            update_interval=30  # Update every 30 seconds
        )

    try:
        await bot.start()
        print("\nBot is running with real-time data. Press Ctrl+C to stop.")

        # Wait for user interruption
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping bot...")
    except Exception as e:
        print(f"\nError in bot execution: {e}")
    finally:
        if bot.is_running:
            await bot.stop()

def main():
    """Entry point."""
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        print("\nBot stopped by user.")
    except Exception as e:
        print(f"\nUnexpected error: {e}")

if __name__ == "__main__":
    main()