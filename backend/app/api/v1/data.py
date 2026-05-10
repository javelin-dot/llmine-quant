"""Data Service API — data sources, market data, lineage, incidents."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.domains.data.schemas import (
    BiasGate,
    DataIncidentOut,
    DataOverview,
    DataScreen,
    DataSourceOut,
    DataSourceTier,
    LatencyTrend,
    LineageNodeOut,
    LineageOut,
)

router = APIRouter()


_HEADER = DataOverview(
    totalSources=12,
    activeSources=10,
    erroredSources=2,
    avgLatencyMs=180,
    p95LatencyMs=420,
    missingRate=0.0008,
    incidents24h=1,
    healthScore=88,
    healthStatus="HEALTHY",
    healthStatusTone="green",
)

_TIERS = [
    DataSourceTier(tier="research", label="研究层", count=6, active=5, avgLatencyMs=150, license="免费", tone="blue", desc="AKShare / Baostock 基础行情"),
    DataSourceTier(tier="paper", label="模拟盘层", count=4, active=4, avgLatencyMs=200, license="付费", tone="yellow", desc="Tushare Pro 增强数据"),
    DataSourceTier(tier="live", label="实盘层", count=2, active=1, avgLatencyMs=300, license="机构", tone="red", desc="Wind / 券商直连"),
]

_SOURCES = [
    DataSourceOut(
        id="ds-001", name="AKShare 日线", provider="akshare", tier="research", tierTone="blue",
        type="kline", coverage="沪深A股", latencyMs=120, latencyP95=350, missingPct=0.001,
        driftScore=0.02, license="免费", status="healthy", statusTone="green", lastUpdate="2 min ago"
    ),
    DataSourceOut(
        id="ds-002", name="Tushare Pro 日线", provider="tushare", tier="paper", tierTone="yellow",
        type="kline", coverage="沪深A股+科创板", latencyMs=180, latencyP95=420, missingPct=0.0005,
        driftScore=0.01, license="付费", status="healthy", statusTone="green", lastUpdate="1 min ago"
    ),
    DataSourceOut(
        id="ds-003", name="Wind 机构数据", provider="wind", tier="live", tierTone="red",
        type="kline", coverage="全市场", latencyMs=280, latencyP95=520, missingPct=0.0002,
        driftScore=0.01, license="机构", status="warning", statusTone="yellow", lastUpdate="5 min ago"
    ),
    DataSourceOut(
        id="ds-004", name="AKShare 财务数据", provider="akshare", tier="research", tierTone="blue",
        type="fundamental", coverage="沪深A股", latencyMs=200, latencyP95=600, missingPct=0.002,
        driftScore=0.03, license="免费", status="healthy", statusTone="green", lastUpdate="10 min ago"
    ),
]

_LATENCY_TREND = LatencyTrend(
    times=["08:00", "09:00", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00"],
    research=[120, 130, 125, 140, 135, 150, 145, 130],
    paper=[180, 200, 190, 210, 205, 220, 215, 195],
    live=[280, 300, 290, 310, 305, 320, 315, 295],
    slaMs=500,
)

_BIAS_GATES = [
    BiasGate(title="未来函数检测", desc="检查特征计算是否使用未来数据", status="pass", statusTone="green", lastCheck="10 min ago", note="无异常"),
    BiasGate(title="幸存者偏差", desc="检查是否排除已退市股票", status="pass", statusTone="green", lastCheck="15 min ago", note="ST/退市标记完整"),
    BiasGate(title="数据完整性", desc="检查关键字段缺失率", status="pass", statusTone="green", lastCheck="5 min ago", note="缺失率 < 0.1%"),
    BiasGate(title="数据及时性", desc="检查行情延迟是否在 SLA 内", status="watch", statusTone="yellow", lastCheck="1 min ago", note="Wind 数据源延迟偏高"),
    BiasGate(title="数据一致性", desc="交叉验证多源数据一致性", status="pass", statusTone="green", lastCheck="20 min ago", note="偏差 < 0.1%"),
]

_LINEAGE = LineageOut(
    nodes=[
        LineageNodeOut(id="n1", label="AKShare Raw", tier="raw", tone="blue", version="v2.1.0", permission="read"),
        LineageNodeOut(id="n2", label="Cleaned Bars", tier="raw", tone="blue", version="v1.3.0", permission="read"),
        LineageNodeOut(id="n3", label="Feature Set", tier="feature", tone="green", version="v4.2.0", permission="read"),
        LineageNodeOut(id="n4", label="MA Strategy", tier="model", tone="purple", version="v1.0.0", permission="execute"),
        LineageNodeOut(id="n5", label="Signal", tier="signal", tone="yellow", version="v1.0.0", permission="read"),
        LineageNodeOut(id="n6", label="Order Draft", tier="order", tone="red", version="v1.0.0", permission="write"),
    ],
    edges=[{"from": "n1", "to": "n2"}, {"from": "n2", "to": "n3"}, {"from": "n3", "to": "n4"}, {"from": "n4", "to": "n5"}, {"from": "n5", "to": "n6"}],
)

_INCIDENTS = [
    DataIncidentOut(
        time="09:15", source="Wind 机构数据", type="latency", typeTone="yellow",
        severity="medium", severityTone="yellow", title="Wind API 延迟升高",
        detail="P95 延迟达到 520ms，超出 SLA 阈值 500ms", resolution="已通知 Wind 技术支持",
        status="ongoing", statusTone="yellow"
    ),
]

_KPIS = [
    {"label": "数据源", "value": "12", "trend": "+1", "tone": "blue"},
    {"label": "P95 延迟", "value": "420ms", "trend": "+15%", "tone": "yellow"},
    {"label": "缺失率", "value": "0.08%", "trend": "-0.02%", "tone": "green"},
    {"label": "漂移分", "value": "0.02", "trend": "+0.01", "tone": "green"},
    {"label": "事件", "value": "1", "trend": "+1", "tone": "yellow"},
]


@router.get("/overview", response_model=DataScreen)
async def get_data_overview(db: AsyncSession = Depends(get_db)) -> DataScreen:
    """Return the complete Data Operations screen data."""
    return DataScreen(
        header=_HEADER,
        tiers=_TIERS,
        kpis=_KPIS,
        sources=_SOURCES,
        latencyTrend=_LATENCY_TREND,
        biasGate=_BIAS_GATES,
        lineage=_LINEAGE,
        incidents=_INCIDENTS,
    )


@router.get("/sources", response_model=list[DataSourceOut])
async def get_data_sources(db: AsyncSession = Depends(get_db)) -> list[DataSourceOut]:
    """Return all data sources."""
    return _SOURCES


@router.get("/latency-trend", response_model=LatencyTrend)
async def get_latency_trend() -> LatencyTrend:
    """Return latency trend data."""
    return _LATENCY_TREND


@router.get("/lineage", response_model=LineageOut)
async def get_lineage() -> LineageOut:
    """Return data lineage DAG."""
    return _LINEAGE


@router.get("/incidents", response_model=list[DataIncidentOut])
async def get_incidents() -> list[DataIncidentOut]:
    """Return data incidents."""
    return _INCIDENTS


@router.get("/bias-gates", response_model=list[BiasGate])
async def get_bias_gates() -> list[BiasGate]:
    """Return bias gate checks."""
    return _BIAS_GATES
