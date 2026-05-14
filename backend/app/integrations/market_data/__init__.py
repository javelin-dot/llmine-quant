"""Market data integration layer.

Public surface:
  get_market_data_provider() → MarketDataProvider
  Quote, OHLCV, HistoryResult (data models)
"""

from .base import OHLCV, HistoryResult, MarketDataProvider, Quote
from .factory import get_market_data_provider

__all__ = [
    "get_market_data_provider",
    "MarketDataProvider",
    "Quote",
    "OHLCV",
    "HistoryResult",
]
