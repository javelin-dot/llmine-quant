"""Collaboration Service API — reviews, diffs, A/B tests, approval flows."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.domains.collaboration.schemas import (
    ABTestOut,
    ActiveReview,
    ApprovalFlowStage,
    CollaborationScreen,
    DiffPanel,
    DiffRow,
    FooterCard,
    Kpi,
    ReviewThreadItem,
    Reviewer,
)

router = APIRouter()

_KPIS = [
    Kpi(label="活跃评审", value="3", trend="+1", tone="yellow"),
    Kpi(label="A/B 测试", value="2", trend="→", tone="blue"),
    Kpi(label="审批通过率", value="92%", trend="▲", tone="green"),
    Kpi(label="平均评审时长", value="4.2h", trend="▼", tone="green"),
]

_ACTIVE_REVIEWS = [
    ActiveReview(
        id="r1", strategy="MA趋势", fromVer="v1.2", toVer="v1.3",
        status="in_review", statusTone="yellow",
        reviewers=[
            Reviewer(role="策略负责人", decision="approve", tone="green"),
            Reviewer(role="风控审核", decision="request_changes", tone="yellow"),
            Reviewer(role="技术审核", decision="pending", tone="gray"),
        ],
        createdAt="2026-05-09", priority="high", priorityTone="red",
    ),
    ActiveReview(
        id="r2", strategy="价值选股", fromVer="v2.0", toVer="v2.1",
        status="pending", statusTone="yellow",
        reviewers=[
            Reviewer(role="策略负责人", decision="pending", tone="gray"),
            Reviewer(role="风控审核", decision="pending", tone="gray"),
        ],
        createdAt="2026-05-10", priority="medium", priorityTone="yellow",
    ),
]

_DIFF = DiffPanel(
    header="MA趋势 v1.2 → v1.3 变更对比",
    rows=[
        DiffRow(field="止损逻辑", from_="固定 5%", to="ATR 动态止损", impact="降低假突破损耗"),
        DiffRow(field="仓位计算", from_="等权重", to="凯利公式优化", impact="提升资金效率"),
        DiffRow(field="过滤条件", from_="无", to="加入成交量确认", impact="减少低质量信号"),
        DiffRow(field="回测周期", from_="3年", to="5年", impact="覆盖更多市场周期"),
    ],
)

_REVIEW_THREAD = [
    ReviewThreadItem(role="Strategy Agent", text="提交 MA趋势 v1.3 版本，主要优化止损逻辑和仓位计算。", tag="提交", tagClass="tag-blue"),
    ReviewThreadItem(role="Risk Agent", text="建议增加成交量确认过滤，避免无量突破。", tag="建议", tagClass="tag-yellow"),
    ReviewThreadItem(role="Strategy Agent", text="已采纳，新增成交量 > 20日均量 1.5x 条件。", tag="更新", tagClass="tag-green"),
    ReviewThreadItem(role="Human Reviewer", text="策略逻辑合理，回测数据完整，建议通过。", tag="审批", tagClass="tag-purple"),
]

_AB_TESTS = [
    ABTestOut(
        id="ab1", name="止损优化测试", control="MA趋势_v1.2", variant="MA趋势_v1.3",
        status="running", statusTone="green", duration="30 天", samples=1250,
        improvement=0.035, sparkline=[1.0, 1.01, 1.02, 1.025, 1.03, 1.032, 1.035],
    ),
    ABTestOut(
        id="ab2", name="因子权重测试", control="价值选股_v2.0", variant="价值选股_v2.1",
        status="completed", statusTone="blue", duration="60 天", samples=3200,
        improvement=0.018, sparkline=[1.0, 1.005, 1.01, 1.012, 1.015, 1.016, 1.018],
    ),
]

_APPROVAL_FLOW = [
    ApprovalFlowStage(stage="策略自测", tone="green", required=True, completed=True, assignee="Strategy Agent", note="回测通过，夏普 1.34"),
    ApprovalFlowStage(stage="风控审查", tone="yellow", required=True, completed=True, assignee="Risk Agent", note="VaR 检查通过，集中度合规"),
    ApprovalFlowStage(stage="技术审核", tone="blue", required=True, completed=False, assignee="Tech Lead", note="待代码审查"),
    ApprovalFlowStage(stage="人工审批", tone="purple", required=True, completed=False, assignee="投资总监", note="待最终确认"),
]

_FOOTER_CARDS = [
    FooterCard(title="评审规范", desc="所有策略变更必须经过至少 2 人评审", tag="规范", tagClass="tag-blue"),
    FooterCard(title="A/B 测试指南", desc="最小样本量 1000 笔交易，观察期 30 天", tag="指南", tagClass="tag-green"),
]


@router.get("/overview", response_model=CollaborationScreen)
async def get_collaboration_overview(db: AsyncSession = Depends(get_db)) -> CollaborationScreen:
    """Return the complete Collaboration Lab screen data."""
    return CollaborationScreen(
        kpis=_KPIS,
        activeReviews=_ACTIVE_REVIEWS,
        diff=_DIFF,
        reviewThread=_REVIEW_THREAD,
        abTests=_AB_TESTS,
        approvalFlow=_APPROVAL_FLOW,
        footerCards=_FOOTER_CARDS,
    )


@router.post("/reviews/{review_id}/approve")
async def approve_review(review_id: str) -> dict[str, str]:
    """Approve a strategy review."""
    return {"review_id": review_id, "status": "approved"}
