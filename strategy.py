import pandas as pd
import numpy as np
from typing import Tuple, Optional
from .config import config
from .logger import logger

class TradingStrategy:
    def __init__(self):
        self.df = pd.DataFrame()
        self.RISK_REWARD_RATIO = 2  # Risk:Reward ratio of 1:2
        self.outside_bands = False  # Track if price is outside bands
        self.last_signal = None  # Track last signal direction

    def prepare_data(self, candles: list) -> None:
        """Convert raw candles to DataFrame and calculate indicators"""
        try:
            # Create DataFrame with consistent column names
            self.df = pd.DataFrame(candles)

            # Ensure required columns exist
            required_columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
            if not all(col in self.df.columns for col in required_columns):
                logger.error(f"Missing required columns in candle data. Got: {self.df.columns}")
                raise ValueError("Invalid candle data format")

            # Convert to float and sort
            for col in ['open', 'high', 'low', 'close', 'volume']:
                self.df[col] = pd.to_numeric(self.df[col], errors='coerce')
            self.df.sort_values('timestamp', inplace=True)

            # Calculate indicators
            logger.debug("Calculating technical indicators...")
            self.df['sma'] = self.df['close'].rolling(window=config.SMA_PERIOD).mean()
            self.df['ema'] = self.df['close'].ewm(span=config.EMA_PERIOD, adjust=False).mean()

            # Calculate band boundaries
            self.df['upper_band'] = self.df[['sma', 'ema']].max(axis=1)
            self.df['lower_band'] = self.df[['sma', 'ema']].min(axis=1)

            logger.info("Technical indicators calculated successfully")
        except Exception as e:
            logger.error(f"Error preparing data: {str(e)}")
            raise

    def generate_signal(self) -> Tuple[Optional[str], float]:
        """Generate trading signal based on price action relative to bands"""
        try:
            if len(self.df) < max(config.SMA_PERIOD, config.EMA_PERIOD):
                logger.warning("Insufficient data for signal generation")
                return None, 0.0

            current_close = self.df['close'].iloc[-1]
            previous_close = self.df['close'].iloc[-2]
            current_upper = self.df['upper_band'].iloc[-1]
            current_lower = self.df['lower_band'].iloc[-1]
            previous_upper = self.df['upper_band'].iloc[-2]
            previous_lower = self.df['lower_band'].iloc[-2]

            # Log current band values
            logger.info(f"Current Band Values:")
            logger.info(f"- Upper Band: {current_upper:.6f}")
            logger.info(f"- Lower Band: {current_lower:.6f}")
            logger.info(f"- Current Price: {current_close:.6f}")
            logger.info(f"- Band Width: {(current_upper - current_lower):.6f}")

            # Reset signal if price returns inside bands
            if current_close <= current_upper and current_close >= current_lower:
                if self.outside_bands:
                    logger.info("Price returned inside bands - resetting signal")
                    self.outside_bands = False
                    self.last_signal = None
                return None, 0.0

            # Generate signal only when price closes outside bands for the first time
            if not self.outside_bands:
                if current_close > current_upper:
                    self.outside_bands = True
                    self.last_signal = 'long'
                    logger.info(f"Long signal generated at {current_close} (closed above upper band)")
                    return 'long', current_close
                elif current_close < current_lower:
                    self.outside_bands = True
                    self.last_signal = 'short'
                    logger.info(f"Short signal generated at {current_close} (closed below lower band)")
                    return 'short', current_close

            # No signal if we missed the first candle outside bands
            logger.debug("No signal - waiting for price to return inside bands")
            return None, 0.0

            return None, 0.0
        except Exception as e:
            logger.error(f"Error generating signal: {str(e)}")
            return None, 0.0

    def calculate_stop_loss(self, direction: str, entry_price: float) -> float:
        """Calculate stop loss based on entry price"""
        try:
            # Calculate stop loss percentage (1% from entry)
            sl_percentage = 0.01

            if direction == 'long':
                # Set stop loss 1% below entry for long positions
                stop_loss = entry_price * (1 - sl_percentage)
                logger.info(f"Calculated long stop loss at {stop_loss} ({sl_percentage*100}% below entry)")
                return stop_loss
            else:
                # Set stop loss 1% above entry for short positions
                stop_loss = entry_price * (1 + sl_percentage)
                logger.info(f"Calculated short stop loss at {stop_loss} ({sl_percentage*100}% above entry)")
                return stop_loss
        except Exception as e:
            logger.error(f"Error calculating stop loss: {str(e)}")
            raise

    def calculate_take_profit(self, entry_price: float, direction: str) -> float:
        """Calculate take profit level with R:R ratio of 2"""
        try:
            # Calculate take profit percentage (2% for 2:1 R:R ratio)
            tp_percentage = 0.01 * self.RISK_REWARD_RATIO  # 2% for 2:1 R:R

            if direction == 'long':
                # Set take profit 2% above entry for long positions
                tp = entry_price * (1 + tp_percentage)
                logger.info(f"Calculated long take profit at {tp} ({tp_percentage*100}% above entry)")
            else:
                # Set take profit 2% below entry for short positions
                tp = entry_price * (1 - tp_percentage)
                logger.info(f"Calculated short take profit at {tp} ({tp_percentage*100}% below entry)")

            # Log R:R ratio
            sl_distance = abs(self.calculate_stop_loss(direction, entry_price) - entry_price)
            tp_distance = abs(tp - entry_price)
            actual_rr = tp_distance / sl_distance if sl_distance > 0 else 0
            logger.info(f"Risk:Reward ratio = 1:{actual_rr:.2f}")

            return tp
        except Exception as e:
            logger.error(f"Error calculating take profit: {str(e)}")
            raise