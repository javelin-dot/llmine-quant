"""Security Service API — vault, AI permissions, withdrawal guards."""

from fastapi import APIRouter

from app.domains.security.schemas import (
    SecurityHeader,
    SecurityScreen,
    VaultSummary,
    WithdrawalPanel,
)

router = APIRouter()


_HEADER = SecurityHeader(
    healthScore=0,
    healthStatus="—",
    healthStatusTone="yellow",
    vaultArmed=False,
    withdrawalEnabled=False,
    lastRotation="—",
    nextRotation="—",
    keyExpiringIn="—",
    plaintextLeaks=0,
    aiViolations24h=0,
)

_VAULT = VaultSummary(
    totalKeys=0,
    apiKeys=0,
    walletKeys=0,
    rotated30d=0,
    expiringSoon=0,
    expired=0,
    plaintextLeaks=0,
    keys=[],
)

_WITHDRAWAL = WithdrawalPanel(
    enabled=False,
    whitelistAddresses=0,
    pendingApprovals=0,
    blocks24h=0,
    lastBlock="—",
    rules=[],
)


@router.get("/overview", response_model=SecurityScreen)
async def get_security_overview() -> SecurityScreen:
    """Return vault shell; accounts and events wire to custody integrations later."""
    return SecurityScreen(
        header=_HEADER,
        kpis=[],
        accounts=[],
        vault=_VAULT,
        aiPermissions=[],
        withdrawal=_WITHDRAWAL,
        events=[],
    )


@router.post("/vault/rotate/{key_id}")
async def rotate_key(key_id: str) -> dict[str, str]:
    """Rotate a vault key."""
    return {"key_id": key_id, "status": "rotated"}
