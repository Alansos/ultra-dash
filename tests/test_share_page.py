"""Tests for the public read-only share page (sharing slice 2)."""

import pytest
from fastapi.testclient import TestClient

import app.db as db
from app.auth import get_or_create_share_token, get_user_by_email
from app.db import insert_activity
from app.main import app


@pytest.fixture
def client(tmp_path):
    """Point the app at a throwaway SQLite file and start fresh."""
    db.DB_PATH = tmp_path / "test.db"
    db.init_db()
    return TestClient(app)


def _activity():
    return {"start_time": "2026-11-05T10:00:00", "distance_km": 10.0,
            "duration_s": 3600.0, "elev_gain_m": 100.0}


def _setup_shared_user(client):
    client.post("/register", data={"email": "alan@test.com", "password": "password123"})
    user = get_user_by_email("alan@test.com")
    insert_activity("a-run.gpx", _activity(), user["id"])
    token = get_or_create_share_token(user["id"])
    client.get("/logout")  # prove the page needs no login
    return token


def test_share_page_loads_without_login(client):
    token = _setup_shared_user(client)
    r = client.get(f"/share/{token}")
    assert r.status_code == 200
    assert "Shared training profile" in r.text
    assert "read-only" in r.text


def test_share_page_shows_training_data(client):
    token = _setup_shared_user(client)
    r = client.get(f"/share/{token}")
    assert "Weekly volume" in r.text
    assert "Overtraining alerts" in r.text
    assert "10.0 km" in r.text


def test_share_page_hides_email(client):
    token = _setup_shared_user(client)
    r = client.get(f"/share/{token}")
    assert "alan@test.com" not in r.text
    assert "Logged in as" not in r.text


def test_share_page_has_no_forms(client):
    token = _setup_shared_user(client)
    r = client.get(f"/share/{token}")
    assert "<form" not in r.text
    assert "Upload a run" not in r.text


def test_share_page_unknown_token_404(client):
    r = client.get("/share/no-such-token")
    assert r.status_code == 404


def test_share_page_empty_profile_loads(client):
    client.post("/register", data={"email": "alan@test.com", "password": "password123"})
    user = get_user_by_email("alan@test.com")
    token = get_or_create_share_token(user["id"])
    client.get("/logout")
    r = client.get(f"/share/{token}")
    assert r.status_code == 200
    assert "Workload looks steady" in r.text
