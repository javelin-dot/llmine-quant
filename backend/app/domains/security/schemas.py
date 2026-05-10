"""Security domain Pydantic schemas aligned with frontend MockData."""

from pydantic import BaseModel


class SecurityHeader(BaseModel):
    healthScore: int
    healthStatus: str
    healthStatusTone: str
    vaultArmed: bool
    withdrawalEnabled: bool
    lastRotation: str
    nextRotation: str
    keyExpiringIn: str
    plaintextLeaks: int
    aiViolations24h: int


class SecurityKpi(BaseModel):
    label: str
    value: str
    trend: str
    tone: str


class AIPermissionItem(BaseModel):
    api: str
    desc: str


class AIPermissionBlock(BaseModel):
    api: str
    desc: str
    reason: str


class AIPermissionCategory(BaseModel):
    category: str
    allowed: list[AIPermissionItem]
    blocked: list[AIPermissionBlock]


class VaultKeyOut(BaseModel):
    id: str
    label: str
    type: str
    typeTone: str
    provider: str
    rotated: str
    expires: str
    daysToExpiry: int
    status: str
    statusTone: str
    scope: str


class VaultSummary(BaseModel):
    totalKeys: int
    apiKeys: int
    walletKeys: int
    rotated30d: int
    expiringSoon: int
    expired: int
    plaintextLeaks: int
    keys: list[VaultKeyOut]


class AccountPermission(BaseModel):
    label: str
    tone: str


class SecurityAccount(BaseModel):
    id: str
    name: str
    role: str
    roleLabel: str
    roleTone: str
    balance: str
    balanceUsd: str
    cap: str
    capPct: float
    aiPermissions: list[AccountPermission]
    withdrawalEnabled: bool
    desc: str


class WithdrawalRuleOut(BaseModel):
    name: str
    desc: str
    status: str
    statusTone: str


class WithdrawalPanel(BaseModel):
    enabled: bool
    whitelistAddresses: int
    pendingApprovals: int
    blocks24h: int
    lastBlock: str
    rules: list[WithdrawalRuleOut]


class SecurityEventOut(BaseModel):
    time: str
    type: str
    typeTone: str
    severity: str
    severityTone: str
    title: str
    actor: str
    detail: str
    resolution: str
    status: str
    statusTone: str


class SecurityScreen(BaseModel):
    header: SecurityHeader
    kpis: list[SecurityKpi]
    accounts: list[SecurityAccount]
    vault: VaultSummary
    aiPermissions: list[AIPermissionCategory]
    withdrawal: WithdrawalPanel
    events: list[SecurityEventOut]
