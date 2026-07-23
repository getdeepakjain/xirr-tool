"""Market data endpoints: refresh latest prices for unit-priced holdings."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_owned_profile
from ..models import Holding, Profile
from ..prices import REFRESHABLE, refresh_prices

router = APIRouter(prefix="/api/profiles", tags=["market"])


@router.post("/{profile_id}/refresh-prices")
def refresh(profile: Profile = Depends(get_owned_profile), db: Session = Depends(get_db)):
    holdings = (
        db.query(Holding)
        .filter(Holding.profile_id == profile.id, Holding.asset_class.in_(REFRESHABLE))
        .all()
    )
    results = refresh_prices(holdings)
    db.commit()

    counts = {"updated": 0, "unchanged": 0, "not_found": 0, "error": 0}
    for r in results:
        counts[r.status] = counts.get(r.status, 0) + 1
    return {
        "counts": counts,
        "results": [
            {
                "holding_id": r.holding_id,
                "name": r.name,
                "asset_class": r.asset_class,
                "old_price": r.old_price,
                "new_price": r.new_price,
                "status": r.status,
                "detail": r.detail,
            }
            for r in results
        ],
    }
