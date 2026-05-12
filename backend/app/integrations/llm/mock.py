"""Mock LLM provider — returns deterministic, hand-crafted strategy code.

Use this when no API key is configured (CI, local dev, free-tier demos).
Generates a realistic A-share value strategy based on `RuleBasedStrategy`.
"""

import json
from typing import Any

from app.integrations.llm.base import LLMMessage, LLMProvider, LLMResponse

_MOCK_STRATEGY_TEMPLATE = '''class GeneratedValueStrategy(RuleBasedStrategy):
    """Auto-generated value strategy — picks low-PE, high-ROE names with momentum filter."""

    def __init__(self, risk_profile: str = "balanced") -> None:
        super().__init__()
        self.risk_profile = risk_profile
        self.max_weight = {{"conservative": 0.05, "balanced": 0.10, "aggressive": 0.20}}[risk_profile]
        self.max_leverage = {{"conservative": 1.0, "balanced": 1.5, "aggressive": 2.0}}[risk_profile]
        self.lookback = 20

    def generate_signals(self, data):
        import numpy as np
        import pandas as pd

        # Value score
        pe = data["pe"].replace([np.inf, -np.inf], np.nan)
        roe = data["roe"].fillna(0.0)
        value_score = roe / pe.clip(lower=1.0)
        value_rank = value_score.rank(pct=True)

        # Momentum filter (positive 20d return)
        if "close" in data.columns and len(data) >= self.lookback:
            mom = data["close"].pct_change(self.lookback).fillna(0.0)
            mom_filter = (mom > 0).astype(float)
        else:
            mom_filter = pd.Series(1.0, index=data.index)

        # Equal weight top-quintile after momentum filter
        eligible = (value_rank >= 0.8) & (mom_filter > 0)
        n_eligible = max(eligible.sum(), 1)
        raw_weight = eligible.astype(float) / n_eligible

        # Clip to per-position cap
        weights = raw_weight.clip(upper=self.max_weight)
        return weights

    def risk_check(self, signals, portfolio):
        # Enforce gross leverage cap
        gross = signals.abs().sum()
        if gross > self.max_leverage:
            signals = signals * (self.max_leverage / gross)
        return signals
'''


_MOCK_STRATEGY_SPEC: dict[str, Any] = {
    "schema_version": "1.0",
    "strategy_kind": "rule",
    "factors": [
        {
            "name": "value_score",
            "kind": "value",
            "description": "ROE/PE composite",
            "params": {"pe_cap": 30},
        },
        {"name": "mom_20d", "kind": "momentum", "params": {"window": 20}},
    ],
    "filters": [{"field": "market_cap", "operator": "gte", "value": 5_000_000_000}],
    "rebalance_frequency": "1d",
    "position_rules": {
        "target_gross_exposure": 1.0,
        "max_single_name_weight": 0.1,
        "min_positions": 5,
        "max_positions": 40,
    },
    "risk_rules": {
        "max_portfolio_drawdown": 0.18,
        "per_symbol_stop_loss_pct": 0.08,
        "max_sector_weight": 0.35,
    },
}


def _is_strategy_generation_spec_schema(schema: dict[str, Any]) -> bool:
    props = schema.get("properties")
    if not isinstance(props, dict):
        return False
    return "strategy_kind" in props and "factors" in props


_MOCK_METADATA: dict[str, Any] = {
    "name": "AI 价值精选 v1",
    "family": "value",
    "description": "ROE/PE 复合打分 + 20 日动量确认，等权配置头部分位",
    "universe": "沪深300",
    "frequency": "1d",
    "expected_sharpe": 1.35,
    "expected_max_dd": 0.18,
}


class MockLLMProvider(LLMProvider):
    """Deterministic mock provider for offline/free usage."""

    name = "mock"
    default_model = "mock-strategy-v1"

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.2,
        history: list[LLMMessage] | None = None,
    ) -> LLMResponse:
        # Always return the canned strategy template, regardless of prompt.
        return LLMResponse(
            text=_MOCK_STRATEGY_TEMPLATE,
            model=self.model,
            provider=self.name,
            usage={"prompt_tokens": len(prompt) // 4, "completion_tokens": len(_MOCK_STRATEGY_TEMPLATE) // 4},
            raw=None,
        )

    async def generate_structured(
        self,
        prompt: str,
        output_schema: dict[str, Any],
        system_prompt: str | None = None,
        temperature: float = 0.2,
    ) -> dict[str, Any]:
        if _is_strategy_generation_spec_schema(output_schema):
            return json.loads(json.dumps(_MOCK_STRATEGY_SPEC))
        return json.loads(json.dumps(_MOCK_METADATA))
