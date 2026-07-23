from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_owned_profile
from ..insights import build_insights
from ..models import Holding, Profile
from ..valuation import aggregate, holding_metrics, portfolio_cashflows
from ..xirr import xirr

router = APIRouter(prefix="/api/profiles", tags=["analytics"])


def _compute(db: Session, profile: Profile) -> dict:
    as_of = date.today()
    holdings = (
        db.query(Holding)
        .filter(Holding.profile_id == profile.id)
        .order_by(Holding.asset_class, Holding.name)
        .all()
    )
    metrics = [holding_metrics(h, as_of) for h in holdings]

    by_class: dict[str, dict] = {}
    holdings_by_class: dict[str, list[Holding]] = {}
    for h, m in zip(holdings, metrics):
        by_class.setdefault(m["asset_class"], [])
        by_class[m["asset_class"]].append(m)
        holdings_by_class.setdefault(h.asset_class, []).append(h)

    class_summary: dict[str, dict] = {}
    for ac, ms in by_class.items():
        agg = aggregate(ms)
        rate = xirr(portfolio_cashflows(holdings_by_class[ac], as_of))
        agg["xirr_pct"] = round(rate * 100, 2) if rate is not None else None
        class_summary[ac] = agg

    portfolio = aggregate(metrics)
    p_rate = xirr(portfolio_cashflows(holdings, as_of))
    portfolio["xirr_pct"] = round(p_rate * 100, 2) if p_rate is not None else None

    return {
        "as_of": as_of.isoformat(),
        "portfolio": portfolio,
        "by_asset_class": class_summary,
        "holdings": metrics,
    }


@router.get("/{profile_id}/analytics")
def analytics(profile: Profile = Depends(get_owned_profile), db: Session = Depends(get_db)):
    return _compute(db, profile)


@router.get("/{profile_id}/insights")
def insights(profile: Profile = Depends(get_owned_profile), db: Session = Depends(get_db)):
    data = _compute(db, profile)
    return {
        "as_of": data["as_of"],
        "insights": build_insights(data["holdings"], data["portfolio"], data["by_asset_class"]),
    }
