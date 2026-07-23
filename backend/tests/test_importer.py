from datetime import date
from io import BytesIO

import openpyxl

from app.importer import make_dedup_hash, parse_workbook


def _sample_workbook() -> bytes:
    wb = openpyxl.Workbook()
    mf = wb.active
    mf.title = "MF"
    # Columns: name(0) date(1) amount(2) nav(3) units(4) latest(5) _(6) div(7)
    mf.append(["Scheme Name", "Date", "Amount", "NAV", "Units", "Latest", "x", "Dividend"])
    mf.append(["My Equity Fund", date(2020, 1, 1), 1000, 10.0, 100.0, 12.0, "", 0])
    mf.append(["My Equity Fund", date(2020, 6, 1), 600, 12.0, 50.0, 12.0, "", 0])

    fd = wb.create_sheet("FD")
    # acno(0) principal(1) accrued(2) matAmt(3) interest(4) tds(5) finalMat(6) start(7) mat(8) rate(9)
    fd.append(["A/c", "Principal", "Accrued", "MatAmt", "Interest", "TDS",
               "FinalMat", "Start", "Maturity", "Rate"])
    fd.append(["FD001", 2000, 2500, 2600, 400, 0, 2600,
               date(2020, 1, 1), date(2025, 1, 1), 7.0])

    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_parse_workbook_mf_and_fd():
    records = parse_workbook(_sample_workbook())
    assert not any("_error" in r for r in records)

    mf = [r for r in records if r["asset_class"] == "MF"]
    assert len(mf) == 2
    assert mf[0]["name"] == "My Equity Fund"
    assert mf[0]["latest_price"] == 12.0
    assert mf[0]["txn"]["amount"] == 1000

    fd = [r for r in records if r["asset_class"] == "FD"]
    assert len(fd) == 1
    assert fd[0]["identifier"] == "FD001"
    assert fd[0]["cv_add"] == 2500


def test_dedup_hash_is_stable_and_distinct():
    a = make_dedup_hash("MF", "Fund X", "", date(2020, 1, 1), 1000.0, 100.0, "buy")
    b = make_dedup_hash("MF", "Fund X", "", date(2020, 1, 1), 1000.0, 100.0, "buy")
    c = make_dedup_hash("MF", "Fund X", "", date(2020, 1, 2), 1000.0, 100.0, "buy")
    assert a == b
    assert a != c
