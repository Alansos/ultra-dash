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
    conn.execute(SCHEMA)
    conn.commit()
    conn.close()

def insert_activity(filename, parsed):
    conn = get_connection()
    conn.execute(
        "INSERT OR IGNORE INTO activities (filename, start_time, distance_km, duration_s, elev_gain_m) VALUES (?, ?, ?, ?, ?)",
        (filename, parsed["start_time"], parsed["distance_km"], parsed["duration_s"], parsed["elev_gain_m"]),
    )
    conn.commit()
    conn.close()

def get_all_activities():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM activities ORDER BY start_time").fetchall()
    conn.close()
    return [dict(r) for r in rows]
