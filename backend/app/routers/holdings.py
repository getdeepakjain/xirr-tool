from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..constants import ASSET_CLASSES
from ..database import get_db
from ..deps import get_current_user, get_owned_profile
from ..models import Holding, Profile, User
from ..schemas import HoldingIn, HoldingOut, HoldingUpdate

router = APIRouter(prefix="/api", tags=["holdings"])


def _get_owned_holding(holding_id: int, db: Session, user: User) -> Holding:
    holding = db.get(Holding, holding_id)
    if holding is None:
        raise HTTPException(status_code=404, detail="Holding not found")
    profile = db.get(Profile, holding.profile_id)
    if profile is None or profile.user_id != user.id:
        raise HTTPException(status_code=404, detail="Holding not found")
    return holding


@router.get("/profiles/{profile_id}/holdings", response_model=list[HoldingOut])
def list_holdings(
    asset_class: str | None = None,
    profile: Profile = Depends(get_owned_profile),
    db: Session = Depends(get_db),
):
    q = db.query(Holding).filter(Holding.profile_id == profile.id)
    if asset_class:
        q = q.filter(Holding.asset_class == asset_class)
    return q.order_by(Holding.asset_class, Holding.name).all()


@router.post("/profiles/{profile_id}/holdings", response_model=HoldingOut, status_code=201)
def create_holding(
    payload: HoldingIn,
    profile: Profile = Depends(get_owned_profile),
    db: Session = Depends(get_db),
):
    if payload.asset_class not in ASSET_CLASSES:
        raise HTTPException(status_code=422, detail=f"Invalid asset_class. Allowed: {ASSET_CLASSES}")
    existing = (
        db.query(Holding)
        .filter(
            Holding.profile_id == profile.id,
            Holding.asset_class == payload.asset_class,
            Holding.name == payload.name,
            Holding.identifier == payload.identifier,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="Holding already exists")
    holding = Holding(
        profile_id=profile.id,
        asset_class=payload.asset_class,
        name=payload.name,
        identifier=payload.identifier,
        latest_price=payload.latest_price,
        current_value=payload.current_value,
        meta=payload.meta,
    )
    db.add(holding)
    db.commit()
    db.refresh(holding)
    return holding


@router.put("/holdings/{holding_id}", response_model=HoldingOut)
def update_holding(
    holding_id: int,
    payload: HoldingUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    holding = _get_owned_holding(holding_id, db, user)
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(holding, field, value)
    db.commit()
    db.refresh(holding)
    return holding


@router.delete("/holdings/{holding_id}", status_code=204)
def delete_holding(
    holding_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    holding = _get_owned_holding(holding_id, db, user)
    db.delete(holding)
    db.commit()
