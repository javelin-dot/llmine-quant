"""Tests for structured strategy generation DSL (Phase 2)."""

import pytest
from pydantic import ValidationError

from app.domains.strategy.generation_dsl import (
    FactorSpec,
    FilterCondition,
    PositionRules,
    StrategyGenerationSpec,
    build_strategy_metadata_bundle,
    parse_strategy_generation_spec,
    strategy_generation_json_schema,
)


def test_parse_minimal_rule_strategy():
    spec = parse_strategy_generation_spec(
        {
            "strategy_kind": "rule",
            "factors": [{"name": "ret_20d", "kind": "momentum", "params": {"window": 20}}],
        }
    )
    assert spec.strategy_kind == "rule"
    assert spec.rebalance_frequency == "1d"
    assert spec.factors[0].name == "ret_20d"
    assert spec.position_rules.target_gross_exposure == 1.0


def test_rejects_unknown_top_level_key():
    with pytest.raises(ValidationError):
        parse_strategy_generation_spec(
            {
                "strategy_kind": "rule",
                "factors": [{"name": "x", "kind": "value"}],
                "extra_field": 1,
            }
        )


def test_filter_between_requires_two_values():
    FilterCondition(field="pe_ttm", operator="between", value=[5.0, 25.0])
    with pytest.raises(ValidationError):
        FilterCondition(field="pe_ttm", operator="between", value=[5.0])


def test_filter_in_requires_list():
    with pytest.raises(ValidationError):
        FilterCondition(field="sector", operator="in", value="bank")


def test_portfolio_may_have_zero_factors():
    spec = parse_strategy_generation_spec({"strategy_kind": "portfolio", "factors": []})
    assert spec.factors == []


def test_rule_requires_at_least_one_factor():
    with pytest.raises(ValidationError, match="at least one factor"):
        parse_strategy_generation_spec({"strategy_kind": "rule", "factors": []})


def test_position_rules_max_ge_min():
    with pytest.raises(ValidationError, match="max_positions"):
        PositionRules(min_positions=10, max_positions=5)


def test_build_strategy_metadata_bundle_maps_legacy_keys():
    spec = parse_strategy_generation_spec(
        {
            "strategy_kind": "rule",
            "factors": [{"name": "roe_rank", "kind": "quality", "params": {}}],
            "filters": [{"field": "pe_ttm", "operator": "between", "value": [5, 40]}],
        }
    )
    meta = build_strategy_metadata_bundle(
        spec, prompt_excerpt="long only quality", display_seed="task-abc-123"
    )
    assert meta["name"] == "roe_rank"
    assert meta["family"] == "quality"
    assert meta["frequency"] == "1d"
    assert meta["params"]["strategy_kind"] == "rule"
    assert meta["riskRules"]["max_portfolio_drawdown"] == 0.2


async def test_mock_llm_structured_output_validates_as_dsl():
    from app.integrations.llm.mock import MockLLMProvider

    provider = MockLLMProvider()
    raw = await provider.generate_structured(
        "ignored",
        strategy_generation_json_schema(),
    )
    spec = parse_strategy_generation_spec(raw)
    assert spec.factors[0].kind == "value"
    assert spec.filters[0].field == "market_cap"


def test_full_spec_roundtrip_dict():
    payload = {
        "schema_version": "1.0",
        "strategy_kind": "rule",
        "factors": [
            FactorSpec(name="roe", kind="quality", params={"min": 0.15}).model_dump(),
            {"name": "pe_rank", "kind": "value", "params": {"max_pct": 30}},
        ],
        "filters": [
            {"field": "market_cap", "operator": "gte", "value": 5e9},
            {"field": "pe_ttm", "operator": "between", "value": [5, 40]},
        ],
        "rebalance_frequency": "1w",
        "position_rules": {
            "target_gross_exposure": 0.95,
            "max_single_name_weight": 0.08,
            "min_positions": 5,
            "max_positions": 40,
        },
        "risk_rules": {
            "max_portfolio_drawdown": 0.18,
            "per_symbol_stop_loss_pct": 0.08,
            "max_sector_weight": 0.35,
        },
    }
    spec = StrategyGenerationSpec.model_validate(payload)
    dumped = spec.model_dump()
    again = StrategyGenerationSpec.model_validate(dumped)
    assert again == spec
