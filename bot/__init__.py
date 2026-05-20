"""
Binance Futures Trading Bot – core package.
"""
from .client  import BinanceFuturesClient, BinanceAPIError
from .orders  import OrderManager, OrderResult
from .logging_config import setup_logging, get_logger

__all__ = [
    "BinanceFuturesClient",
    "BinanceAPIError",
    "OrderManager",
    "OrderResult",
    "setup_logging",
    "get_logger",
]
