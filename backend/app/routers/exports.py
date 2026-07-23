"""CSV export endpoints for holdings and transactions."""
import csv
import io
from datetime import date

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_owned_profile
from ..models import Holding, Profile, Transaction
from ..valuation import holding_metrics

router = APIRouter(prefix="/api/profiles", tags=["exports"])


def _csv_response(rows: list[list], header: list[str], filename: str) -> StreamingResponse:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(header)
    writer.writerows(rows)
    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{profile_id}/export/holdings.csv")
def export_holdings(
    profile: Profile = Depends(get_owned_profile), db: Session = Depends(get_db)
):
    as_of = date.today()
    holdings = (
        db.query(Holding)
        .filter(Holding.profile_id == profile.id)
        .order_by(Holding.asset_class, Holding.name)
        .all()
    )
    header = [
        "Asset Class", "Name", "Identifier", "Units", "Latest Price",
        "Invested", "Current Value", "Dividends", "Gain",
        "Absolute Return %", "XIRR %", "Transactions",
    ]
    rows = []
    for h in holdings:
        m = holding_metrics(h, as_of)
        rows.append([
            m["asset_class"], m["name"], m["identifier"], m["units"],
            m["latest_price"], m["invested"], m["current_value"], m["dividends"],
            m["gain"], m["absolute_return_pct"], m["xirr_pct"], m["txn_count"],
        ])
    return _csv_response(rows, header, f"holdings_{profile.id}_{as_of.isoformat()}.csv")


@router.get("/{profile_id}/export/transactions.csv")
def export_transactions(
    profile: Profile = Depends(get_owned_profile), db: Session = Depends(get_db)
):
    as_of = date.today()
    rows_q = (
        db.query(Transaction, Holding)
        .join(Holding, Transaction.holding_id == Holding.id)
        .filter(Holding.profile_id == profile.id)
        .order_by(Holding.asset_class, Holding.name, Transaction.txn_date)
        .all()
    )
    header = [
        "Asset Class", "Holding", "Identifier", "Date", "Type", "Quantity",
        "Price", "Amount", "Charges", "Dividend", "Source", "Notes",
    ]
    rows = []
    for txn, h in rows_q:
        rows.append([
            h.asset_class, h.name, h.identifier, txn.txn_date.isoformat(),
            txn.txn_type, txn.quantity, txn.price, txn.amount, txn.charges,
            txn.dividend, txn.source, txn.notes,
        ])
    return _csv_response(rows, header, f"transactions_{profile.id}_{as_of.isoformat()}.csv")
