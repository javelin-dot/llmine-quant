"""Security Service API — vault, AI permissions, withdrawal guards, security events."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.domains.security.schemas import (
    AIPermissionBlock,
    AIPermissionCategory,
    AIPermissionItem,
    AccountPermission,
    SecurityAccount,
    SecurityEventOut,
    SecurityHeader,
    SecurityKpi,
    SecurityScreen,
    VaultKeyOut,
    VaultSummary,
    WithdrawalPanel,
    WithdrawalRuleOut,
)

router = APIRouter()

_HEADER = SecurityHeader(
    healthScore=96,
    healthStatus="SECURE",
    healthStatusTone="green",
    vaultArmed=True,
    withdrawalEnabled=False,
    lastRotation="2026-04-15",
    nextRotation="2026-07-15",
    keyExpiringIn="66 天",
    plaintextLeaks=0,
    aiViolations24h=0,
)

_KPIS = [
    SecurityKpi(label="Vault Keys", value="24", trend="→", tone="blue"),
    SecurityKpi(label="Key Rotations", value="3", trend="▲", tone="green"),
    SecurityKpi(label="AI Violations", value="0", trend="→", tone="green"),
    SecurityKpi(label="Blocked Withdrawals", value="2", trend="▲", tone="yellow"),
    SecurityKpi(label="Security Events", value="5", trend="▼", tone="green"),
]

_ACCOUNTS = [
    SecurityAccount(
        id="acc-001", name="主资金账户", role="live-main", roleLabel="实盘主账户", roleTone="red",
        balance="¥850万", balanceUsd="$118万", cap="¥1000万", capPct=0.85,
        aiPermissions=[
            AccountPermission(label="买入", tone="green"),
            AccountPermission(label="卖出", tone="green"),
            AccountPermission(label="撤单", tone="yellow"),
            AccountPermission(label="提现", tone="red"),
        ],
        withdrawalEnabled=False,
        desc="实盘交易主账户，仅允许交易操作，禁止提现",
    ),
    SecurityAccount(
        id="acc-002", name="模拟盘账户", role="paper", roleLabel="模拟盘", roleTone="green",
        balance="¥500万", balanceUsd="$69万", cap="¥500万", capPct=1.0,
        aiPermissions=[
            AccountPermission(label="买入", tone="green"),
            AccountPermission(label="卖出", tone="green"),
            AccountPermission(label="撤单", tone="green"),
            AccountPermission(label="策略切换", tone="green"),
        ],
        withdrawalEnabled=False,
        desc="模拟盘账户，AI 拥有完全操作权限",
    ),
    SecurityAccount(
        id="acc-003", name="托管账户", role="custody", roleLabel="资金托管", roleTone="blue",
        balance="¥2000万", balanceUsd="$278万", cap="¥2000万", capPct=1.0,
        aiPermissions=[
            AccountPermission(label="查看", tone="green"),
            AccountPermission(label="交易", tone="red"),
            AccountPermission(label="提现", tone="red"),
        ],
        withdrawalEnabled=False,
        desc="资金托管账户，仅人工可操作",
    ),
]

_VAULT = VaultSummary(
    totalKeys=24,
    apiKeys=12,
    walletKeys=4,
    rotated30d=3,
    expiringSoon=2,
    expired=0,
    plaintextLeaks=0,
    keys=[
        VaultKeyOut(id="k1", label="Tushare Pro", type="api", typeTone="blue", provider="Tushare", rotated="2026-04-15", expires="2026-10-15", daysToExpiry=158, status="active", statusTone="green", scope="数据读取"),
        VaultKeyOut(id="k2", label="Wind 机构", type="api", typeTone="blue", provider="Wind", rotated="2026-03-01", expires="2026-09-01", daysToExpiry=114, status="active", statusTone="green", scope="数据读取"),
        VaultKeyOut(id="k3", label="券商直连", type="api", typeTone="yellow", provider="中信证券", rotated="2026-05-01", expires="2026-06-01", daysToExpiry=22, status="expiring", statusTone="yellow", scope="交易执行"),
        VaultKeyOut(id="k4", label="冷钱包", type="wallet", typeTone="red", provider="Ledger", rotated="2026-01-01", expires="2027-01-01", daysToExpiry=266, status="active", statusTone="green", scope="资金存储"),
    ],
)

_AI_PERMISSIONS = [
    AIPermissionCategory(
        category="交易执行",
        allowed=[
            AIPermissionItem(api="place_order", desc="下单买入/卖出"),
            AIPermissionItem(api="cancel_order", desc="撤销未成交订单"),
            AIPermissionItem(api="query_position", desc="查询持仓"),
        ],
        blocked=[
            AIPermissionBlock(api="withdraw", desc="资金提现", reason="需人工二次确认"),
            AIPermissionBlock(api="transfer", desc="资金划转", reason="需人工二次确认"),
        ],
    ),
    AIPermissionCategory(
        category="数据访问",
        allowed=[
            AIPermissionItem(api="query_market_data", desc="查询行情数据"),
            AIPermissionItem(api="query_fundamental", desc="查询财务数据"),
            AIPermissionItem(api="query_news", desc="查询新闻舆情"),
        ],
        blocked=[
            AIPermissionBlock(api="export_raw_data", desc="导出原始数据", reason="超出 AI 权限范围"),
        ],
    ),
]

_WITHDRAWAL = WithdrawalPanel(
    enabled=False,
    whitelistAddresses=5,
    pendingApprovals=0,
    blocks24h=2,
    lastBlock="2h ago",
    rules=[
        WithdrawalRuleOut(name="单笔限额", desc="单笔提现不超过 100 万", status="enforced", statusTone="green"),
        WithdrawalRuleOut(name="日累计限额", desc="每日累计提现不超过 500 万", status="enforced", statusTone="green"),
        WithdrawalRuleOut(name="白名单", desc="仅允许提现到白名单地址", status="enforced", statusTone="green"),
        WithdrawalRuleOut(name="AI 自主提现", desc="AI 可在限额内自主提现", status="disabled", statusTone="red"),
    ],
)

_EVENTS = [
    SecurityEventOut(
        time="09:15", type="block", typeTone="red", severity="high", severityTone="red",
        title="阻止异常提现请求", actor="Risk", detail="检测到单笔提现金额 200 万，超出单笔限额",
        resolution="已拦截，通知管理员", status="resolved", statusTone="green",
    ),
    SecurityEventOut(
        time="08:30", type="rotation", typeTone="green", severity="info", severityTone="green",
        title="API Key 自动轮换", actor="System", detail="Tushare Pro Key 已自动轮换",
        resolution="轮换成功，旧 Key 已失效", status="resolved", statusTone="green",
    ),
]


@router.get("/overview", response_model=SecurityScreen)
async def get_security_overview(db: AsyncSession = Depends(get_db)) -> SecurityScreen:
    """Return the complete Security & Vault screen data."""
    return SecurityScreen(
        header=_HEADER,
        kpis=_KPIS,
        accounts=_ACCOUNTS,
        vault=_VAULT,
        aiPermissions=_AI_PERMISSIONS,
        withdrawal=_WITHDRAWAL,
        events=_EVENTS,
    )


@router.post("/vault/rotate/{key_id}")
async def rotate_key(key_id: str) -> dict[str, str]:
    """Rotate a vault key."""
    return {"key_id": key_id, "status": "rotated"}
