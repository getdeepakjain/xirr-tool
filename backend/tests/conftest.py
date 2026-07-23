"""Shared pytest fixtures.

An isolated throwaway SQLite database is configured via ``DATABASE_URL`` *before*
any application module is imported, so tests never touch the real data file.
"""
import os
import tempfile
import uuid

_TMP_DIR = tempfile.mkdtemp(prefix="xirr_test_")
os.environ["DATABASE_URL"] = f"sqlite:///{os.path.join(_TMP_DIR, 'test.sqlite3')}"
os.environ.setdefault("SECRET_KEY", "test-secret-key")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.database import Base, engine, init_db  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _database():
    init_db()
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client():
    return TestClient(app)


@pytest.fixture()
def auth_client(client):
    """A TestClient already authenticated as a fresh unique user."""
    email = f"user_{uuid.uuid4().hex[:12]}@example.com"
    resp = client.post(
        "/api/auth/register",
        json={"email": email, "password": "secret123", "name": "Tester"},
    )
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    client.default_profile_id = _first_profile_id(client)
    return client


def _first_profile_id(client) -> int:
    resp = client.get("/api/profiles")
    assert resp.status_code == 200, resp.text
    return resp.json()[0]["id"]
