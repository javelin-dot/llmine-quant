"""Market data provider factory.

Add a new commercial provider:
  1. Create `app/integrations/market_data/<name>_provider.py`
     subclassing `MarketDataProvider`.
  2. Add an `elif name == "<name>"` branch below.
  3. Set `MARKET_DATA_PROVIDER=<name>` in .env.

No other files need to change.
"""

from __future__ import annotations

from app.core.config import settings
from app.core.logging import get_logger

from .base import MarketDataProvider

logger = get_logger("market_data.factory")
_instance: MarketDataProvider | None = None


def get_market_data_provider() -> MarketDataProvider:
    """Return the singleton provider selected by `settings.market_data_provider`."""
    global _instance  # noqa: PLW0603
    if _instance is not None:
        return _instance

    name = (settings.market_data_provider or "akshare").lower()

    if name == "akshare":
        try:
            import akshare  # noqa: F401
            from .akshare_provider import AKShareProvider
            _instance = AKShareProvider()
        except ImportError:
            logger.warning("akshare_not_installed_falling_back_to_mock")
            from .mock_provider import MockMarketDataProvider
            _instance = MockMarketDataProvider()

    elif name == "tushare":
        from .tushare_provider import TushareProvider  # type: ignore[import]
        _instance = TushareProvider(token=settings.tushare_token)

    elif name == "wind":
        from .wind_provider import WindProvider  # type: ignore[import]
        _instance = WindProvider()

    else:  # "mock" or unknown
        if name not in ("mock",):
            logger.warning("unknown_market_data_provider", name=name, fallback="mock")
        from .mock_provider import MockMarketDataProvider
        _instance = MockMarketDataProvider()

    logger.info("market_data_provider_selected", provider=_instance.name)
    return _instance
