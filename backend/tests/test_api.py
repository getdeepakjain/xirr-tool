from app.prices import PriceResult


def test_register_creates_default_profile(auth_client):
    resp = auth_client.get("/api/profiles")
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


def test_login_rejects_bad_password(client):
    client.post("/api/auth/register",
                json={"email": "login@example.com", "password": "secret123", "name": "L"})
    ok = client.post("/api/auth/login",
                     json={"email": "login@example.com", "password": "secret123"})
    assert ok.status_code == 200
    bad = client.post("/api/auth/login",
                      json={"email": "login@example.com", "password": "wrong"})
    assert bad.status_code == 401


def test_requires_auth(client):
    assert client.get("/api/profiles").status_code == 401


def _create_mf_holding_with_txns(auth_client):
    pid = auth_client.default_profile_id
    h = auth_client.post(f"/api/profiles/{pid}/holdings", json={
        "asset_class": "MF", "name": "Alpha Fund", "identifier": "",
        "latest_price": 15.0,
    })
    assert h.status_code == 201, h.text
    hid = h.json()["id"]
    auth_client.post(f"/api/holdings/{hid}/transactions", json={
        "txn_date": "2020-01-01", "txn_type": "buy",
        "quantity": 100, "price": 10, "amount": 1000,
    })
    return pid, hid


def test_holding_transaction_and_analytics_flow(auth_client):
    pid, hid = _create_mf_holding_with_txns(auth_client)
    analytics = auth_client.get(f"/api/profiles/{pid}/analytics")
    assert analytics.status_code == 200
    data = analytics.json()
    assert data["portfolio"]["invested"] == 1000
    assert data["portfolio"]["current_value"] == 1500  # 100 units * 15
    mf = next(h for h in data["holdings"] if h["holding_id"] == hid)
    assert mf["units"] == 100


def test_export_holdings_and_transactions_csv(auth_client):
    pid, _ = _create_mf_holding_with_txns(auth_client)

    h_csv = auth_client.get(f"/api/profiles/{pid}/export/holdings.csv")
    assert h_csv.status_code == 200
    assert h_csv.headers["content-type"].startswith("text/csv")
    assert "Asset Class,Name" in h_csv.text
    assert "Alpha Fund" in h_csv.text

    t_csv = auth_client.get(f"/api/profiles/{pid}/export/transactions.csv")
    assert t_csv.status_code == 200
    assert "Alpha Fund" in t_csv.text
    assert "buy" in t_csv.text


def test_export_respects_asset_class_filter(auth_client):
    pid, _ = _create_mf_holding_with_txns(auth_client)
    # Add a second holding in a different class.
    auth_client.post(f"/api/profiles/{pid}/holdings", json={
        "asset_class": "Crypto", "name": "Bitcoin", "identifier": "btc",
        "latest_price": 100.0,
    })

    mf_only = auth_client.get(
        f"/api/profiles/{pid}/export/holdings.csv", params={"asset_class": "MF"}
    )
    assert mf_only.status_code == 200
    assert "Alpha Fund" in mf_only.text
    assert "Bitcoin" not in mf_only.text

    all_rows = auth_client.get(f"/api/profiles/{pid}/export/holdings.csv")
    assert "Alpha Fund" in all_rows.text
    assert "Bitcoin" in all_rows.text


def test_refresh_prices_endpoint(auth_client, monkeypatch):
    pid, hid = _create_mf_holding_with_txns(auth_client)

    def fake_refresh(holdings, service=None):
        results = []
        for h in holdings:
            old = h.latest_price
            h.latest_price = 20.0
            results.append(PriceResult(h.id, h.name, h.asset_class, old, 20.0, "updated"))
        return results

    monkeypatch.setattr("app.routers.market.refresh_prices", fake_refresh)
    resp = auth_client.post(f"/api/profiles/{pid}/refresh-prices")
    assert resp.status_code == 200
    body = resp.json()
    assert body["counts"]["updated"] == 1

    # New price persisted -> current value reflects 100 units * 20.
    analytics = auth_client.get(f"/api/profiles/{pid}/analytics").json()
    mf = next(h for h in analytics["holdings"] if h["holding_id"] == hid)
    assert mf["latest_price"] == 20.0
    assert mf["current_value"] == 2000
