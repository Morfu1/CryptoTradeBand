import ccxt
import pandas as pd
import time
from typing import Dict, List
from .config import config
from .logger import logger

class BloFinExchange:
    def __init__(self):
        self.logger = logger
        self.MAX_RETRIES = config.MAX_RETRIES
        self.RETRY_DELAY = config.RETRY_DELAY
        self.CONTRACT_VALUE = 0.1  # Each contract is 0.1 ETH
        self.exchange = self._initialize_exchange()

    def _initialize_exchange(self):
        """Initialize exchange with retries"""
        try:
            exchange = ccxt.blofin({
                'apiKey': config.API_KEY,
                'secret': config.API_SECRET,
                'password': config.API_PASSPHRASE,
                'enableRateLimit': True,
                'timeout': 30000,  # 30 seconds timeout
                'options': {
                    'defaultType': 'swap',
                    'hedgeMode': True
                }
            })
            exchange.set_sandbox_mode(True)  # Use demo account

            # Set leverage (supported by CCXT)
            self._handle_request(
                exchange.setLeverage,
                config.LEVERAGE,
                symbol=config.SYMBOL
            )

            return exchange
        except Exception as e:
            logger.error(f"Failed to initialize exchange: {str(e)}")
            raise

    def _handle_request(self, operation, *args, **kwargs):
        """Handle exchange requests with retry logic"""
        for attempt in range(self.MAX_RETRIES):
            try:
                return operation(*args, **kwargs)
            except ccxt.NetworkError as e:
                if attempt == self.MAX_RETRIES - 1:
                    raise
                logger.warning(f"Network error, retrying... ({attempt + 1}/{self.MAX_RETRIES})")
                time.sleep(self.RETRY_DELAY)
            except ccxt.ExchangeError as e:
                if attempt == self.MAX_RETRIES - 1:
                    raise
                logger.warning(f"Exchange error, retrying... ({attempt + 1}/{self.MAX_RETRIES})")
                time.sleep(self.RETRY_DELAY)

    def _get_instrument_id(self) -> str:
        """Get properly formatted instrument ID"""
        # Convert ETH/USDT to ETH-USDT
        return config.SYMBOL.replace('/', '-')

    def get_candlesticks(self, limit: int = 100) -> List[Dict]:
        """Fetch historical candlesticks"""
        try:
            timeframe_map = {
                '1m': '1m', '5m': '5m', '15m': '15m',
                '30m': '30m', '1h': '1H', '4h': '4H',
                '1d': '1D'
            }
            timeframe = timeframe_map.get(config.TIMEFRAME, '5m')

            ohlcv = self._handle_request(
                self.exchange.fetch_ohlcv,
                config.SYMBOL,
                timeframe,
                limit=limit
            )

            candles = [
                {
                    'timestamp': candle[0],
                    'open': candle[1],
                    'high': candle[2],
                    'low': candle[3],
                    'close': candle[4],
                    'volume': candle[5]
                }
                for candle in ohlcv
            ]

            logger.info(f"Retrieved {len(candles)} candlesticks")
            return candles
        except Exception as e:
            logger.error(f"Failed to fetch candlesticks: {str(e)}")
            raise

    def get_balance(self) -> float:
        """Get current account balance"""
        try:
            balance = self._handle_request(self.exchange.fetch_balance)
            total_usdt = float(balance.get('total', {}).get('USDT', 0))
            logger.info(f"Current balance: {total_usdt} USDT")
            return total_usdt
        except Exception as e:
            logger.error(f"Failed to get balance: {str(e)}")
            raise

    def place_order(self, direction: str, size: float, entry_price: float,
                   stop_loss: float, take_profit: float) -> Dict:
        """Place a new order with TP and SL"""
        try:
            # Convert direction to side
            side = "buy" if direction == "long" else "sell"

            # Calculate contracts needed for target margin
            contract_value = self.CONTRACT_VALUE  # Each contract is 0.1 ETH
            position_value = config.BASE_MARGIN * config.LEVERAGE  # e.g., 100 * 3 = 300 USDT
            eth_amount = position_value / entry_price  # Amount in ETH
            target_contracts = round(eth_amount / contract_value) * 10  # Multiply by 10 to get to ~100 USD margin

            # Ensure at least 1 contract
            contracts = max(1, target_contracts)

            # Calculate actual margin and position size
            actual_size = contracts * contract_value  # Size in ETH
            position_value = actual_size * entry_price  # Value in USDT
            actual_margin = position_value / config.LEVERAGE

            # Log detailed position calculations
            logger.info(f"Position size calculation:")
            logger.info(f"- Entry price: {entry_price:.2f} USDT")
            logger.info(f"- Contract value: {contract_value} ETH")
            logger.info(f"- Target position value: {position_value:.2f} USDT")
            logger.info(f"- Target ETH amount: {eth_amount:.4f}")
            logger.info(f"- Selected contracts: {contracts}")
            logger.info(f"- Actual margin: {actual_margin:.2f} USDT")
            logger.info(f"- Position value: {position_value:.2f} USDT")

            # Log SL/TP distances for verification
            sl_distance = abs(entry_price - stop_loss)
            tp_distance = abs(entry_price - take_profit)
            rr_ratio = tp_distance / sl_distance if sl_distance > 0 else 0

            logger.info(f"Risk/Reward Analysis:")
            logger.info(f"- Entry Price: {entry_price:.2f}")
            logger.info(f"- Stop Loss: {stop_loss:.2f} (Distance: {sl_distance:.2f})")
            logger.info(f"- Take Profit: {take_profit:.2f} (Distance: {tp_distance:.2f})")
            logger.info(f"- R/R Ratio: 1:{rr_ratio:.2f}")

            # Prepare order parameters exactly as needed by Blofin API
            order_params = {
                'instId': config.SYMBOL,  # Already in correct format (ETH-USDT)
                'marginMode': 'isolated',
                'side': side,
                'size': str(contracts),  # Number of contracts
                'orderType': 'market',  # Changed from ordType to orderType
                'tpslMode': 'Full',
                'tpTriggerPrice': str(take_profit),  # Changed from tpTriggerPx
                'tpOrderPrice': "-1",  # Market price execution for TP
                'slTriggerPrice': str(stop_loss),  # Changed from slTriggerPx
                'slOrderPrice': "-1",  # Market price execution for SL
                'leverage': str(config.LEVERAGE)
            }

            # Place the order
            response = self._handle_request(
                self.exchange.privatePostTradeOrder,
                order_params
            )

            logger.info(f"Order placed successfully: {direction} {contracts} contracts")
            logger.info(f"Take Profit: {take_profit}, Stop Loss: {stop_loss}")
            return response

        except Exception as e:
            logger.error(f"Order placement failed: {str(e)}")
            raise

    def get_positions(self) -> List[Dict]:
        """Get current positions"""
        try:
            response = self._handle_request(
                self.exchange.privateGetAccountPositions
            )
            positions = response.get('data', []) if response else []
            active_positions = [
                pos for pos in positions 
                if float(pos.get('positions', '0')) != 0
            ]
            logger.info(f"Retrieved {len(active_positions)} open positions")
            return active_positions
        except Exception as e:
            logger.error(f"Failed to get positions: {str(e)}")
            return []

    def add_tp_sl_to_position(self, position_id: str, stop_loss: float, take_profit: float) -> Dict:
        """Add TP/SL to an existing position"""
        try:
            # Format order parameters according to Blofin API
            order_params = {
                "symbol": config.SYMBOL,
                "positionId": position_id,
                "params": {
                    "tpslMode": "Full",
                    "tpTriggerPrice": str(take_profit),
                    "tpOrderPrice": "-1",  # Market price execution
                    "slTriggerPrice": str(stop_loss),
                    "slOrderPrice": "-1",  # Market price execution
                    "reduceOnly": "true"
                }
            }

            # Place the TP/SL orders
            response = self._handle_request(
                self.exchange.create_order,
                **order_params
            )

            logger.info(f"Added TP/SL orders to position {position_id}")
            return response
        except Exception as e:
            logger.error(f"Failed to add TP/SL orders: {str(e)}")
            raise

    def close_position(self) -> bool:
        """Close existing positions"""
        try:
            # Get current positions
            positions = self.get_positions()

            # Close each position
            for position in positions:
                if not position:
                    continue

                size = float(position.get('positions', '0'))
                if size == 0:
                    continue

                side = position.get('posSide', 'net')
                # Determine close direction (opposite of current position)
                close_side = "sell" if side == "long" else "buy"

                # Prepare order parameters
                order_params = {
                    "instId": position.get('instId', self._get_instrument_id()),
                    "marginMode": "isolated",
                    "positionSide": "net",  # Use net mode for closing
                    "side": close_side,
                    "orderType": "market",
                    "size": str(size),
                    "reduceOnly": "true"  # Ensure this only closes positions
                }

                # Place the closing order
                self._handle_request(
                    self.exchange.privatePostTradeOrder,
                    order_params
                )

                logger.info(f"Closed position: {size} at market price")

            return True
        except Exception as e:
            logger.error(f"Failed to close position: {str(e)}")
            return False