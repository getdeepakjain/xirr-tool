from datetime import date

from app.constants import AssetClass, TxnType
from app.models import Holding, Transaction
from app.valuation import (
    current_value,
    dividends_received,
    holding_metrics,
    invested_amount,
)


def _txn(**kw) -> Transaction:
    base = dict(txn_type=TxnType.BUY.value, quantity=0.0, price=0.0,
                amount=0.0, charges=0.0, dividend=0.0)
    base.update(kw)
    return Transaction(**base)


def _mf_holding() -> Holding:
    h = Holding(asset_class=AssetClass.MF.value, name="Test Fund", identifier="",
                latest_price=15.0, current_value=None, meta={})
    h.transactions = [
        _txn(txn_date=date(2020, 1, 1), quantity=100.0, price=10.0, amount=1000.0),
        _txn(txn_date=date(2021, 1, 1), quantity=50.0, price=12.0, amount=600.0),
    ]
    return h


def test_unit_priced_current_value():
    h = _mf_holding()
    # 150 units * 15.0 latest price
    assert current_value(h) == 150 * 15.0
    assert invested_amount(h) == 1600.0


def test_explicit_current_value_for_non_unit_priced():
    h = Holding(asset_class=AssetClass.FD.value, name="FD 1", identifier="1",
                latest_price=None, current_value=2500.0, meta={})
    h.transactions = [_txn(txn_date=date(2020, 1, 1), amount=2000.0)]
    assert current_value(h) == 2500.0


def test_dividends_received():
    h = _mf_holding()
    h.transactions.append(
        _txn(txn_date=date(2021, 6, 1), txn_type=TxnType.DIVIDEND.value, amount=25.0)
    )
    assert dividends_received(h) == 25.0


def test_holding_metrics_shape():
    m = holding_metrics(_mf_holding(), date(2022, 1, 1))
    assert m["asset_class"] == "MF"
    assert m["units"] == 150.0
    assert m["invested"] == 1600.0
    assert m["current_value"] == 2250.0
    assert m["gain"] == 650.0
    assert m["xirr_pct"] is not None
