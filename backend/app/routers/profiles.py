from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user, get_owned_profile
from ..models import Profile, User
from ..schemas import ProfileIn, ProfileOut

router = APIRouter(prefix="/api/profiles", tags=["profiles"])


@router.get("", response_model=list[ProfileOut])
def list_profiles(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return (
        db.query(Profile)
        .filter(Profile.user_id == user.id)
        .order_by(Profile.created_at)
        .all()
    )


@router.post("", response_model=ProfileOut, status_code=201)
def create_profile(
    payload: ProfileIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    profile = Profile(user_id=user.id, name=payload.name, description=payload.description)
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


@router.put("/{profile_id}", response_model=ProfileOut)
def update_profile(payload: ProfileIn, profile: Profile = Depends(get_owned_profile),
                   db: Session = Depends(get_db)):
    profile.name = payload.name
    profile.description = payload.description
    db.commit()
    db.refresh(profile)
    return profile


@router.delete("/{profile_id}", status_code=204)
def delete_profile(profile: Profile = Depends(get_owned_profile), db: Session = Depends(get_db)):
    db.delete(profile)
    db.commit()
