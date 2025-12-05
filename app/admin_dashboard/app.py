# app/admin_dashboard/app.py
import os
import json
import sqlite3
from datetime import datetime
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

DB_PATH = os.path.join(os.getcwd(), "data", "submissions.db")

st.set_page_config(page_title="Review — Admin", layout="wide")
st.title("Admin — Submissions")

def load_submissions(db_path=DB_PATH):
    """Load submissions from SQLite and return a safe DataFrame."""
    if not os.path.exists(db_path):
        # return empty dataframe with expected columns
        cols = ["id", "rating", "review", "ai_response", "admin_json", "created_at"]
        return pd.DataFrame(columns=cols)

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT id, rating, review, ai_response, admin_json, created_at FROM submissions ORDER BY id DESC")
    rows = cur.fetchall()
    conn.close()

    cols = ["id", "rating", "review", "ai_response", "admin_json", "created_at"]

    # If there are no rows, return empty DF with columns
    if not rows:
        return pd.DataFrame(columns=cols)

    # rows is list of tuples -> build DataFrame directly with columns
    df = pd.DataFrame(rows, columns=cols)

    # parse admin_json column which is stored as JSON string
    def _safe_parse(x):
        if not x:
            return {}
        if isinstance(x, dict):
            return x
        try:
            return json.loads(x)
        except Exception:
            # fallback: try to interpret as dict-like string or return raw
            return {"raw": str(x)}

    df["admin_json_parsed"] = df["admin_json"].apply(_safe_parse)
    # Optionally create nicer preview columns
    df["ai_preview"] = df["ai_response"].str.slice(0, 200)
    df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")
    return df

# Load data
df = load_submissions()

# Top-level stats and filters
st.markdown(f"**Total submissions:** {len(df)}")
col1, col2 = st.columns([1, 3])
with col1:
    rating_filter = st.multiselect("Filter by rating", options=sorted(df["rating"].dropna().unique().astype(int).tolist()), default=sorted(df["rating"].dropna().unique().astype(int).tolist()))
with col2:
    search = st.text_input("Search review text", value="")

# Apply filters
df_filtered = df.copy()
if rating_filter:
    df_filtered = df_filtered[df_filtered["rating"].isin(rating_filter)]
if search:
    df_filtered = df_filtered[df_filtered["review"].str.contains(search, case=False, na=False)]

# Show table
st.markdown("### Submissions")
if df_filtered.empty:
    st.info("No submissions match the current filters.")
else:
    # Show a compact table
    display_df = df_filtered[["id", "rating", "review", "ai_preview", "created_at"]].copy()
    display_df = display_df.rename(columns={"ai_preview": "ai_response_preview"})
    st.dataframe(display_df.head(200), use_container_width=True)

    # Allow selecting a row to inspect
    sel = st.number_input("Enter submission id to inspect (or 0 to pick latest):", min_value=0, max_value=int(df_filtered["id"].max()), value=0, step=1)
    if sel == 0:
        # pick the first (latest) row in filtered DF
        sel_row = df_filtered.iloc[0] if not df_filtered.empty else None
    else:
        sel_row = df_filtered[df_filtered["id"] == sel]
        sel_row = sel_row.iloc[0] if not sel_row.empty else None

    if sel_row is not None:
        st.markdown("### Submission detail")
        st.write(f"**ID:** {int(sel_row['id'])}")
        st.write(f"**Rating:** {int(sel_row['rating']) if pd.notna(sel_row['rating']) else 'N/A'}")
        st.write(f"**Review:** {sel_row['review']}")
        st.write(f"**Submitted at:** {sel_row['created_at']}")

        st.markdown("**AI Response (raw):**")
        st.code(sel_row["ai_response"] or "")

        st.markdown("**AI Response (parsed)**")
        parsed = sel_row["admin_json_parsed"] if "admin_json_parsed" in sel_row else {}
        if isinstance(parsed, dict):
            st.json(parsed)
        else:
            st.write(parsed)

        st.markdown("**Admin JSON (raw field stored):**")
        st.code(sel_row["admin_json"] or "")
    else:
        st.info("No submission selected or no submissions available.")