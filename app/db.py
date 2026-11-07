"""SQLite storage for parsed activities. Plain sqlite3, no ORM."""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "ultra.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS activities (
  id INTEGER PRIMARY KEY,
  filename TEXT UNIQUE,
  start_time TEXT,
  distance_km REAL,
  duration_s REAL,
  elev_gain_m REAL,
  user_id INTEGER,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY,
  email TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  race_date TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

"""

def get_connection():
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()
    _migrate_activities_user_id()
    _migrate_users_race_date()

def _migrate_users_race_date():
    """Add the race_date column to a pre-existing users table."""
    conn = get_connection()
    cols = [r[1] for r in conn.execute("PRAGMA table_info(users)").fetchall()]
    if "race_date" not in cols:
        conn.execute("ALTER TABLE users ADD COLUMN race_date TEXT")
        conn.commit()
    conn.close()

def _migrate_activities_user_id():
    """Add the user_id column to a pre-existing activities table."""
    conn = get_connection()
    cols = [r[1] for r in conn.execute("PRAGMA table_info(activities)").fetchall()]
    if "user_id" not in cols:
        conn.execute("ALTER TABLE activities ADD COLUMN user_id INTEGER")
        conn.commit()
    conn.close()


def insert_activity(filename, parsed, user_id):
    conn = get_connection()
    conn.execute(
        "INSERT OR IGNORE INTO activities (filename, start_time, distance_km, duration_s, elev_gain_m, user_id) VALUES (?, ?, ?, ?, ?, ?)",
        (filename, parsed["start_time"], parsed["distance_km"], parsed["duration_s"], parsed["elev_gain_m"], user_id),
    )
    conn.commit()
    conn.close()

def get_activities_for_user(user_id):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM activities WHERE user_id = ? ORDER BY start_time", (user_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_all_activities():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM activities ORDER BY start_time").fetchall()
    conn.close()
    return [dict(r) for r in rows]
