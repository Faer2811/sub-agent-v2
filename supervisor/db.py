"""
Database module — PostgreSQL via Supabase.
Replaces JSON files on Drive for messages, sessions, profiles.
"""
from __future__ import annotations
import json
import logging
import os
from typing import Any, Dict, List, Optional
log = logging.getLogger(__name__)


def get_conn():
    """Get PostgreSQL connection."""
    import psycopg2
    url = os.environ.get("SUPABASE_DB_URL")
    if not url:
        raise RuntimeError("SUPABASE_DB_URL not set")
    return psycopg2.connect(url)


# ---------------------------------------------------------------------------
# Messages
# ---------------------------------------------------------------------------
def log_message(user_id: int, chat_id: int, direction: str, text: str) -> None:
    """Save message to PostgreSQL."""
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO messages (user_id, chat_id, direction, text) VALUES (%s, %s, %s, %s)",
            (user_id, chat_id, direction, text[:2000])
        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception:
        log.error("Failed to log message for user_id=%s", user_id, exc_info=True)


def get_messages(user_id: int, limit: int = 200) -> List[Dict[str, Any]]:
    """Get messages for user from PostgreSQL."""
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            "SELECT user_id, chat_id, direction, text, ts FROM messages "
            "WHERE user_id = %s ORDER BY ts DESC LIMIT %s",
            (user_id, limit)
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return [
            {"user_id": r[0], "chat_id": r[1], "direction": r[2],
             "text": r[3], "ts": r[4].isoformat() if r[4] else ""}
            for r in reversed(rows)
        ]
    except Exception:
        log.error("Failed to get messages for user_id=%s", user_id, exc_info=True)
        return []


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------
def get_session(user_id: int) -> Optional[Dict[str, Any]]:
    """Get session for user."""
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT * FROM sessions WHERE user_id = %s", (user_id,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        if not row:
            return None
        return {
            "user_id": row[0], "username": row[1],
            "message_count": row[2], "portrait_stage": row[3],
            "last_message_at": row[4], "last_full_portrait_message_count": row[5]
        }
    except Exception:
        log.error("Failed to get session for user_id=%s", user_id, exc_info=True)
        return None


def upsert_session(user_id: int, **kwargs) -> None:
    """Create or update session."""
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO sessions (user_id, username, message_count, portrait_stage, last_message_at)
               VALUES (%s, %s, %s, %s, NOW())
               ON CONFLICT (user_id) DO UPDATE SET
                 message_count = EXCLUDED.message_count,
                 portrait_stage = COALESCE(%s, sessions.portrait_stage),
                 last_message_at = NOW(),
                 updated_at = NOW()""",
            (user_id, kwargs.get("username"), kwargs.get("message_count", 0),
             kwargs.get("portrait_stage", 0), kwargs.get("portrait_stage"))
        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception:
        log.error("Failed to upsert session for user_id=%s", user_id, exc_info=True)


# ---------------------------------------------------------------------------
# Profiles
# ---------------------------------------------------------------------------
def get_profile(user_id: int) -> Optional[Dict[str, Any]]:
    """Get profile for user."""
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT user_id, username, portrait_status, portrait, raw_observations FROM profiles WHERE user_id = %s", (user_id,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        if not row:
            return None
        return {
            "user_id": row[0], "username": row[1],
            "portrait_status": row[2], "portrait": row[3],
            "raw_observations": row[4]
        }
    except Exception:
        log.error("Failed to get profile for user_id=%s", user_id, exc_info=True)
        return None


def upsert_profile(user_id: int, username: str, portrait_status: str, portrait: Dict[str, Any]) -> None:
    """Create or update profile."""
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO profiles (user_id, username, portrait_status, portrait, updated_at)
               VALUES (%s, %s, %s, %s, NOW())
               ON CONFLICT (user_id) DO UPDATE SET
                 portrait_status = EXCLUDED.portrait_status,
                 portrait = EXCLUDED.portrait,
                 updated_at = NOW()""",
            (user_id, username, portrait_status, json.dumps(portrait, ensure_ascii=False))
        )
        conn.commit()
        cur.close()
        conn.close()
        log.info("Profile upserted for user_id=%s", user_id)
    except Exception:
        log.error("Failed to upsert profile for user_id=%s", user_id, exc_info=True)

