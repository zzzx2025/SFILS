import os
import time
import json
import logging
from logging.handlers import RotatingFileHandler
from pymongo import MongoClient
import pandas as pd
import streamlit as st
from bson.objectid import ObjectId
from dotenv import load_dotenv

# Env
load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME = os.getenv("DB_NAME", "sfpl")

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

INT_FIELDS = {"Patron_ID", "Total_Checkouts", "Total_Renewals"}
BOOL_FIELDS = {"Provided_Email_Address", "Within_San_Francisco_County"}
STRING_FIELDS = {
    "Patron_Type_Definition", "Age_Range", "Home_Library_Definition",
    "Circulation_Active_Month", "Circulation_Active_Year",
    "Notice_Preference_Definition", "Year_Patron_Registered"
}

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
def get_db():
    client = MongoClient(MONGO_URI)
    return client[DB_NAME]

def get_collection():
    db = get_db()
    return db["patrons"]

def refresh_table():
    col = get_collection()
    t0 = time.time()

    docs = list(col.find().sort("Patron_ID", 1))
    dt = time.time() - t0

    st.caption(f"Fetched {len(docs)} row(s) in {dt:.3f}s • Last refresh: {time.strftime('%H:%M:%S')}")

    if not docs:
        return pd.DataFrame()

    df = pd.DataFrame(docs)
    if "_id" in df.columns:
        df = df.drop(columns=["_id"])
    return df

# User Interface
st.set_page_config(page_title="Patron Manager", layout="wide")
st.title("📚 PATRONS List")

with st.sidebar:
    st.header("MongoDB Connection")
    st.text(f"URI: {MONGO_URI}")
    st.text(f"Database: {DB_NAME}")
    st.text("Collection: patrons")

    st.markdown("---")
    st.subheader("View options")

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
            try:
                col = get_collection()
                last = col.find_one(sort=[("Patron_ID", -1)])
                next_id = (last.get("Patron_ID", 0) + 1) if last else 1

                doc = {
                    "_id": next_id,
                    "Patron_ID": next_id,
                    "Patron_Type_Definition": patron_type or None,
                    "Total_Checkouts": int(total_checkouts) if total_checkouts is not None else None,
                    "Total_Renewals": int(total_renewals) if total_renewals is not None else None,
                    "Age_Range": age_range or None,
                    "Home_Library_Definition": home_lib or None,
                    "Circulation_Active_Month": circ_month or None,
                    "Circulation_Active_Year": circ_year or None,
                    "Notice_Preference_Definition": notice_pref or None,
                    "Provided_Email_Address": None if provided_email_null else (True if provided_email else False),
                    "Year_Patron_Registered": year_reg or None,
                    "Within_San_Francisco_County": None if sf_county_null else (True if sf_county else False),
                }

                t0 = time.time()
                col.insert_one(doc)
                dt = time.time() - t0

                log_event("info", "insert", status="ok", elapsed=f"{dt:.3f}s", values=doc)
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
                    val = True
                elif v in ["false", "f", "0", "no"]:
                    val = False
                else:
                    val = None

            col = get_collection()
            patron_id = int(patron_id)
            t0 = time.time()

            if val is None:
                col.update_one({"Patron_ID": patron_id}, {"$unset": {field: ""}})
            else:
                col.update_one({"Patron_ID": patron_id}, {"$set": {field: val}})

            dt = time.time() - t0
            log_event("info", "update", status="ok", patron_id=patron_id, field=field, value=val, elapsed=f"{dt:.3f}s")
            st.success(f"Updated Patron {patron_id} ({field}) in {dt:.3f}s")
            st.rerun()

        except Exception as e:
            log_event("error", "update", status="fail", patron_id=patron_id, field=field, value=new_val, error=str(e))
            st.error(f"Update failed: {e}")

# Search
with tab_search:
    st.subheader("Search patrons")
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        field = st.selectbox("Field", ALLOWED_FIELDS)
    with col2:
        mode = st.radio("Match type", ["exact", "like"], horizontal=True, index=0)
    with col3:
        null_search = st.checkbox("Find rows where value IS NULL")

    value = st.text_input("Value (ignored if 'IS NULL' is checked)")

    if st.button("Run search"):
        try:
            col = get_collection()
            t0 = time.time()
            query = {}

            if null_search:
                query = {field: None}
            else:
                raw_val = value.strip()
                if mode == "like":
                    if field not in STRING_FIELDS:
                        st.error("LIKE search is only supported for text fields.")
                        st.stop()
                    query = {field: {"$regex": raw_val, "$options": "i"}}
                else:
                    qval = raw_val
                    if field in INT_FIELDS:
                        try:
                            qval = int(raw_val)
                        except ValueError:
                            st.error(f"Value '{raw_val}' is not a valid integer for {field}.")
                            st.stop()
                    if field in BOOL_FIELDS:
                        v = raw_val.lower()
                        if v in ["true", "t", "1", "yes"]:
                            qval = True
                        elif v in ["false", "f", "0", "no"]:
                            qval = False
                        else:
                            st.error(f"Value '{raw_val}' is not a valid boolean. Use true/false, yes/no, 1/0.")
                            st.stop()

                    query = {field: qval}

            docs = list(col.find(query))
            dt = time.time() - t0

            for d in docs:
                d["_id"] = str(d["_id"])

            log_event("info", "search", mode=mode, field=field, value=value,
                      results=len(docs), elapsed=f"{dt:.3f}s")
            st.caption(f"Query in {dt:.3f}s • Last refresh: {time.strftime('%H:%M:%S')}")
            st.dataframe(pd.DataFrame(docs), use_container_width=True)

        except Exception as e:
            log_event("error", "search", mode=mode, field=field, value=value, error=str(e))
            st.error(f"Search failed: {e}")

# Delete
with tab_delete:
    st.subheader("Delete patron")
    df_now = refresh_table()
    id_list = df_now["Patron_ID"].tolist() if "Patron_ID" in df_now else []
    if id_list:
        del_id = st.selectbox("Patron_ID to delete", id_list, key="delete_select_id")
    else:
        del_id = st.number_input("Patron_ID", step=1, key="delete_number_id")

    if st.button("Delete", type="primary"):
        try:
            col = get_collection()
            del_id = int(del_id)
            t0 = time.time()
            existing = col.find_one({"Patron_ID": del_id})
            if not existing:
                st.error(f"No patron with ID {del_id} found.")
                log_event("info", "delete", status="not_found", patron_id=del_id)
            else:
                col.delete_one({"Patron_ID": del_id})
                dt = time.time() - t0
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
