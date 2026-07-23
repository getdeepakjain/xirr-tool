"""Rule-based portfolio insights: highlight winners, laggards and risks."""
from __future__ import annotations

from .constants import AssetClass

# Rough long-term benchmark annualised returns (%) per asset class.
BENCHMARK_XIRR = {
    AssetClass.MF.value: 12.0,
    AssetClass.STOCKS.value: 14.0,
    AssetClass.CRYPTO.value: 20.0,
    AssetClass.NPS.value: 9.0,
    AssetClass.PF.value: 8.0,
    AssetClass.FD.value: 6.5,
    AssetClass.BONDS.value: 7.5,
    AssetClass.GRATUITY.value: 8.0,
    AssetClass.POLICIES.value: 6.0,
}

INFLATION = 6.0  # % — real returns should beat this.


def _sev(level: str) -> int:
    return {"positive": 0, "info": 1, "warning": 2, "critical": 3}.get(level, 1)


def build_insights(metrics: list[dict], portfolio: dict, by_class: dict) -> list[dict]:
    insights: list[dict] = []

    def add(level, title, detail, holding=None):
        insights.append({
            "level": level, "title": title, "detail": detail,
            "holding": holding,
        })

    priced = [m for m in metrics if m["xirr_pct"] is not None]

    # Best / worst performers.
    if priced:
        best = max(priced, key=lambda m: m["xirr_pct"])
        worst = min(priced, key=lambda m: m["xirr_pct"])
        add("positive", f"Top performer: {best['name']}",
            f"{best['asset_class']} delivering {best['xirr_pct']}% XIRR "
            f"(gain ₹{best['gain']:,.0f}). Consider maintaining or adding.",
            best["name"])
        if worst["xirr_pct"] < INFLATION:
            add("warning", f"Laggard: {worst['name']}",
                f"{worst['asset_class']} XIRR of {worst['xirr_pct']}% is below inflation "
                f"(~{INFLATION}%). Review whether to exit or rebalance.",
                worst["name"])

    # Per-holding checks.
    for m in metrics:
        bench = BENCHMARK_XIRR.get(m["asset_class"])
        if m["xirr_pct"] is not None and bench is not None:
            if m["xirr_pct"] < 0:
                add("critical", f"Losing money: {m['name']}",
                    f"Negative XIRR ({m['xirr_pct']}%). Currently down ₹{-m['gain']:,.0f}.",
                    m["name"])
            elif m["xirr_pct"] < bench - 3:
                add("warning", f"Underperforming its class: {m['name']}",
                    f"{m['xirr_pct']}% XIRR vs ~{bench}% typical for {m['asset_class']}. "
                    f"Look for better options in the same category.",
                    m["name"])
        # Stop-loss breach for stocks.
        if m["asset_class"] == AssetClass.STOCKS.value:
            sl = (m.get("meta") or {}).get("stop_loss")
            if sl and m.get("latest_price") is not None:
                try:
                    if float(str(sl).replace(",", "")) > float(m["latest_price"]):
                        add("critical", f"Stop-loss breached: {m['name']}",
                            f"Latest price {m['latest_price']} is below stop-loss {sl}.",
                            m["name"])
                except ValueError:
                    pass

    # Concentration risk.
    total_cv = portfolio.get("current_value") or 0.0
    if total_cv > 0:
        for m in metrics:
            share = m["current_value"] / total_cv
            if share > 0.25 and m["current_value"] > 0:
                add("warning", f"Concentration risk: {m['name']}",
                    f"This single holding is {share*100:.0f}% of your portfolio. "
                    f"Consider diversifying.",
                    m["name"])

    # Asset-class diversification.
    active_classes = [c for c, a in by_class.items() if a["current_value"] > 0]
    if 0 < len(active_classes) < 3:
        add("info", "Low diversification across asset classes",
            f"You are invested in {len(active_classes)} asset class(es). "
            f"Spreading across MF, equity, debt and gold-like assets reduces risk.")

    # Overall portfolio health.
    p_xirr = portfolio.get("xirr_pct")
    if p_xirr is not None:
        if p_xirr >= 12:
            add("positive", "Healthy overall return",
                f"Portfolio XIRR of {p_xirr}% is comfortably beating inflation.")
        elif p_xirr < INFLATION:
            add("warning", "Portfolio barely beating inflation",
                f"Overall XIRR {p_xirr}% is close to / below inflation (~{INFLATION}%). "
                f"Consider shifting some debt allocation to growth assets.")

    insights.sort(key=lambda i: _sev(i["level"]), reverse=True)
    return insights
