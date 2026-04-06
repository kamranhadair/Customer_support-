"""
app/database.py — SQLite CRUD operations for customers, tickets, and draft responses.
"""
import json
import logging
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Generator, Optional

from app.config import get_settings
from app.models import (
    Customer,
    CustomerCreate,
    DraftResponse,
    Ticket,
    TicketCreate,
    TicketStatus,
)

logger = logging.getLogger(__name__)

# ── Helpers ────────────────────────────────────────────────────────────────────


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_db_path() -> str:
    path = get_settings().sqlite_db_path
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return path


@contextmanager
def get_connection() -> Generator[sqlite3.Connection, None, None]:
    """Yield a thread-safe SQLite connection with row factory."""
    db_path = _get_db_path()
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ── Schema Initialization ──────────────────────────────────────────────────────


def init_db() -> None:
    """Create all tables if they do not exist."""
    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS customers (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT    NOT NULL,
                email       TEXT    NOT NULL UNIQUE,
                plan        TEXT    NOT NULL DEFAULT 'free',
                company     TEXT,
                phone       TEXT,
                created_at  TEXT    NOT NULL
            );

            CREATE TABLE IF NOT EXISTS tickets (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL REFERENCES customers(id),
                subject     TEXT    NOT NULL,
                description TEXT    NOT NULL,
                status      TEXT    NOT NULL DEFAULT 'open',
                priority    TEXT    NOT NULL DEFAULT 'medium',
                created_at  TEXT    NOT NULL,
                updated_at  TEXT    NOT NULL
            );

            CREATE TABLE IF NOT EXISTS draft_responses (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id    INTEGER NOT NULL REFERENCES tickets(id),
                draft_text   TEXT    NOT NULL,
                context_used TEXT,
                created_at   TEXT    NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_tickets_customer ON tickets(customer_id);
            CREATE INDEX IF NOT EXISTS idx_tickets_status   ON tickets(status);
            CREATE INDEX IF NOT EXISTS idx_drafts_ticket    ON draft_responses(ticket_id);
            """
        )
    logger.info("Database initialized at %s", _get_db_path())


# ── Customer CRUD ──────────────────────────────────────────────────────────────


def create_customer(payload: CustomerCreate) -> Customer:
    now = _now()
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO customers (name, email, plan, company, phone, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (payload.name, payload.email, payload.plan.value,
             payload.company, payload.phone, now),
        )
        row_id = cur.lastrowid
    return get_customer(row_id)


def get_customer(customer_id: int) -> Optional[Customer]:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM customers WHERE id = ?", (customer_id,)
        ).fetchone()
    if row is None:
        return None
    return Customer(**dict(row))


def get_customer_by_email(email: str) -> Optional[Customer]:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM customers WHERE email = ?", (email,)
        ).fetchone()
    if row is None:
        return None
    return Customer(**dict(row))


def list_customers(limit: int = 100, offset: int = 0) -> list[Customer]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM customers ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
    return [Customer(**dict(r)) for r in rows]


# ── Ticket CRUD ────────────────────────────────────────────────────────────────


def create_ticket(payload: TicketCreate) -> Ticket:
    now = _now()
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO tickets
                (customer_id, subject, description, status, priority, created_at, updated_at)
            VALUES (?, ?, ?, 'open', ?, ?, ?)
            """,
            (payload.customer_id, payload.subject, payload.description,
             payload.priority.value, now, now),
        )
        row_id = cur.lastrowid
    return get_ticket(row_id)


def get_ticket(ticket_id: int) -> Optional[Ticket]:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM tickets WHERE id = ?", (ticket_id,)
        ).fetchone()
    if row is None:
        return None
    return Ticket(**dict(row))


def list_tickets(
    status: Optional[str] = None,
    customer_id: Optional[int] = None,
    limit: int = 100,
    offset: int = 0,
) -> list[Ticket]:
    query = "SELECT * FROM tickets WHERE 1=1"
    params: list = []
    if status:
        query += " AND status = ?"
        params.append(status)
    if customer_id:
        query += " AND customer_id = ?"
        params.append(customer_id)
    query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
    return [Ticket(**dict(r)) for r in rows]


def update_ticket_status(ticket_id: int, status: TicketStatus) -> Optional[Ticket]:
    now = _now()
    with get_connection() as conn:
        conn.execute(
            "UPDATE tickets SET status = ?, updated_at = ? WHERE id = ?",
            (status.value, now, ticket_id),
        )
    return get_ticket(ticket_id)


def get_recent_tickets_by_customer(customer_id: int, limit: int = 5) -> list[Ticket]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT * FROM tickets WHERE customer_id = ?
            ORDER BY created_at DESC LIMIT ?
            """,
            (customer_id, limit),
        ).fetchall()
    return [Ticket(**dict(r)) for r in rows]


# ── Draft CRUD ─────────────────────────────────────────────────────────────────


def save_draft(ticket_id: int, draft_text: str, context_used: Optional[dict] = None) -> DraftResponse:
    now = _now()
    context_json = json.dumps(context_used) if context_used else None
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO draft_responses (ticket_id, draft_text, context_used, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (ticket_id, draft_text, context_json, now),
        )
        row_id = cur.lastrowid

    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM draft_responses WHERE id = ?", (row_id,)
        ).fetchone()
    return DraftResponse(**dict(row))


def get_drafts_for_ticket(ticket_id: int) -> list[DraftResponse]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT * FROM draft_responses WHERE ticket_id = ?
            ORDER BY created_at DESC
            """,
            (ticket_id,),
        ).fetchall()
    return [DraftResponse(**dict(r)) for r in rows]
