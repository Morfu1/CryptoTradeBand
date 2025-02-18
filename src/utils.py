import time
from functools import wraps
from typing import Callable, Any, Optional
from .logger import logger
from .config import config

def retry_on_error(max_retries: Optional[int] = None, delay: Optional[int] = None):
    max_retries = max_retries or config.MAX_RETRIES
    delay = delay or config.RETRY_DELAY

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        logger.error(f"Max retries reached for {func.__name__}: {str(e)}")
                        raise
                    logger.warning(f"Attempt {attempt + 1} failed for {func.__name__}: {str(e)}")
                    time.sleep(delay * (attempt + 1))  # Exponential backoff
            return None
        return wrapper
    return decorator

def calculate_contract_size(entry_price: float, margin: Optional[float] = None) -> float:
    """Calculate the contract size based on margin and entry price"""
    margin = margin or config.BASE_MARGIN
    position_value = margin * config.LEVERAGE
    raw_size = position_value / entry_price
    return int(raw_size / 100)  # Round to 0.1 precision

def format_price(price: float) -> str:
    """Format price to string with appropriate precision"""
    return f"{price:.8f}"