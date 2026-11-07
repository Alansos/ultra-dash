"""Tests for the taper guidance card + race-date form (taper slice 3)."""

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

import app.db as db
from app.main import app


@pytest.fixture
def client(tmp_path):
    """Point the app at a throwaway SQLite file and start fresh."""
    db.DB_PATH = tmp_path / "test.db"
    db.init_db()
    return TestClient(app)


def _register(client):
    client.post("/register", data={"email": "alan@test.com", "password": "password123"})


def test_dashboard_shows_taper_card_and_form(client):
    _register(client)
    r = client.get("/")
    assert r.status_code == 200
    assert "Taper guidance" in r.text
    assert 'name="race_date"' in r.text
    assert "Set your next race date to see taper guidance." in r.text


def test_save_race_date_shows_guidance(client):
    _register(client)
    # Race 10 days out, so the taper window is live whatever day this runs.
    race_day = (date.today() + timedelta(days=10)).isoformat()
    r = client.post("/race-date", data={"race_date": race_day}, follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/"
    r = client.get("/")
    assert race_day in r.text
    # No runs uploaded, so there is no build-block data to judge the taper.
    assert "taper guidance" in r.text.lower()


def test_race_date_requires_login(client):
    r = client.post("/race-date", data={"race_date": "2026-11-14"}, follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/login"
