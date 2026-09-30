"""SQLite storage: escalation tickets, conversation history, and pending offers.

Uses the standard-library `sqlite3` module with a short-lived connection per
operation. FastAPI runs sync endpoints in a thread pool, and SQLite
connections shouldn't be shared across threads, so this is the simplest
thread-safe approach.
"""

import random
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from app.config import DB_PATH
from app.models import Ticket

SCHEMA = """
CREATE TABLE IF NOT EXISTS tickets (
    ticket_id       TEXT PRIMARY KEY,
    conversation_id TEXT,
    message         TEXT NOT NULL,
    ai_response     TEXT NOT NULL,
    reason          TEXT NOT NULL,
    created_at      TEXT NOT NULL,
    transcript      TEXT
);

CREATE TABLE IF NOT EXISTS messages (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT NOT NULL,
    role            TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content         TEXT NOT NULL,
    created_at      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages (conversation_id, id);

CREATE TABLE IF NOT EXISTS pending_offers (
    conversation_id TEXT PRIMARY KEY,
    message         TEXT NOT NULL,
    ai_response     TEXT NOT NULL,
    reason          TEXT NOT NULL,
    created_at      TEXT NOT NULL
);
"""

MAX_ID_ATTEMPTS = 10


def utc_now() -> str:
    """Current UTC time as an ISO-8601 string (seconds precision)."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@contextmanager
def get_connection(db_path: Path | None = None) -> Iterator[sqlite3.Connection]:
    """Open a connection, commit on success, roll back on error, always close."""
    conn = sqlite3.connect(db_path or DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    """Create all tables, and add columns introduced after a database was created."""
    with get_connection() as conn:
        conn.executescript(SCHEMA)
        ticket_columns = {row["name"] for row in conn.execute("PRAGMA table_info(tickets)")}
        if "transcript" not in ticket_columns:
            conn.execute("ALTER TABLE tickets ADD COLUMN transcript TEXT")


# --- Tickets -------------------------------------------------------------------


def generate_ticket_id() -> str:
    """Return a mock, human-friendly ticket ID such as `#84231`."""
    return f"#{random.randint(10000, 99999)}"


def create_ticket(
    message: str,
    ai_response: str,
    reason: str,
    conversation_id: str | None = None,
    transcript: str | None = None,
) -> str:
    """Insert an escalation ticket and return its ID.

    The ID is random, so on the rare collision with an existing ticket the
    PRIMARY KEY constraint fails and a new ID is tried.
    """
    for _ in range(MAX_ID_ATTEMPTS):
        ticket_id = generate_ticket_id()
        try:
            with get_connection() as conn:
                conn.execute(
                    "INSERT INTO tickets (ticket_id, conversation_id, message, ai_response, reason, created_at, transcript) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (ticket_id, conversation_id, message, ai_response, reason, utc_now(), transcript),
                )
            return ticket_id
        except sqlite3.IntegrityError:
            continue
    raise RuntimeError("Could not generate a unique ticket ID")


def list_tickets() -> list[Ticket]:
    """Return all tickets, newest first."""
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM tickets ORDER BY created_at DESC, rowid DESC").fetchall()
    return [Ticket(**dict(row)) for row in rows]
