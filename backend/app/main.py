from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from .config import settings
from .constants import ASSET_CLASSES
from .database import init_db
from .routers import analytics, auth, holdings, profiles, transactions, uploads

app = FastAPI(title="Portfolio XIRR Tracker", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Needed for Authlib's Google OAuth state (stored in the session cookie).
app.add_middleware(SessionMiddleware, secret_key=settings.secret_key)


@app.on_event("startup")
def _startup() -> None:
    init_db()


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "asset_classes": ASSET_CLASSES, "google_enabled": settings.google_enabled}


app.include_router(auth.router)
app.include_router(profiles.router)
app.include_router(holdings.router)
app.include_router(transactions.router)
app.include_router(uploads.router)
app.include_router(analytics.router)
