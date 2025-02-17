import os
from dataclasses import dataclass


@dataclass
class TradingConfig:
    # Trading parameters
    TIMEFRAME: str = '5m'  # Supported: 1m,5m,15m,30m,1h,4h,1d
    LEVERAGE: int = 3
    MARGIN_MODE: str = 'isolated'  # Changed from cross to isolated
    BASE_MARGIN: float = 100  # USD
    TP_PERCENTAGE: float = 0.03  # 3%
    RISK_PER_TRADE: float = 0.01  # 1% of balance
    SYMBOL: str = 'XRP-USDT'  # Changed from ETH/USDT:USDT to ETH-USDT

    # API credentials
    API_KEY: str = os.getenv('BLOFIN_KEY', 'demo_key')
    API_SECRET: str = os.getenv('BLOFIN_SECRET', 'demo_secret')
    API_PASSPHRASE: str = os.getenv('BLOFIN_PASSPHRASE', 'demo_pass')

    # Technical indicators
    SMA_PERIOD: int = 21
    EMA_PERIOD: int = 34
    SL_LOOKBACK: int = 10

    # System settings
    MAX_RETRIES: int = 3
    RETRY_DELAY: int = 2  # seconds


config = TradingConfig()
