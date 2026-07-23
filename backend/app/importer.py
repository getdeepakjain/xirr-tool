"""Excel workbook importer.

Parses the multi-tab "Upload Format.xlsx" style workbook into normalized
holdings + transactions. On import, only *new* transactions (not already
present for the holding, matched by a content hash) are inserted.
"""
from __future__ import annotations

import hashlib
from datetime import date, datetime
from io import BytesIO
from typing import Any, Callable

import openpyxl
from sqlalchemy.orm import Session

from .constants import AssetClass, TxnType
from .models import Holding, Profile, Transaction

_ERR_VALUES = {"#value!", "#n/a", "#ref!", "#div/0!", "#name?", "#null!", "#num!", ""}


def _norm(v: Any) -> str:
    if v is None:
        return ""
    return " ".join(str(v).replace("\n", " ").split()).strip()


def _clean_name(v: Any) -> str:
    s = _norm(v)
    return "" if s.lower() in _ERR_VALUES else s


def _to_float(v: Any) -> float | None:
    if v is None or v == "":
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace(",", "")
    if s.lower() in _ERR_VALUES:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _to_date(v: Any) -> date | None:
    if v is None or v == "":
        return None
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y", "%d-%b-%Y", "%d-%b-%y"):
        try:
            return datetime.strptime(str(v).strip(), fmt).date()
        except ValueError:
            continue
    return None


def make_dedup_hash(
    asset_class: str, name: str, identifier: str, txn_date: date | None,
    amount: float, quantity: float, txn_type: str,
) -> str:
    key = "|".join([
        asset_class,
        _norm(name).lower(),
        _norm(identifier).lower(),
        txn_date.isoformat() if txn_date else "",
        f"{round(amount or 0.0, 2)}",
        f"{round(quantity or 0.0, 4)}",
        txn_type,
    ])
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


# A parsed row: contributes to a holding and optionally a transaction.
def _rec(asset_class: str, name: str, identifier: str = "", meta: dict | None = None,
         latest_price: float | None = None, cv_add: float | None = None,
         txn: dict | None = None) -> dict:
    return {
        "asset_class": asset_class,
        "name": name,
        "identifier": identifier,
        "meta": meta or {},
        "latest_price": latest_price,
        "cv_add": cv_add,
        "txn": txn,
    }


def _rows(ws, header_row: int):
    data = list(ws.iter_rows(values_only=True))
    return data[header_row + 1:]


def _cell(row: tuple, idx: int):
    return row[idx] if idx < len(row) else None


# ----------------------- per-sheet parsers -----------------------
def parse_stocks(ws) -> list[dict]:
    out = []
    for r in _rows(ws, 1):
        name = _clean_name(_cell(r, 1))
        d = _to_date(_cell(r, 2))
        amount = _to_float(_cell(r, 6))
        if not name or d is None or amount is None:
            continue
        meta = {
            "sector": _norm(_cell(r, 18)),
            "ownership": _norm(_cell(r, 19)),
            "market_cap_category": _norm(_cell(r, 20)),
            "market_cap_cr": _norm(_cell(r, 21)),
            "stop_loss": _norm(_cell(r, 22)),
        }
        out.append(_rec(
            AssetClass.STOCKS.value, name, meta=meta,
            latest_price=_to_float(_cell(r, 8)),
            txn={
                "txn_date": d, "txn_type": TxnType.BUY.value,
                "quantity": _to_float(_cell(r, 3)) or 0.0,
                "price": _to_float(_cell(r, 4)) or 0.0,
                "amount": amount,
                "charges": _to_float(_cell(r, 5)) or 0.0,
                "dividend": _to_float(_cell(r, 11)) or 0.0,
            },
        ))
    return out


