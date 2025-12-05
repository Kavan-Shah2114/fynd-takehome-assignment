# app/admin_dashboard/app.py
import streamlit as st
import requests
import os
import pandas as pd

API = os.environ.get("BACKEND_URL", "http://127.0.0.1:8000")

st.set_page_config(page_title="Admin — Submissions", layout="wide")
st.title("Admin Dashboard — Submissions")

@st.cache_data(ttl=10)
def fetch_submissions():
    r = requests.get(f"{API}/submissions", timeout=20)
    return r.json()

rows = fetch_submissions()
if not rows:
    st.info("No submissions yet.")
else:
    df = pd.DataFrame(rows)
    st.dataframe(df[["id","timestamp","user_rating","user_review","status"]])

    st.markdown("---")
    st.header("Export")
    csv = df.to_csv(index=False)
    st.download_button("Download CSV", csv, file_name="submissions.csv")

    st.markdown("---")
    st.header("Detail view")
    sel = st.number_input("Enter submission id to view", min_value=1, value=int(df.iloc[0]["id"]))
    detail = df[df["id"]==sel]
    if not detail.empty:
        d = detail.iloc[0]
        st.write("**Review**")
        st.write(d["user_review"])
        st.write("**AI Response (user-facing)**")
        st.write(d["ai_response"])
        st.write("**AI Admin Raw**")
        st.write(d["ai_admin_raw"])
        st.write("**AI Admin JSON**")
        st.write(d["ai_admin_json"])