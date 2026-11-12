"""Tests for the share toggle on the dashboard (sharing slice 3)."""

import pytest
from fastapi.testclient import TestClient

import app.db as db
from app.auth import get_or_create_share_token, get_user_by_email, get_user_by_share_token
from app.main import app


@pytest.fixture
def client(tmp_path):
    """Point the app at a throwaway SQLite file and start fresh."""
    db.DB_PATH = tmp_path / "test.db"
    db.init_db()
    return TestClient(app)


def _register(client):
    client.post("/register", data={"email": "alan@test.com", "password": "password123"})


def test_dashboard_offers_sharing_when_off(client):
    _register(client)
    r = client.get("/")
    assert r.status_code == 200
    assert "Share my profile" in r.text
    assert "Enable sharing" in r.text
    assert "Copy link" not in r.text


def test_enable_sharing_shows_link_on_dashboard(client):
    _register(client)
    r = client.post("/share/enable", follow_redirects=False)
    assert r.status_code == 303
    r = client.get("/")
    user = get_user_by_email("alan@test.com")
    token = get_or_create_share_token(user["id"])
    assert f"/share/{token}" in r.text
    assert "Copy link" in r.text
    assert "Turn off sharing" in r.text


def test_disable_sharing_removes_link_and_kills_old_url(client):
    _register(client)
    user = get_user_by_email("alan@test.com")
    token = get_or_create_share_token(user["id"])
    assert client.get(f"/share/{token}").status_code == 200
    r = client.post("/share/disable", follow_redirects=False)
    assert r.status_code == 303
    r = client.get("/")
    assert f"/share/{token}" not in r.text
    assert "Copy link" not in r.text
    assert "Enable sharing" in r.text
    assert client.get(f"/share/{token}").status_code == 404


def test_enable_sharing_requires_login(client):
    r = client.post("/share/enable", follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/login"


def test_disable_sharing_requires_login(client):
    r = client.post("/share/disable", follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/login"


def test_shared_link_works_after_enable(client):
    _register(client)
    client.post("/share/enable")
    user = get_user_by_email("alan@test.com")
    token = get_or_create_share_token(user["id"])
    client.get("/logout")
    assert client.get(f"/share/{token}").status_code == 200
