"""Tests for strategy generation semantic + AST validation (Phase 2 task 3)."""

import pytest

from app.domains.strategy.generation_dsl import parse_strategy_generation_spec
from app.domains.strategy.generation_validate import (
    validate_generated_strategy_ast,
    validate_spec_semantics,
)


def _minimal_rule_spec_dict() -> dict:
    return {
        "strategy_kind": "rule",
        "factors": [{"name": "mom20", "kind": "momentum", "params": {"window": 20}}],
        "position_rules": {
            "target_gross_exposure": 1.0,
            "max_single_name_weight": 0.1,
            "min_positions": 1,
            "max_positions": 30,
        },
        "risk_rules": {"max_portfolio_drawdown": 0.18},
    }


def test_validate_spec_semantics_accepts_balanced_default():
    spec = parse_strategy_generation_spec(_minimal_rule_spec_dict())
    validate_spec_semantics(spec, risk_profile="balanced", market="A")


def test_validate_spec_rejects_weight_over_cap_for_conservative():
    raw = _minimal_rule_spec_dict()
    raw["position_rules"]["max_single_name_weight"] = 0.2
    spec = parse_strategy_generation_spec(raw)
    with pytest.raises(ValueError, match="max_single_name_weight"):
        validate_spec_semantics(spec, risk_profile="conservative", market="A")


def test_validate_spec_rejects_drawdown_over_cap():
    raw = _minimal_rule_spec_dict()
    raw["risk_rules"]["max_portfolio_drawdown"] = 0.25
    spec = parse_strategy_generation_spec(raw)
    with pytest.raises(ValueError, match="max_portfolio_drawdown"):
        validate_spec_semantics(spec, risk_profile="balanced", market="A")


def test_validate_spec_rejects_bad_factor_window():
    raw = _minimal_rule_spec_dict()
    raw["factors"][0]["params"]["window"] = 400
    spec = parse_strategy_generation_spec(raw)
    with pytest.raises(ValueError, match="window"):
        validate_spec_semantics(spec, risk_profile="balanced", market="A")


def test_validate_spec_rejects_invalid_market():
    spec = parse_strategy_generation_spec(_minimal_rule_spec_dict())
    with pytest.raises(ValueError, match="market"):
        validate_spec_semantics(spec, risk_profile="balanced", market="Mars")


def test_validate_ast_accepts_rule_based_mock_shape():
    code = """
class GeneratedValueStrategy(RuleBasedStrategy):
    def generate_signals(self, data):
        return data

    def risk_check(self, signals, portfolio):
        return signals
"""
    validate_generated_strategy_ast(code)


def test_validate_ast_accepts_base_strategy_shape():
    code = """
class Foo(BaseStrategy):
    def generate_signals(self, context, bars, state):
        return ()

    def rebalance(self, context, signals, state):
        from app.domains.strategy.runtime import RebalancePlan
        return RebalancePlan(trade_date=context.trade_date, targets=())
"""
    validate_generated_strategy_ast(code)


def test_validate_ast_rejects_missing_interface():
    code = """
class Bad(RuleBasedStrategy):
    def generate_signals(self, data):
        return data
"""
    with pytest.raises(ValueError, match="no class found"):
        validate_generated_strategy_ast(code)


def test_validate_ast_rejects_syntax():
    with pytest.raises(ValueError, match="invalid Python"):
        validate_generated_strategy_ast("def x(")


def test_validate_spec_rejects_future_like_filter_field():
    raw = {
        "strategy_kind": "rule",
        "factors": [{"name": "x", "kind": "value", "params": {}}],
        "filters": [{"field": "next_close", "operator": "gt", "value": 0}],
    }
    spec = parse_strategy_generation_spec(raw)
    with pytest.raises(ValueError, match="filter field"):
        validate_spec_semantics(spec, risk_profile="balanced", market="A")


def test_validate_ast_rejects_negative_shift():
    code = """
class X(RuleBasedStrategy):
    def generate_signals(self, data):
        return data["close"].shift(-1)

    def risk_check(self, signals, portfolio):
        return signals
"""
    with pytest.raises(ValueError, match="shift"):
        validate_generated_strategy_ast(code)


def test_validate_ast_rejects_negative_pct_change():
    code = """
class X(RuleBasedStrategy):
    def generate_signals(self, data):
        return data["close"].pct_change(-1)

    def risk_check(self, signals, portfolio):
        return signals
"""
    with pytest.raises(ValueError, match="pct_change"):
        validate_generated_strategy_ast(code)


def test_validate_ast_accepts_positive_shift():
    code = """
class GeneratedValueStrategy(RuleBasedStrategy):
    def generate_signals(self, data):
        return data["close"].shift(1)

    def risk_check(self, signals, portfolio):
        return signals
"""
    validate_generated_strategy_ast(code)
