"""Main entry point for trading bot."""
from decimal import Decimal
from traid.runner import TradingBotRunner

def main():
    """Run trading bot."""
    # Configuration
    SYMBOL = "BTC/USDT"
    TIMEFRAME = "1h"
    INITIAL_BALANCE = Decimal("10000")
    UPDATE_INTERVAL = 3600  # 1 hour in seconds

    # Create and start bot
    bot = TradingBotRunner(
        symbol=SYMBOL,
        timeframe=TIMEFRAME,
        initial_balance=INITIAL_BALANCE,
        update_interval=UPDATE_INTERVAL
    )

    try:
        bot.start()
        input("Press Enter to stop the bot...\n")
    except KeyboardInterrupt:
        print("\nStopping bot...")
    finally:
        bot.stop()

if __name__ == "__main__":
    main()