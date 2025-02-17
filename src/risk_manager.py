from typing import Tuple
from .config import config
from .logger import logger

class RiskManager:
    def __init__(self):
        self.consecutive_losses = 0
        self.max_consecutive_losses = 3
        self.MAX_MARGIN_USD = 100.0  # Maximum margin in USD
        self.CONTRACT_VALUE = 0.01  # ETH contract value from exchange
        self.FLOAT_TOLERANCE = 0.0001  # 0.01% tolerance for float comparisons

    def calculate_position_size(self, balance: float, entry_price: float, stop_loss: float) -> float:
        """Calculate position size based on risk parameters and exchange limits"""
        try:
            # Calculate maximum position size based on margin limit
            max_position_value = self.MAX_MARGIN_USD * config.LEVERAGE
            max_position_eth = max_position_value / entry_price
            logger.info(f"Max position value from margin limit: ${max_position_value:.2f} (max ETH: {max_position_eth:.4f})")

            # Calculate risk amount in USD (1% of balance)
            risk_amount = balance * config.RISK_PER_TRADE
            logger.info(f"Risk amount: {risk_amount:.2f} USDT")

            # Calculate position size based on risk and stop loss distance
            stop_loss_distance = abs(entry_price - stop_loss)
            risk_based_size = (risk_amount / stop_loss_distance)

            # Use the smaller of risk-based size and margin-limited size
            position_size = min(risk_based_size, max_position_eth)

            # Round down to nearest contract value
            contracts = int(position_size / self.CONTRACT_VALUE)
            position_size = contracts * self.CONTRACT_VALUE

            # Verify final position doesn't exceed margin limit
            margin_used = (position_size * entry_price) / config.LEVERAGE
            if margin_used > self.MAX_MARGIN_USD:
                logger.warning(f"Position size {position_size:.4f} ETH would use {margin_used:.2f} USD margin, exceeding limit")
                # Reduce by one contract
                contracts -= 1
                position_size = contracts * self.CONTRACT_VALUE
                margin_used = (position_size * entry_price) / config.LEVERAGE

            logger.info(f"Final position size: {position_size:.4f} ETH ({contracts} contracts)")
            logger.info(f"Margin required: ${margin_used:.2f}")
            logger.info(f"Position value: ${position_size * entry_price:.2f}")

            return position_size

        except Exception as e:
            logger.error(f"Error calculating position size: {str(e)}")
            return 0.0

    def validate_trade(self, direction: str, entry_price: float, 
                      stop_loss: float, take_profit: float) -> bool:
        """Validate trade parameters before execution"""
        try:
            if self.consecutive_losses >= self.max_consecutive_losses:
                logger.warning("Maximum consecutive losses reached. Trading halted.")
                return False

            # Calculate margin required for the minimum contract
            min_margin = (self.CONTRACT_VALUE * entry_price) / config.LEVERAGE
            if min_margin > self.MAX_MARGIN_USD:
                logger.warning(f"Trade rejected: Even one contract ({self.CONTRACT_VALUE} ETH) requires {min_margin:.2f} USD margin")
                return False

            # Validate price levels
            if direction == 'long':
                if not (stop_loss < entry_price < take_profit):
                    logger.warning("Invalid price levels for long position")
                    return False
            else:  # short
                if not (take_profit < entry_price < stop_loss):
                    logger.warning("Invalid price levels for short position")
                    return False

            # Validate stop loss distance (1% with tolerance)
            target_distance = entry_price * 0.01  # 1% target distance
            actual_distance = abs(entry_price - stop_loss)
            distance_diff = abs(actual_distance - target_distance)

            # Check if the difference is within tolerance
            if distance_diff > (target_distance * self.FLOAT_TOLERANCE):
                logger.warning(f"Stop loss distance {actual_distance:.2f} too far from target {target_distance:.2f}")
                return False

            return True
        except Exception as e:
            logger.error(f"Error validating trade: {str(e)}")
            return False

    def update_trade_result(self, is_profit: bool) -> None:
        """Update consecutive losses counter"""
        if is_profit:
            self.consecutive_losses = 0
        else:
            self.consecutive_losses += 1