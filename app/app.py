import os
import time
import json
import logging
from logging.handlers import RotatingFileHandler

import pandas as pd
import streamlit as st
import mysql.connector
from mysql.connector import pooling
from dotenv import load_dotenv

# Env
load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "root")
DB_PASS = os.getenv("DB_PASS", "password")
DB_NAME = os.getenv("DB_NAME", "sfils_db")

ALLOWED_FIELDS = [
    'Patron_ID', 'Patron_Type_Definition', 'Total_Checkouts', 'Total_Renewals',
    'Age_Range', 'Home_Library_Definition', 'Circulation_Active_Month',
    'Circulation_Active_Year', 'Notice_Preference_Definition',
    'Provided_Email_Address', 'Year_Patron_Registered',
    'Within_San_Francisco_County'
]

# Logs
LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "app.log")
os.makedirs(LOG_DIR, exist_ok=True)

logger = logging.getLogger("patron_app")
logger.setLevel(logging.INFO)

if not any(isinstance(h, RotatingFileHandler) for h in logger.handlers):
    file_handler = RotatingFileHandler(LOG_FILE, maxBytes=2_000_000, backupCount=3)
    file_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
    logger.addHandler(file_handler)

def log_event(level: str, action: str, **kwargs):
    payload = {"action": action}
    payload.update(kwargs)
    line = json.dumps(payload, ensure_ascii=False)
    if level.lower() == "error":
        logger.error(line)
    else:
        logger.info(line)

# Database Pool
@st.cache_resource
def get_pool():
    return pooling.MySQLConnectionPool(
        pool_name="patron_pool",
        pool_size=5,
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME
    )

def get_conn():
    conn = get_pool().get_connection()
    conn.autocommit = True
    return conn

def run_query(query, params=None, fetch="all", as_dict=True):
    """
    Safe query runner with timing + error logging.
    fetch: "all" | "one" | "none"
    """
    t0 = time.time()
    try:
        conn = get_conn()
        cur = conn.cursor(dictionary=as_dict)
        cur.execute(query, params or ())
        if fetch == "one":
            rows = cur.fetchone()
        elif fetch == "none":
            rows = None
        else:
            rows = cur.fetchall()
        conn.commit()
        cur.close()
        conn.close()
        dt = time.time() - t0
        return rows, dt
    except Exception as e:
        dt = time.time() - t0
        log_event("error", "db_error", query=query, params=str(params), elapsed=f"{dt:.3f}s", error=str(e))
        raise

def refresh_table():
    rows, dt = run_query("SELECT * FROM PATRONS ORDER BY Patron_ID DESC")
    st.caption(f"Fetched {len(rows)} row(s) in {dt:.3f}s • Last refresh: {time.strftime('%H:%M:%S')}")
    return pd.DataFrame(rows) if rows else pd.DataFrame()

# User Interface
st.set_page_config(page_title="Patron Manager", layout="wide")
st.title("📚 PATRONS List")

with st.sidebar:
    st.subheader("Database connection")
    st.text_input("Host", value=DB_HOST, key="host", disabled=True)
    st.number_input("Port", value=DB_PORT, key="port", disabled=True)
    st.text_input("User", value=DB_USER, key="user", disabled=True)
    st.text_input("Database", value=DB_NAME, key="db", disabled=True)
    st.caption("Edit values in a .env file to change these.")

tab_view, tab_add, tab_update, tab_search, tab_delete, tab_logs = st.tabs(
    ["View All", "Add New", "Update", "Search", "Delete", "Logs"]
)

