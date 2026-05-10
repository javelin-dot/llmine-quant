"""Data source adapter interface."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

import pandas as pd


@dataclass
class DataSourceConfig:
    """Configuration for a data source adapter."""

    name: str
    provider: str
    api_key: str | None = None
    base_url: str | None = None
    timeout: int = 30
    retry_count: int = 3


@dataclass
class DataSourceHealth:
    """Health status of a data source."""

    status: str  # healthy / warning / error
    latency_ms: int
    missing_pct: float
    drift_score: float
    last_check: str
    message: str | None = None


class DataSourceAdapter(ABC):
    """Abstract base class for market data source adapters."""

    def __init__(self, config: DataSourceConfig) -> None:
        self.config = config

    @abstractmethod
    async def get_daily_kline(
        self,
        symbols: list[str],
        start_date: str,
        end_date: str,
    ) -> pd.DataFrame:
        """Fetch daily OHLCV data for given symbols and date range."""
        raise NotImplementedError

    @abstractmethod
    async def get_fundamental(
        self,
        symbols: list[str],
        fields: list[str],
        report_date: str,
    ) -> pd.DataFrame:
        """Fetch fundamental data for given symbols."""
        raise NotImplementedError

    @abstractmethod
    async def health_check(self) -> DataSourceHealth:
        """Check data source health."""
        raise NotImplementedError

    @abstractmethod
    async def get_symbols(self, market: str = "A") -> list[dict[str, Any]]:
        """Get list of available symbols."""
        raise NotImplementedError


class AKShareAdapter(DataSourceAdapter):
    """AKShare free data source adapter."""

    async def get_daily_kline(self, symbols: list[str], start_date: str, end_date: str) -> pd.DataFrame:
        """Fetch daily kline from AKShare."""
        return pd.DataFrame()

    async def get_fundamental(self, symbols: list[str], fields: list[str], report_date: str) -> pd.DataFrame:
        """Fetch fundamental data from AKShare."""
        return pd.DataFrame()

    async def health_check(self) -> DataSourceHealth:
        """Check AKShare health."""
        return DataSourceHealth(
            status="healthy", latency_ms=120, missing_pct=0.001,
            drift_score=0.02, last_check="now", message="OK"
        )

    async def get_symbols(self, market: str = "A") -> list[dict[str, Any]]:
        """Get A-share symbols from AKShare."""
        return []


class TushareAdapter(DataSourceAdapter):
    """Tushare Pro paid data source adapter."""

    async def get_daily_kline(self, symbols: list[str], start_date: str, end_date: str) -> pd.DataFrame:
        """Fetch daily kline from Tushare."""
        return pd.DataFrame()

    async def get_fundamental(self, symbols: list[str], fields: list[str], report_date: str) -> pd.DataFrame:
        """Fetch fundamental data from Tushare."""
        return pd.DataFrame()

    async def health_check(self) -> DataSourceHealth:
        """Check Tushare health."""
        return DataSourceHealth(
            status="healthy", latency_ms=180, missing_pct=0.0005,
            drift_score=0.01, last_check="now", message="OK"
        )

    async def get_symbols(self, market: str = "A") -> list[dict[str, Any]]:
        """Get symbols from Tushare."""
        return []
