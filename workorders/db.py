from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Iterable


# Default SQLite database filename used when no explicit path is provided.
DB_FILENAME = "workorders.db"


def utc_now_iso() -> str:
    """Return the current UTC time as an ISO-8601 string with Z suffix."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

def get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Create a SQLite connection and configure it to return Row objects."""
    # Use the provided path, otherwise default to the current working directory.
    path = Path(db_path) if db_path else (Path.cwd() / DB_FILENAME)
    # Open the database file and set a row factory for dict-like access.
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(conn: sqlite3.Connection) -> None:
    
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS work_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            machine_id TEXT NOT NULL,
            issue TEXT NOT NULL,
            priority TEXT NOT NULL CHECK (priority IN ('low', 'med', 'high')),
            status TEXT NOT NULL CHECK (status IN ('open', 'closed')),
            created_at TEXT NOT NULL,
            closed_at TEXT
        );
        """
    )
    conn.commit()

def add_work_order(conn: sqlite3.connection, machine_id: str, issue: str, priority: str = "med",)  -> int:
    created_at = utc_now_iso()
    cur = conn.execute(
        """
        INSERT INTO work_orders (machine_id, issue, priority, status, created_at, closed_at)
        VALUES (?, ?, ?, 'open', ?, NULL);
        """,
        (machine_id, issue, priority, created_at),
    )
    conn.commit()
    return int(cur.lastrowid)

def list_work_orders(
    conn: sqlite3.Connection,
    status: Optional[str] = None,) -> list[sqlite3.Row]:
    """
    Lists work orders. If status is provided, filters by it.
    """
    if status:
        cur = conn.execute(
            """
            SELECT id, machine_id, issue, priority, status, created_at, closed_at
            FROM work_orders
            WHERE status = ?
            ORDER BY id DESC;
            """,
            (status,),
        )
    else:
        cur = conn.execute(
            """
            SELECT id, machine_id, issue, priority, status, created_at, closed_at
            FROM work_orders
            ORDER BY id DESC;
            """
        )
    return list(cur.fetchall())

def close_work_order(conn: sqlite3.Connection, work_order_id: int) -> int:
    """
    Marks a work order as closed. Returns number of rows updated (0 or 1).
    """
    closed_at = utc_now_iso()
    cur = conn.execute(
        """
        UPDATE work_orders
        SET status = 'closed', closed_at = ?
        WHERE id = ? AND status = 'open';
        """,
        (closed_at, work_order_id),
    )
    conn.commit()
    return cur.rowcount

def list_work_orders_by_machine(
    conn: sqlite3.Connection,
    machine_id: str,
    status: Optional[str] = None,
) -> list[sqlite3.Row]:
    """
    Lists work orders for a specific machine_id.
    Optional status filter.
    """
    if status:
        cur = conn.execute(
            """
            SELECT id, machine_id, issue, priority, status, created_at, closed_at
            FROM work_orders
            WHERE machine_id = ? AND status = ?
            ORDER BY id DESC;
            """,
            (machine_id, status),
        )
    else:
        cur = conn.execute(
            """
            SELECT id, machine_id, issue, priority, status, created_at, closed_at
            FROM work_orders
            WHERE machine_id = ?
            ORDER BY id DESC;
            """,
            (machine_id,),
        )

    return list(cur.fetchall())

def get_work_order_by_id(conn: sqlite3.Connection, work_order_id: int) -> Optional[sqlite3.Row]:
    cur = conn.execute(
        """
        SELECT id, machine_id, issue, priority, status, created_at, closed_at
        FROM work_orders
        WHERE id = ?;
        """,
        (work_order_id,),
    )
    return cur.fetchone()




    




