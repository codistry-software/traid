"""Main entry point for trading bot."""
from decimal import Decimal
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

def main():
    """Run trading bot."""
    # Get user configuration
    INITIAL_BALANCE = get_user_config()

    # Fixed configuration
    SYMBOL = "BTC/USDT"
    TIMEFRAME = "1h"
    UPDATE_INTERVAL = 3600  # 1 hour in seconds

    print(f"\nStarting bot with:")
    print(f"Initial Portfolio: {INITIAL_BALANCE} USDT")
    print(f"Trading Pair: {SYMBOL}")
    print(f"Timeframe: {TIMEFRAME}")

    # Create and start bot
    bot = TradingBotRunner(
        symbol=SYMBOL,
        timeframe=TIMEFRAME,
        initial_balance=INITIAL_BALANCE,
        update_interval=UPDATE_INTERVAL
    )

    try:
        bot.start()
        input("\nPress Enter to stop the bot...\n")
    except KeyboardInterrupt:
        print("\nStopping bot...")
    finally:
        bot.stop()

if __name__ == "__main__":
    main()