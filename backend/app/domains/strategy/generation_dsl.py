"""Structured strategy generation DSL — LLM output must map into this shape (Phase 2).

Fields cover strategy kind, factors, universe filters, rebalance cadence, position
limits, and risk caps. Validation is strict (no unknown keys) so downstream
pipelines can rely on a stable contract.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

StrategyKind = Literal["rule", "ml", "portfolio"]
FactorKind = Literal["momentum", "value", "quality", "volatility", "size", "custom"]
FilterOperator = Literal["eq", "ne", "gt", "gte", "lt", "lte", "between", "in"]
RebalanceFrequency = Literal["1d", "1w", "2w", "1m"]


class FactorSpec(BaseModel):
    """Single factor or signal definition."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1, max_length=64)
    kind: FactorKind
    description: str | None = Field(default=None, max_length=512)
    params: dict[str, float | int | str] = Field(default_factory=dict)


class FilterCondition(BaseModel):
    """Universe or cross-sectional filter."""

    model_config = ConfigDict(extra="forbid")

    field: str = Field(..., min_length=1, max_length=64)
    operator: FilterOperator
    value: float | int | str | list[float | int | str]

    @model_validator(mode="after")
    def _validate_between(self) -> FilterCondition:
        if self.operator == "between":
            if not isinstance(self.value, list) or len(self.value) != 2:
                raise ValueError("operator 'between' requires value as a list of two scalars")
        elif self.operator == "in":
            if not isinstance(self.value, list) or len(self.value) < 1:
                raise ValueError("operator 'in' requires value as a non-empty list")
        return self


class PositionRules(BaseModel):
    """Portfolio construction and concentration limits."""

    model_config = ConfigDict(extra="forbid")

    target_gross_exposure: float = Field(default=1.0, ge=0.0, le=1.0)
    max_single_name_weight: float = Field(default=0.1, gt=0.0, le=1.0)
    min_positions: int = Field(default=1, ge=0, le=500)
    max_positions: int = Field(default=50, ge=1, le=500)

    @model_validator(mode="after")
    def _min_max_positions(self) -> PositionRules:
        if self.max_positions < self.min_positions:
            raise ValueError("max_positions must be >= min_positions")
        return self


class RiskRules(BaseModel):
    """Risk caps applied at design / pre-trade stage (not execution yet)."""

    model_config = ConfigDict(extra="forbid")

    max_portfolio_drawdown: float = Field(default=0.2, gt=0.0, le=1.0)
    per_symbol_stop_loss_pct: float | None = Field(default=None, gt=0.0, le=0.5)
    max_sector_weight: float | None = Field(default=None, gt=0.0, le=1.0)


class StrategyGenerationSpec(BaseModel):
    """Root document: validated strategy intent produced from NL + LLM."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    strategy_kind: StrategyKind
    factors: list[FactorSpec] = Field(default_factory=list, max_length=32)
    filters: list[FilterCondition] = Field(default_factory=list, max_length=64)
    rebalance_frequency: RebalanceFrequency = "1d"
    position_rules: PositionRules = Field(default_factory=PositionRules)
    risk_rules: RiskRules = Field(default_factory=RiskRules)

    @model_validator(mode="after")
    def _at_least_one_signal(self) -> StrategyGenerationSpec:
        if self.strategy_kind != "portfolio" and len(self.factors) < 1:
            raise ValueError("at least one factor is required unless strategy_kind is 'portfolio'")
        return self


def parse_strategy_generation_spec(data: dict[str, Any]) -> StrategyGenerationSpec:
    """Parse and validate a dict (e.g. JSON from LLM tool output)."""
    return StrategyGenerationSpec.model_validate(data)


def strategy_generation_json_schema() -> dict[str, Any]:
    """JSON Schema for LLM structured output (snake_case keys, matches model)."""
    return StrategyGenerationSpec.model_json_schema()


def build_strategy_metadata_bundle(
    spec: StrategyGenerationSpec,
    *,
    prompt_excerpt: str,
    display_seed: str,
) -> dict[str, Any]:
    """Map a validated DSL document into legacy metadata keys used by persistence/UI.

    ``params`` holds the full spec dict for ``StrategyVersion.params_schema``;
    ``riskRules`` mirrors ``risk_rules`` for ``StrategyVersion.risk_rules``.
    """
    first = spec.factors[0] if spec.factors else None
    family_map: dict[FactorKind, str] = {
        "momentum": "momentum",
        "value": "value",
        "quality": "quality",
        "volatility": "mean_reversion",
        "size": "value",
        "custom": "trend",
    }
    family = family_map.get(first.kind, "trend") if first else "portfolio"
    name = (first.name[:32] if first else f"AI-{display_seed[:6]}") or f"AI-{display_seed[:6]}"
    universe_bits = [f"{f.field}:{f.operator}" for f in spec.filters[:5]]
    universe = ", ".join(universe_bits) if universe_bits else "unspecified"
    description = (prompt_excerpt[:100] if prompt_excerpt else name)[:100]
    return {
        "name": name,
        "family": family,
        "description": description,
        "universe": universe[:128],
        "frequency": spec.rebalance_frequency,
        "expected_sharpe": 1.2,
        "expected_max_dd": float(spec.risk_rules.max_portfolio_drawdown),
        "params": spec.model_dump(),
        "riskRules": spec.risk_rules.model_dump(),
    }
