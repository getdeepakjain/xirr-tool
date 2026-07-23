from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..deps import get_current_user
from ..models import Profile, User
from ..schemas import LoginIn, RegisterIn, Token, UserOut
from ..security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _issue_token(user: User) -> Token:
    token = create_access_token(subject=str(user.id))
    return Token(access_token=token, user=UserOut.model_validate(user))


def _ensure_default_profile(db: Session, user: User) -> None:
    exists = db.query(Profile).filter(Profile.user_id == user.id).first()
    if not exists:
        db.add(Profile(user_id=user.id, name=user.name or "My Portfolio",
                       description="Default profile"))
        db.commit()


@router.post("/register", response_model=Token)
def register(payload: RegisterIn, db: Session = Depends(get_db)) -> Token:
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(
        email=payload.email,
        name=payload.name or payload.email.split("@")[0],
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    _ensure_default_profile(db, user)
    return _issue_token(user)


@router.post("/login", response_model=Token)
def login(payload: LoginIn, db: Session = Depends(get_db)) -> Token:
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not user.hashed_password or not verify_password(
        payload.password, user.hashed_password
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
        )
    return _issue_token(user)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> UserOut:
    return UserOut.model_validate(user)


@router.get("/config")
def auth_config() -> dict:
    return {"google_enabled": settings.google_enabled}


# ---------------- Google OAuth ----------------
def _oauth():
    from authlib.integrations.starlette_client import OAuth

    oauth = OAuth()
    oauth.register(
        name="google",
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )
    return oauth


@router.get("/google/login")
async def google_login(request: Request):
    if not settings.google_enabled:
        raise HTTPException(status_code=400, detail="Google login not configured")
    oauth = _oauth()
    redirect_uri = f"{settings.backend_base_url}/api/auth/google/callback"
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/google/callback")
async def google_callback(request: Request, db: Session = Depends(get_db)):
    if not settings.google_enabled:
        raise HTTPException(status_code=400, detail="Google login not configured")
    oauth = _oauth()
    try:
        token = await oauth.google.authorize_access_token(request)
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=400, detail=f"Google auth failed: {exc}")
    info = token.get("userinfo") or {}
    email = info.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Google account has no email")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(email=email, name=info.get("name", ""), google_sub=info.get("sub"),
                    avatar_url=info.get("picture"))
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        user.google_sub = user.google_sub or info.get("sub")
        user.avatar_url = user.avatar_url or info.get("picture")
        db.commit()
    _ensure_default_profile(db, user)

    jwt_token = create_access_token(subject=str(user.id))
    params = urlencode({"token": jwt_token})
    return RedirectResponse(url=f"{settings.frontend_url}/auth/callback?{params}")
