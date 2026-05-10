"""Explain Service API — signal attribution, decision chain, lineage, bias gates."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.domains.explain.schemas import (
    AttributionItemOut,
    AttributionOut,
    BiasGateOut,
    ConfidenceRadar,
    DecisionChainStep,
    ExplainScreen,
    LineageStep,
    RadarAxis,
    SignalHeader,
    SimilarCaseOut,
    SimilarHistory,
)

router = APIRouter()

_SIGNAL_HEADER = SignalHeader(
    strategy="MA趋势",
    action="BUY",
    target="贵州茅台 (600519)",
    size="100股 / ¥16.8万",
    confidence=0.92,
    riskGrade="A",
    traceId="trace-20260510-093115",
    timestamp="2026-05-10 09:31:15",
    status="待审批",
    statusTone="yellow",
)

_ATTRIBUTION = AttributionOut(
    base=0.50,
    items=[
        AttributionItemOut(name="趋势动量", value=0.25, desc="MA5 > MA20，短期趋势向上"),
        AttributionItemOut(name="成交量确认", value=0.12, desc="成交量放大 1.8x，确认突破"),
        AttributionItemOut(name="行业景气度", value=0.08, desc="白酒板块动量排名前 10%"),
        AttributionItemOut(name="估值修复", value=0.05, desc="PE 处于历史 35% 分位"),
        AttributionItemOut(name="情绪指标", value=-0.02, desc="市场情绪偏谨慎，轻微扣分"),
    ],
    final=0.98,
    decision="强烈买入",
    decisionTone="green",
)

_CONFIDENCE_RADAR = ConfidenceRadar(
    axes=[
        RadarAxis(name="数据质量", score=0.95, desc="数据源完整，无缺失"),
        RadarAxis(name="模型稳定性", score=0.88, desc="过去 30 天信号一致性高"),
        RadarAxis(name="因子显著性", score=0.92, desc="动量因子 t-stat > 2.5"),
        RadarAxis(name="回测表现", score=0.85, desc="样本外夏普 1.34"),
        RadarAxis(name="风险控制", score=0.90, desc="止损位合理，仓位可控"),
        RadarAxis(name="可解释性", score=0.78, desc="决策链逻辑清晰"),
    ],
    avg=0.88,
)

_DECISION_CHAIN = [
    DecisionChainStep(step=1, title="信号生成", desc="MA趋势策略扫描全市场", detail="识别出 600519 满足 MA5 > MA20 且成交量放大", tag="Strategy", tone="blue"),
    DecisionChainStep(step=2, title="因子打分", desc="多因子模型综合评分", detail="趋势动量 0.25 + 成交量 0.12 + 行业 0.08 + 估值 0.05 = 0.50", tag="Model", tone="purple"),
    DecisionChainStep(step=3, title="风险检查", desc="三层风控系统审查", detail="通过集中度检查、VaR 检查、涨跌停检查", tag="Risk", tone="green"),
    DecisionChainStep(step=4, title="组合影响", desc="预估对组合的影响", detail="权重将从 7.2% 升至 8.5%，夏普比率预计 +0.02", tag="Portfolio", tone="yellow"),
    DecisionChainStep(step=5, title="人类审批", desc="待人工确认", detail="该信号名义金额超过单票限额 80%，需人工审批", tag="HITL", tone="red"),
]

_LINEAGE = [
    LineageStep(step="原始数据", version="AKShare v2.1.0", hash="a1b2c3", permission="read", permissionTone="green", detail="日线行情、成交量、复权因子"),
    LineageStep(step="特征工程", version="FeatureSet v4.2.0", hash="d4e5f6", permission="read", permissionTone="green", detail="MA5、MA20、成交量比率、行业动量"),
    LineageStep(step="模型推理", version="MA趋势 v1.0.0", hash="g7h8i9", permission="execute", permissionTone="yellow", detail="XGBoost 分类模型，预测 5 日收益方向"),
    LineageStep(step="信号生成", version="Signal v1.0.0", hash="j0k1l2", permission="read", permissionTone="green", detail="BUY 600519 100股 @ 1680.00"),
    LineageStep(step="风控审查", version="RiskEngine v3.0.0", hash="m3n4o5", permission="execute", permissionTone="green", detail="通过所有风控检查"),
]

_BIAS_GATES = [
    BiasGateOut(check="未来函数检测", status="pass", desc="特征计算未使用未来数据"),
    BiasGateOut(check="幸存者偏差", status="pass", desc="已排除退市股票"),
    BiasGateOut(check="数据窥探", status="watch", desc="该因子在 50 个因子中被选中，可能存在过拟合风险"),
    BiasGateOut(check="回测偏差", status="pass", desc="滑点、佣金已按实盘标准计入"),
]

_SIMILAR_HISTORY = SimilarHistory(
    summary="过去 3 年中，该策略在相似条件下共发出 24 次买入信号",
    winRate=0.68,
    avgReturn=0.052,
    cases=[
        SimilarCaseOut(id="c1", date="2025-08-12", action="BUY", ret=0.085, days=5, success=True, note="突破后 5 日上涨 8.5%"),
        SimilarCaseOut(id="c2", date="2025-03-20", action="BUY", ret=-0.021, days=5, success=False, note="突破失败，5 日下跌 2.1%"),
        SimilarCaseOut(id="c3", date="2024-11-05", action="BUY", ret=0.042, days=5, success=True, note="震荡后 5 日上涨 4.2%"),
        SimilarCaseOut(id="c4", date="2024-06-18", action="BUY", ret=0.031, days=5, success=True, note="温和上涨 3.1%"),
    ],
)


@router.get("/overview", response_model=ExplainScreen)
async def get_explain_overview(db: AsyncSession = Depends(get_db)) -> ExplainScreen:
    """Return the complete Explain & Trace screen data."""
    return ExplainScreen(
        signalHeader=_SIGNAL_HEADER,
        attribution=_ATTRIBUTION,
        confidenceRadar=_CONFIDENCE_RADAR,
        decisionChain=_DECISION_CHAIN,
        lineage=_LINEAGE,
        biasGate=_BIAS_GATES,
        similarHistory=_SIMILAR_HISTORY,
    )
