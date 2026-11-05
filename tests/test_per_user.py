"""Tests for per-user activities: login required, users only see their own runs."""

import pytest
from fastapi.testclient import TestClient

import app.db as db
from app.db import insert_activity
from app.auth import get_user_by_email
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


def test_dashboard_requires_login(client):
    r = client.get("/", follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/login"


def test_users_only_see_their_own_activities(client):
    client.post("/register", data={"email": "a@test.com", "password": "password123"})
    user_a = get_user_by_email("a@test.com")
    client.post("/register", data={"email": "b@test.com", "password": "password123"})
    user_b = get_user_by_email("b@test.com")
    insert_activity("a-run.gpx", _activity(), user_a["id"])
    insert_activity("b-run.gpx", _activity(), user_b["id"])
    # Client is logged in as b (the last register); switch to a.
    client.get("/logout")
    client.post("/login", data={"email": "a@test.com", "password": "password123"})
    r = client.get("/activities")
    assert r.status_code == 200
    assert [a["filename"] for a in r.json()] == ["a-run.gpx"]
