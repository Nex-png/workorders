import time
import streamlit as st
import pandas as pd
from workorders.db import ensure_admin_from_env
from workorders.db import (
    get_connection, init_db,
    add_work_order, list_work_orders, list_work_orders_by_machine,
    close_work_order, get_work_order_by_id, update_work_order,
    delete_all_work_orders, delete_work_orders_by_machine, delete_closed_older_than,
    ensure_admin_user, authenticate,
)

st.set_page_config(
    page_title="Work Orders",
    page_icon=":hammer_and_wrench:",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
#  GLOBAL CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
/* ── Palette ─────────────────────────────── */
:root {
  --bg:            #07070f;
  --surface:       #0e0e1c;
  --surface-2:     #13131f;
  --accent:        #6366f1;
  --accent-light:  #818cf8;
  --accent-glow:   rgba(99,102,241,0.18);
  --accent-border: rgba(99,102,241,0.28);
  --border:        rgba(255,255,255,0.07);
  --border-hover:  rgba(255,255,255,0.13);
  --text:          #f1f5f9;
  --text-muted:    rgba(241,245,249,0.45);
  --success:       #10b981;
  --warning:       #f59e0b;
  --danger:        #ef4444;
  --radius-lg:     20px;
  --radius-md:     14px;
  --radius-sm:     8px;
}

/* ── Reset & base ────────────────────────── */
html, body, [class*="css"] {
  font-feature-settings: "ss01" 1, "ss02" 1;
  -webkit-font-smoothing: antialiased;
}
.block-container {
  padding-top: 1.8rem !important;
  padding-bottom: 3rem !important;
  max-width: 1280px !important;
}
#MainMenu { visibility: hidden; }
footer    { visibility: hidden; }

/* ── App background ──────────────────────── */
.stApp {
  background:
    radial-gradient(ellipse 900px 600px at 8% -5%,  rgba(99,102,241,0.10), transparent 60%),
    radial-gradient(ellipse 700px 500px at 92% 5%,  rgba(139,92,246,0.07), transparent 60%),
    radial-gradient(ellipse 600px 800px at 50% 100%, rgba(99,102,241,0.04), transparent 60%),
    var(--bg);
}

/* ── Sidebar ─────────────────────────────── */
[data-testid="stSidebar"] {
  background: var(--surface) !important;
  border-right: 1px solid var(--border) !important;
}
[data-testid="stSidebar"] > div:first-child {
  padding-top: 1.5rem;
}

/* ── Cards ───────────────────────────────── */
.ix-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 22px 24px;
  margin-bottom: 4px;
}
.ix-card-accent {
  background: linear-gradient(135deg, rgba(99,102,241,0.10) 0%, rgba(139,92,246,0.06) 100%);
  border: 1px solid var(--accent-border);
  border-radius: var(--radius-lg);
  padding: 22px 24px;
}
.ix-card-success {
  background: rgba(16,185,129,0.08);
  border: 1px solid rgba(16,185,129,0.25);
  border-radius: var(--radius-lg);
  padding: 22px 24px;
}

/* ── Typography ──────────────────────────── */
.ix-app-title {
  font-size: 26px;
  font-weight: 760;
  letter-spacing: -0.03em;
  background: linear-gradient(135deg, #fff 30%, var(--accent-light) 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin: 0 0 3px 0;
  line-height: 1.1;
}
.ix-app-sub {
  color: var(--text-muted);
  font-size: 13px;
  margin: 0;
}
.ix-section-title {
  font-size: 15px;
  font-weight: 640;
  letter-spacing: -0.01em;
  color: var(--text);
  margin: 0 0 14px 0;
}
.ix-label {
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text-muted);
  margin-bottom: 6px;
}
.ix-meta {
  font-size: 12px;
  color: var(--text-muted);
  line-height: 1.7;
}
.ix-hint {
  font-size: 11px;
  color: var(--text-muted);
  margin-top: 4px;
  font-style: italic;
}

/* ── Sidebar user card ───────────────────── */
.ix-sidebar-user {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 14px;
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  margin-bottom: 12px;
}
.ix-avatar {
  width: 32px; height: 32px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--accent), var(--accent-light));
  display: flex; align-items: center; justify-content: center;
  font-size: 13px; font-weight: 700; color: #fff;
  flex-shrink: 0;
}
.ix-sidebar-name  { font-size: 13px; font-weight: 600; color: var(--text); }
.ix-sidebar-role  { font-size: 11px; color: var(--text-muted); }
.ix-sidebar-section {
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--text-muted);
  padding: 14px 0 6px 0;
}

/* ── Sidebar service buttons ─────────────── */
.ix-service-btn {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  margin-bottom: 6px;
  cursor: not-allowed;
  opacity: 0.65;
}
.ix-service-icon { font-size: 16px; flex-shrink: 0; }
.ix-service-name { font-size: 13px; font-weight: 500; color: var(--text); flex: 1; }
.ix-service-soon {
  font-size: 9px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--accent-light);
  background: var(--accent-glow);
  border: 1px solid var(--accent-border);
  border-radius: 99px;
  padding: 2px 6px;
}