# View
with tab_view:
    st.subheader("All patrons")

    c1, c2, c3 = st.columns([1, 1, 2])
    with c1:
        if st.button("🔄 Refresh now"):
            st.rerun()

    default_auto = st.session_state.get("auto_refresh", False)
    default_interval = st.session_state.get("auto_interval", 5)

    with c2:
        auto = st.toggle("Auto-refresh", value=default_auto, key="auto_refresh")
    with c3:
        interval = st.slider("Interval (sec)", min_value=2, max_value=60, value=default_interval, key="auto_interval")

    df = refresh_table()
    st.dataframe(df, use_container_width=True)

    # Auto-refresh
    if auto:
        if "last_refresh_ts" not in st.session_state:
            st.session_state.last_refresh_ts = time.time()

        now = time.time()
        elapsed = now - st.session_state.last_refresh_ts

        remaining = max(0, int(interval - elapsed))
        st.caption(f"⏱️ Auto-refresh every {interval}s • Next in {remaining}s")

        if elapsed >= interval:
            st.session_state.last_refresh_ts = time.time()
            st.rerun()
        else:
            time.sleep(1)
            st.rerun()

# Add New
with tab_add:
    st.subheader("Add new patron")
    with st.form("add_patron"):
        c1, c2, c3 = st.columns(3)
        with c1:
            patron_type = st.text_input("Patron_Type_Definition")
            total_checkouts = st.number_input("Total_Checkouts", step=1, format="%d", placeholder="0")
            total_renewals = st.number_input("Total_Renewals", step=1, format="%d", placeholder="0")
            age_range = st.text_input("Age_Range")
        with c2:
            home_lib = st.text_input("Home_Library_Definition")
            circ_month = st.text_input("Circulation_Active_Month")
            circ_year = st.text_input("Circulation_Active_Year")
            notice_pref = st.text_input("Notice_Preference_Definition")
        with c3:
            provided_email = st.toggle("Provided_Email_Address (bool / nullable)", value=False)
            provided_email_null = st.checkbox("Set Provided_Email_Address = NULL", value=False)
            year_reg = st.text_input("Year_Patron_Registered")
            sf_county = st.toggle("Within_San_Francisco_County (bool / nullable)", value=False)
            sf_county_null = st.checkbox("Set Within_San_Francisco_County = NULL", value=False)

        submitted = st.form_submit_button("Insert")
        if submitted:
            data = (
                patron_type or None,
                int(total_checkouts) if total_checkouts is not None else None,
                int(total_renewals) if total_renewals is not None else None,
                age_range or None,
                home_lib or None,
                circ_month or None,
                circ_year or None,
                notice_pref or None,
                (None if provided_email_null else (1 if provided_email else 0)),
                year_reg or None,
                (None if sf_county_null else (1 if sf_county else 0)),
            )
            q = """
            INSERT INTO PATRONS (
                Patron_Type_Definition, Total_Checkouts, Total_Renewals,
                Age_Range, Home_Library_Definition, Circulation_Active_Month,
                Circulation_Active_Year, Notice_Preference_Definition,
                Provided_Email_Address, Year_Patron_Registered,
                Within_San_Francisco_County
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """
            try:
                _, dt = run_query(q, data, fetch="none")
                log_event("info", "insert", status="ok", elapsed=f"{dt:.3f}s", values=data)
                st.success(f"Inserted new patron in {dt:.3f}s")
                st.rerun()
            except Exception as e:
                log_event("error", "insert", status="fail", error=str(e))
                st.error(f"Insert failed: {e}")

# Update
with tab_update:
    st.subheader("Update a field")
    df_now = refresh_table()
    id_list = df_now["Patron_ID"].tolist() if "Patron_ID" in df_now else []
    patron_id = st.selectbox("Patron_ID", id_list) if id_list else st.number_input("Patron_ID", step=1)
    field = st.selectbox("Field", ALLOWED_FIELDS, index=1)
    new_val = st.text_input("New value (leave blank for NULL)")

    if st.button("Update"):
        try:
            if field not in ALLOWED_FIELDS:
                st.error("Invalid field.")
                st.stop()

            val = None if new_val.strip() == "" else new_val.strip()

            if field in ["Total_Checkouts", "Total_Renewals"] and val is not None:
                val = int(val)

            if field in ["Provided_Email_Address", "Within_San_Francisco_County"] and val is not None:
                v = val.lower()
                if v in ["true", "t", "1", "yes"]:
                    val = 1
                elif v in ["false", "f", "0", "no"]:
                    val = 0
                else:
                    val = None  # treat unknown as NULL

            if val is None:
                q = f"UPDATE PATRONS SET {field} = NULL WHERE Patron_ID = %s"
                _, dt = run_query(q, (patron_id,), fetch="none")
            else:
                q = f"UPDATE PATRONS SET {field} = %s WHERE Patron_ID = %s"
                _, dt = run_query(q, (val, patron_id), fetch="none")

            log_event("info", "update", status="ok", patron_id=patron_id, field=field, value=val, elapsed=f"{dt:.3f}s")
            st.success(f"Updated Patron {patron_id} ({field}) in {dt:.3f}s")
            st.rerun()
        except Exception as e:
            log_event("error", "update", status="fail", patron_id=patron_id, field=field, value=new_val, error=str(e))
            st.error(f"Update failed: {e}")

