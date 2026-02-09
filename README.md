Work Orders
===========

Overview
--------
This project is a small, local work-order tracker backed by SQLite. It exposes two entry points:
1) A command-line interface (CLI) for quick terminal-based operations.
2) A Streamlit web app for a simple browser-based UI.

Both entry points share the same database layer in `workorders/db.py`, which encapsulates all
SQLite access and uses a single `work_orders` table to store records.

What It Does
------------
The tracker supports a basic lifecycle:
- Create a work order with `machine_id`, `issue`, and `priority`.
- List work orders, optionally filtered by open/closed status.
- Close a work order by ID (sets status to closed and records a close timestamp).
- View history for a specific machine ID.
- Show a single work order by ID.

How It Works
------------
The system is intentionally minimal:
- All data is stored in a SQLite database file (default `workorders.db`).
- The database is created on first use with a single table: `work_orders`.
- Each record stores identifiers, issue description, priority, status, and timestamps.
- The CLI and Streamlit app call the same functions in `workorders/db.py`.

Database Schema
---------------
The schema is created automatically by `init_db`:
- `id` INTEGER PRIMARY KEY AUTOINCREMENT
- `machine_id` TEXT NOT NULL
- `issue` TEXT NOT NULL
- `priority` TEXT NOT NULL CHECK IN ('low', 'med', 'high')
- `status` TEXT NOT NULL CHECK IN ('open', 'closed')
- `created_at` TEXT NOT NULL (UTC, ISO-8601 with Z suffix)
- `closed_at` TEXT (UTC, ISO-8601 with Z suffix) or NULL

CLI Usage
---------
All CLI commands accept an optional `--db` argument to point at a specific database file.

Add a work order:
`python -m workorders add --machine-id KMT-102 --issue "Hydraulic leak" --Priority med`

List work orders:
`python -m workorders list`
`python -m workorders list --status open`

Close a work order:
`python -m workorders close --id 12`

Show machine history:
`python -m workorders history --machine-id KMT-102`
`python -m workorders history --machine-id KMT-102 --status closed`

Show a single work order:
`python -m workorders show --id 12`

Streamlit App
-------------
The Streamlit UI is defined in `app.py`. It provides tabs for the same operations
as the CLI. Run it with:
`streamlit run app.py`

File Layout
-----------
- `app.py`: Streamlit UI that calls into the shared DB layer.
- `workorders/cli.py`: CLI argument parsing and command dispatch.
- `workorders/db.py`: SQLite schema creation and CRUD helpers.
- `workorders/__main__.py`: Allows `python -m workorders` to run the CLI.
- `workorders/__init__.py`: Package marker.
