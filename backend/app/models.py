from datetime import date, datetime, timezone

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from .database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255), default="")
    hashed_password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    google_sub: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    avatar_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    profiles: Mapped[list["Profile"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Profile(Base):
    """A portfolio owner (e.g. self, spouse, child) belonging to a user."""

    __tablename__ = "profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(String(1000), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    user: Mapped["User"] = relationship(back_populates="profiles")
    holdings: Mapped[list["Holding"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )


class Holding(Base):
    """A logical instrument, e.g. a specific MF scheme, stock script or FD account."""

    __tablename__ = "holdings"
    __table_args__ = (
        UniqueConstraint("profile_id", "asset_class", "name", "identifier", name="uq_holding"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    profile_id: Mapped[int] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE"), index=True
    )
    asset_class: Mapped[str] = mapped_column(String(32), index=True)
    name: Mapped[str] = mapped_column(String(512))
    identifier: Mapped[str] = mapped_column(String(255), default="")
    # Latest market price per unit (MF NAV, stock/crypto price). Optional.
    latest_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Explicit current value override (FD/PF/Gratuity/Bonds/Policies where value is not qty*price).
    current_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    meta: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    profile: Mapped["Profile"] = relationship(back_populates="holdings")
    transactions: Mapped[list["Transaction"]] = relationship(
        back_populates="holding", cascade="all, delete-orphan"
    )


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    holding_id: Mapped[int] = mapped_column(
        ForeignKey("holdings.id", ondelete="CASCADE"), index=True
    )
    txn_date: Mapped[date] = mapped_column(Date, index=True)
    txn_type: Mapped[str] = mapped_column(String(16), default="buy")
    quantity: Mapped[float] = mapped_column(Float, default=0.0)
    price: Mapped[float] = mapped_column(Float, default=0.0)      # NAV / unit price at txn
    amount: Mapped[float] = mapped_column(Float, default=0.0)     # net cash invested (incl charges)
    charges: Mapped[float] = mapped_column(Float, default=0.0)
    dividend: Mapped[float] = mapped_column(Float, default=0.0)
    notes: Mapped[str] = mapped_column(String(1000), default="")
    source: Mapped[str] = mapped_column(String(16), default="manual")  # manual | excel
    dedup_hash: Mapped[str] = mapped_column(String(64), index=True, default="")
    meta: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    holding: Mapped["Holding"] = relationship(back_populates="transactions")
