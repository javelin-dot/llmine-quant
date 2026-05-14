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


def _is_universe_suggest_schema(schema: dict[str, Any]) -> bool:
    props = schema.get("properties")
    if not isinstance(props, dict):
        return False
    return "selected" in props and "excluded" in props


def _mock_universe_response(prompt: str) -> dict[str, Any]:
    """Parse symbol list from prompt and return a mock AI-selected universe."""
    import re
    symbols_found: list[tuple[str, int, int]] = []

    # New format (CSI index pool):
    #   300750.SZ 宁德时代: 指数权重4.393%, 本地数据:1055根K线(2022-01-04~2026-05-08)
    for m in re.finditer(r"(\w+\.\w+)\s+\S+:\s*指数权重[\d.]+%,\s*本地数据:(\d+)根K线", prompt):
        sym, bars = m.group(1), int(m.group(2))
        symbols_found.append((sym, bars, bars))
    # New format — stocks without local data
    for m in re.finditer(r"(\w+\.\w+)\s+\S+:\s*指数权重[\d.]+%,\s*需导入数据", prompt):
        symbols_found.append((m.group(1), 0, 0))

    # Legacy format (old DB-only prompt): "  000001.SZ: 1055根K线, ..., 覆盖1585天"
    if not symbols_found:
        for m in re.finditer(r"(\w+\.\w+):\s*(\d+)根K线,.*?覆盖(\d+)天", prompt):
            sym, bars, days = m.group(1), int(m.group(2)), int(m.group(3))
            symbols_found.append((sym, bars, days))

    # Mock: select top 20 by bars count (already sorted in prompt), skip < 60 bars
    selected = []
    excluded = []
    reasons_select = [
        "数据连续性强，K线覆盖充足，适合趋势信号计算",
        "历史数据完整，覆盖多个市场周期，样本外泛化能力有保障",
        "流动性充足，日线数据无明显缺失，适合日频回测",
        "覆盖期跨越牛熊转换，有助于评估策略在不同市场环境下的稳健性",
    ]
    for i, (sym, bars, days) in enumerate(symbols_found):
        if bars < 60:
            excluded.append({"symbol": sym, "reason": f"数据不足（{bars}根K线，低于60根最低要求），统计显著性不足"})
        elif len(selected) < 20:
            selected.append({"symbol": sym, "reason": reasons_select[i % len(reasons_select)]})
        else:
            excluded.append({"symbol": sym, "reason": "已达到目标标的数量上限（20个），数据质量达标但不在优先队列内"})

    return {
        "selected": selected,
        "excluded": excluded,
        "rationale": (
            f"基于数据质量优先原则，从 {len(symbols_found)} 个可用标的中筛选出 {len(selected)} 个。"
            "筛选标准：K线数量充足（≥60根）、覆盖时间跨度长、数据连续性强。"
            "建议在每次回测前重新运行 Agent 构建，避免对固定标的集合过拟合。"
        ),
        "diversity_note": "当前为 Mock 模式（未配置真实 LLM），理由为模板生成。接入真实 AI 后将提供基于行业分散度、相关性分析的深度推荐。",
    }


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
        if _is_universe_suggest_schema(output_schema):
            return _mock_universe_response(prompt)
        return json.loads(json.dumps(_MOCK_METADATA))
