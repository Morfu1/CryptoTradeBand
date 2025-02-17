import time
from typing import NoReturn
from .config import config
from .exchange import BloFinExchange
from .strategy import TradingStrategy
from .risk_manager import RiskManager
from .logger import logger

class TradingBot:
    def __init__(self):
        self.exchange = BloFinExchange()
        self.strategy = TradingStrategy()
        self.risk_manager = RiskManager()
        logger.info("Trading bot initialized")

    def process_candles(self) -> None:
        """Fetch and process candle data"""
        required_candles = max(config.EMA_PERIOD + 1, config.SMA_PERIOD + 1)
        candles = self.exchange.get_candlesticks(limit=required_candles)
        self.strategy.prepare_data(candles)

    def execute_trade(self, direction: str, entry_price: float) -> None:
        """Execute trade with proper risk management"""
        try:
            # Check existing positions
            positions = self.exchange.get_positions()
            if positions:
                logger.info("Skipping trade - active position exists")
                return

            # Calculate trade parameters
            stop_loss = self.strategy.calculate_stop_loss(direction, entry_price)
            take_profit = self.strategy.calculate_take_profit(entry_price, direction)

            # Validate trade parameters
            if not self.risk_manager.validate_trade(direction, entry_price, stop_loss, take_profit):
                logger.warning("Trade validation failed")
                return

            # Calculate position size
            balance = self.exchange.get_balance()
            position_size = self.risk_manager.calculate_position_size(
                balance, entry_price, stop_loss
            )

            # Execute order
            self.exchange.place_order(
                direction=direction,
                size=position_size,
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit
            )
            logger.info(f"Trade executed: {direction} {position_size} contracts at {entry_price}")
        except Exception as e:
            logger.error(f"Trade execution failed: {str(e)}")

    def run(self) -> NoReturn:
        """Main trading loop"""
        logger.info("Starting trading bot...")

        while True:
            try:
                # Process market data
                self.process_candles()

                # Generate trading signal
                signal, entry_price = self.strategy.generate_signal()

                # Execute trade if signal exists
                if signal:
                    self.execute_trade(signal, entry_price)

                # Wait for next candle
                time.sleep(self._get_sleep_time())

            except Exception as e:
                logger.error(f"Error in main loop: {str(e)}")
                time.sleep(config.RETRY_DELAY)

    def _get_sleep_time(self) -> int:
        """Calculate sleep time based on timeframe"""
        timeframe_seconds = {
            '1m': 60,
            '5m': 300,
            '15m': 900,
            '30m': 1800,
            '1h': 3600,
            '4h': 14400,
            '1d': 86400
        }
        return timeframe_seconds.get(config.TIMEFRAME, 60)

def main():
    bot = TradingBot()
    bot.run()

if __name__ == "__main__":
    main()