"""Conversation memory, persisted in SQLite.

Stores every message of every conversation plus, per conversation, at most
one pending "connect you with a human agent?" offer. Because it lives in
the database, memory survives server restarts and is shared by all workers.
"""

from dataclasses import dataclass

from app.db import get_connection, utc_now


@dataclass
class PendingOffer:
    """An out-of-scope question waiting for the customer to accept a human handoff."""

    message: str
    ai_response: str
    reason: str


def get_history(conversation_id: str, limit: int = 20) -> list[dict]:
    """Return the last `limit` messages of a conversation, oldest first."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT role, content FROM messages WHERE conversation_id = ? ORDER BY id DESC LIMIT ?",
            (conversation_id, limit),
        ).fetchall()
    return [{"role": row["role"], "content": row["content"]} for row in reversed(rows)]


def append_turn(conversation_id: str, user_message: str, assistant_message: str) -> None:
    """Record one customer message and the assistant's reply, atomically."""
    now = utc_now()
    with get_connection() as conn:
        conn.executemany(
            "INSERT INTO messages (conversation_id, role, content, created_at) VALUES (?, ?, ?, ?)",
            [
                (conversation_id, "user", user_message, now),
                (conversation_id, "assistant", assistant_message, now),
            ],
        )


def set_offer(conversation_id: str, offer: PendingOffer) -> None:
    """Remember that we asked the customer whether they want a human agent."""
    with get_connection() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO pending_offers (conversation_id, message, ai_response, reason, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (conversation_id, offer.message, offer.ai_response, offer.reason, utc_now()),
        )


def pop_offer(conversation_id: str) -> PendingOffer | None:
    """Remove and return the pending offer, if any (an offer is answered once)."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT message, ai_response, reason FROM pending_offers WHERE conversation_id = ?",
            (conversation_id,),
        ).fetchone()
        if row is None:
            return None
        conn.execute("DELETE FROM pending_offers WHERE conversation_id = ?", (conversation_id,))
    return PendingOffer(row["message"], row["ai_response"], row["reason"])
