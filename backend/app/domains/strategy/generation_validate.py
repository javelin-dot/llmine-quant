"""Semantic and AST validation for AI strategy generation (Phase 2 task 3).

Pydantic already enforces JSON shape; this module adds:

- DSL semantics vs. ``risk_profile`` / ``market`` (position caps, drawdown caps, factor params).
- Generated Python: syntax plus required class/method contract (legacy ``RuleBasedStrategy``
  pipeline or ``BaseStrategy`` runtime contract).
- Minimal **future-function / look-ahead** rules on generated code (negative shifts, etc.)
  and obvious future-looking **DSL filter field** names.
"""

from __future__ import annotations

import ast
import math
import re

from app.domains.strategy.generation_dsl import FactorSpec, StrategyGenerationSpec

_MAX_SINGLE_WEIGHT_BY_PROFILE: dict[str, float] = {
    "conservative": 0.05,
    "balanced": 0.10,
    "aggressive": 0.20,
}

_MAX_DD_BY_PROFILE: dict[str, float] = {
    "conservative": 0.12,
    "balanced": 0.20,
    "aggressive": 0.35,
}

_MARKETS_ALLOWED = frozenset({"A", "US", "HK", "crypto"})

_NAME_PATTERN = re.compile(r"^[a-zA-Z][a-zA-Z0-9_]{0,63}$")

_FUTURE_FIELD_SNIPPETS = (
    "_t+",
    "t+1",
    "next_",
    "forward_",
    "_fwd",
    "future_",
    "lead_",
    "tomorrow",
)


def validate_spec_semantics(
    spec: StrategyGenerationSpec,
    *,
    risk_profile: str,
    market: str,
) -> None:
    """Raise ``ValueError`` when the DSL disagrees with task risk/market context."""
    if risk_profile not in _MAX_SINGLE_WEIGHT_BY_PROFILE:
        raise ValueError(f"unknown risk_profile: {risk_profile!r}")

    if market and market not in _MARKETS_ALLOWED:
        raise ValueError(f"market must be one of {sorted(_MARKETS_ALLOWED)}, got {market!r}")

    cap_w = _MAX_SINGLE_WEIGHT_BY_PROFILE[risk_profile]
    if spec.position_rules.max_single_name_weight > cap_w + 1e-9:
        raise ValueError(
            f"position_rules.max_single_name_weight ({spec.position_rules.max_single_name_weight}) "
            f"exceeds cap for {risk_profile!r} ({cap_w})"
        )

    cap_dd = _MAX_DD_BY_PROFILE[risk_profile]
    if spec.risk_rules.max_portfolio_drawdown > cap_dd + 1e-9:
        raise ValueError(
            f"risk_rules.max_portfolio_drawdown ({spec.risk_rules.max_portfolio_drawdown}) "
            f"exceeds cap for {risk_profile!r} ({cap_dd})"
        )

    for factor in spec.factors:
        _validate_factor_spec(factor)

    for flt in spec.filters:
        low = flt.field.lower()
        for snip in _FUTURE_FIELD_SNIPPETS:
            if snip in low:
                raise ValueError(
                    f"filter field {flt.field!r} looks like a future-dated or forward-looking "
                    "column; use only values observable at the rebalance date"
                )


def _validate_factor_spec(factor: FactorSpec) -> None:
    if not _NAME_PATTERN.match(factor.name):
        raise ValueError(
            f"invalid factor name {factor.name!r}: use ASCII letters, digits, underscore; max 64 chars"
        )
    for key, raw in factor.params.items():
        if not isinstance(key, str) or not key:
            raise ValueError("factor params keys must be non-empty strings")
        kl = key.lower()
        if kl in {"window", "lookback", "days", "period"}:
            if isinstance(raw, bool) or not isinstance(raw, (int, float)):
                raise ValueError(f"factor {factor.name!r} param {key!r} must be numeric")
            v = float(raw)
            if not math.isfinite(v) or v < 1 or v > 252:
                raise ValueError(
                    f"factor {factor.name!r} param {key!r} must be between 1 and 252, got {raw!r}"
                )


