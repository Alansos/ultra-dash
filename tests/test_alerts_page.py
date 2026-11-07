"""Tests for the overtraining alerts card (alerts slice 2)."""

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

import app.db as db
from app.auth import get_user_by_email
from app.db import insert_activity
from app.main import app


@pytest.fixture
def client(tmp_path):
    """Point the app at a throwaway SQLite file and start fresh."""
    db.DB_PATH = tmp_path / "test.db"
    db.init_db()
    return TestClient(app)


def _register(client):
    client.post("/register", data={"email": "alan@test.com", "password": "password123"})


def test_dashboard_shows_alerts_card_steady(client):
    _register(client)
    r = client.get("/")
    assert r.status_code == 200
    assert "Overtraining alerts" in r.text
    assert "Workload looks steady" in r.text


def test_dashboard_shows_acwr_alert(client):
    _register(client)
    user = get_user_by_email("alan@test.com")
    # Four weeks of runs, 7 days apart: 50, 50, 50, 100 km, ending this week.
    today = date.today()
    for i, km in enumerate([50.0, 50.0, 50.0, 100.0]):
        day = today - timedelta(days=27 - 7 * i)
        insert_activity(f"run{i}.gpx", {
            "start_time": f"{day}T08:00:00+00:00",
            "distance_km": km, "duration_s": 3600, "elev_gain_m": 0,
        }, user["id"])
    r = client.get("/")
    assert "Workload spiked" in r.text
