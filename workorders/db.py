from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Iterable
import os
import hashlib
import base64
import hmac


# Default SQLite database filename used when no explicit path is provided.
DB_FILENAME = "workorders.db"

def migrate_db(conn: sqlite3.Connection) -> None:
    """
    Adds missing columns to older databases safely.
    """
    existing = {row["name"] for row in conn.execute("PRAGMA table_info(work_orders);").fetchall()}

    def add_col(sql: str) -> None:
        conn.execute(sql)
        conn.commit()

    if "assigned_to" not in existing:
        add_col("ALTER TABLE work_orders ADD COLUMN assigned_to TEXT;")

    if "notes" not in existing:
        add_col("ALTER TABLE work_orders ADD COLUMN notes TEXT;")

    if "updated_at" not in existing:
        add_col("ALTER TABLE work_orders ADD COLUMN updated_at TEXT;")

    # Backfill updated_at if it's NULL
    conn.execute(
        """
        UPDATE work_orders
        SET updated_at = COALESCE(updated_at, closed_at, created_at)
        WHERE updated_at IS NULL;
        """
    )
    conn.commit()


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
    """
    Creates the work_orders table if it doesn't exist,
    and migrates older DBs to include any missing columns.
    """
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS work_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            machine_id TEXT NOT NULL,
            issue TEXT NOT NULL,
            priority TEXT NOT NULL CHECK (priority IN ('low', 'med', 'high')),
            status TEXT NOT NULL CHECK (status IN ('open', 'closed')),
            created_at TEXT NOT NULL,
            closed_at TEXT,

            assigned_to TEXT,
            notes TEXT,
            updated_at TEXT
        );
        """
    )
    conn.commit()
    migrate_db(conn)


def add_work_order(
    conn: sqlite3.Connection,
    machine_id: str,
    issue: str,
    priority: str = "med",
    assigned_to: str | None = None,
    notes: str | None = None,
) -> int:
    try:
        # Preferred location: package-local notifier.
        from .notify import send_sms
    except ModuleNotFoundError:
        try:
            # Fallback for current project layout where notify.py is at repo root.
            from notify import send_sms
        except ModuleNotFoundError:
            send_sms = None

    created_at = utc_now_iso()
    cur = conn.execute(
        """
        INSERT INTO work_orders (
            machine_id, issue, priority, status, created_at, closed_at,
            assigned_to, notes, updated_at
        )
        VALUES (?, ?, ?, 'open', ?, NULL, ?, ?, ?);
        """,
        (machine_id, issue, priority, created_at, assigned_to, notes, created_at),
    )
    conn.commit()
    if send_sms is not None:
        try:
            send_sms(f"New Work Order #{cur.lastrowid}\nMachine: {machine_id}\nIssue: {issue[:100]}")
        except Exception:
            # Never block order creation due to notification issues.
            pass

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
            SELECT id, machine_id, issue, priority, status, created_at, closed_at, assigned_to, notes, updated_at
            FROM work_orders
            WHERE status = ?
            ORDER BY id DESC;
            """,
            (status,),
        )
    else:
        cur = conn.execute(
            """
            SELECT id, machine_id, issue, priority, status, created_at, closed_at, assigned_to, notes, updated_at
            FROM work_orders
            ORDER BY id DESC;
            """
        )
    return list(cur.fetchall())

def close_work_order(conn: sqlite3.Connection, work_order_id: int) -> int:
    closed_at = utc_now_iso()
    cur = conn.execute(
        """
        UPDATE work_orders
        SET status = 'closed', closed_at = ?, updated_at = ?
        WHERE id = ? AND status = 'open';
        """,
        (closed_at, closed_at, work_order_id),
    )
    conn.commit()
    return cur.rowcount