/* ── Buttons ─────────────────────────────── */
.stButton > button {
  border-radius: var(--radius-md) !important;
  border: 1px solid var(--border) !important;
  background: var(--surface-2) !important;
  color: var(--text) !important;
  font-size: 13px !important;
  font-weight: 500 !important;
  padding: 8px 16px !important;
  transition: all 180ms ease !important;
  letter-spacing: -0.01em !important;
}
.stButton > button:hover {
  border-color: var(--border-hover) !important;
  background: rgba(255,255,255,0.07) !important;
  transform: translateY(-1px) !important;
}
[data-testid="stBaseButton-primary"] > button,
button[kind="primary"],
.stButton > button[kind="primary"] {
  background: linear-gradient(135deg, var(--accent) 0%, #7c3aed 100%) !important;
  border: 1px solid transparent !important;
  color: #fff !important;
  font-weight: 600 !important;
  box-shadow: 0 4px 20px rgba(99,102,241,0.35) !important;
}
[data-testid="stBaseButton-primary"] > button:hover,
button[kind="primary"]:hover {
  opacity: 0.90 !important;
  transform: translateY(-1px) !important;
  box-shadow: 0 6px 28px rgba(99,102,241,0.45) !important;
}

/* ── Inputs ──────────────────────────────── */
.stTextInput > div > div > input,
.stNumberInput > div > div > input,
.stTextArea > div > div > textarea {
  background: var(--surface-2) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--radius-md) !important;
  color: var(--text) !important;
  font-size: 14px !important;
  transition: border-color 150ms ease !important;
}
.stTextInput > div > div > input:focus,
.stNumberInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
  border-color: var(--accent) !important;
  box-shadow: 0 0 0 3px var(--accent-glow) !important;
}
.stSelectbox > div > div {
  background: var(--surface-2) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--radius-md) !important;
}

/* ── Hide type markers / input instructions ── */
/* "Press / to search", keyboard hints, etc.   */
[data-testid="InputInstructions"] { display: none !important; }
.stSelectbox  small { display: none !important; }
.stTextInput  small { display: none !important; }
.stTextArea   small { display: none !important; }
.stNumberInput small { display: none !important; }

/* ── Tabs ────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
  gap: 4px !important;
  background: var(--surface) !important;
  border-radius: var(--radius-lg) !important;
  padding: 5px !important;
  border: 1px solid var(--border) !important;
  width: fit-content !important;
  margin-bottom: 20px !important;
}
.stTabs [data-baseweb="tab"] {
  border-radius: var(--radius-md) !important;
  padding: 7px 18px !important;
  font-size: 13px !important;
  font-weight: 500 !important;
  color: var(--text-muted) !important;
  background: transparent !important;
  border: none !important;
  transition: all 150ms ease !important;
}
.stTabs [data-baseweb="tab"]:hover {
  color: var(--text) !important;
  background: rgba(255,255,255,0.05) !important;
}
.stTabs [aria-selected="true"] {
  background: linear-gradient(135deg, var(--accent) 0%, #7c3aed 100%) !important;
  color: #fff !important;
  font-weight: 600 !important;
  box-shadow: 0 2px 12px rgba(99,102,241,0.4) !important;
}
.stTabs [data-baseweb="tab-highlight"] { display: none !important; }
.stTabs [data-baseweb="tab-border"]    { display: none !important; }

/* ── Dataframe ───────────────────────────── */
[data-testid="stDataFrame"],
[data-testid="stDataEditor"] {
  border-radius: var(--radius-lg) !important;
  overflow: hidden !important;
  border: 1px solid var(--border) !important;
}

/* ── Metrics ─────────────────────────────── */
[data-testid="stMetric"] {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 14px 18px !important;
}
[data-testid="stMetricValue"] {
  font-size: 28px !important;
  font-weight: 720 !important;
  letter-spacing: -0.03em !important;
}

/* ── Alerts ──────────────────────────────── */
.stSuccess > div, .stInfo > div,
.stWarning > div, .stError > div {
  border-radius: var(--radius-md) !important;
}

/* ── Dividers ────────────────────────────── */
hr, [data-testid="stDivider"] { border-color: var(--border) !important; }

/* ── Badges ──────────────────────────────── */
.ix-badge {
  display: inline-flex; align-items: center;
  padding: 3px 10px;
  border-radius: 99px;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}