def parse_crypto(ws) -> list[dict]:
    out = []
    for r in _rows(ws, 1):
        name = _clean_name(_cell(r, 2))
        d = _to_date(_cell(r, 3))
        amount = _to_float(_cell(r, 7))
        if not name or d is None or amount is None:
            continue
        out.append(_rec(
            AssetClass.CRYPTO.value, name, identifier=_norm(_cell(r, 1)),
            meta={"exchange": _norm(_cell(r, 1))},
            latest_price=_to_float(_cell(r, 9)),
            txn={
                "txn_date": d, "txn_type": TxnType.BUY.value,
                "quantity": _to_float(_cell(r, 4)) or 0.0,
                "price": _to_float(_cell(r, 5)) or 0.0,
                "amount": amount,
                "charges": _to_float(_cell(r, 6)) or 0.0,
                "dividend": _to_float(_cell(r, 11)) or 0.0,
            },
        ))
    return out


def parse_mf(ws) -> list[dict]:
    out = []
    for r in _rows(ws, 0):
        name = _clean_name(_cell(r, 0))
        d = _to_date(_cell(r, 1))
        amount = _to_float(_cell(r, 2))
        if not name or d is None or amount is None:
            continue
        out.append(_rec(
            AssetClass.MF.value, name,
            meta={"fund_type": _norm(_cell(r, 14)), "comments": _norm(_cell(r, 12))},
            latest_price=_to_float(_cell(r, 5)),
            txn={
                "txn_date": d, "txn_type": TxnType.BUY.value,
                "quantity": _to_float(_cell(r, 4)) or 0.0,
                "price": _to_float(_cell(r, 3)) or 0.0,
                "amount": amount,
                "dividend": _to_float(_cell(r, 7)) or 0.0,
            },
        ))
    return out


def _parse_nps(ws, tier: str) -> list[dict]:
    out = []
    for r in _rows(ws, 0):
        name = _clean_name(_cell(r, 0))
        d = _to_date(_cell(r, 1))
        amount = _to_float(_cell(r, 4))
        if not name or d is None or amount is None:
            continue
        out.append(_rec(
            AssetClass.NPS.value, name, identifier=tier, meta={"tier": tier},
            latest_price=_to_float(_cell(r, 7)),
            txn={
                "txn_date": d, "txn_type": TxnType.BUY.value,
                "quantity": _to_float(_cell(r, 6)) or 0.0,
                "price": _to_float(_cell(r, 5)) or 0.0,
                "amount": amount,
                "charges": _to_float(_cell(r, 3)) or 0.0,
                "dividend": _to_float(_cell(r, 9)) or 0.0,
            },
        ))
    return out


def parse_nps_tier1(ws):
    return _parse_nps(ws, "Tier I")


def parse_nps_tier2(ws):
    return _parse_nps(ws, "Tier II")


def parse_fd(ws) -> list[dict]:
    out = []
    for r in _rows(ws, 0):
        acno = _norm(_cell(r, 0))
        principal = _to_float(_cell(r, 1))
        d = _to_date(_cell(r, 7))
        if not acno or principal is None or d is None:
            continue
        meta = {
            "account_no": acno,
            "maturity_date": (_to_date(_cell(r, 8)).isoformat() if _to_date(_cell(r, 8)) else ""),
            "maturity_amount": _to_float(_cell(r, 3)),
            "final_maturity_amount": _to_float(_cell(r, 6)),
            "interest": _to_float(_cell(r, 4)),
            "tds": _to_float(_cell(r, 5)),
            "interest_rate": _to_float(_cell(r, 9)),
        }
        out.append(_rec(
            AssetClass.FD.value, f"FD {acno}", identifier=acno, meta=meta,
            cv_add=_to_float(_cell(r, 2)),  # current accrued value
            txn={"txn_date": d, "txn_type": TxnType.BUY.value, "amount": principal},
        ))
    return out


def parse_pf(ws) -> list[dict]:
    out = []
    for r in _rows(ws, 1):
        d = _to_date(_cell(r, 0))
        total = _to_float(_cell(r, 4))
        company = _norm(_cell(r, 23)) or "PF"
        if d is None or total is None or total == 0:
            continue
        out.append(_rec(
            AssetClass.PF.value, f"PF - {company}", identifier=company,
            meta={"company": company, "interest_rate": _to_float(_cell(r, 5))},
            cv_add=_to_float(_cell(r, 19)),  # total latest value for the month
            txn={"txn_date": d, "txn_type": TxnType.BUY.value, "amount": total,
                 "notes": f"Emp {_to_float(_cell(r, 1))}, Employer {_to_float(_cell(r, 2))}, "
                          f"Pension {_to_float(_cell(r, 3))}"},
        ))
    return out


