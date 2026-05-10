"""Audit domain Pydantic schemas aligned with frontend MockData."""

from pydantic import BaseModel


class AuditKpi(BaseModel):
    label: str
    value: str
    trend: str
    tone: str


class AuditRow(BaseModel):
    time: str
    actor: str
    actorType: str
    action: str
    resource: str
    result: str
    resultTone: str
    confidence: float
    detail: str
    traceId: str


class ActorStat(BaseModel):
    actor: str
    count: int
    tone: str


class ToolRegistryItem(BaseModel):
    name: str
    level: str
    levelTone: str
    desc: str
    agents: list[str]


class HitlRule(BaseModel):
    rule: str
    desc: str
    status: str
    statusTone: str


class AuditScreen(BaseModel):
    kpis: list[AuditKpi]
    rows: list[AuditRow]
    actorStats: list[ActorStat]
    toolRegistry: list[ToolRegistryItem]
    hitlRules: list[HitlRule]
