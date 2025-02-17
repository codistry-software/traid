"""Main entry point for trading bot."""
from decimal import Decimal
import asyncio
from traid.runner import TradingBotRunner

def get_user_config():
    """Get trading configuration from user."""
    while True:
        try:
            portfolio = input("\nEnter your initial portfolio value in USDT: ")
            initial_balance = Decimal(portfolio)
            if initial_balance <= 0:
                print("Portfolio value must be positive!")
                continue
            return initial_balance
        except:
            print("Invalid input! Please enter a valid number.")

async def run_bot():
    """Run trading bot with WebSocket connection."""
    # Get user configuration
    INITIAL_BALANCE = get_user_config()

    # Fixed configuration
    SYMBOL = "BTC/USDT"
    TIMEFRAME = "1m"  # 1 minute for more frequent updates

    print(f"\nStarting bot with:")
    print(f"Initial Portfolio: {INITIAL_BALANCE} USDT")
    print(f"Trading Pair: {SYMBOL}")
    print(f"Timeframe: {TIMEFRAME}")

    # Create and start bot
    bot = TradingBotRunner(
        symbol=SYMBOL,
        timeframe=TIMEFRAME,
        initial_balance=INITIAL_BALANCE
    )

    try:
        await bot.start()
        print("\nBot is running with real-time data. Press Ctrl+C to stop.")
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping bot...")
    finally:
        await bot.stop()

def main():
    """Entry point."""
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        print("\nBot stopped by user.")

if __name__ == "__main__":
    main()