def update_work_order(
    conn: sqlite3.Connection,
    work_order_id: int,
    *,
    issue: str | None = None,
    priority: str | None = None,
    assigned_to: str | None = None,
    notes: str | None = None,
) -> int:
    fields = []
    values = []

    if issue is not None:
        fields.append("issue = ?")
        values.append(issue)

    if priority is not None:
        fields.append("priority = ?")
        values.append(priority)

    if assigned_to is not None:
        fields.append("assigned_to = ?")
        values.append(assigned_to)

    if notes is not None:
        fields.append("notes = ?")
        values.append(notes)

    if not fields:
        return 0

    updated_at = utc_now_iso()
    fields.append("updated_at = ?")
    values.append(updated_at)

    values.append(work_order_id)

    cur = conn.execute(
        f"""
        UPDATE work_orders
        SET {", ".join(fields)}
        WHERE id = ?;
        """,
        tuple(values),
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
            SELECT id, machine_id, issue, priority, status, created_at, closed_at, assigned_to, notes, updated_at

            FROM work_orders
            WHERE machine_id = ? AND status = ?
            ORDER BY id DESC;
            """,
            (machine_id, status),
        )
    else:
        cur = conn.execute(
            """
            SELECT id, machine_id, issue, priority, status, created_at, closed_at, assigned_to, notes, updated_at

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
        SELECT id, machine_id, issue, priority, status, created_at, closed_at, assigned_to, notes, updated_at
        FROM work_orders
        WHERE id = ?;
        """,
        (work_order_id,),
    )
    return cur.fetchone()


def delete_all_work_orders(conn: sqlite3.Connection) -> int:
    """
    Deletes ALL work orders. Returns number of rows deleted.
    """
    cur = conn.execute("DELETE FROM work_orders;")
    conn.commit()
    return cur.rowcount


def delete_work_orders_by_machine(conn: sqlite3.Connection, machine_id: str) -> int:
    """
    Deletes all work orders for a specific machine_id.
    """
    cur = conn.execute("DELETE FROM work_orders WHERE machine_id = ?;", (machine_id,))
    conn.commit()
    return cur.rowcount


def delete_closed_older_than(conn: sqlite3.Connection, days: int) -> int:
    """
    Deletes CLOSED work orders with closed_at older than N days.
    closed_at is stored as ISO string like 2026-02-09T01:21:59Z.
    SQLite can parse this if we replace 'Z' with '+00:00'.
    """
    cur = conn.execute(
        """
        DELETE FROM work_orders
        WHERE status = 'closed'
          AND closed_at IS NOT NULL
          AND datetime(replace(closed_at, 'Z', '+00:00')) < datetime('now', ?);
        """,
        (f"-{int(days)} days",),
    )
    conn.commit()
    return cur.rowcount


def init_auth(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        """
    )
    conn.commit()


def _hash_password(password: str, salt: bytes | None = None, iterations: int = 200_000) -> str:
    """
    Returns a string encoding: pbkdf2_sha256$iterations$salt_b64$dk_b64
    """
    if salt is None:
        salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return "pbkdf2_sha256$%d$%s$%s" % (
        iterations,
        base64.b64encode(salt).decode("ascii"),
        base64.b64encode(dk).decode("ascii"),
    )


def _verify_password(password: str, stored: str) -> bool:
    try:
        algo, iters_s, salt_b64, dk_b64 = stored.split("$", 3)
        if algo != "pbkdf2_sha256":
            return False
        iterations = int(iters_s)
        salt = base64.b64decode(salt_b64.encode("ascii"))
        expected = base64.b64decode(dk_b64.encode("ascii"))

        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
        return hmac.compare_digest(dk, expected)
    except Exception:
        return False


def ensure_admin_user(conn: sqlite3.Connection, username: str, password: str) -> None:
    """
    Creates an initial user if it doesn't exist.
    """
    init_auth(conn)
    existing = conn.execute("SELECT 1 FROM users WHERE username = ?;", (username,)).fetchone()
    if existing:
        return
    conn.execute(
        "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?);",
        (username, _hash_password(password), utc_now_iso()),
    )
    conn.commit()


def authenticate(conn: sqlite3.Connection, username: str, password: str) -> bool:
    init_auth(conn)
    row = conn.execute(
        "SELECT password_hash FROM users WHERE username = ?;",
        (username,),
    ).fetchone()
    if row is None:
        return False
    return _verify_password(password, row["password_hash"])

def ensure_admin_from_env(conn: sqlite3.Connection) -> None:
    """
    Bootstraps an admin user from environment variables:
      WORKORDERS_ADMIN_USER
      WORKORDERS_ADMIN_PASS

    If either is missing, does nothing (app will require you to set them).
    """
    init_auth(conn)

    user = os.getenv("WORKORDERS_ADMIN_USER")
    pw = os.getenv("WORKORDERS_ADMIN_PASS")

    if not user or not pw:
        return

    ensure_admin_user(conn, username=user, password=pw)







    



