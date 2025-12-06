# user_dashboard.py
import streamlit as st
import requests
import json

# backend submit endpoint
BACKEND_URL = "http://127.0.0.1:8000/submit"

st.set_page_config(page_title="Review Assistant", layout="centered")
st.title("📝 Customer Review – AI Assistant")

if "last_response" not in st.session_state:
    st.session_state.last_response = None

# ---------------------------------------------------
# Submit review to FastAPI backend
# ---------------------------------------------------
def submit_review(rating, review, timeout_seconds=180):
    payload = {
        "rating": rating,
        "review": review
    }

    try:
        resp = requests.post(
            BACKEND_URL,
            json=payload,
            timeout=timeout_seconds  # increased timeout to allow LLM processing
        )
        # If server returned a non-2xx, try to surface useful message
        try:
            data = resp.json()
        except ValueError:
            resp.raise_for_status()  # will raise HTTPError when not 2xx
            return None

        if resp.status_code >= 400:
            # Show backend-provided message if available
            msg = data.get("message") or data.get("error") or f"Backend returned status {resp.status_code}"
            st.error(f"Backend error: {msg}")
            return None

        return data

    except requests.exceptions.Timeout:
        st.error("Backend took too long to respond. (Timeout)")
        return None

    except requests.exceptions.RequestException as e:
        st.error(f"Error connecting to backend: {str(e)}")
        return None


# ---------------------------------------------------
# UI
# ---------------------------------------------------
with st.form("review_form"):
    st.subheader("⭐ Rate Your Experience")
    rating = st.slider("Rating (1–5)", 1, 5, 5)

    review = st.text_area(
        "Write your review:",
        placeholder="Describe your experience...",
        height=150
    )

    submitted = st.form_submit_button("Submit Review")

if submitted:
    if not review.strip():
        st.warning("Please enter a review before submitting.")
    else:
        with st.spinner("AI analyzing your feedback… This can take a little while for the first request."):
            result = submit_review(rating, review, timeout_seconds=180)

        if result and result.get("status") == "ok":
            st.session_state.last_response = result
        else:
            # detailed feedback already shown inside submit_review
            if not result:
                st.error("Failed to process the review. See the error messages above for details.")

# ---------------------------------------------------
# DISPLAY AI RESPONSE
# ---------------------------------------------------
if st.session_state.last_response:
    r = st.session_state.last_response

    st.success("AI Response Received!")

    st.subheader("🤖 AI Reply")
    st.info(r.get("ai_reply", "No reply provided."))

    st.subheader("📌 Interpretation")
    st.write(f"**Predicted Stars:** {r.get('predicted_stars')}")
    st.write(f"**Explanation:** {r.get('explanation')}")

    st.subheader("🧠 Summary")
    st.write(r.get("ai_summary", ""))

    st.subheader("📈 Recommendations")
    recs = r.get("ai_recommendations", [])
    if recs:
        for rec in recs:
            st.write(f"- {rec}")
    else:
        st.write("No recommendations provided.")

    st.divider()
    st.caption("Data processed by AI Review Intelligence System")