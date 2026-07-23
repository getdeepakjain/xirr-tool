from datetime import date

from app.xirr import xirr


def test_simple_annual_double():
    # Invest 100, get back 110 exactly one year later -> ~10%.
    rate = xirr([(date(2020, 1, 1), -100.0), (date(2021, 1, 1), 110.0)])
    assert rate is not None
    assert abs(rate - 0.10) < 1e-3


def test_multiple_contributions():
    flows = [
        (date(2020, 1, 1), -1000.0),
        (date(2020, 7, 1), -1000.0),
        (date(2021, 1, 1), 2200.0),
    ]
    rate = xirr(flows)
    assert rate is not None
    assert rate > 0


def test_returns_none_without_sign_change():
    assert xirr([(date(2020, 1, 1), -100.0), (date(2021, 1, 1), -50.0)]) is None


def test_returns_none_with_single_flow():
    assert xirr([(date(2020, 1, 1), -100.0)]) is None
