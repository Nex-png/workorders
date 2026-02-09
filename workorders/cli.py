from __future__ import annotations

import argparse
import sys

from .db import get_connection, init_db, add_work_order, list_work_orders, close_work_order, list_work_orders_by_machine,get_work_order_by_id

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog = "workorders",
        description="Simple Work Order CLI.",

    )

    parser.add_argument(
        "--db",
        default=None,
        help="Path to the SQLite DB file (default: ./workorders.db)",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    p_add = subparsers.add_parser("add", help="Add aa new work order")
    p_add.add_argument("--machine-id",required=True,help="Machine identifier (e.g., KMT-102)")
    p_add.add_argument("--issue", required=True, help="Issue description")
    p_add.add_argument("--Priority", choices=["low", "med", "high"], default="med", help="Priority level",)


    #list
    p_list = subparsers.add_parser("list", help="List work order")
    p_list.add_argument(
    "--status",
    choices=["open", "closed"],
    default=None,
    help="Filter by status",
    )
    
    
    p_close = subparsers.add_parser("close", help="Close a work order by id")
    p_close.add_argument("--id", type=int, required=True, help="Work order id")

    # history
    p_hist = subparsers.add_parser("history", help="Show work order history for a machine")
    p_hist.add_argument("--machine-id", required=True, help="Machine identifier (e.g., KMT-102)")
    p_hist.add_argument(
    "--status",
    choices=["open", "closed"],
    default=None,
    help="Optional status filter",
    )

    # show
    p_show = subparsers.add_parser("show", help="Show a work order by id")
    p_show.add_argument("--id", type=int, required=True, help="Work order id")



    return parser


def cmd_add(args: argparse.Namespace) -> int:
    conn = get_connection(args.db)
    init_db(conn)

    new_id = add_work_order(conn, machine_id=args.machine_id, issue=args.issue, priority=args.Priority)
    print(f"✅Added work order #{new_id}")
    return 0

def cmd_list(args: argparse.Namespace) -> int:
    conn = get_connection(args.db)
    init_db(conn)

    rows = list_work_orders(conn, status=args.status)

    if not rows:
        print("(no work orders found)")
        return 0

    print(f"{'ID':>4}  {'MACHINE':<10}  {'PRIO':<4}  {'STATUS':<6}  ISSUE")
    print("-" * 70)

    for r in rows:
        issue = r["issue"]
        if len(issue) > 45:
            issue = issue[:42] + "..."
        print(f"{r['id']:>4}  {r['machine_id']:<10}  {r['priority']:<4}  {r['status']:<6}  {issue}")

    return 0

    


def cmd_close(args: argparse.Namespace) -> int:
    conn = get_connection(args.db)
    init_db(conn)

    updated = close_work_order(conn, args.id)
    if updated == 0:
        print(f"⚠️ No open work order with id {args.id} (maybe already closed?)")
        return 1
    
    print(f"✅ Closed work order #{args.id}")
    return 0



def cmd_history(args: argparse.Namespace) -> int:
    conn = get_connection(args.db)
    init_db(conn)

    rows = list_work_orders_by_machine(conn, machine_id=args.machine_id, status=args.status)

    if not rows:
        status_note = f" with status={args.status}" if args.status else ""
        print(f"(no work orders found for machine {args.machine_id}{status_note})")
        return 0

    print(f"History for machine: {args.machine_id}")
    print(f"{'ID':>4}  {'PRIO':<4}  {'STATUS':<6}  {'CREATED':<20}  ISSUE")
    print("-" * 80)

    for r in rows:
        issue = r["issue"]
        if len(issue) > 40:
            issue = issue[:37] + "..."
        print(f"{r['id']:>4}  {r['priority']:<4}  {r['status']:<6}  {r['created_at']:<20}  {issue}")

    return 0


def cmd_show(args: argparse.Namespace) -> int:
    conn = get_connection(args.db)
    init_db(conn)

    row = get_work_order_by_id(conn, args.id)
    if row is None:
        print(f"(no work order found with id {args.id})")
        return 1

    print(f"Work Order #{row['id']}")
    print(f"Machine ID : {row['machine_id']}")
    print(f"Priority   : {row['priority']}")
    print(f"Status     : {row['status']}")
    print(f"Created At : {row['created_at']}")
    print(f"Closed At  : {row['closed_at'] or '-'}")
    print(f"Issue      : {row['issue']}")
    return 0



def main(argv: list[str]| None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "add":
        code = cmd_add(args)
    elif args.command == "list":
        code = cmd_list(args)
    elif args.command == "close":
        code = cmd_close(args)
    elif args.command == "history":
        code = cmd_history(args)
    elif args.command == "show":
        code = cmd_show(args)
    else:
        parser.error("unknown command")
        return
    
    raise SystemExit(code)


