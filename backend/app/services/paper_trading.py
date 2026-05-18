"""End-of-day paper trading engine.

For each active PaperAccount we run, on a given ``trade_date``:
    1. **mark**     — refresh PaperPosition.last_price / market_value with the
                      day's close, snapshot pre-rebalance equity for risk checks.
    2. **signal**   — replay the built-in strategy (``dual_ma`` proxy mapped from
                      the strategy version's DSL) on persisted bars, emit target
                      weights, write PaperOrder rows in ``pending`` state.
    3. **pre-check**— PreTradeCheckService rejects orders that breach single-name
                      cap / cash floor / daily-loss / max-drawdown rules; rejected
                      orders move to ``rejected`` and may raise a PaperRiskBreach.
    4. **match**    — fill remaining orders at the close price with the same cost
                      model the backtest uses (``BacktestCostConfig`` slippage,
                      commission, stamp tax). Updates cash + position state.
    5. **nav**      — write the daily PaperNavPoint (NAV / cash / market_value /
                      daily_return / drawdown) and bump ``last_processed_date``.

The same engine instance powers the manual `/paper/run-eod` endpoint and the
Celery beat schedule.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, replace
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.data.models import MarketBarDaily
from app.domains.execution.paper_models import (
    PaperAccount,
    PaperFill,
    PaperNavPoint,
    PaperOrder,
    PaperPosition,
    PaperPreTradeCheck,
    PaperRiskBreach,
)
from app.domains.strategy.examples import create_builtin_strategy
from app.domains.strategy.models import StrategyVersion
from app.domains.strategy.runtime import (
    Position as RuntimePosition,
    StrategyBar,
    StrategyContext,
    StrategyRunner,
)
from app.services.daily_backtest import BacktestCostConfig
from app.services.strategy_generation_research import spec_to_dual_ma_params
from app.domains.strategy.generation_dsl import parse_strategy_generation_spec

logger = logging.getLogger(__name__)


# ── runtime dataclasses ─────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class EodSummary:
    """Per-account result of one end-of-day cycle."""

    account_id: str
    trade_date: str
    orders_created: int
    orders_filled: int
    orders_rejected: int
    breaches: int
    nav: float | None


@dataclass(frozen=True, slots=True)
class TargetDriftRow:
    symbol: str
    target_weight: float
    current_weight: float
    drift_weight: float
    target_quantity: float
    current_quantity: float
    recommended_action: str
    reason: str | None


@dataclass(frozen=True, slots=True)
class EvaluationSnapshot:
    trade_date: str | None
    session_status: str
    strategy_bound: bool
    target_gross: float
    current_gross: float
    drift_gross: float
    targets: tuple[TargetDriftRow, ...]


# ── engine ──────────────────────────────────────────────────────────────


class PaperTradingEngine:
    """Orchestrates the EOD cycle for paper trading accounts."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def run_end_of_day(
        self, account_id: str, trade_date: str
    ) -> EodSummary:
        account = await self.session.get(PaperAccount, account_id)
        if account is None:
            raise ValueError(f"PaperAccount {account_id} not found")
        if account.status != "active":
            return EodSummary(account_id=account_id, trade_date=trade_date, orders_created=0, orders_filled=0, orders_rejected=0, breaches=0, nav=None)

        # Idempotency: if this date has already been processed, skip silently.
        if account.last_processed_date and account.last_processed_date >= trade_date:
            return EodSummary(account_id=account_id, trade_date=trade_date, orders_created=0, orders_filled=0, orders_rejected=0, breaches=0, nav=None)

        cost_config = _cost_config_from_account(account)
        bars_today = await self._bars_for_date(trade_date)
        if not bars_today:
            return EodSummary(account_id=account_id, trade_date=trade_date, orders_created=0, orders_filled=0, orders_rejected=0, breaches=0, nav=None)

        positions = await self._load_positions(account.id)
        await self._mark_to_market(account, positions, bars_today)
        pre_rebalance_nav = _equity(account, positions)

        targets = await self._compute_targets(account, trade_date, bars_today)
        orders = await self._create_orders(account, trade_date, targets, positions, bars_today)

        checks_blocked = await self._run_pre_trade_checks(account, orders, positions, bars_today, pre_rebalance_nav)

        filled, rejected_runtime = await self._execute_orders(
            account=account,
            orders=orders,
            positions=positions,
            bars_today=bars_today,
            cost_config=cost_config,
            already_rejected_ids=checks_blocked,
        )
        rejected = len(checks_blocked) + rejected_runtime

        await self._mark_to_market(account, positions, bars_today)
        nav = await self._write_nav(account, trade_date, positions)
        breaches = await self._post_trade_breach_check(account, trade_date, nav, pre_rebalance_nav)

        account.last_processed_date = trade_date
        await self.session.commit()

        return EodSummary(
            account_id=account.id,
            trade_date=trade_date,
            orders_created=len(orders),
            orders_filled=filled,
            orders_rejected=rejected,
            breaches=breaches,
            nav=nav,
        )

    async def submit_manual_order(
        self,
        account_id: str,
        *,
        symbol: str,
        side: str,
        quantity: float,
        trade_date: str | None = None,
        reason: str | None = None,
        execution_mode: str = "immediate",
    ) -> PaperOrder:
        """Submit a manual order, optionally queueing it before later matching.

        Matching remains intentionally conservative: it uses the latest persisted
        daily bar as the execution reference until intraday market data is wired in.
        """
        account = await self.session.get(PaperAccount, account_id)
        if account is None:
            raise ValueError(f"PaperAccount {account_id} not found")
        if account.status != "active":
            raise ValueError("paper account is not active")
        side = side.lower()
        if side not in {"buy", "sell"}:
            raise ValueError("side must be buy or sell")
        if quantity <= 0:
            raise ValueError("quantity must be positive")
        execution_mode = execution_mode.lower()
        if execution_mode not in {"immediate", "queue"}:
            raise ValueError("execution_mode must be immediate or queue")

        bar = await self._latest_bar(symbol, trade_date)
        if bar is None:
            raise ValueError(f"no market bar found for {symbol}")
        actual_trade_date = trade_date or bar.trade_date
        if account.market.upper() in {"A", "ASHARE"}:
            quantity = _normalize_ashare_quantity(quantity, side)
            if quantity <= 0:
                raise ValueError("A-share buy orders must be at least 100 shares")

        positions = await self._load_positions(account.id)
        await self._mark_to_market(account, positions, {symbol: bar})
        order = PaperOrder(
            account_id=account.id,
            strategy_id=account.strategy_id,
            trade_date=actual_trade_date,
            symbol=symbol,
            side=side,
            target_weight=0.0,
            target_quantity=quantity,
            status="pending",
            reason=reason or "manual_order",
        )
        self.session.add(order)
        await self.session.flush()

        if execution_mode == "queue":
            await self.session.commit()
            await self.session.refresh(order)
            return order

        pre_rebalance_nav = _equity(account, positions)
        blocked = await self._run_pre_trade_checks(
            account, [order], positions, {symbol: bar}, pre_rebalance_nav
        )
        await self._execute_orders(
            account=account,
            orders=[order],
            positions=positions,
            bars_today={symbol: bar},
            cost_config=_cost_config_from_account(account),
            already_rejected_ids=blocked,
        )
        await self._mark_to_market(account, positions, {symbol: bar})
        await self._write_nav(account, actual_trade_date, positions)
        await self.session.commit()
        await self.session.refresh(order)
        return order

    async def cancel_order(self, account_id: str, order_id: str) -> PaperOrder:
        order = await self._require_order(account_id, order_id)
        if order.status not in {"pending", "approved"}:
            raise ValueError("only pending orders can be cancelled")
        order.status = "canceled"
        await self.session.commit()
        await self.session.refresh(order)
        return order

    async def replace_order(
        self, account_id: str, order_id: str, *, quantity: float
    ) -> PaperOrder:
        order = await self._require_order(account_id, order_id)
        if order.status not in {"pending", "approved"}:
            raise ValueError("only pending orders can be replaced")
        if quantity <= 0:
            raise ValueError("quantity must be positive")
        account = await self.session.get(PaperAccount, account_id)
        assert account is not None  # guaranteed by _require_order path
        if account.market.upper() in {"A", "ASHARE"}:
            quantity = _normalize_ashare_quantity(quantity, order.side)
            if quantity <= 0:
                raise ValueError("A-share buy orders must be at least 100 shares")
        order.target_quantity = quantity
        order.rejection_reason = None
        await self.session.commit()
        await self.session.refresh(order)
        return order

    async def match_pending_orders(
        self, account_id: str, trade_date: str | None = None
    ) -> tuple[int, int]:
        account = await self.session.get(PaperAccount, account_id)
        if account is None:
            raise ValueError(f"PaperAccount {account_id} not found")
        orders = (
            await self.session.execute(
                select(PaperOrder).where(
                    PaperOrder.account_id == account_id,
                    PaperOrder.status.in_(("pending", "approved")),
                )
            )
        ).scalars().all()
        if not orders:
            return 0, 0

        bars_today: dict[str, MarketBarDaily] = {}
        for symbol in sorted({order.symbol for order in orders}):
            bar = await self._latest_bar(symbol, trade_date)
            if bar is None:
                for order in orders:
                    if order.symbol == symbol:
                        order.status = "rejected"
                        order.rejection_reason = f"no market bar found for {symbol}"
                continue
            bars_today[symbol] = bar
        executable = [order for order in orders if order.symbol in bars_today]
        if not executable:
            await self.session.commit()
            return 0, len(orders)

        actual_trade_date = trade_date or max(bar.trade_date for bar in bars_today.values())
        for order in executable:
            order.trade_date = actual_trade_date
        positions = await self._load_positions(account.id)
        await self._mark_to_market(account, positions, bars_today)
        pre_rebalance_nav = _equity(account, positions)
        blocked = await self._run_pre_trade_checks(
            account, executable, positions, bars_today, pre_rebalance_nav
        )
        filled, rejected_runtime = await self._execute_orders(
            account=account,
            orders=executable,
            positions=positions,
            bars_today=bars_today,
            cost_config=_cost_config_from_account(account),
            already_rejected_ids=blocked,
        )
        await self._mark_to_market(account, positions, bars_today)
        await self._write_nav(account, actual_trade_date, positions)
        await self.session.commit()
        rejected_missing_bar = len(orders) - len(executable)
        return filled, len(blocked) + rejected_runtime + rejected_missing_bar

    async def evaluation_snapshot(self, account_id: str) -> EvaluationSnapshot:
        account = await self.session.get(PaperAccount, account_id)
        if account is None:
            raise ValueError(f"PaperAccount {account_id} not found")
        latest_date = await self._latest_market_trade_date()
        if not account.strategy_version_id:
            positions = await self._load_positions(account.id)
            if latest_date is not None and positions:
                bars_today = await self._bars_for_date(latest_date)
                await self._mark_to_market(account, positions, bars_today)
            current_gross = sum(abs(pos.weight) for pos in positions.values())
            return EvaluationSnapshot(
                trade_date=latest_date,
                session_status=_ashare_session_status(),
                strategy_bound=False,
                target_gross=0.0,
                current_gross=current_gross,
                drift_gross=0.0,
                targets=(),
            )
        if latest_date is None:
            return EvaluationSnapshot(
                trade_date=None,
                session_status=_ashare_session_status(),
                strategy_bound=True,
                target_gross=0.0,
                current_gross=0.0,
                drift_gross=0.0,
                targets=(),
            )
        bars_today = await self._bars_for_date(latest_date)
        positions = await self._load_positions(account.id)
        await self._mark_to_market(account, positions, bars_today)
        targets = await self._compute_targets(account, latest_date, bars_today)
        equity = _equity(account, positions)
        rows: list[TargetDriftRow] = []
        all_symbols = sorted(set(targets) | set(positions))
        for symbol in all_symbols:
            target_weight, reason = targets.get(symbol, (0.0, None))
            current = positions.get(symbol)
            current_weight = current.weight if current else 0.0
            mark = bars_today.get(symbol)
            px = (mark.adjusted_close or mark.close) if mark else (current.last_price if current else None)
            target_quantity = (target_weight * equity / px) if px and px > 0 else 0.0
            if account.market.upper() in {"A", "ASHARE"}:
                target_quantity = _normalize_ashare_quantity(target_quantity, "buy")
            current_quantity = current.quantity if current else 0.0
            drift = target_weight - current_weight
            rows.append(
                TargetDriftRow(
                    symbol=symbol,
                    target_weight=target_weight,
                    current_weight=current_weight,
                    drift_weight=drift,
                    target_quantity=target_quantity,
                    current_quantity=current_quantity,
                    recommended_action=_recommended_action(current_weight, target_weight),
                    reason=reason,
                )
            )
        target_gross = sum(abs(row.target_weight) for row in rows)
        current_gross = sum(abs(row.current_weight) for row in rows)
        drift_gross = sum(abs(row.drift_weight) for row in rows)
        return EvaluationSnapshot(
            trade_date=latest_date,
            session_status=_ashare_session_status(),
            strategy_bound=True,
            target_gross=target_gross,
            current_gross=current_gross,
            drift_gross=drift_gross,
            targets=tuple(rows),
        )

    # ── internals ────────────────────────────────────────────────────────

    async def _bars_for_date(self, trade_date: str) -> dict[str, MarketBarDaily]:
        rows = (
            await self.session.execute(
                select(MarketBarDaily).where(MarketBarDaily.trade_date == trade_date)
            )
        ).scalars().all()
        return {b.symbol: b for b in rows}

    async def _latest_market_trade_date(self) -> str | None:
        return (
            await self.session.execute(
                select(MarketBarDaily.trade_date)
                .order_by(MarketBarDaily.trade_date.desc())
                .limit(1)
            )
        ).scalar_one_or_none()

    async def _latest_bar(
        self, symbol: str, trade_date: str | None = None
    ) -> MarketBarDaily | None:
        stmt = select(MarketBarDaily).where(MarketBarDaily.symbol == symbol)
        if trade_date:
            stmt = stmt.where(MarketBarDaily.trade_date == trade_date)
        else:
            stmt = stmt.order_by(MarketBarDaily.trade_date.desc()).limit(1)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def _require_order(self, account_id: str, order_id: str) -> PaperOrder:
        order = await self.session.get(PaperOrder, order_id)
        if order is None or order.account_id != account_id:
            raise ValueError("paper order not found")
        return order

    async def _bars_history(
        self, symbols: tuple[str, ...], up_to: str, limit_per_symbol: int = 200
    ) -> list[MarketBarDaily]:
        if not symbols:
            return []
        rows = (
            await self.session.execute(
                select(MarketBarDaily)
                .where(
                    MarketBarDaily.symbol.in_(symbols),
                    MarketBarDaily.trade_date <= up_to,
                )
                .order_by(MarketBarDaily.symbol, MarketBarDaily.trade_date.asc())
            )
        ).scalars().all()
        # Cap each symbol's history (engineering safety on huge universes).
        grouped: dict[str, list[MarketBarDaily]] = {}
        for r in rows:
            grouped.setdefault(r.symbol, []).append(r)
        out: list[MarketBarDaily] = []
        for s, hist in grouped.items():
            out.extend(hist[-limit_per_symbol:])
        out.sort(key=lambda b: (b.trade_date, b.symbol))
        return out

    async def _load_positions(self, account_id: str) -> dict[str, PaperPosition]:
        rows = (
            await self.session.execute(
                select(PaperPosition).where(PaperPosition.account_id == account_id)
            )
        ).scalars().all()
        return {p.symbol: p for p in rows}

    async def _mark_to_market(
        self,
        account: PaperAccount,
        positions: dict[str, PaperPosition],
        bars_today: dict[str, MarketBarDaily],
    ) -> None:
        total_mv = 0.0
        for symbol, pos in positions.items():
            bar = bars_today.get(symbol)
            if bar is not None:
                price = bar.adjusted_close or bar.close
                pos.last_price = price
                pos.market_value = pos.quantity * price
            total_mv += pos.market_value or 0.0
        equity = account.cash + total_mv
        for pos in positions.values():
            pos.weight = (pos.market_value / equity) if equity > 0 else 0.0
        await self.session.flush()

    async def _compute_targets(
        self,
        account: PaperAccount,
        trade_date: str,
        bars_today: dict[str, MarketBarDaily],
    ) -> dict[str, tuple[float, str]]:
        """Return ``{symbol: (target_weight, reason)}`` for the given trade date."""
        universe, params = await self._resolve_strategy_params(account)
        if not universe:
            # Unbound paper accounts should stay cheap to inspect. Falling back to
            # the entire market makes evaluation_snapshot() fetch every symbol's
            # full history and can effectively freeze the local SQLite dev server.
            fallback_size = max(1, int(params.get("max_positions", 20)))
            universe = tuple(sorted(bars_today.keys())[:fallback_size])
        if not universe:
            return {}

        strategy = create_builtin_strategy("dual_ma", dict(params))
        runner = StrategyRunner(strategy)

        history_bars = await self._bars_history(universe, up_to=trade_date)
        history_until_yesterday = [b for b in history_bars if b.trade_date < trade_date]

        positions = await self._load_positions(account.id)
        portfolio_value = account.cash + sum((p.market_value or 0.0) for p in positions.values())
        ctx = StrategyContext(
            trade_date=trade_date,
            universe=universe,
            portfolio_value=portfolio_value,
            cash=account.cash,
            positions={
                s: RuntimePosition(
                    symbol=s,
                    quantity=p.quantity,
                    market_value=p.market_value,
                    weight=p.weight,
                    available_quantity=p.quantity,
                )
                for s, p in positions.items()
                if p.quantity > 0
            },
            params=params,
        )
        result = runner.run_daily(
            ctx, [_bar_to_runtime(b) for b in history_until_yesterday]
        )
        out: dict[str, tuple[float, str]] = {}
        for target in result.rebalance.targets:
            out[target.symbol] = (target.weight, target.reason)
        return out

    async def _resolve_strategy_params(
        self, account: PaperAccount
    ) -> tuple[tuple[str, ...], dict[str, Any]]:
        """Look up the strategy version's DSL spec and project it to dual_ma params."""
        params: dict[str, Any] = {"short_window": 5, "long_window": 20, "target_gross": 0.95, "max_positions": 20}
        universe: tuple[str, ...] = ()

        if not account.strategy_version_id:
            return universe, params

        version = await self.session.get(StrategyVersion, account.strategy_version_id)
        if version is None or not version.params_schema:
            return universe, params

        try:
            spec_payload = json.loads(version.params_schema)
            spec = parse_strategy_generation_spec(spec_payload)
            dual = spec_to_dual_ma_params(spec)
            params.update(dual)
        except Exception:  # noqa: BLE001
            logger.exception("paper: failed to parse strategy spec, using defaults")
        return universe, params

    async def _create_orders(
        self,
        account: PaperAccount,
        trade_date: str,
        targets: dict[str, tuple[float, str]],
        positions: dict[str, PaperPosition],
        bars_today: dict[str, MarketBarDaily],
    ) -> list[PaperOrder]:
        """Compute order side + target_quantity from target weights vs current positions."""
        equity = _equity(account, positions)
        orders: list[PaperOrder] = []
        # First close-or-resize known holdings; then open new positions.
        all_symbols = sorted(set(targets) | set(positions))
        for symbol in all_symbols:
            target_weight, reason = targets.get(symbol, (0.0, ""))
            bar = bars_today.get(symbol)
            if bar is None:
                continue
            mark = bar.adjusted_close or bar.close
            target_qty = (target_weight * equity / mark) if mark > 0 else 0.0
            if account.market.upper() in {"A", "ASHARE"}:
                target_qty = _normalize_ashare_quantity(target_qty, "buy")
            current_qty = positions[symbol].quantity if symbol in positions else 0.0
            delta = target_qty - current_qty
            if abs(delta * mark) < 1e-3:
                continue
            side = "buy" if delta > 0 else "sell"
            if side == "buy" and not bar.can_buy:
                continue
            if side == "sell" and not bar.can_sell:
                continue
            order = PaperOrder(
                account_id=account.id,
                strategy_id=account.strategy_id,
                trade_date=trade_date,
                symbol=symbol,
                side=side,
                target_weight=target_weight,
                target_quantity=abs(delta),
                status="pending",
                reason=reason,
            )
            self.session.add(order)
            orders.append(order)
        if orders:
            await self.session.flush()
        return orders

    async def _run_pre_trade_checks(
        self,
        account: PaperAccount,
        orders: list[PaperOrder],
        positions: dict[str, PaperPosition],
        bars_today: dict[str, MarketBarDaily],
        pre_rebalance_nav: float,
    ) -> set[str]:
        """Reject any order that fails a hard rule. Returns the rejected order IDs."""
        single_name_cap = 0.10  # 10% of equity
        rejected: set[str] = set()
        for order in orders:
            bar = bars_today[order.symbol]
            mark = bar.adjusted_close or bar.close
            order_notional = order.target_quantity * mark
            if order.side == "buy":
                current_mv = positions.get(order.symbol)
                current_value = current_mv.market_value if current_mv else 0.0
                new_value = current_value + order_notional
                position_pct = new_value / pre_rebalance_nav if pre_rebalance_nav > 0 else 0.0
                status = "fail" if position_pct > single_name_cap else "pass"
                self.session.add(
                    PaperPreTradeCheck(
                        order_id=order.id,
                        account_id=account.id,
                        rule="single_name_cap",
                        current_value=position_pct,
                        limit_value=single_name_cap,
                        status=status,
                        note=f"target {position_pct:.2%} vs cap {single_name_cap:.0%}",
                    )
                )
                if status == "fail":
                    order.status = "rejected"
                    order.rejection_reason = (
                        f"single_name_cap exceeded ({position_pct:.2%} > {single_name_cap:.0%})"
                    )
                    rejected.add(order.id)
                    continue

                # Cash floor: keep at least 1% cash
                cash_needed = order_notional * 1.005  # +50bps headroom for cost
                if account.cash - cash_needed < pre_rebalance_nav * 0.01:
                    self.session.add(
                        PaperPreTradeCheck(
                            order_id=order.id,
                            account_id=account.id,
                            rule="cash_floor",
                            current_value=account.cash,
                            limit_value=pre_rebalance_nav * 0.01,
                            status="fail",
                            note="not enough cash for buy",
                        )
                    )
                    order.status = "rejected"
                    order.rejection_reason = "insufficient cash after reserve"
                    rejected.add(order.id)
        await self.session.flush()
        return rejected

    async def _execute_orders(
        self,
        *,
        account: PaperAccount,
        orders: list[PaperOrder],
        positions: dict[str, PaperPosition],
        bars_today: dict[str, MarketBarDaily],
        cost_config: BacktestCostConfig,
        already_rejected_ids: set[str],
    ) -> tuple[int, int]:
        filled = 0
        rejected_runtime = 0
        # Process sells first to free cash, then buys.
        ordered = sorted(orders, key=lambda o: (0 if o.side == "sell" else 1, o.symbol))
        for order in ordered:
            if order.id in already_rejected_ids:
                continue
            bar = bars_today[order.symbol]
            mark = bar.adjusted_close or bar.close
            if mark <= 0:
                order.status = "rejected"
                order.rejection_reason = "invalid mark price"
                rejected_runtime += 1
                continue
            exec_price = _execution_price(mark, order.side, cost_config)
            qty = order.target_quantity

            if order.side == "buy":
                gross_amount = qty * exec_price
                commission = max(gross_amount * cost_config.commission_rate, cost_config.min_commission if gross_amount > 0 else 0.0)
                # Re-cap quantity to what cash allows after costs.
                affordable_qty = _affordable_buy_qty(account.cash, exec_price, cost_config)
                if account.market.upper() in {"A", "ASHARE"}:
                    affordable_qty = _normalize_ashare_quantity(affordable_qty, "buy")
                qty = min(qty, affordable_qty)
                if qty <= 0:
                    order.status = "rejected"
                    order.rejection_reason = "insufficient cash"
                    rejected_runtime += 1
                    continue
                amount = qty * exec_price
                commission = max(amount * cost_config.commission_rate, cost_config.min_commission)
                stamp_tax = 0.0  # Buy side: no stamp tax in A-share
                slippage = qty * (exec_price - mark)
                total_cost = commission + stamp_tax + slippage
                net_cash_flow = -(amount + commission + stamp_tax)
                account.cash += net_cash_flow
                pos = positions.get(order.symbol)
                if pos is None:
                    pos = PaperPosition(
                        account_id=account.id,
                        symbol=order.symbol,
                        quantity=0.0,
                        avg_cost=0.0,
                        last_price=mark,
                        market_value=0.0,
                    )
                    self.session.add(pos)
                    positions[order.symbol] = pos
                new_qty = pos.quantity + qty
                pos.avg_cost = (pos.avg_cost * pos.quantity + amount) / new_qty if new_qty > 0 else exec_price
                pos.quantity = new_qty
                pos.last_price = mark
                pos.market_value = pos.quantity * mark
                self.session.add(
                    PaperFill(
                        order_id=order.id,
                        account_id=account.id,
                        trade_date=order.trade_date,
                        symbol=order.symbol,
                        side="buy",
                        quantity=qty,
                        price=exec_price,
                        amount=amount,
                        commission=commission,
                        stamp_tax=stamp_tax,
                        slippage=slippage,
                        total_cost=total_cost,
                        net_cash_flow=net_cash_flow,
                    )
                )
                order.filled_quantity = qty
                order.status = "filled" if abs(qty - order.target_quantity) < 1e-6 else "partial"
                filled += 1
            else:  # sell
                pos = positions.get(order.symbol)
                if pos is None or pos.quantity <= 0:
                    order.status = "rejected"
                    order.rejection_reason = "no position to sell"
                    rejected_runtime += 1
                    continue
                available_qty = await self._available_sell_quantity(
                    account.id, order.symbol, order.trade_date, pos.quantity
                )
                qty = min(qty, available_qty)
                if qty <= 0:
                    order.status = "rejected"
                    order.rejection_reason = "T+1 unavailable quantity"
                    rejected_runtime += 1
                    continue
                amount = qty * exec_price
                commission = max(amount * cost_config.commission_rate, cost_config.min_commission)
                stamp_tax = amount * cost_config.stamp_tax_rate
                slippage = qty * (mark - exec_price)
                total_cost = commission + stamp_tax + slippage
                net_cash_flow = amount - commission - stamp_tax
                account.cash += net_cash_flow
                pos.quantity -= qty
                if pos.quantity <= 1e-9:
                    pos.quantity = 0.0
                    pos.avg_cost = 0.0
                pos.last_price = mark
                pos.market_value = pos.quantity * mark
                self.session.add(
                    PaperFill(
                        order_id=order.id,
                        account_id=account.id,
                        trade_date=order.trade_date,
                        symbol=order.symbol,
                        side="sell",
                        quantity=qty,
                        price=exec_price,
                        amount=amount,
                        commission=commission,
                        stamp_tax=stamp_tax,
                        slippage=slippage,
                        total_cost=total_cost,
                        net_cash_flow=net_cash_flow,
                    )
                )
                order.filled_quantity = qty
                order.status = "filled" if abs(qty - order.target_quantity) < 1e-6 else "partial"
                filled += 1
        await self.session.flush()
        return filled, rejected_runtime

    async def available_position_quantities(
        self, account_id: str
    ) -> dict[str, tuple[float, float]]:
        positions = await self._load_positions(account_id)
        current_trade_date = await self._latest_account_trade_date(account_id)
        out: dict[str, tuple[float, float]] = {}
        for symbol, pos in positions.items():
            today_buys = await self._today_buy_quantity(
                account_id, symbol, current_trade_date
            ) if current_trade_date else 0.0
            out[symbol] = (max(0.0, pos.quantity - today_buys), today_buys)
        return out

    async def _latest_account_trade_date(
        self, account_id: str
    ) -> str | None:
        row = (
            await self.session.execute(
                select(PaperFill.trade_date)
                .where(PaperFill.account_id == account_id)
                .order_by(PaperFill.trade_date.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        return row

    async def _today_buy_quantity(
        self, account_id: str, symbol: str, trade_date: str
    ) -> float:
        rows = (
            await self.session.execute(
                select(PaperFill).where(
                    PaperFill.account_id == account_id,
                    PaperFill.symbol == symbol,
                    PaperFill.trade_date == trade_date,
                    PaperFill.side == "buy",
                )
            )
        ).scalars().all()
        return sum(fill.quantity for fill in rows)

    async def _available_sell_quantity(
        self, account_id: str, symbol: str, trade_date: str, current_quantity: float
    ) -> float:
        today_buys = await self._today_buy_quantity(account_id, symbol, trade_date)
        return max(0.0, current_quantity - today_buys)

    async def _write_nav(
        self,
        account: PaperAccount,
        trade_date: str,
        positions: dict[str, PaperPosition],
    ) -> float:
        market_value = sum((p.market_value or 0.0) for p in positions.values())
        nav = account.cash + market_value
        prev = (
            await self.session.execute(
                select(PaperNavPoint)
                .where(
                    PaperNavPoint.account_id == account.id,
                    PaperNavPoint.trade_date < trade_date,
                )
                .order_by(PaperNavPoint.trade_date.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        daily_return = None
        if prev and prev.nav > 0:
            daily_return = nav / prev.nav - 1
        peak = max(account.peak_nav or 0.0, nav)
        account.peak_nav = peak
        drawdown = (nav / peak - 1) if peak > 0 else 0.0
        same_day = (
            await self.session.execute(
                select(PaperNavPoint).where(
                    PaperNavPoint.account_id == account.id,
                    PaperNavPoint.trade_date == trade_date,
                )
            )
        ).scalar_one_or_none()
        if same_day is None:
            self.session.add(
                PaperNavPoint(
                    account_id=account.id,
                    trade_date=trade_date,
                    nav=nav,
                    cash=account.cash,
                    market_value=market_value,
                    daily_return=daily_return,
                    drawdown=drawdown,
                )
            )
        else:
            same_day.nav = nav
            same_day.cash = account.cash
            same_day.market_value = market_value
            same_day.daily_return = daily_return
            same_day.drawdown = drawdown
        await self.session.flush()
        return nav

    async def _post_trade_breach_check(
        self,
        account: PaperAccount,
        trade_date: str,
        nav: float,
        pre_rebalance_nav: float,
    ) -> int:
        breaches = 0
        # 1) Daily loss > 5%
        if pre_rebalance_nav > 0:
            daily_change = nav / pre_rebalance_nav - 1
            if daily_change < -0.05:
                self.session.add(
                    PaperRiskBreach(
                        account_id=account.id,
                        trade_date=trade_date,
                        rule="daily_loss",
                        severity="high",
                        detail=f"NAV change {daily_change:.2%} below -5%",
                        status="ongoing",
                    )
                )
                breaches += 1

        # 2) Drawdown > 15%
        peak = account.peak_nav or 0.0
        if peak > 0:
            dd = nav / peak - 1
            if dd < -0.15:
                self.session.add(
                    PaperRiskBreach(
                        account_id=account.id,
                        trade_date=trade_date,
                        rule="max_drawdown",
                        severity="critical",
                        detail=f"drawdown {dd:.2%} below -15%",
                        status="ongoing",
                    )
                )
                breaches += 1
        await self.session.flush()
        return breaches


# ── helpers ─────────────────────────────────────────────────────────────


def _bar_to_runtime(b: MarketBarDaily) -> StrategyBar:
    return StrategyBar(
        symbol=b.symbol,
        trade_date=b.trade_date,
        open=b.open,
        high=b.high,
        low=b.low,
        close=b.close,
        volume=b.volume,
        amount=b.amount,
        adjusted_close=b.adjusted_close,
        can_buy=b.can_buy,
        can_sell=b.can_sell,
        is_suspended=b.is_suspended,
        is_limit_up=b.is_limit_up,
        is_limit_down=b.is_limit_down,
    )


def _cost_config_from_account(account: PaperAccount) -> BacktestCostConfig:
    if account.cost_config_json:
        try:
            data = json.loads(account.cost_config_json)
            return BacktestCostConfig(
                commission_rate=float(data.get("commission_rate", 0.0003)),
                min_commission=float(data.get("min_commission", 5.0)),
                stamp_tax_rate=float(data.get("stamp_tax_rate", 0.001)),
                slippage_bps=float(data.get("slippage_bps", 1.0)),
            )
        except Exception:  # noqa: BLE001
            pass
    return BacktestCostConfig()


def _execution_price(mark: float, side: str, cost_config: BacktestCostConfig) -> float:
    slip = cost_config.slippage_rate
    if side == "buy":
        return mark * (1.0 + slip)
    return mark * (1.0 - slip)


def _affordable_buy_qty(cash: float, price: float, cost_config: BacktestCostConfig) -> float:
    if price <= 0 or cash <= 0:
        return 0.0
    denom = price * (1.0 + cost_config.commission_rate)
    qty = (cash - cost_config.min_commission) / denom
    return max(qty, 0.0)


def _normalize_ashare_quantity(quantity: float, side: str) -> float:
    if side == "buy":
        return float(int(quantity // 100) * 100)
    return float(int(quantity))


def _equity(account: PaperAccount, positions: dict[str, PaperPosition]) -> float:
    return account.cash + sum((p.market_value or 0.0) for p in positions.values())


def _recommended_action(current_weight: float, target_weight: float) -> str:
    if current_weight <= 1e-9 and target_weight > 1e-9:
        return "open"
    if current_weight > 1e-9 and target_weight <= 1e-9:
        return "close"
    if target_weight > current_weight + 1e-6:
        return "increase"
    if target_weight < current_weight - 1e-6:
        return "decrease"
    return "hold"


def _ashare_session_status(now: datetime | None = None) -> str:
    current = now or datetime.now()
    hhmm = current.hour * 100 + current.minute
    if 915 <= hhmm < 925:
        return "call_auction"
    if 930 <= hhmm < 1130 or 1300 <= hhmm < 1457:
        return "continuous"
    if 1457 <= hhmm < 1500:
        return "closing_auction"
    if 1130 <= hhmm < 1300:
        return "lunch_break"
    return "closed"
