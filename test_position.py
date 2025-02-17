import time
from src.exchange import BloFinExchange
from src.logger import logger

def test_position_sizing():
    """Test position sizing and margin calculation"""
    try:
        exchange = BloFinExchange()
        logger.info("Testing position sizing with isolated margin...")

        # Get current price from market
        candles = exchange.get_candlesticks(limit=1)
        entry_price = float(candles[0]['close'])

        # Calculate parameters for a test short position
        stop_loss = entry_price * 1.01  # 1% above for short
        take_profit = entry_price * 0.97  # 3% below for short

        # Place test order
        try:
            response = exchange.place_order(
                direction='short',
                size=1.0,  # Size will be recalculated in place_order
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit
            )
            logger.info(f"Test order placed successfully: {response}")

            # Wait briefly for position to be registered
            time.sleep(2)

            # Verify position details
            positions = exchange.get_positions()
            if positions:
                for pos in positions:
                    logger.info(f"Position verified:")
                    logger.info(f"- Size: {abs(float(pos.get('positions', 0)))} contracts")
                    logger.info(f"- Entry Price: {pos.get('averagePrice')} USDT")
                    logger.info(f"- Margin Mode: {pos.get('marginMode')}")
                    logger.info(f"- Position Side: {pos.get('positionSide')}")
                    logger.info(f"- Margin Used: {float(pos.get('margin', 0))} USDT")
                    logger.info(f"- Leverage: {pos.get('leverage')}x")

                    # Verify margin is close to target 100 USDT
                    margin = float(pos.get('margin', 0))
                    if abs(margin - 100) > 5:  # Allow 5 USDT tolerance
                        logger.warning(f"Margin {margin} USDT is not close to target 100 USDT")
            else:
                logger.error("No positions found after order placement")

        except Exception as e:
            logger.error(f"Order placement failed: {str(e)}")
            raise

    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        raise

if __name__ == "__main__":
    test_position_sizing()