"""Tests for saving a race date per user (taper slice 2)."""

import pytest

import app.db as db
from app.auth import create_user, get_user_by_id, set_race_date


@pytest.fixture
def fresh_db(tmp_path):
    """Point the app at a throwaway SQLite file and start fresh."""
    db.DB_PATH = tmp_path / "test.db"
    db.init_db()


def test_users_table_has_race_date_column(fresh_db):
    conn = db.get_connection()
    cols = [r[1] for r in conn.execute("PRAGMA table_info(users)").fetchall()]
    conn.close()
    assert "race_date" in cols


def test_migration_adds_race_date_to_old_db(tmp_path):
    # Build a users table the old way (no race_date), then init_db must add it.
    db.DB_PATH = tmp_path / "old.db"
    conn = db.get_connection()
    conn.execute(
        "CREATE TABLE users (id INTEGER PRIMARY KEY, email TEXT UNIQUE NOT NULL,"
        " password_hash TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP)"
    )
    conn.commit()
    conn.close()
    db.init_db()
    conn = db.get_connection()
    cols = [r[1] for r in conn.execute("PRAGMA table_info(users)").fetchall()]
    conn.close()
    assert "race_date" in cols


def test_set_and_read_race_date(fresh_db):
    user = create_user("alan@test.com", "password123")
    assert user["race_date"] is None
    updated = set_race_date(user["id"], "2026-11-14")
    assert updated["race_date"] == "2026-11-14"
    assert get_user_by_id(user["id"])["race_date"] == "2026-11-14"


def test_bad_race_date_rejected(fresh_db):
    user = create_user("alan@test.com", "password123")
    with pytest.raises(ValueError):
        set_race_date(user["id"], "not-a-date")
