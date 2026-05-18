"""Dashboard API — overview aligned with frontend; empty placeholders until wired to telemetry."""

from fastapi import APIRouter

from app.schemas.dashboard import (
    Alert,
    DashboardOverview,
    Meta,
    ModalData,
    PortfolioMetrics,
    SystemHealth,
)

router = APIRouter()


_META = Meta(product="LLMine Quant", subtitle="AI-native quantitative platform")

_SYSTEM = SystemHealth(
    healthScore=0,
    healthStatusLabel="—",
    healthBarHeights=[0] * 12,
    autopilot=False,
    riskGateLabel="—",
)

_MODALS: dict[str, ModalData] = {
    "global": ModalData(title="", body="", primary=""),
    "kill": ModalData(title="", body="", primary=""),
    "create": ModalData(title="", body="", primary=""),
    "autopilot": ModalData(title="", body="", primary=""),
    "approve": ModalData(title="", body="", primary=""),
    "pause": ModalData(title="", body="", primary=""),
}


@router.get("/overview", response_model=DashboardOverview)
async def get_dashboard_overview() -> DashboardOverview:
    """Return dashboard shell; KPIs/charts wire to live aggregates in a future iteration."""
    return DashboardOverview(
        meta=_META,
        system=_SYSTEM,
        modals=_MODALS,
        marketIndices=[],
        portfolioMetrics=PortfolioMetrics(
            totalReturn=0.0,
            annualReturn=0.0,
            maxDrawdown=0.0,
            sharpeRatio=0.0,
            sortinoRatio=0.0,
            benchmark="—",
            benchmarkReturn=0.0,
        ),
        equityCurve=[],
        agents=[],
        alerts=[],
        strategies=[],
        pendingApprovals=0,
    )


@router.get("/system-health")
async def get_system_health() -> SystemHealth:
    """Return system health status."""
    return _SYSTEM


@router.get("/alerts")
async def get_alerts() -> list[Alert]:
    """Return active alerts."""
    return []
