import streamlit as st
import pandas as pd
from workorders.db import ensure_admin_from_env

from workorders.db import (
    get_connection,
    init_db,
    add_work_order,
    list_work_orders,
    list_work_orders_by_machine,
    close_work_order,
    get_work_order_by_id,
    update_work_order,
    delete_all_work_orders,
    delete_work_orders_by_machine,
    delete_closed_older_than,
    ensure_admin_user,
    authenticate
)

st.set_page_config(page_title="Work Orders", page_icon="🛠️", layout="wide")

st.title("🛠️ Work Orders")
st.caption("SQLite-backed work order tracker")

with st.sidebar:
    st.header("Settings")
    db_path = st.text_input("DB path (optional)", value="")
    if db_path.strip() == "":
        db_path = None

conn = get_connection(db_path)
init_db(conn)

# --- AUTH SETUP ---
# Create a default user the first time you run the app.
# Change these immediately after verifying login works.
ensure_admin_from_env(conn)


if "authed" not in st.session_state:
    st.session_state.authed = False
if "user" not in st.session_state:
    st.session_state.user = None

import time

if "failed_logins" not in st.session_state:
    st.session_state.failed_logins = 0
if "lock_until" not in st.session_state:
    st.session_state.lock_until = 0.0



def login_screen():
    st.markdown(
        """
        <style>
          .login-card {
            max-width: 420px;
            margin: 8vh auto 0 auto;
            padding: 28px 26px;
            border-radius: 18px;
            border: 1px solid rgba(255,255,255,0.12);
            background: rgba(255,255,255,0.04);
            backdrop-filter: blur(8px);
          }
          .login-title {
            font-size: 26px;
            font-weight: 700;
            margin-bottom: 6px;
          }
          .login-sub {
            opacity: 0.8;
            margin-bottom: 18px;
          }
          .tiny {
            opacity: 0.65;
            font-size: 12px;
            margin-top: 12px;
          }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="login-card">', unsafe_allow_html=True)
    st.markdown('<div class="login-title">Sign in</div>', unsafe_allow_html=True)
    st.markdown('<div class="login-sub">Access the Work Orders dashboard</div>', unsafe_allow_html=True)
    now = time.time()
    if now < st.session_state.lock_until:
        secs = int(st.session_state.lock_until - now)
        st.error(f"Too many failed attempts. Try again in {secs}s.")
        st.stop()

    username = st.text_input("Username", placeholder="admin")
    password = st.text_input("Password", type="password", placeholder="••••••••")

    c1, c2 = st.columns([1, 1])
    with c1:
        do_login = st.button("Sign in", type="primary", use_container_width=True)
    with c2:
        st.button("Clear", use_container_width=True, on_click=lambda: None)

    if do_login:
        if authenticate(conn, username.strip(), password):
            st.session_state.authed = True
            st.session_state.user = username.strip()
            st.success("Signed in!")
            st.rerun()
        else:
            st.session_state.failed_logins += 1
            # lockout after 5 fails for 30 seconds
            if st.session_state.failed_logins >= 5:
                st.session_state.lock_until = time.time() + 30
                st.session_state.failed_logins = 0
            st.error("Invalid username or password.")


    
    st.markdown("</div>", unsafe_allow_html=True)


def topbar():
    with st.sidebar:
        st.markdown("---")
        st.write(f"Signed in as **{st.session_state.user}**")
        if st.button("Log out", use_container_width=True):
            st.session_state.authed = False
            st.session_state.user = None
            st.rerun()


# Gate the app
if not st.session_state.authed:
    login_screen()
    st.stop()

topbar()


def rows_to_df(rows) -> pd.DataFrame:
    data = []
    for r in rows:
        data.append(
            {
                "id": int(r["id"]),
                "machine_id": r["machine_id"],
                "priority": r["priority"],
                "status": r["status"],
                "created_at": r["created_at"],
                "closed_at": r["closed_at"],
                "updated_at": r.get("updated_at", None) if hasattr(r, "get") else r["updated_at"],
                "assigned_to": r.get("assigned_to", None) if hasattr(r, "get") else r["assigned_to"],
                "notes": r.get("notes", None) if hasattr(r, "get") else r["notes"],
                "issue": r["issue"],
            }
        )
    df = pd.DataFrame(data)
    if not df.empty:
        df["created_at_dt"] = pd.to_datetime(df["created_at"], utc=True, errors="coerce")
    return df

def apply_text_search(df: pd.DataFrame, query: str) -> pd.DataFrame:
    q = (query or "").strip().lower()
    if df.empty or not q:
        return df
    mask = (
        df["machine_id"].astype(str).str.lower().str.contains(q, na=False)
        | df["issue"].astype(str).str.lower().str.contains(q, na=False)
        | df["assigned_to"].fillna("").astype(str).str.lower().str.contains(q, na=False)
        | df["notes"].fillna("").astype(str).str.lower().str.contains(q, na=False)
    )
    return df[mask].copy()

tab_add, tab_list, tab_history, tab_close, tab_show, tab_insights, tab_clear = st.tabs(
    ["➕ Add", "📋 List + Actions", "🕘 History", "✅ Close", "🔎 Show", "📊 Insights", "🧹 Clear"]
)


# ---------- Add ----------
with tab_add:
    st.subheader("Add a work order")

    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        machine_id = st.text_input("Machine ID", placeholder="KMT-102")
        assigned_to = st.text_input("Assigned to (optional)", placeholder="e.g., Mark")
    with col2:
        issue = st.text_input("Issue", placeholder="Hydraulic leak")
        notes = st.text_area("Notes (optional)", placeholder="Extra context…", height=100)
    with col3:
        priority = st.selectbox("Priority", ["low","med","high"], index=1, key="add_priority")

    if st.button("Add Work Order", type="primary"):
        if not machine_id.strip():
            st.error("Machine ID is required.")
        elif not issue.strip():
            st.error("Issue is required.")
        else:
            new_id = add_work_order(
                conn,
                machine_id.strip(),
                issue.strip(),
                priority,
                assigned_to=assigned_to.strip() if assigned_to.strip() else None,
                notes=notes.strip() if notes.strip() else None,
            )
            st.success(f"Added work order #{new_id}")

# ---------- List + Actions + Details Pane + Export ----------
with tab_list:
    st.subheader("List work orders (search + inline close + details pane + export)")

    c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
    with c1:
        search = st.text_input("Search (machine/issue/assigned/notes)", placeholder="e.g., leak or KMT-102 or Mark")
    with c2:
        status_filter = st.selectbox("Status", ["(all)", "open", "closed"], index=0, key="list_status")
    with c3:
        priority_filter = st.selectbox("Priority", ["(all)", "low", "med", "high"], index=0, key="list_priority")
    with c4:
        st.write("")

    rows = list_work_orders(conn, status=None if status_filter == "(all)" else status_filter)
    df = rows_to_df(rows)

    if not df.empty and priority_filter != "(all)":
        df = df[df["priority"] == priority_filter].copy()

    df = apply_text_search(df, search)

    if df.empty:
        st.info("No work orders match your filters.")
    else:
        left, right = st.columns([2.2, 1.2], gap="large")

        with left:
            st.caption("Select `close_now` for OPEN items, then click Apply closures.")

            display_cols = [
                "id", "machine_id", "priority", "status",
                "assigned_to", "updated_at", "created_at", "closed_at", "issue"
            ]
            display = df[display_cols].copy()
            display["close_now"] = False

            edited = st.data_editor(
                display,
                hide_index=True,
                use_container_width=True,
                column_config={
                    "close_now": st.column_config.CheckboxColumn("close_now"),
                    "id": st.column_config.NumberColumn("id", disabled=True),
                    "machine_id": st.column_config.TextColumn("machine_id", disabled=True),
                    "priority": st.column_config.TextColumn("priority", disabled=True),
                    "status": st.column_config.TextColumn("status", disabled=True),
                    "assigned_to": st.column_config.TextColumn("assigned_to", disabled=True),
                    "updated_at": st.column_config.TextColumn("updated_at", disabled=True),
                    "created_at": st.column_config.TextColumn("created_at", disabled=True),
                    "closed_at": st.column_config.TextColumn("closed_at", disabled=True),
                    "issue": st.column_config.TextColumn("issue", disabled=True),
                },
                key="list_editor",
            )

            col_apply, col_export = st.columns([1, 1])
            with col_apply:
                if st.button("Apply closures", type="primary"):
                    to_close = edited[(edited["close_now"] == True) & (edited["status"] == "open")]["id"].tolist()
                    if not to_close:
                        st.warning("No OPEN work orders selected.")
                    else:
                        closed_ids = []
                        for wid in to_close:
                            if close_work_order(conn, int(wid)) == 1:
                                closed_ids.append(int(wid))
                        if closed_ids:
                            st.success(f"Closed: {closed_ids}")
                            st.rerun()
                        else:
                            st.warning("Nothing was closed (maybe already closed?).")

            with col_export:
                export_df = df.drop(columns=["created_at_dt"], errors="ignore").copy()
                csv_bytes = export_df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    "Export filtered CSV",
                    data=csv_bytes,
                    file_name="work_orders_filtered.csv",
                    mime="text/csv",
                )

        with right:
            st.markdown("### Details")
            st.caption("Pick an ID from the filtered list (acts like click-through).")

            ids = df["id"].tolist()
            selected_id = st.selectbox("Work Order ID", ids)

            row = get_work_order_by_id(conn, int(selected_id))
            if row is None:
                st.info("No work order found.")
            else:
                st.markdown(f"**Machine:** `{row['machine_id']}`")
                st.markdown(f"**Status:** `{row['status']}`")
                st.markdown(f"**Created:** `{row['created_at']}`")
                st.markdown(f"**Closed:** `{row['closed_at'] or '-'}`")
                st.markdown(f"**Updated:** `{row['updated_at'] or '-'}`")

                issue_edit = st.text_input("Issue", value=row["issue"])
                prio_options = ["low", "med", "high"]
                current_prio = row["priority"] if row and row["priority"] in prio_options else "med"
                prio_index = prio_options.index(current_prio)

                priority_edit = st.selectbox(
                    "Priority",
                    prio_options,
                    index=prio_index,
                    key="detail_priority",
                )

                assigned_edit = st.text_input("Assigned to", value=row["assigned_to"] or "")
                notes_edit = st.text_area("Notes", value=row["notes"] or "", height=140)

                col_save, col_close = st.columns(2)
                with col_save:
                    if st.button("Save changes", type="primary"):
                        updated = update_work_order(
                            conn,
                            int(selected_id),
                            issue=issue_edit.strip(),
                            priority=priority_edit,
                            assigned_to=assigned_edit.strip() if assigned_edit.strip() else None,
                            notes=notes_edit.strip() if notes_edit.strip() else None,
                        )
                        if updated:
                            st.success("Saved.")
                            st.rerun()
                        else:
                            st.warning("No changes to save.")

                with col_close:
                    if st.button("Close this order"):
                        upd = close_work_order(conn, int(selected_id))
                        if upd == 1:
                            st.success("Closed.")
                            st.rerun()
                        else:
                            st.warning("Already closed (or not found).")

# ---------- History ----------
with tab_history:
    st.subheader("Machine history")

    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        hist_machine = st.text_input("Machine ID", key="hist_machine", placeholder="KMT-102")
    with col2:
        hist_status_filter = st.selectbox("Status (optional)", ["(all)", "open", "closed"], index=0, key="history_status")
    with col3:
        hist_search = st.text_input("Search within history (optional)", placeholder="e.g., leak, pump, Mark")

    if st.button("Load History"):
        if not hist_machine.strip():
            st.error("Machine ID is required.")
        else:
            hist_status = None if hist_status_filter == "(all)" else hist_status_filter
            rows = list_work_orders_by_machine(conn, hist_machine.strip(), status=hist_status)
            dfh = rows_to_df(rows)
            dfh = apply_text_search(dfh, hist_search)

            if dfh.empty:
                st.info("No work orders found for that machine (with those filters).")
            else:
                st.dataframe(
                    dfh[["id", "priority", "status", "assigned_to", "updated_at", "created_at", "closed_at", "issue"]],
                    use_container_width=True,
                    hide_index=True,
                )

# ---------- Close ----------
with tab_close:
    st.subheader("Close a work order")

    close_id = st.number_input("Work order ID", min_value=1, step=1)

    if st.button("Close Work Order", type="primary"):
        updated = close_work_order(conn, int(close_id))
        if updated == 0:
            st.warning("No open work order with that ID (maybe already closed?).")
        else:
            row = get_work_order_by_id(conn, int(close_id))
            st.success(f"Closed work order #{close_id}")
            if row and row["closed_at"]:
                st.write(f"Closed At: `{row['closed_at']}`")
                st.write(f"Updated At: `{row['updated_at']}`")

# ---------- Show ----------
with tab_show:
    st.subheader("Show one work order")

    show_id = st.number_input("Work order ID", min_value=1, step=1, key="show_id")

    if st.button("Load Work Order"):
        row = get_work_order_by_id(conn, int(show_id))
        if row is None:
            st.info("No work order found with that ID.")
        else:
            st.markdown(f"### Work Order #{row['id']}")
            c1, c2, c3 = st.columns(3)
            c1.metric("Machine", row["machine_id"])
            c2.metric("Priority", row["priority"])
            c3.metric("Status", row["status"])

            st.write(f"**Assigned:** {row['assigned_to'] or '-'}")
            st.write(f"**Created:** {row['created_at']}")
            st.write(f"**Closed:** {row['closed_at'] or '-'}")
            st.write(f"**Updated:** {row['updated_at'] or '-'}")
            st.write("**Issue:**")
            st.write(row["issue"])
            st.write("**Notes:**")
            st.write(row["notes"] or "-")

# ---------- Insights ----------
with tab_insights:
    st.subheader("Insights")

    rows = list_work_orders(conn, status=None)
    df = rows_to_df(rows)

    if df.empty:
        st.info("No data yet—add a few work orders to see charts.")
    else:
        c1, c2 = st.columns(2)

        open_df = df[df["status"] == "open"].copy()
        pr_counts = open_df["priority"].value_counts().reindex(["low", "med", "high"]).fillna(0).astype(int)

        with c1:
            st.caption("Open work orders by priority")
            st.bar_chart(pr_counts)

        with c2:
            st.caption("Work orders created per day")
            day_counts = (
                df.dropna(subset=["created_at_dt"])
                .assign(day=lambda d: d["created_at_dt"].dt.date)
                .groupby("day")["id"]
                .count()
                .sort_index()
            )
            st.line_chart(day_counts)

        st.divider()
        m1, m2, m3 = st.columns(3)
        m1.metric("Total work orders", int(len(df)))
        m2.metric("Open", int((df["status"] == "open").sum()))
        m3.metric("Closed", int((df["status"] == "closed").sum()))

# ---------- Clear ----------
with tab_clear:
    st.subheader("🧹 Clear work orders")
    st.warning("These actions permanently delete data from your SQLite database.")

    st.markdown("### Option 1: Delete by machine")
    machine_to_delete = st.text_input("Machine ID to delete", placeholder="KMT-102", key="clear_machine")

    confirm_machine = st.checkbox("I understand this will permanently delete matching orders.", key="confirm_machine")

    if st.button("Delete machine history", type="primary", disabled=not confirm_machine):
        if not machine_to_delete.strip():
            st.error("Enter a machine ID.")
        else:
            n = delete_work_orders_by_machine(conn, machine_to_delete.strip())
            st.success(f"Deleted {n} work orders for machine {machine_to_delete.strip()}.")
            st.rerun()

    st.divider()

    st.markdown("### Option 2: Delete closed orders older than N days")
    days = st.number_input("Days", min_value=1, step=1, value=30, key="clear_days")
    confirm_old = st.checkbox("I understand this will permanently delete closed orders older than N days.", key="confirm_old")

    if st.button("Delete old closed orders", disabled=not confirm_old):
        n = delete_closed_older_than(conn, int(days))
        st.success(f"Deleted {n} closed work orders older than {int(days)} days.")
        st.rerun()

    st.divider()

    st.markdown("### Option 3: Delete ALL orders (danger)")
    st.error("Danger zone: this removes everything.")
    typed = st.text_input('Type DELETE ALL to confirm', key="confirm_delete_all")

    if st.button("DELETE ALL WORK ORDERS", type="primary", disabled=(typed.strip().upper() != "DELETE ALL")):
        n = delete_all_work_orders(conn)
        st.success(f"Deleted {n} work orders (all data cleared).")
        st.rerun()

