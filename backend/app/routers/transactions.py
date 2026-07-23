from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import Holding, Profile, Transaction, User
from ..schemas import TransactionIn, TransactionOut, TransactionUpdate
from ..importer import make_dedup_hash

router = APIRouter(prefix="/api", tags=["transactions"])


def _owned_holding(holding_id: int, db: Session, user: User) -> Holding:
    holding = db.get(Holding, holding_id)
    if holding is None:
        raise HTTPException(status_code=404, detail="Holding not found")
    profile = db.get(Profile, holding.profile_id)
    if profile is None or profile.user_id != user.id:
        raise HTTPException(status_code=404, detail="Holding not found")
    return holding


def _owned_txn(txn_id: int, db: Session, user: User) -> Transaction:
    txn = db.get(Transaction, txn_id)
    if txn is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    _owned_holding(txn.holding_id, db, user)
    return txn


@router.get("/holdings/{holding_id}/transactions", response_model=list[TransactionOut])
def list_transactions(
    holding_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    _owned_holding(holding_id, db, user)
    return (
        db.query(Transaction)
        .filter(Transaction.holding_id == holding_id)
        .order_by(Transaction.txn_date)
        .all()
    )


@router.post("/holdings/{holding_id}/transactions", response_model=TransactionOut, status_code=201)
def create_transaction(
    holding_id: int,
    payload: TransactionIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    holding = _owned_holding(holding_id, db, user)
    txn = Transaction(
        holding_id=holding.id,
        txn_date=payload.txn_date,
        txn_type=payload.txn_type,
        quantity=payload.quantity,
        price=payload.price,
        amount=payload.amount,
        charges=payload.charges,
        dividend=payload.dividend,
        notes=payload.notes,
        source="manual",
        meta=payload.meta,
    )
    txn.dedup_hash = make_dedup_hash(
        holding.asset_class, holding.name, holding.identifier,
        payload.txn_date, payload.amount, payload.quantity, payload.txn_type,
    )
    db.add(txn)
    db.commit()
    db.refresh(txn)
    return txn


@router.put("/transactions/{txn_id}", response_model=TransactionOut)
def update_transaction(
    txn_id: int,
    payload: TransactionUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    txn = _owned_txn(txn_id, db, user)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(txn, field, value)
    db.commit()
    db.refresh(txn)
    return txn


@router.delete("/transactions/{txn_id}", status_code=204)
def delete_transaction(
    txn_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    txn = _owned_txn(txn_id, db, user)
    db.delete(txn)
    db.commit()
