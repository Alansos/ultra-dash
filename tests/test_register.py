"""Tests for register / login (slice 1 of multi-user auth)."""

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


def test_register_creates_user_and_redirects(client):
    r = client.post("/register", data={"email": "alan@test.com", "password": "password123"}, follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/"


def test_register_duplicate_rejected(client):
    client.post("/register", data={"email": "alan@test.com", "password": "password123"})
    r = client.post("/register", data={"email": "alan@test.com", "password": "password123"}, follow_redirects=False)
    assert r.status_code == 400
    assert "already registered" in r.text


def test_login_wrong_password_rejected(client):
    client.post("/register", data={"email": "alan@test.com", "password": "password123"})
    r = client.post("/login", data={"email": "alan@test.com", "password": "wrongpass"}, follow_redirects=False)
    assert r.status_code == 400
    assert "Invalid email or password" in r.text


def test_login_success_after_logout(client):
    client.post("/register", data={"email": "alan@test.com", "password": "password123"})
    r = client.get("/logout", follow_redirects=False)
    assert r.status_code == 303
    r = client.post("/login", data={"email": "alan@test.com", "password": "password123"}, follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/"


def test_password_is_hashed_not_plaintext(client):
    from app.auth import get_user_by_email
    client.post("/register", data={"email": "alan@test.com", "password": "password123"})
    user = get_user_by_email("alan@test.com")
    assert user["password_hash"] != "password123"
    assert user["password_hash"].startswith("scrypt$")
