"""User accounts for Ultra Dash: password hashing + SQLite user store.

Uses only the standard library (hashlib.scrypt), so no new dependency.
Passwords are never stored — only the salted scrypt hash.
"""

import hashlib
import secrets
import sqlite3
from datetime import datetime

from app.db import get_connection


def hash_password(password: str) -> str:
    """Hash a password with a random salt. Returns a single storable string."""
    salt = secrets.token_bytes(16)
    dk = hashlib.scrypt(password.encode(), salt=salt, n=16384, r=8, p=1, dklen=32)
    return f"scrypt$16384$8$1${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """Check a password against a stored hash. False on any bad input."""
    try:
        _, n, r, p, salt_hex, dk_hex = stored.split("$")
        dk = hashlib.scrypt(
            password.encode(),
            salt=bytes.fromhex(salt_hex),
            n=int(n), r=int(r), p=int(p), dklen=32,
        )
        return secrets.compare_digest(dk.hex(), dk_hex)
    except Exception:
        return False


def create_user(email: str, password: str, race_date: str = None):
    """Create a user. Returns the user (id, email, created_at), or None if the email is taken."""
    email = email.lower().strip()
    conn = get_connection()
    try:
        cur = conn.execute(
            "INSERT INTO users (email, password_hash, race_date) VALUES (?, ?, ?)",
            (email, hash_password(password), race_date),
        )
        conn.commit()
        user_id = cur.lastrowid
    except sqlite3.IntegrityError:
        conn.close()
        return None
    row = conn.execute(
       "SELECT id, email, race_date, share_token, created_at FROM users WHERE id = ?", (user_id,)
    ).fetchone()
    conn.close()
    return dict(row)


def get_user_by_email(email: str):
    """Return the full user row (including password_hash) or None."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM users WHERE email = ?", (email.lower().strip(),)
    ).fetchone()
    conn.close()
    return dict(row) if row else None

def get_user_by_id(user_id: int):
    """Return the user (id, email, race_date, share_token, created_at) or None."""
    conn = get_connection()
    row = conn.execute(
       "SELECT id, email, race_date, share_token, created_at FROM users WHERE id = ?", (user_id,)

    ).fetchone()
    conn.close()
    return dict(row) if row else None

def get_or_create_share_token(user_id: int):
    """Return the user's public share token, creating one if sharing is off.
    Returns None if the user doesn't exist. Sharing stays off (NULL token)
    until this is called."""
    user = get_user_by_id(user_id)
    if user is None:
        return None
    conn = get_connection()
    row = conn.execute(
        "SELECT share_token FROM users WHERE id = ?", (user_id,)
    ).fetchone()
    token = row["share_token"] if row else None
    if not token:
        token = secrets.token_urlsafe(24)
        conn.execute(
            "UPDATE users SET share_token = ? WHERE id = ?", (token, user_id)
        )
        conn.commit()
    conn.close()
    return token


def get_user_by_share_token(token: str):
    """Return the user (id, email, race_date, share_token, created_at) for a
    public share token, or None. Never returns the password hash."""
    if not token:
        return None
    conn = get_connection()
    row = conn.execute(
        "SELECT id, email, race_date, share_token, created_at FROM users WHERE share_token = ?",
        (token,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def disable_sharing(user_id: int):
    """Turn sharing off: clear the token so the old link stops working.
    Returns the updated user, or None if the user doesn't exist."""
    conn = get_connection()
    conn.execute("UPDATE users SET share_token = NULL WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    return get_user_by_id(user_id)


def set_race_date(user_id: int, race_date: str):
    """Save the user's next race date (YYYY-MM-DD). Empty string clears it.
    Returns the updated user, or None if the user doesn't exist."""
    if race_date:
        datetime.fromisoformat(race_date)  # raises ValueError on a bad date
    else:
        race_date = None
    conn = get_connection()
    conn.execute("UPDATE users SET race_date = ? WHERE id = ?", (race_date, user_id))
    conn.commit()
    conn.close()
    return get_user_by_id(user_id)

