"""Valuation & aggregation of holdings into invested / current value / XIRR."""
from __future__ import annotations

from datetime import date
from typing import Iterable

from .constants import UNIT_PRICED, TxnType
from .models import Holding
from .xirr import xirr


def _net_units(holding: Holding) -> float:
    units = 0.0
    for t in holding.transactions:
        if t.txn_type == TxnType.BUY.value:
            units += t.quantity
        elif t.txn_type == TxnType.SELL.value:
            units -= t.quantity
    return units


def current_value(holding: Holding) -> float:
    """Best-effort current market value of a holding."""
    if holding.asset_class in UNIT_PRICED and holding.latest_price is not None:
        return _net_units(holding) * holding.latest_price
    if holding.current_value is not None:
        return holding.current_value
    # Fall back to net invested if no market data is available yet.
    return invested_amount(holding)


def invested_amount(holding: Holding) -> float:
    """Net amount still invested (buys - sells)."""
    total = 0.0
    for t in holding.transactions:
        if t.txn_type == TxnType.BUY.value:
            total += t.amount
        elif t.txn_type == TxnType.SELL.value:
            total -= t.amount
    return total


def total_invested(holding: Holding) -> float:
    """Gross amount ever invested (buys only)."""
    return sum(t.amount for t in holding.transactions if t.txn_type == TxnType.BUY.value)


def dividends_received(holding: Holding) -> float:
    return sum(
        (t.dividend or 0.0)
        + (t.amount if t.txn_type in (TxnType.DIVIDEND.value, TxnType.CASHBACK.value) else 0.0)
        for t in holding.transactions
    )


def holding_cashflows(holding: Holding, as_of: date) -> list[tuple[date, float]]:
    flows: list[tuple[date, float]] = []
    for t in holding.transactions:
        if t.txn_type == TxnType.BUY.value:
            flows.append((t.txn_date, -t.amount))
        elif t.txn_type == TxnType.SELL.value:
            flows.append((t.txn_date, t.amount))
        elif t.txn_type in (TxnType.DIVIDEND.value, TxnType.CASHBACK.value):
            amt = t.amount if t.amount else t.dividend
            flows.append((t.txn_date, amt))
        if t.dividend and t.txn_type == TxnType.BUY.value:
            flows.append((t.txn_date, t.dividend))
    cv = current_value(holding)
    flows.append((as_of, cv))
    return flows


def holding_metrics(holding: Holding, as_of: date) -> dict:
    invested = invested_amount(holding)
    cv = current_value(holding)
    gain = cv - invested
    rate = xirr(holding_cashflows(holding, as_of))
    pct = (gain / invested) if invested > 1e-9 else None
    return {
        "holding_id": holding.id,
        "name": holding.name,
        "identifier": holding.identifier,
        "asset_class": holding.asset_class,
        "units": _net_units(holding),
        "latest_price": holding.latest_price,
        "invested": round(invested, 2),
        "current_value": round(cv, 2),
        "dividends": round(dividends_received(holding), 2),
        "gain": round(gain, 2),
        "absolute_return_pct": round(pct * 100, 2) if pct is not None else None,
        "xirr_pct": round(rate * 100, 2) if rate is not None else None,
        "txn_count": len(holding.transactions),
        "meta": holding.meta or {},
    }


def aggregate(metrics: Iterable[dict]) -> dict:
    metrics = list(metrics)
    invested = sum(m["invested"] for m in metrics)
    cv = sum(m["current_value"] for m in metrics)
    gain = cv - invested
    pct = (gain / invested) if invested > 1e-9 else None
    return {
        "invested": round(invested, 2),
        "current_value": round(cv, 2),
        "gain": round(gain, 2),
        "absolute_return_pct": round(pct * 100, 2) if pct is not None else None,
        "count": len(metrics),
    }


def portfolio_cashflows(holdings: list[Holding], as_of: date) -> list[tuple[date, float]]:
    flows: list[tuple[date, float]] = []
    for h in holdings:
        for t in h.transactions:
            if t.txn_type == TxnType.BUY.value:
                flows.append((t.txn_date, -t.amount))
            elif t.txn_type == TxnType.SELL.value:
                flows.append((t.txn_date, t.amount))
            elif t.txn_type in (TxnType.DIVIDEND.value, TxnType.CASHBACK.value):
                flows.append((t.txn_date, t.amount if t.amount else t.dividend))
        flows.append((as_of, current_value(h)))
    return flows