def parse_gratuity(ws) -> list[dict]:
    out = []
    for r in _rows(ws, 0):
        d = _to_date(_cell(r, 0))
        amount = _to_float(_cell(r, 1))
        company = _norm(_cell(r, 8)) or "Gratuity"
        if d is None or amount is None:
            continue
        out.append(_rec(
            AssetClass.GRATUITY.value, f"Gratuity - {company}", identifier=company,
            meta={"company": company, "interest_rate": _to_float(_cell(r, 2))},
            cv_add=_to_float(_cell(r, 4)),
            txn={"txn_date": d, "txn_type": TxnType.BUY.value, "amount": amount},
        ))
    return out


def parse_bonds(ws) -> list[dict]:
    out = []
    for r in _rows(ws, 0):
        name = _clean_name(_cell(r, 0))
        d = _to_date(_cell(r, 1))
        amount = _to_float(_cell(r, 2))
        if not name or d is None or amount is None or amount == 0:
            continue
        out.append(_rec(
            AssetClass.BONDS.value, name,
            cv_add=_to_float(_cell(r, 5)),
            meta={"interest_realized": _to_float(_cell(r, 6))},
            txn={"txn_date": d, "txn_type": TxnType.BUY.value, "amount": amount},
        ))
    return out


def parse_policies(ws) -> list[dict]:
    out = []
    # Block 3 (summary) gives policy number + remaining corpus per scheme.
    summary: dict[str, dict] = {}
    for r in _rows(ws, 0):
        sname = _clean_name(_cell(r, 12))
        if sname and sname.lower() != "total":
            summary[sname] = {
                "policy_number": _norm(_cell(r, 13)),
                "remaining": _to_float(_cell(r, 18)),
            }
    for r in _rows(ws, 0):
        # Premium payments (block 1)
        name = _clean_name(_cell(r, 0))
        d = _to_date(_cell(r, 1))
        amount = _to_float(_cell(r, 2))
        if name and d is not None and amount is not None:
            info = summary.get(name, {})
            out.append(_rec(
                AssetClass.POLICIES.value, name, identifier=info.get("policy_number", ""),
                meta={"policy_number": info.get("policy_number", ""),
                      "remaining": info.get("remaining")},
                txn={"txn_date": d, "txn_type": TxnType.BUY.value, "amount": amount},
            ))
        # Cashbacks / survival benefits (block 2)
        cname = _clean_name(_cell(r, 6))
        cd = _to_date(_cell(r, 7))
        camount = _to_float(_cell(r, 8))
        if cname and cd is not None and camount:
            out.append(_rec(
                AssetClass.POLICIES.value, cname,
                txn={"txn_date": cd, "txn_type": TxnType.CASHBACK.value, "amount": camount},
            ))
    return out


SHEET_PARSERS: dict[str, Callable] = {
    "Stocks": parse_stocks,
    "Crypto": parse_crypto,
    "MF": parse_mf,
    "NPS - Tier I": parse_nps_tier1,
    "NPS - Tier II": parse_nps_tier2,
    "FD": parse_fd,
    "PF": parse_pf,
    "Gratuity": parse_gratuity,
    "Bonds": parse_bonds,
    "Policies": parse_policies,
}


def parse_workbook(content: bytes) -> list[dict]:
    wb = openpyxl.load_workbook(BytesIO(content), read_only=True, data_only=True)
    records: list[dict] = []
    for sheet_name, parser in SHEET_PARSERS.items():
        if sheet_name in wb.sheetnames:
            try:
                records.extend(parser(wb[sheet_name]))
            except Exception as exc:  # keep importing other sheets
                records.append({"_error": f"{sheet_name}: {exc}"})
    wb.close()
    return records


