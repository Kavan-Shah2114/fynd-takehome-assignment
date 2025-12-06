import streamlit as st
import pandas as pd
import json
import requests

BACKEND_URL = "http://127.0.0.1:8000/submissions"

st.set_page_config(page_title="Admin Dashboard", layout="wide")
st.title("📊 Admin Dashboard – Review Intelligence System")

# ------------------------------------
# Safe JSON parser
# ------------------------------------
def safe_parse_json(text):
    if isinstance(text, dict):
        return text
    if not text:
        return {}
    try:
        return json.loads(text)
    except:
        return {}

# ------------------------------------
# Fetch submissions
# ------------------------------------
def load_submissions():
    try:
        resp = requests.get(BACKEND_URL, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return data.get("submissions", [])
    except Exception as e:
        st.error(f"Could not fetch submissions. Error: {str(e)}")
        return []

# ------------------------------------
# Process submissions into DataFrame
# ------------------------------------
def process_submissions(data):
    if not data:
        return pd.DataFrame()

    df = pd.DataFrame(data)

    # The backend returns BOTH keys, but admin should use ai_admin_json
    if "ai_admin_json" not in df.columns:
        # fallback – older backend versions
        df["ai_admin_json"] = df.get("admin_json", "{}")

    # Parse nested JSON safely
    df["parsed_admin"] = df["ai_admin_json"].apply(safe_parse_json)

    df["predicted_stars"] = df["parsed_admin"].apply(
        lambda x: x.get("predicted_stars", "N/A")
    ).astype(str)
    df["explanation"] = df["parsed_admin"].apply(
        lambda x: x.get("explanation", "N/A")
    )
    df["summary"] = df["parsed_admin"].apply(
        lambda x: x.get("ai_summary", "N/A")
    )
    df["recommendations"] = df["parsed_admin"].apply(
        lambda x: x.get("ai_recommendations", [])
    )
    df["ai_reply"] = df["parsed_admin"].apply(
        lambda x: x.get("ai_reply", "")
    )

    return df


# ------------------------------------
# MAIN UI
# ------------------------------------
submissions = load_submissions()
df = process_submissions(submissions)

if df.empty:
    st.warning("No submissions found.")
else:
    st.subheader("📋 Stored Reviews")
    display_df = df[[
        "id",
        "rating",
        "review",
        "predicted_stars",
        "explanation",
        "summary",
        "ai_reply",
        "created_at"
    ]].copy()
    display_df["predicted_stars"] = display_df["predicted_stars"].astype(str)
    
    st.dataframe(display_df, use_container_width=True)

    st.subheader("🧠 Parsed Admin JSON")
    st.json(df["parsed_admin"].tolist(), expanded=False)