.ix-badge-open   { background: rgba(99,102,241,0.18); color: var(--accent-light); border: 1px solid var(--accent-border); }
.ix-badge-closed { background: rgba(16,185,129,0.15); color: #34d399;             border: 1px solid rgba(16,185,129,0.28); }
.ix-badge-high   { background: rgba(239,68,68,0.15);  color: #f87171;             border: 1px solid rgba(239,68,68,0.28); }
.ix-badge-med    { background: rgba(245,158,11,0.15); color: #fbbf24;             border: 1px solid rgba(245,158,11,0.28); }
.ix-badge-low    { background: rgba(148,163,184,0.12);color: #94a3b8;             border: 1px solid rgba(148,163,184,0.2); }

/* ── Expander ────────────────────────────── */
[data-testid="stExpander"] {
  background: var(--surface-2) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--radius-md) !important;
}

/* ── Login ───────────────────────────────── */
.ix-login-wrap {
  max-width: 420px;
  margin: 12vh auto 0 auto;
  background: rgba(14,14,28,0.90);
  border: 1px solid var(--accent-border);
  border-radius: 28px;
  padding: 44px 40px 40px;
  backdrop-filter: blur(24px);
  box-shadow: 0 0 100px rgba(99,102,241,0.10), 0 32px 64px rgba(0,0,0,0.45);
}
.ix-login-mark {
  width: 46px; height: 46px;
  background: linear-gradient(135deg, var(--accent) 0%, #7c3aed 100%);
  border-radius: 13px;
  display: inline-flex; align-items: center; justify-content: center;
  font-size: 22px;
  margin-bottom: 18px;
  box-shadow: 0 8px 24px rgba(99,102,241,0.4);
}
.ix-login-title {
  font-size: 26px;
  font-weight: 760;
  letter-spacing: -0.03em;
  background: linear-gradient(135deg, #fff 30%, #818cf8 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin: 0 0 6px 0;
  line-height: 1.15;
}
.ix-login-sub {
  font-size: 14px;
  color: var(--text-muted);
  margin: 0 0 28px 0;
}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
#  DB + SESSION BOOTSTRAP
# ─────────────────────────────────────────────
db_path = None
conn = get_connection(db_path)
init_db(conn)
ensure_admin_from_env(conn)

for k, v in [("authed", False), ("user", None), ("failed_logins", 0), ("lock_until", 0.0),
             ("last_created_id", None), ("selected_order_id", None)]:
    if k not in st.session_state:
        st.session_state[k] = v


# ─────────────────────────────────────────────
#  LOGIN SCREEN
# ─────────────────────────────────────────────
def login_screen():
    st.markdown("""
    <style>
      [data-testid="stSidebar"], header { display: none !important; }
      .block-container { padding-top: 0 !important; max-width: 520px !important; }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="ix-login-wrap">
      <div class="ix-login-mark">🔧</div>
      <div class="ix-login-title">Sign in</div>
      <div class="ix-login-sub">Access your Work Orders dashboard</div>
    </div>
    """, unsafe_allow_html=True)

    st.write("")
    now = time.time()
    if now < st.session_state.lock_until:
        secs = int(st.session_state.lock_until - now)
        st.error(f"Too many failed attempts — try again in {secs}s.")
        st.stop()

    username = st.text_input("Username", placeholder="admin")
    password = st.text_input("Password", type="password", placeholder="••••••••")
    st.write("")
    do_login = st.button("Sign in →", type="primary", use_container_width=True)

    if do_login:
        if authenticate(conn, username.strip(), password):
            st.session_state.authed = True
            st.session_state.user   = username.strip()
            st.rerun()
        else:
            st.session_state.failed_logins += 1
            if st.session_state.failed_logins >= 5:
                st.session_state.lock_until    = time.time() + 30
                st.session_state.failed_logins = 0
            st.error("Invalid username or password.")


if not st.session_state.authed:
    login_screen()
    st.stop()


# ─────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────
def rows_to_df(rows) -> pd.DataFrame:
    data = []
    for r in rows:
        data.append({
            "id":          int(r["id"]),
            "machine_id":  r["machine_id"],
            "priority":    r["priority"],
            "status":      r["status"],
            "created_at":  r["created_at"],
            "closed_at":   r["closed_at"],
            "updated_at":  r["updated_at"] if "updated_at" in r.keys() else None,
            "assigned_to": r["assigned_to"] if "assigned_to" in r.keys() else None,
            "notes":       r["notes"]       if "notes"       in r.keys() else None,
            "issue":       r["issue"],
        })
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


def badge(value: str, kind: str) -> str:
    return f'<span class="ix-badge ix-badge-{kind}">{value}</span>'


def get_recent_machines(limit: int = 8) -> list:
    """Return the most recently used machine IDs."""
    rows = list_work_orders(conn, status=None)
    seen = []
    for r in rows:
        mid = r["machine_id"]
        if mid not in seen:
            seen.append(mid)
        if len(seen) >= limit:
            break
    return seen


# ─────────────────────────────────────────────
#  SIDEBAR (authenticated)
# ─────────────────────────────────────────────
with st.sidebar:
    uname   = st.session_state.user or "user"
    initial = uname[0].upper()

    # User card
    st.markdown(f"""
    <div style="padding: 0 4px;">
      <div style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.08em;
                  color:var(--text-muted);padding:4px 0 12px 0;">Work Orders</div>
      <div class="ix-sidebar-user">
        <div class="ix-avatar">{initial}</div>
        <div>
          <div class="ix-sidebar-name">{uname}</div>
          <div class="ix-sidebar-role">Operator</div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Live stats
    open_count_sb   = len(list_work_orders(conn, status="open"))
    closed_count_sb = len(list_work_orders(conn, status="closed"))
    st.markdown(f"""
    <div style="display:flex;gap:8px;margin-bottom:4px;">
      <div style="flex:1;text-align:center;padding:10px 6px;background:rgba(99,102,241,0.10);
                  border:1px solid var(--accent-border);border-radius:12px;">
        <div style="font-size:20px;font-weight:720;color:var(--accent-light);">{open_count_sb}</div>
        <div style="font-size:10px;color:var(--text-muted);text-transform:uppercase;letter-spacing:.06em;">Open</div>
      </div>
      <div style="flex:1;text-align:center;padding:10px 6px;background:rgba(16,185,129,0.08);
                  border:1px solid rgba(16,185,129,0.22);border-radius:12px;">
        <div style="font-size:20px;font-weight:720;color:#34d399;">{closed_count_sb}</div>
        <div style="font-size:10px;color:var(--text-muted);text-transform:uppercase;letter-spacing:.06em;">Closed</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Quick actions
    st.markdown('<div class="ix-sidebar-section">Quick actions</div>', unsafe_allow_html=True)
    if st.button("⟳  Refresh", use_container_width=True):
        st.rerun()

    # ── Future services ────────────────────────
    st.markdown('<div class="ix-sidebar-section">Services</div>', unsafe_allow_html=True)
    st.markdown("""
    <div class="ix-service-btn">
      <div class="ix-service-icon">🗓</div>
      <div class="ix-service-name">Maintenance Calendar</div>
      <div class="ix-service-soon">Soon</div>
    </div>
    <div class="ix-service-btn">
      <div class="ix-service-icon">📦</div>
      <div class="ix-service-name">Parts & Inventory</div>
      <div class="ix-service-soon">Soon</div>
    </div>
    <div class="ix-service-btn">
      <div class="ix-service-icon">👥</div>
      <div class="ix-service-name">Team Management</div>
      <div class="ix-service-soon">Soon</div>
    </div>
    <div class="ix-service-btn">
      <div class="ix-service-icon">🔔</div>
      <div class="ix-service-name">Alerts & Notifications</div>
      <div class="ix-service-soon">Soon</div>
    </div>
    <div class="ix-service-btn">
      <div class="ix-service-icon">📈</div>
      <div class="ix-service-name">Advanced Reports</div>
      <div class="ix-service-soon">Soon</div>
    </div>
    <div class="ix-service-btn">
      <div class="ix-service-icon">⚙️</div>
      <div class="ix-service-name">Settings</div>
      <div class="ix-service-soon">Soon</div>
    </div>
    """, unsafe_allow_html=True)

    # Sign out
    st.markdown('<div class="ix-sidebar-section">Session</div>', unsafe_allow_html=True)
    if st.button("Sign out", use_container_width=True):
        st.session_state.authed = False
        st.session_state.user   = None
        st.rerun()


# ─────────────────────────────────────────────
#  HEADER
# ─────────────────────────────────────────────
open_count   = len(list_work_orders(conn, status="open"))
closed_count = len(list_work_orders(conn, status="closed"))

st.markdown(f"""
<div class="ix-card-accent" style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px;">
  <div>
    <div class="ix-app-title">🔧 Work Orders</div>
    <div class="ix-app-sub">Equipment issue tracking — fast &amp; minimal</div>
  </div>
  <div style="display:flex;gap:10px;flex-wrap:wrap;">
    <div style="text-align:center;padding:10px 18px;background:rgba(99,102,241,0.12);border:1px solid var(--accent-border);border-radius:14px;">
      <div style="font-size:22px;font-weight:720;letter-spacing:-0.03em;color:var(--accent-light);">{open_count}</div>
      <div style="font-size:11px;color:var(--text-muted);text-transform:uppercase;letter-spacing:.06em;">Open</div>
    </div>
    <div style="text-align:center;padding:10px 18px;background:rgba(16,185,129,0.10);border:1px solid rgba(16,185,129,0.22);border-radius:14px;">
      <div style="font-size:22px;font-weight:720;letter-spacing:-0.03em;color:#34d399;">{closed_count}</div>
      <div style="font-size:11px;color:var(--text-muted);text-transform:uppercase;letter-spacing:.06em;">Closed</div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)
st.write("")


# ─────────────────────────────────────────────
#  TABS  (5 focused views, down from 7)
# ─────────────────────────────────────────────
tab_add, tab_orders, tab_history, tab_insights, tab_manage = st.tabs(
    ["＋  New Order", "📋  Orders", "🔍  History", "📊  Insights", "⚙  Manage"]
)


# ══════════════════════════════════════════════
#  NEW ORDER
# ══════════════════════════════════════════════
with tab_add:
    st.markdown('<div class="ix-section-title">Create a new work order</div>', unsafe_allow_html=True)

    recent_machines = get_recent_machines()

    col_form, col_tip = st.columns([2, 1], gap="large")

    with col_form:
        with st.container():
            c1, c2 = st.columns(2, gap="medium")

            with c1:
                st.markdown('<div class="ix-label">Equipment ID <span style="color:#f87171;">*</span></div>', unsafe_allow_html=True)
                machine_id = st.text_input("Machine ID", placeholder="e.g. KMT-102",
                                           label_visibility="collapsed", key="add_machine")
                if recent_machines:
                    st.markdown('<div class="ix-hint">Recent: ' +
                                " · ".join(f"<code style='font-size:11px;'>{m}</code>" for m in recent_machines[:4]) +
                                '</div>', unsafe_allow_html=True)

            with c2:
                st.markdown('<div class="ix-label">Assigned to</div>', unsafe_allow_html=True)
                assigned_to = st.text_input("Assigned to", placeholder="e.g. Mark",
                                            label_visibility="collapsed", key="add_assigned")

            st.write("")
            st.markdown('<div class="ix-label">Issue description <span style="color:#f87171;">*</span></div>', unsafe_allow_html=True)
            issue = st.text_input("Issue", placeholder="Describe the problem briefly — e.g. Hydraulic leak on left cylinder",
                                  label_visibility="collapsed", key="add_issue")

            st.write("")
            nc1, nc2 = st.columns([1, 2], gap="medium")
            with nc1:
                st.markdown('<div class="ix-label">Priority</div>', unsafe_allow_html=True)
                priority = st.selectbox("Priority", ["low", "med", "high"], index=1,
                                        key="add_priority", label_visibility="collapsed")
            with nc2:
                st.markdown('<div class="ix-label">Notes (optional)</div>', unsafe_allow_html=True)
                notes = st.text_area("Notes", placeholder="Any additional context or steps taken…",
                                     height=80, label_visibility="collapsed", key="add_notes")

            st.write("")
            btn_col, _ = st.columns([1, 2])
            with btn_col:
                submit = st.button("Create work order →", type="primary", use_container_width=True)

    with col_tip:
        st.markdown("""
        <div class="ix-card" style="margin-top:2px;">
          <div class="ix-label">Tips</div>
          <div class="ix-meta" style="margin-top:8px;">
            <b style="color:var(--text);">Equipment ID</b><br>
            Use a consistent naming format like <code>KMT-102</code> so history searches stay accurate.<br><br>
            <b style="color:var(--text);">Priority</b><br>
            <span style="color:#f87171;">High</span> — production stopped or safety risk<br>
            <span style="color:#fbbf24;">Med</span> — degraded but running<br>
            <span style="color:#94a3b8;">Low</span> — cosmetic or minor issue<br><br>
            <b style="color:var(--text);">Assigned to</b><br>
            First name is fine. Leave blank if unassigned.
          </div>
        </div>
        """, unsafe_allow_html=True)

    # Handle submission
    if submit:
        if not machine_id.strip():
            st.error("Equipment ID is required.")
        elif not issue.strip():
            st.error("Issue description is required.")
        else:
            new_id = add_work_order(
                conn, machine_id.strip(), issue.strip(), priority,
                assigned_to=assigned_to.strip() or None,
                notes=notes.strip() or None,
            )
            st.session_state.last_created_id = new_id
            st.rerun()

    # Success confirmation card
    if st.session_state.last_created_id:
        row = get_work_order_by_id(conn, st.session_state.last_created_id)
        if row:
            st.markdown(f"""
            <div class="ix-card-success" style="margin-top:16px;">
              <div style="font-size:13px;font-weight:700;color:#34d399;margin-bottom:8px;">
                ✓ Work order #{row['id']} created
              </div>
              <div class="ix-meta">
                <b>Machine</b> &nbsp;{row['machine_id']}&nbsp;&nbsp;
                <b>Priority</b> &nbsp;{row['priority']}&nbsp;&nbsp;
                <b>Assigned</b> &nbsp;{row['assigned_to'] or '—'}
              </div>
              <div class="ix-meta" style="margin-top:6px;">{row['issue']}</div>
            </div>
            """, unsafe_allow_html=True)
            c_new, c_dismiss = st.columns([1, 1])
            with c_new:
                if st.button("＋ Create another", use_container_width=True):
                    st.session_state.last_created_id = None
                    st.rerun()
            with c_dismiss:
                if st.button("View in Orders →", type="primary", use_container_width=True):
                    st.session_state.last_created_id    = None
                    st.session_state.selected_order_id  = int(row['id'])
                    st.rerun()


# ══════════════════════════════════════════════
#  ORDERS (List + inline details + close)
# ══════════════════════════════════════════════
with tab_orders:
    st.markdown('<div class="ix-section-title">All work orders</div>', unsafe_allow_html=True)

    # ── Live filter bar ──────────────────────
    st.markdown('<div class="ix-card" style="padding:16px 20px;">', unsafe_allow_html=True)
    fc1, fc2, fc3 = st.columns([3, 1, 1])
    with fc1:
        search = st.text_input("Search", placeholder="🔍  Machine, issue, person, notes…",
                               label_visibility="collapsed", key="orders_search")
    with fc2:
        status_filter = st.selectbox("Status", ["All", "Open only", "Closed only"],
                                     index=1, key="orders_status", label_visibility="collapsed")
    with fc3:
        priority_filter = st.selectbox("Priority", ["All priorities", "high", "med", "low"],
                                       index=0, key="orders_priority", label_visibility="collapsed")
    st.markdown('</div>', unsafe_allow_html=True)
    st.write("")

    # ── Fetch + filter ───────────────────────
    status_map = {"All": None, "Open only": "open", "Closed only": "closed"}
    rows = list_work_orders(conn, status=status_map[status_filter])
    df   = rows_to_df(rows)

    if not df.empty and priority_filter != "All priorities":
        df = df[df["priority"] == priority_filter].copy()
    df = apply_text_search(df, search)

    if df.empty:
        st.info("No work orders match your filters.")
    else:
        left_col, right_col = st.columns([2.2, 1.3], gap="large")

        with left_col:
            st.markdown('<div class="ix-card" style="padding:14px 16px;">', unsafe_allow_html=True)
            st.caption(f"{len(df)} order{'s' if len(df) != 1 else ''} — tick ☑ Close? then hit Apply Closures")

            display_cols = ["id", "machine_id", "priority", "status", "assigned_to", "issue", "created_at"]
            display = df[display_cols].copy()
            display["close_now"] = False

            edited = st.data_editor(
                display, hide_index=True, use_container_width=True,
                column_config={
                    "close_now":   st.column_config.CheckboxColumn("Close?", width="small"),
                    "id":          st.column_config.NumberColumn("ID",       disabled=True, width="small"),
                    "machine_id":  st.column_config.TextColumn("Machine",    disabled=True),
                    "priority":    st.column_config.TextColumn("Priority",   disabled=True, width="small"),
                    "status":      st.column_config.TextColumn("Status",     disabled=True, width="small"),
                    "assigned_to": st.column_config.TextColumn("Assigned",   disabled=True),
                    "issue":       st.column_config.TextColumn("Issue",      disabled=True),
                    "created_at":  st.column_config.TextColumn("Created",    disabled=True),
                },
                key="orders_editor",
            )
            st.markdown('</div>', unsafe_allow_html=True)
            st.write("")

            act1, act2, act3 = st.columns(3)
            with act1:
                if st.button("✓ Apply Closures", type="primary", use_container_width=True):
                    to_close = edited[(edited["close_now"] == True) & (edited["status"] == "open")]["id"].tolist()
                    if not to_close:
                        st.warning("No open orders ticked for closure.")
                    else:
                        closed_ids = [int(wid) for wid in to_close if close_work_order(conn, int(wid)) == 1]
                        if closed_ids:
                            st.success(f"Closed: {closed_ids}")
                            st.rerun()
                        else:
                            st.warning("Nothing was closed (already closed?).")
            with act2:
                export_df = df.drop(columns=["created_at_dt"], errors="ignore").copy()
                st.download_button(
                    "↓ Export CSV",
                    data=export_df.to_csv(index=False).encode("utf-8"),
                    file_name="work_orders.csv", mime="text/csv",
                    use_container_width=True,
                )
            with act3:
                if st.button("⟳ Refresh", use_container_width=True):
                    st.rerun()

        with right_col:
            st.markdown('<div class="ix-card">', unsafe_allow_html=True)
            st.markdown('<div class="ix-section-title">Order detail</div>', unsafe_allow_html=True)

            ids         = df["id"].tolist()
            default_idx = 0
            if st.session_state.selected_order_id and st.session_state.selected_order_id in ids:
                default_idx = ids.index(st.session_state.selected_order_id)

            selected_id = st.selectbox(
                "Select order", ids, index=default_idx,
                format_func=lambda i: f"#{i} — {df[df['id']==i]['machine_id'].values[0]}",
                label_visibility="collapsed", key="orders_select"
            )
            st.session_state.selected_order_id = selected_id

            row = get_work_order_by_id(conn, int(selected_id))
            if row is None:
                st.info("Not found.")
            else:
                prio = row["priority"]
                stat = row["status"]
                st.markdown(
                    f'{badge(stat, stat)}&nbsp;&nbsp;{badge(prio, prio)}',
                    unsafe_allow_html=True,
                )
                st.markdown(f"""
                <div class="ix-meta" style="margin-top:10px;">
                  <b>Machine</b>&nbsp;&nbsp;{row['machine_id']}<br>
                  <b>Created</b>&nbsp;&nbsp;{row['created_at']}<br>
                  <b>Updated</b>&nbsp;&nbsp;{row['updated_at'] or '—'}<br>
                  <b>Closed</b>&nbsp;&nbsp;&nbsp;{row['closed_at'] or '—'}
                </div>
                """, unsafe_allow_html=True)
                st.write("")

                prio_options  = ["low", "med", "high"]
                # Keys are scoped to selected_id so edits persist while the same
                # order is open, but reset cleanly when switching to another order.
                _k = selected_id
                issue_edit    = st.text_input("Issue",       value=row["issue"],             key=f"det_issue_{_k}")
                priority_edit = st.selectbox("Priority",     prio_options,
                                             index=prio_options.index(prio),                 key=f"det_prio_{_k}")
                assigned_edit = st.text_input("Assigned to", value=row["assigned_to"] or "", key=f"det_assigned_{_k}")
                notes_edit    = st.text_area("Notes",        value=row["notes"] or "",
                                             height=100,                                      key=f"det_notes_{_k}")

                da, db_ = st.columns(2)
                with da:
                    if st.button("💾 Save changes", type="primary", use_container_width=True):
                        if update_work_order(conn, int(selected_id),
                                             issue=issue_edit.strip(), priority=priority_edit,
                                             assigned_to=assigned_edit.strip() or None,
                                             notes=notes_edit.strip() or None):
                            st.success("Saved.")
                            st.rerun()
                        else:
                            st.warning("No changes.")
                with db_:
                    if stat == "open":
                        if st.button("✓ Close order", use_container_width=True):
                            if close_work_order(conn, int(selected_id)) == 1:
                                st.success("Closed.")
                                st.rerun()
                            else:
                                st.warning("Already closed.")
                    else:
                        st.markdown('<div class="ix-meta" style="margin-top:10px;color:#34d399;">✓ Already closed</div>',
                                    unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════
#  HISTORY  (auto-loads as you type)
# ══════════════════════════════════════════════
with tab_history:
    st.markdown('<div class="ix-section-title">Machine history</div>', unsafe_allow_html=True)

    st.markdown('<div class="ix-card" style="padding:16px 20px;">', unsafe_allow_html=True)
    hc1, hc2, hc3 = st.columns([1.4, 1, 2])
    with hc1:
        hist_machine = st.text_input("Machine ID", placeholder="KMT-102",
                                     key="hist_machine", label_visibility="collapsed")
    with hc2:
        hist_status = st.selectbox("Status", ["All", "Open only", "Closed only"],
                                   index=0, key="history_status", label_visibility="collapsed")
    with hc3:
        hist_search = st.text_input("Search within results",
                                    placeholder="e.g. leak, pump, Mark",
                                    label_visibility="collapsed", key="hist_search")
    st.markdown('</div>', unsafe_allow_html=True)
    st.write("")

    if hist_machine.strip():
        hs_map = {"All": None, "Open only": "open", "Closed only": "closed"}
        hs     = hs_map[hist_status]
        rows   = list_work_orders_by_machine(conn, hist_machine.strip(), status=hs)
        dfh    = apply_text_search(rows_to_df(rows), hist_search)

        if dfh.empty:
            st.info(f"No work orders found for **{hist_machine.strip()}**.")
        else:
            # Summary strip
            h_open   = int((dfh["status"] == "open").sum())
            h_closed = int((dfh["status"] == "closed").sum())
            h_high   = int((dfh["priority"] == "high").sum())
            st.markdown(f"""
            <div style="display:flex;gap:8px;margin-bottom:14px;flex-wrap:wrap;">
              <div style="padding:6px 14px;background:rgba(99,102,241,0.10);border:1px solid var(--accent-border);
                          border-radius:99px;font-size:12px;color:var(--accent-light);">
                {h_open} open
              </div>
              <div style="padding:6px 14px;background:rgba(16,185,129,0.08);border:1px solid rgba(16,185,129,0.22);
                          border-radius:99px;font-size:12px;color:#34d399;">
                {h_closed} closed
              </div>
              {'<div style="padding:6px 14px;background:rgba(239,68,68,0.12);border:1px solid rgba(239,68,68,0.28);border-radius:99px;font-size:12px;color:#f87171;">' + str(h_high) + ' high priority</div>' if h_high else ''}
            </div>
            """, unsafe_allow_html=True)

            st.markdown('<div class="ix-card" style="padding:14px 16px;">', unsafe_allow_html=True)
            st.dataframe(
                dfh[["id", "priority", "status", "assigned_to",
                      "updated_at", "created_at", "closed_at", "issue"]],
                use_container_width=True, hide_index=True,
            )
            st.markdown('</div>', unsafe_allow_html=True)

            # Inline detail expanders for each open order
            open_rows = dfh[dfh["status"] == "open"]
            if not open_rows.empty:
                st.write("")
                st.markdown('<div class="ix-label">Open orders — quick actions</div>', unsafe_allow_html=True)
                for _, r in open_rows.iterrows():
                    with st.expander(f"#{int(r['id'])} · {r['issue'][:60]}"):
                        ea, eb = st.columns(2)
                        with ea:
                            st.markdown(f'<div class="ix-meta"><b>Created</b> {r["created_at"]}</div>',
                                        unsafe_allow_html=True)
                            if st.button("✓ Close this order", key=f"hist_close_{r['id']}", type="primary"):
                                if close_work_order(conn, int(r["id"])) == 1:
                                    st.success("Closed.")
                                    st.rerun()
                        with eb:
                            new_notes = st.text_area("Add / update notes", value=r["notes"] or "",
                                                     key=f"hist_notes_{r['id']}", height=80)
                            if st.button("Save notes", key=f"hist_save_{r['id']}"):
                                update_work_order(conn, int(r["id"]), notes=new_notes.strip() or None)
                                st.success("Notes saved.")
                                st.rerun()
    else:
        st.markdown('<div class="ix-meta" style="text-align:center;padding:40px 0;color:var(--text-muted);">'
                    'Type a Machine ID above to load its history.</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════
#  INSIGHTS
# ══════════════════════════════════════════════
with tab_insights:
    st.markdown('<div class="ix-section-title">Insights</div>', unsafe_allow_html=True)

    rows = list_work_orders(conn, status=None)
    df   = rows_to_df(rows)

    if df.empty:
        st.info("Create some work orders to see insights.")
    else:
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total",         int(len(df)))
        m2.metric("Open",          int((df["status"] == "open").sum()))
        m3.metric("Closed",        int((df["status"] == "closed").sum()))
        m4.metric("High priority", int((df["priority"] == "high").sum()))

        st.write("")
        ic1, ic2 = st.columns(2, gap="large")

        with ic1:
            st.markdown('<div class="ix-card">', unsafe_allow_html=True)
            st.markdown('<div class="ix-label">Open orders by priority</div>', unsafe_allow_html=True)
            pr_counts = (
                df[df["status"] == "open"]["priority"]
                .value_counts()
                .reindex(["high", "med", "low"])
                .fillna(0)
                .astype(int)
            )
            st.bar_chart(pr_counts)
            st.markdown('</div>', unsafe_allow_html=True)

        with ic2:
            st.markdown('<div class="ix-card">', unsafe_allow_html=True)
            st.markdown('<div class="ix-label">Orders created per day</div>', unsafe_allow_html=True)
            day_counts = (
                df.dropna(subset=["created_at_dt"])
                .assign(day=lambda d: d["created_at_dt"].dt.date)
                .groupby("day")["id"].count()
                .sort_index()
            )
            st.line_chart(day_counts)
            st.markdown('</div>', unsafe_allow_html=True)

        st.write("")
        ic3, ic4 = st.columns(2, gap="large")

        with ic3:
            st.markdown('<div class="ix-card">', unsafe_allow_html=True)
            st.markdown('<div class="ix-label">Top machines by open orders</div>', unsafe_allow_html=True)
            top_machines = (
                df[df["status"] == "open"]["machine_id"]
                .value_counts()
                .head(8)
            )
            if not top_machines.empty:
                st.bar_chart(top_machines)
            else:
                st.info("No open orders.")
            st.markdown('</div>', unsafe_allow_html=True)

        with ic4:
            st.markdown('<div class="ix-card">', unsafe_allow_html=True)
            st.markdown('<div class="ix-label">Orders by assignee</div>', unsafe_allow_html=True)
            by_person = (
                df[df["assigned_to"].notna()]["assigned_to"]
                .value_counts()
                .head(8)
            )
            if not by_person.empty:
                st.bar_chart(by_person)
            else:
                st.info("No assigned orders.")
            st.markdown('</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════
#  MANAGE  (data management / danger zone)
# ══════════════════════════════════════════════
with tab_manage:
    st.markdown('<div class="ix-section-title">Data management</div>', unsafe_allow_html=True)
    st.warning("All actions below permanently delete data and cannot be undone.")
    st.write("")

    mg1, mg2 = st.columns(2, gap="large")

    with mg1:
        st.markdown('<div class="ix-card">', unsafe_allow_html=True)
        st.markdown('<div class="ix-label">Delete by machine ID</div>', unsafe_allow_html=True)
        machine_to_delete = st.text_input("Machine ID", placeholder="KMT-102", key="clear_machine",
                                          label_visibility="collapsed")
        confirm_machine = st.checkbox("I understand this permanently deletes matching orders.",
                                      key="confirm_machine")
        if st.button("Delete machine history", type="primary",
                     disabled=(not confirm_machine), use_container_width=True):
            if not machine_to_delete.strip():
                st.error("Enter a machine ID.")
            else:
                n = delete_work_orders_by_machine(conn, machine_to_delete.strip())
                st.success(f"Deleted {n} work orders for {machine_to_delete.strip()}.")
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    with mg2:
        st.markdown('<div class="ix-card">', unsafe_allow_html=True)
        st.markdown('<div class="ix-label">Delete old closed orders</div>', unsafe_allow_html=True)
        days = st.number_input("Older than (days)", min_value=1, step=1, value=30, key="clear_days")
        confirm_old = st.checkbox("I understand this permanently deletes old closed orders.",
                                  key="confirm_old")
        if st.button("Delete old closed orders", disabled=not confirm_old, use_container_width=True):
            n = delete_closed_older_than(conn, int(days))
            st.success(f"Deleted {n} closed work orders older than {int(days)} days.")
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    st.write("")

    # Danger zone
    st.markdown('<div class="ix-card" style="border-color:rgba(239,68,68,0.3);">', unsafe_allow_html=True)
    st.markdown('<div class="ix-label" style="color:#f87171;">⚠ Danger zone — delete everything</div>',
                unsafe_allow_html=True)
    st.error("This removes ALL work orders from the database.")
    typed = st.text_input('Type "DELETE ALL" to confirm', key="confirm_delete_all")
    if st.button("Delete all work orders", type="primary",
                 disabled=(typed.strip().upper() != "DELETE ALL"), use_container_width=True):
        n = delete_all_work_orders(conn)
        st.success(f"Deleted {n} work orders.")
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
