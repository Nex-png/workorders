import streamlit as st

from workorders.db import (
    get_connection,
    init_db,
    add_work_order,
    list_work_orders,
    list_work_orders_by_machine,
    close_work_order,
    get_work_order_by_id,
)

st.set_page_config(page_title="Work Orders", page_icon="🛠️", layout="wide")

st.title("🛠️ Work Orders")
st.caption("SQLite-backed work order tracker")

# Sidebar DB path (optional)
with st.sidebar:
    st.header("Settings")
    db_path = st.text_input("DB path (optional)", value="")
    if db_path.strip() == "":
        db_path = None

conn = get_connection(db_path)
init_db(conn)

tab_add, tab_list, tab_history, tab_close, tab_show = st.tabs(
    ["➕ Add", "📋 List", "🕘 History", "✅ Close", "🔎 Show"]
)

with tab_add:
    st.subheader("Add a work order")

    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        machine_id = st.text_input("Machine ID", placeholder="KMT-102")
    with col2:
        issue = st.text_input("Issue", placeholder="Hydraulic leak")
    with col3:
        priority = st.selectbox("Priority", ["low", "med", "high"], index=1)

    if st.button("Add Work Order", type="primary"):
        if not machine_id.strip():
            st.error("Machine ID is required.")
        elif not issue.strip():
            st.error("Issue is required.")
        else:
            new_id = add_work_order(conn, machine_id.strip(), issue.strip(), priority)
            st.success(f"Added work order #{new_id}")

with tab_list:
    st.subheader("List work orders")

    col1, col2 = st.columns([1, 2])
    with col1:
        status_filter = st.selectbox("Status filter", ["(all)", "open", "closed"], index=0)
    with col2:
        st.write("")

    status = None if status_filter == "(all)" else status_filter
    rows = list_work_orders(conn, status=status)

    if not rows:
        st.info("No work orders found.")
    else:
        # Turn rows into a display-friendly table
        data = []
        for r in rows:
            data.append(
                {
                    "id": r["id"],
                    "machine_id": r["machine_id"],
                    "priority": r["priority"],
                    "status": r["status"],
                    "created_at": r["created_at"],
                    "closed_at": r["closed_at"],
                    "issue": r["issue"],
                }
            )
        st.dataframe(data, use_container_width=True, hide_index=True)

with tab_history:
    st.subheader("Machine history")

    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        hist_machine = st.text_input("Machine ID", key="hist_machine", placeholder="KMT-102")
    with col2:
        hist_status_filter = st.selectbox("Status (optional)", ["(all)", "open", "closed"], index=0, key="hist_status")
    with col3:
        st.write("")

    if st.button("Load History"):
        if not hist_machine.strip():
            st.error("Machine ID is required.")
        else:
            hist_status = None if hist_status_filter == "(all)" else hist_status_filter
            rows = list_work_orders_by_machine(conn, hist_machine.strip(), status=hist_status)
            if not rows:
                st.info("No work orders found for that machine.")
            else:
                data = []
                for r in rows:
                    data.append(
                        {
                            "id": r["id"],
                            "priority": r["priority"],
                            "status": r["status"],
                            "created_at": r["created_at"],
                            "closed_at": r["closed_at"],
                            "issue": r["issue"],
                        }
                    )
                st.dataframe(data, use_container_width=True, hide_index=True)

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

            st.write(f"**Created:** {row['created_at']}")
            st.write(f"**Closed:** {row['closed_at'] or '-'}")
            st.write("**Issue:**")
            st.write(row["issue"])
