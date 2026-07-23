from app.constants import AssetClass
from app.models import Holding
from app.prices import (
    match_mf_nav,
    normalize_mf_name,
    parse_amfi_navall,
    parse_stock_symbol,
    refresh_prices,
)

SAMPLE_NAVALL = """Scheme Code;ISIN Div Payout/ ISIN Growth;ISIN Div Reinvestment;Scheme Name;Net Asset Value;Date
119551;INF209K01UN8;INF209K01UO6;Axis Bluechip Fund - Direct Plan - Growth;62.5400;23-Jul-2026
120503;INF109K012B0;-;ICICI Prudential Value Discovery Fund - Growth;385.1200;23-Jul-2026
invalid line without enough columns
"""


def test_parse_amfi_navall():
    navs = parse_amfi_navall(SAMPLE_NAVALL)
    assert len(navs) == 2
    assert navs[normalize_mf_name("Axis Bluechip Fund - Direct Plan - Growth")] == 62.54


def test_match_mf_nav_fuzzy():
    navs = parse_amfi_navall(SAMPLE_NAVALL)
    # A slightly different phrasing should still match Axis Bluechip.
    assert match_mf_nav("Axis Bluechip Direct Growth", navs) == 62.54
    assert match_mf_nav("Totally Unknown Fund XYZ", navs) is None


def test_parse_stock_symbol():
    assert parse_stock_symbol("APOLLO HOSPITALS ENTERPRISE LIMITED (XNSE:APOLLOHOSP)") == "APOLLOHOSP.NS"
    assert parse_stock_symbol("Some Co (XBOM:500001)") == "500001.BO"
    assert parse_stock_symbol("No marker here") is None


class _FakeService:
    """Stands in for PriceService; returns canned prices, no network."""

    def __init__(self, mapping):
        self._mapping = mapping

    def price_for(self, holding):
        return self._mapping.get(holding.id)


def test_refresh_prices_updates_and_reports():
    holdings = [
        Holding(id=1, asset_class=AssetClass.MF.value, name="A", identifier="", latest_price=10.0),
        Holding(id=2, asset_class=AssetClass.STOCKS.value, name="B", identifier="", latest_price=None),
        Holding(id=3, asset_class=AssetClass.CRYPTO.value, name="C", identifier="", latest_price=5.0),
        Holding(id=4, asset_class=AssetClass.FD.value, name="D", identifier="", latest_price=None),
    ]
    service = _FakeService({1: 12.0, 2: 100.0, 3: 5.0})  # 3 unchanged, FD skipped entirely
    results = refresh_prices(holdings, service=service)

    by_id = {r.holding_id: r for r in results}
    assert set(by_id) == {1, 2, 3}  # FD not refreshable
    assert by_id[1].status == "updated" and holdings[0].latest_price == 12.0
    assert by_id[2].status == "updated" and holdings[1].latest_price == 100.0
    assert by_id[3].status == "unchanged"
