"""XIRR (money-weighted annualised return) computation.

Uses the `pyxirr` library when available (fast, robust) and falls back to a
pure-Python Newton/bisection solver otherwise.
"""
from __future__ import annotations

from datetime import date

try:  # pragma: no cover - preferred fast path
    from pyxirr import xirr as _pyxirr

    def _compute(dates: list[date], amounts: list[float]) -> float | None:
        try:
            result = _pyxirr(dates, amounts)
        except Exception:
            return None
        if result is None:
            return None
        return float(result)

except Exception:  # pragma: no cover - fallback path

    def _xnpv(rate: float, dates: list[date], amounts: list[float]) -> float:
        d0 = dates[0]
        return sum(
            amt / (1.0 + rate) ** ((d - d0).days / 365.0)
            for d, amt in zip(dates, amounts)
        )

    def _compute(dates: list[date], amounts: list[float]) -> float | None:
        # Bisection over a wide range; robust even when Newton diverges.
        low, high = -0.9999, 100.0
        f_low = _xnpv(low, dates, amounts)
        f_high = _xnpv(high, dates, amounts)
        if f_low * f_high > 0:
            return None
        for _ in range(200):
            mid = (low + high) / 2.0
            f_mid = _xnpv(mid, dates, amounts)
            if abs(f_mid) < 1e-7:
                return mid
            if f_low * f_mid < 0:
                high, f_high = mid, f_mid
            else:
                low, f_low = mid, f_mid
        return (low + high) / 2.0


def xirr(cashflows: list[tuple[date, float]]) -> float | None:
    """Return annualised XIRR as a decimal (0.12 == 12%), or None if undefined.

    `cashflows` is a list of (date, amount) pairs. Negative = money out
    (investment), positive = money in (redemption / current value).
    """
    flows = [(d, float(a)) for d, a in cashflows if a is not None and abs(a) > 1e-12]
    if len(flows) < 2:
        return None
    flows.sort(key=lambda x: x[0])
    has_pos = any(a > 0 for _, a in flows)
    has_neg = any(a < 0 for _, a in flows)
    if not (has_pos and has_neg):
        return None
    dates = [d for d, _ in flows]
    amounts = [a for _, a in flows]
    return _compute(dates, amounts)
