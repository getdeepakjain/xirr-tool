from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ---------- Auth ----------
class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: EmailStr
    name: str
    avatar_url: str | None = None


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    name: str = ""


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ---------- Profiles ----------
class ProfileIn(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str = ""


class ProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    description: str
    created_at: datetime


# ---------- Holdings ----------
class HoldingIn(BaseModel):
    asset_class: str
    name: str = Field(min_length=1)
    identifier: str = ""
    latest_price: float | None = None
    current_value: float | None = None
    meta: dict = Field(default_factory=dict)


class HoldingUpdate(BaseModel):
    name: str | None = None
    identifier: str | None = None
    latest_price: float | None = None
    current_value: float | None = None
    meta: dict | None = None


class HoldingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    profile_id: int
    asset_class: str
    name: str
    identifier: str
    latest_price: float | None
    current_value: float | None
    meta: dict


# ---------- Transactions ----------
class TransactionIn(BaseModel):
    txn_date: date
    txn_type: str = "buy"
    quantity: float = 0.0
    price: float = 0.0
    amount: float = 0.0
    charges: float = 0.0
    dividend: float = 0.0
    notes: str = ""
    meta: dict = Field(default_factory=dict)


class TransactionUpdate(BaseModel):
    txn_date: date | None = None
    txn_type: str | None = None
    quantity: float | None = None
    price: float | None = None
    amount: float | None = None
    charges: float | None = None
    dividend: float | None = None
    notes: str | None = None
    meta: dict | None = None


class TransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    holding_id: int
    txn_date: date
    txn_type: str
    quantity: float
    price: float
    amount: float
    charges: float
    dividend: float
    notes: str
    source: str
