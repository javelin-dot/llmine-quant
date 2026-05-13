"""API v1 router aggregation."""

from fastapi import APIRouter

from app.api.v1 import (
    agents,
    audit,
    auth,
    backtests,
    collaboration,
    dashboard,
    data,
    execution,
    explain,
    paper,
    portfolio,
    risk,
    security,
    strategies,
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
api_router.include_router(data.router, prefix="/data", tags=["Data Operations"])
api_router.include_router(strategies.router, prefix="/strategies", tags=["Strategy Factory"])
api_router.include_router(backtests.router, prefix="/backtests", tags=["Backtest Lab"])
api_router.include_router(risk.router, prefix="/risk", tags=["Risk Control"])
api_router.include_router(portfolio.router, prefix="/portfolio", tags=["Portfolio Cockpit"])
api_router.include_router(execution.router, prefix="/execution", tags=["Execution Center"])
api_router.include_router(explain.router, prefix="/explain", tags=["Explain & Trace"])
api_router.include_router(security.router, prefix="/security", tags=["Security & Vault"])
api_router.include_router(collaboration.router, prefix="/collaboration", tags=["Collaboration Lab"])
api_router.include_router(audit.router, prefix="/audit", tags=["Audit & Compliance"])
api_router.include_router(agents.router, prefix="/agents", tags=["Agent Orchestrator"])
api_router.include_router(paper.router, prefix="/paper", tags=["Paper Trading"])
