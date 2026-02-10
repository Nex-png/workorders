from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

import pytest # pyright: ignore[reportMissingImports]

from workorders.db import (
    add_work_order,
    close_work_order,
    get_connection,
    get_work_order_by_id,
    init_db,
    list_work_orders,
    list_work_orders_by_machine,
    update_work_order,
    delete_closed_older_than,
    delete_work_orders_by_machine,
    delete_all_work_orders,
)


@pytest.fixture
def conn(tmp_path):
    db_path = tmp_path / "test_workorders.db"
    connection = get_connection(str(db_path))
    init_db(connection)
    yield connection
    connection.close()


def test_get_connection_uses_row_factory(tmp_path):
    db_path = tmp_path / "row_factory.db"
    connection = get_connection(str(db_path))
    try:
        assert connection.row_factory is sqlite3.Row
    finally:
        connection.close()


def test_init_db_creates_work_orders_table(conn):
    row = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table' AND name = 'work_orders';
        """
    ).fetchone()
    assert row is not None


def test_add_work_order_persists_expected_defaults(conn):
    new_id = add_work_order(conn, machine_id="KMT-102", issue="Hydraulic leak", priority="med")

    row = get_work_order_by_id(conn, new_id)
    assert row is not None
    assert row["id"] == new_id
    assert row["machine_id"] == "KMT-102"
    assert row["issue"] == "Hydraulic leak"
    assert row["priority"] == "med"
    assert row["status"] == "open"
    assert row["closed_at"] is None
    assert isinstance(row["created_at"], str)
    assert row["created_at"].endswith("Z")
    assert row["updated_at"] == row["created_at"]
    assert row["assigned_to"] is None
    assert row["notes"] is None


def test_add_work_order_invalid_priority_raises_integrity_error(conn):
    with pytest.raises(sqlite3.IntegrityError):
        add_work_order(conn, machine_id="KMT-102", issue="Bad priority", priority="urgent")


def test_list_work_orders_returns_descending_and_supports_status_filter(conn):
    id1 = add_work_order(conn, machine_id="M1", issue="Issue 1", priority="low")
    id2 = add_work_order(conn, machine_id="M2", issue="Issue 2", priority="med")
    id3 = add_work_order(conn, machine_id="M3", issue="Issue 3", priority="high")

    close_work_order(conn, id2)

    all_rows = list_work_orders(conn)
    assert [r["id"] for r in all_rows] == [id3, id2, id1]

    open_rows = list_work_orders(conn, status="open")
    assert [r["id"] for r in open_rows] == [id3, id1]
    assert all(r["status"] == "open" for r in open_rows)

    closed_rows = list_work_orders(conn, status="closed")
    assert [r["id"] for r in closed_rows] == [id2]
    assert all(r["status"] == "closed" for r in closed_rows)


def test_close_work_order_updates_once_and_sets_closed_at(conn):
    work_order_id = add_work_order(conn, machine_id="M1", issue="Needs repair", priority="med")

    updated = close_work_order(conn, work_order_id)
    assert updated == 1

    row = get_work_order_by_id(conn, work_order_id)
    assert row is not None
    assert row["status"] == "closed"
    assert isinstance(row["closed_at"], str)
    assert row["closed_at"].endswith("Z")

    second_update = close_work_order(conn, work_order_id)
    assert second_update == 0

    missing_update = close_work_order(conn, 999999)
    assert missing_update == 0


def test_list_work_orders_by_machine_filters_machine_and_optional_status(conn):
    id_a1 = add_work_order(conn, machine_id="KMT-102", issue="Leak", priority="med")
    id_a2 = add_work_order(conn, machine_id="KMT-102", issue="Sensor fault", priority="high")
    add_work_order(conn, machine_id="KMT-200", issue="Alignment", priority="low")

    close_work_order(conn, id_a1)

    machine_rows = list_work_orders_by_machine(conn, machine_id="KMT-102")
    assert [r["id"] for r in machine_rows] == [id_a2, id_a1]
    assert all(r["machine_id"] == "KMT-102" for r in machine_rows)

    machine_open_rows = list_work_orders_by_machine(conn, machine_id="KMT-102", status="open")
    assert [r["id"] for r in machine_open_rows] == [id_a2]
    assert all(r["status"] == "open" for r in machine_open_rows)

    machine_closed_rows = list_work_orders_by_machine(conn, machine_id="KMT-102", status="closed")
    assert [r["id"] for r in machine_closed_rows] == [id_a1]
    assert all(r["status"] == "closed" for r in machine_closed_rows)


def test_get_work_order_by_id_returns_none_for_unknown_id(conn):
    assert get_work_order_by_id(conn, 424242) is None


def test_update_work_order_updates_fields_and_timestamp(conn):
    work_order_id = add_work_order(
        conn,
        machine_id="M1",
        issue="Initial issue",
        priority="med",
        assigned_to="Alex",
        notes="Initial notes",
    )
    original = get_work_order_by_id(conn, work_order_id)
    assert original is not None

    updated = update_work_order(
        conn,
        work_order_id,
        issue="Updated issue",
        priority="high",
        assigned_to="Priya",
        notes="Updated notes",
    )
    assert updated == 1

    current = get_work_order_by_id(conn, work_order_id)
    assert current is not None
    assert current["issue"] == "Updated issue"
    assert current["priority"] == "high"
    assert current["assigned_to"] == "Priya"
    assert current["notes"] == "Updated notes"
    assert current["updated_at"].endswith("Z")

    original_ts = datetime.fromisoformat(original["updated_at"].replace("Z", "+00:00"))
    current_ts = datetime.fromisoformat(current["updated_at"].replace("Z", "+00:00"))
    assert current_ts >= original_ts


def test_update_work_order_handles_no_fields_and_missing_id(conn):
    work_order_id = add_work_order(conn, machine_id="M1", issue="Issue", priority="low")

    no_field_update = update_work_order(conn, work_order_id)
    assert no_field_update == 0

    missing_update = update_work_order(conn, 999999, issue="No row")
    assert missing_update == 0


def test_delete_work_orders_by_machine_deletes_only_matching_rows(conn):
    add_work_order(conn, machine_id="KMT-102", issue="A", priority="low")
    add_work_order(conn, machine_id="KMT-102", issue="B", priority="med")
    add_work_order(conn, machine_id="KMT-200", issue="C", priority="high")

    deleted = delete_work_orders_by_machine(conn, "KMT-102")
    assert deleted == 2

    remaining = list_work_orders(conn)
    assert len(remaining) == 1
    assert remaining[0]["machine_id"] == "KMT-200"


def test_delete_closed_older_than_deletes_only_old_closed_orders(conn):
    old_closed_id = add_work_order(conn, machine_id="M1", issue="Old closed", priority="low")
    new_closed_id = add_work_order(conn, machine_id="M2", issue="New closed", priority="med")
    open_id = add_work_order(conn, machine_id="M3", issue="Still open", priority="high")

    assert close_work_order(conn, old_closed_id) == 1
    assert close_work_order(conn, new_closed_id) == 1

    conn.execute(
        "UPDATE work_orders SET closed_at = ?, updated_at = ? WHERE id = ?;",
        ("2000-01-01T00:00:00Z", "2000-01-01T00:00:00Z", old_closed_id),
    )
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    conn.execute(
        "UPDATE work_orders SET closed_at = ?, updated_at = ? WHERE id = ?;",
        (now, now, new_closed_id),
    )
    conn.commit()

    deleted = delete_closed_older_than(conn, 30)
    assert deleted == 1

    assert get_work_order_by_id(conn, old_closed_id) is None
    assert get_work_order_by_id(conn, new_closed_id) is not None
    assert get_work_order_by_id(conn, open_id) is not None


def test_delete_all_work_orders_clears_table(conn):
    add_work_order(conn, machine_id="M1", issue="A", priority="low")
    add_work_order(conn, machine_id="M2", issue="B", priority="med")

    deleted = delete_all_work_orders(conn)
    assert deleted == 2
    assert list_work_orders(conn) == []
