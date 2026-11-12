"""Tests for profile sharing tokens (sharing slice 1)."""

import pytest

import app.db as db
from app.auth import (
    create_user,
    get_or_create_share_token,
    get_user_by_share_token,
)


@pytest.fixture
def fresh_db(tmp_path):
    """Point the app at a throwaway SQLite file and start fresh."""
    db.DB_PATH = tmp_path / "test.db"
    db.init_db()


def test_users_table_has_share_token_column(fresh_db):
    conn = db.get_connection()
    cols = [r[1] for r in conn.execute("PRAGMA table_info(users)").fetchall()]
    conn.close()
    assert "share_token" in cols


def test_migration_adds_share_token_to_old_db(tmp_path):
    # Build a users table the old way (no share_token), then init_db must add it.
    db.DB_PATH = tmp_path / "old.db"
    conn = db.get_connection()
    conn.execute(
        "CREATE TABLE users (id INTEGER PRIMARY KEY, email TEXT UNIQUE NOT NULL,"
        " password_hash TEXT NOT NULL, race_date TEXT,"
        " created_at TEXT DEFAULT CURRENT_TIMESTAMP)"
    )
    conn.commit()
    conn.close()
    db.init_db()
    conn = db.get_connection()
    cols = [r[1] for r in conn.execute("PRAGMA table_info(users)").fetchall()]
    conn.close()
    assert "share_token" in cols


def test_new_user_has_no_share_token(fresh_db):
    # Sharing is off by default: the token starts NULL.
    user = create_user("alan@test.com", "password123")
    conn = db.get_connection()
    row = conn.execute(
        "SELECT share_token FROM users WHERE id = ?", (user["id"],)
    ).fetchone()
    conn.close()
    assert row["share_token"] is None


def test_get_or_create_returns_same_token_twice(fresh_db):
    user = create_user("alan@test.com", "password123")
    first = get_or_create_share_token(user["id"])
    second = get_or_create_share_token(user["id"])
    assert first
    assert first == second


def test_different_users_get_different_tokens(fresh_db):
    one = create_user("alan@test.com", "password123")
    two = create_user("coach@test.com", "password123")
    assert get_or_create_share_token(one["id"]) != get_or_create_share_token(two["id"])


def test_get_user_by_share_token_finds_user(fresh_db):
    user = create_user("alan@test.com", "password123")
    token = get_or_create_share_token(user["id"])
    found = get_user_by_share_token(token)
    assert found["id"] == user["id"]
    assert found["email"] == "alan@test.com"
    assert "password_hash" not in found


def test_get_user_by_share_token_unknown_returns_none(fresh_db):
    assert get_user_by_share_token("no-such-token") is None
    assert get_user_by_share_token("") is None
    assert get_user_by_share_token(None) is None


def test_get_or_create_for_missing_user_returns_none(fresh_db):
    assert get_or_create_share_token(999) is None
