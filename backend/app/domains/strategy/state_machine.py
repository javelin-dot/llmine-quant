"""Strategy lifecycle state machine."""

# Valid transitions: from_status -> list[to_status]
STRATEGY_TRANSITIONS: dict[str, list[str]] = {
    "draft": ["backtesting", "archived"],
    "backtesting": ["paper", "draft", "archived"],
    "paper": ["live", "backtesting", "paused", "archived"],
    "live": ["paused", "archived"],
    "paused": ["live", "backtesting", "archived"],
    "archived": ["draft"],
}


def can_transition(from_status: str, to_status: str) -> bool:
    """Check if a strategy status transition is valid."""
    allowed = STRATEGY_TRANSITIONS.get(from_status, [])
    return to_status in allowed


def get_allowed_transitions(status: str) -> list[str]:
    """Get all allowed transitions from a given status."""
    return STRATEGY_TRANSITIONS.get(status, [])