def import_workbook(db: Session, profile: Profile, content: bytes) -> dict:
    records = parse_workbook(content)
    errors = [r["_error"] for r in records if "_error" in r]
    records = [r for r in records if "_error" not in r]

    # Cache existing holdings for this profile.
    holdings: dict[tuple, Holding] = {}
    for h in db.query(Holding).filter(Holding.profile_id == profile.id).all():
        holdings[(h.asset_class, h.name.lower(), h.identifier.lower())] = h

    cv_sums: dict[int, float] = {}          # holding id (or temp key) -> summed current value
    cv_tracks: dict[tuple, float] = {}      # holding key -> summed cv (pre-id)
    latest_prices: dict[tuple, float] = {}

    summary: dict[str, dict] = {}

    def bump(ac: str, field: str, by: int = 1):
        s = summary.setdefault(ac, {"parsed": 0, "new_transactions": 0,
                                    "duplicates": 0, "holdings_created": 0})
        s[field] += by

    # First pass: ensure holdings exist and aggregate holding-level values.
    for rec in records:
        ac = rec["asset_class"]
        key = (ac, rec["name"].lower(), rec["identifier"].lower())
        bump(ac, "parsed")
        holding = holdings.get(key)
        if holding is None:
            holding = Holding(
                profile_id=profile.id, asset_class=ac, name=rec["name"],
                identifier=rec["identifier"], meta=dict(rec["meta"]),
            )
            db.add(holding)
            db.flush()
            holdings[key] = holding
            bump(ac, "holdings_created")
        else:
            if rec["meta"]:
                merged = dict(holding.meta or {})
                merged.update({k: v for k, v in rec["meta"].items() if v not in (None, "")})
                holding.meta = merged
        if rec["latest_price"] is not None:
            latest_prices[key] = rec["latest_price"]
        if rec["cv_add"] is not None:
            cv_tracks[key] = cv_tracks.get(key, 0.0) + rec["cv_add"]

    # Apply holding-level valuations (file is source of truth).
    for key, price in latest_prices.items():
        holdings[key].latest_price = price
    for key, cv in cv_tracks.items():
        holdings[key].current_value = round(cv, 2)

    # Second pass: insert only new transactions (dedup by content hash).
    for rec in records:
        txn = rec["txn"]
        if not txn:
            continue
        ac = rec["asset_class"]
        key = (ac, rec["name"].lower(), rec["identifier"].lower())
        holding = holdings[key]
        h = make_dedup_hash(ac, rec["name"], rec["identifier"], txn.get("txn_date"),
                            txn.get("amount", 0.0), txn.get("quantity", 0.0),
                            txn.get("txn_type", TxnType.BUY.value))
        exists = (
            db.query(Transaction)
            .filter(Transaction.holding_id == holding.id, Transaction.dedup_hash == h)
            .first()
        )
        if exists:
            bump(ac, "duplicates")
            continue
        db.add(Transaction(
            holding_id=holding.id,
            txn_date=txn["txn_date"],
            txn_type=txn.get("txn_type", TxnType.BUY.value),
            quantity=txn.get("quantity", 0.0) or 0.0,
            price=txn.get("price", 0.0) or 0.0,
            amount=txn.get("amount", 0.0) or 0.0,
            charges=txn.get("charges", 0.0) or 0.0,
            dividend=txn.get("dividend", 0.0) or 0.0,
            notes=txn.get("notes", ""),
            source="excel",
            dedup_hash=h,
        ))
        bump(ac, "new_transactions")

    db.commit()

    totals = {
        "parsed": sum(s["parsed"] for s in summary.values()),
        "new_transactions": sum(s["new_transactions"] for s in summary.values()),
        "duplicates": sum(s["duplicates"] for s in summary.values()),
        "holdings_created": sum(s["holdings_created"] for s in summary.values()),
    }
    return {"totals": totals, "by_asset_class": summary, "errors": errors}