def validate_generated_strategy_ast(code: str) -> None:
    """Parse ``code``, block obvious look-ahead patterns, then verify strategy class shape."""
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        raise ValueError(f"invalid Python syntax: {exc}") from exc

    _assert_no_forward_leak_in_ast(tree)

    classes = [n for n in tree.body if isinstance(n, ast.ClassDef)]
    if not classes:
        raise ValueError("generated code must define at least one class")

    for cls in classes:
        if _class_matches_strategy_contract(cls):
            return

    raise ValueError(
        "no class found subclassing RuleBasedStrategy or BaseStrategy with required methods "
        "(generate_signals + risk_check, or generate_signals + rebalance)"
    )


def _class_matches_strategy_contract(cls: ast.ClassDef) -> bool:
    base_ids = _class_base_names(cls)
    methods = {n.name for n in cls.body if isinstance(n, ast.FunctionDef)}

    if "RuleBasedStrategy" in base_ids:
        return "generate_signals" in methods and "risk_check" in methods

    if "BaseStrategy" in base_ids:
        return "generate_signals" in methods and "rebalance" in methods

    return False


def _class_base_names(cls: ast.ClassDef) -> set[str]:
    names: set[str] = set()
    for base in cls.bases:
        if isinstance(base, ast.Name):
            names.add(base.id)
        elif isinstance(base, ast.Attribute):
            if isinstance(base.attr, str):
                names.add(base.attr)
    return names


def _assert_no_forward_leak_in_ast(tree: ast.AST) -> None:
    """Reject a small set of AST patterns that typically imply look-ahead bias."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            _raise_if_forward_leak_call(node)


def _raise_if_forward_leak_call(node: ast.Call) -> None:
    func = node.func
    if isinstance(func, ast.Attribute):
        if func.attr == "shift":
            _raise_if_negative_shift(node)
        elif func.attr in {"pct_change", "diff"}:
            _raise_if_negative_first_period(node, func.attr)
        elif func.attr == "roll" and len(node.args) >= 2:
            if _is_strictly_negative_constant(node.args[1]):
                raise ValueError(
                    "np.roll / roll with negative shift is not allowed (uses future observations)"
                )
    elif isinstance(func, ast.Name) and func.id == "roll" and len(node.args) >= 2:
        if _is_strictly_negative_constant(node.args[1]):
            raise ValueError(
                "roll(...) with negative shift is not allowed (uses future observations)"
            )


def _raise_if_negative_shift(node: ast.Call) -> None:
    if node.args and _is_strictly_negative_constant(node.args[0]):
        raise ValueError(
            "negative .shift(...) is not allowed (shifts into future observations)"
        )
    for kw in node.keywords or []:
        if kw.arg in ("periods", "n", "period") and _is_strictly_negative_constant(kw.value):
            raise ValueError(
                "negative shift periods are not allowed (look-ahead / future data leak)"
            )


def _raise_if_negative_first_period(node: ast.Call, name: str) -> None:
    if node.args and _is_strictly_negative_constant(node.args[0]):
        raise ValueError(
            f"negative first argument to .{name}(...) is not allowed (typically looks ahead)"
        )
    for kw in node.keywords or []:
        if kw.arg in ("periods", "n", "period") and _is_strictly_negative_constant(kw.value):
            raise ValueError(
                f"negative {name} periods are not allowed (look-ahead / future data leak)"
            )


def _is_strictly_negative_constant(expr: ast.expr) -> bool:
    if isinstance(expr, ast.UnaryOp) and isinstance(expr.op, ast.USub):
        return _is_positive_nonzero_constant(expr.operand)
    if isinstance(expr, ast.Constant) and isinstance(expr.value, (int, float)):
        return expr.value < 0
    return False


def _is_positive_nonzero_constant(expr: ast.expr) -> bool:
    if isinstance(expr, ast.Constant) and isinstance(expr.value, (int, float)):
        return expr.value > 0 and math.isfinite(float(expr.value))
    return False