# Search
with tab_search:
    st.subheader("Search patrons")
    col1, col2, col3 = st.columns([1,1,1])
    with col1:
        field = st.selectbox("Field", ALLOWED_FIELDS)
    with col2:
        mode = st.radio("Match type", ["exact", "like"], horizontal=True, index=0)
    with col3:
        null_search = st.checkbox("Find rows where value IS NULL")

    value = st.text_input("Value (ignored if 'IS NULL' is checked)")
    if st.button("Run search"):
        try:
            if null_search:
                q = f"SELECT * FROM PATRONS WHERE {field} IS NULL"
                rows, dt = run_query(q)
                log_event("info", "search", mode="is_null", field=field, results=len(rows), elapsed=f"{dt:.3f}s")
            else:
                if mode == "like":
                    q = f"SELECT * FROM PATRONS WHERE {field} LIKE %s"
                    rows, dt = run_query(q, (f"%{value}%",))
                else:
                    q = f"SELECT * FROM PATRONS WHERE {field} = %s"
                    rows, dt = run_query(q, (value,))
                log_event("info", "search", mode=mode, field=field, value=value, results=len(rows), elapsed=f"{dt:.3f}s")
            st.caption(f"Query in {dt:.3f}s • Last refresh: {time.strftime('%H:%M:%S')}")
            st.dataframe(pd.DataFrame(rows), use_container_width=True)
        except Exception as e:
            log_event("error", "search", mode=mode, field=field, value=value, error=str(e))
            st.error(f"Search failed: {e}")

# Delete
with tab_delete:
    st.subheader("Delete patron")
    df_now = refresh_table()
    id_list = df_now["Patron_ID"].tolist() if "Patron_ID" in df_now else []
    del_id = st.selectbox("Patron_ID to delete", id_list) if id_list else st.number_input("Patron_ID", step=1)
    if st.button("Delete", type="primary"):
        try:
            row, _ = run_query("SELECT * FROM PATRONS WHERE Patron_ID = %s", (del_id,), fetch="one")
            if not row:
                st.error(f"No patron with ID {del_id} found.")
                log_event("info", "delete", status="not_found", patron_id=del_id)
            else:
                _, dt = run_query("DELETE FROM PATRONS WHERE Patron_ID = %s", (del_id,), fetch="none")
                log_event("info", "delete", status="ok", patron_id=del_id, elapsed=f"{dt:.3f}s")
                st.success(f"Deleted Patron {del_id} in {dt:.3f}s")
                st.rerun()
        except Exception as e:
            log_event("error", "delete", status="fail", patron_id=del_id, error=str(e))
            st.error(f"Delete failed: {e}")

# Logs
with tab_logs:
    st.subheader("Application logs")
    colA, colB = st.columns([1, 3])
    with colA:
        max_lines = st.number_input("Show last N lines", min_value=10, max_value=10000, value=500, step=10)
        if st.button("Refresh logs"):
            st.rerun()
    with colB:
        if os.path.exists(LOG_FILE):
            def tail(path, n=500):
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()
                return "".join(lines[-n:])
            content = tail(LOG_FILE, int(max_lines))
            st.code(content or "(no log content yet)", language="text")
            with open(LOG_FILE, "rb") as f:
                st.download_button("Download app.log", f, file_name="app.log", mime="text/plain")
        else:
            st.info("No logs yet. Perform an action (add/update/delete) to generate logs.")
