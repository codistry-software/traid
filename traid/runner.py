"""Main trading bot runner."""
from decimal import Decimal
from typing import Dict, List
import time
import threading
from .trading.execution import TradingExecutor


class TradingBotRunner:
    """Main trading bot runner.

    Handles the continuous execution of trading cycles
    and maintains execution history.
    """

    def __init__(
            self,
            symbol: str,
            timeframe: str,
            initial_balance: Decimal,
            update_interval: int = 3600
    ) -> None:
        """Initialize trading bot runner.

        Args:
            symbol: Trading pair symbol
            timeframe: Trading timeframe
            initial_balance: Starting balance
            update_interval: Seconds between updates
        """
        self.executor = TradingExecutor(
            symbol=symbol,
            timeframe=timeframe,
            initial_balance=initial_balance
        )
        self.update_interval = update_interval
        self.is_running = False
        self.execution_history: List[Dict] = []
        self._thread = None
        self._stop_event = threading.Event()

    def start(self) -> None:
        """Start the trading bot."""
        if self.is_running:
            return

        self.is_running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run)
        self._thread.start()
        print(f"Trading bot started - {self.executor.symbol} on {self.executor.timeframe}")

    def stop(self) -> None:
        """Stop the trading bot."""
        if not self.is_running:
            return

        self._stop_event.set()
        if self._thread:
            self._thread.join()
        self.is_running = False
        print("\nTrading bot stopped")
        self._print_final_summary()

    def _run(self) -> None:
        """Main execution loop."""
        while not self._stop_event.is_set():
            try:
                result = self.executor.execute_cycle()
                self.execution_history.append(result)
                self._print_cycle_result(result)

                # Wait for next update
                self._stop_event.wait(self.update_interval)
            except Exception as e:
                print(f"Error in execution cycle: {e}")
                # Continue running despite errors
                time.sleep(self.update_interval)

    def _print_cycle_result(self, result: Dict) -> None:
        """Print execution cycle result."""
        print("\nExecution cycle completed:")
        print(f"Action: {result['action']}")
        print(f"Balance: {result['balance']:.2f}")
        print(f"Portfolio Value: {result['portfolio_value']:.2f}")
        if 'error' in result:
            print(f"Error: {result['error']}")

    def _print_final_summary(self) -> None:
        """Print trading session summary."""
        if not self.execution_history:
            return

        first_result = self.execution_history[0]
        last_result = self.execution_history[-1]
        total_trades = sum(1 for r in self.execution_history if r['action'] in ['buy', 'sell'])

        print("\nTrading Session Summary")
        print("=" * 30)
        print(f"Total Cycles: {len(self.execution_history)}")
        print(f"Total Trades: {total_trades}")
        print(f"Initial Portfolio: {first_result['portfolio_value']:.2f}")
        print(f"Final Portfolio: {last_result['portfolio_value']:.2f}")
        profit = last_result['portfolio_value'] - first_result['portfolio_value']
        print(f"Total Profit/Loss: {profit:.2f} ({(profit / first_result['portfolio_value'] * 100):.2f}%)")