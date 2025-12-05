# app/user_dashboard/app.py
import os
import json
import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

API = os.environ.get("BACKEND_URL", "http://127.0.0.1:8000")

st.set_page_config(page_title="Review — User", layout="centered")
st.title("Leave a short review")

# initialize session state keys before widgets
if "review_text" not in st.session_state:
    st.session_state["review_text"] = ""
if "rating" not in st.session_state:
    st.session_state["rating"] = 5

# widgets bound to session_state keys
stars = st.slider("Rating", 1, 5, key="rating")
review = st.text_area("Write your review (one or two sentences)", key="review_text")

# submit button logic
if st.button("Submit"):
    user_rating = int(st.session_state.get("rating", 3))
    user_review = (st.session_state.get("review_text", "") or "").strip()

    if len(user_review) == 0:
        st.error("Please write a short review before submitting.")
    else:
        payload = {"user_rating": user_rating, "user_review": user_review}
        try:
            resp = requests.post(f"{API.rstrip('/')}/submit", json=payload, timeout=20)

            st.write("DEBUG: status_code:", resp.status_code)
            st.write("DEBUG: response_text (raw):")
            st.code(resp.text[:4000])

            try:
                data = resp.json()
                st.write("DEBUG: parsed json keys:", list(data.keys()))

                # success case
                if resp.status_code == 200 and data.get("status") == "ok":
                    st.success("Submitted — backend returned JSON.")
                    st.markdown("### AI Reply")

                    ai_raw = data.get("ai_response", "")

                    # try to parse LLM output JSON
                    try:
                        ai_obj = json.loads(ai_raw) if isinstance(ai_raw, str) else ai_raw
                    except Exception:
                        ai_obj = None

                    if isinstance(ai_obj, dict):
                        pred = ai_obj.get("predicted_stars")
                        expl = ai_obj.get("explanation") or ai_obj.get("reason") or ""

                        st.write(f"**Predicted stars:** {pred}")
                        if expl:
                            st.write("**Explanation:**")
                            st.write(expl)
                    else:
                        # fallback — show raw string
                        st.write(ai_raw)

                # backend-side error
                else:
                    st.error(f"Backend returned error: {data.get('error')}")
                    st.write(data.get("detail"))

            except Exception as e:
                st.error(f"JSON parse error: {e}")
                st.warning("Backend did not return valid JSON. See raw response above.")

        except Exception as exc:
            st.error(f"Error during request: {exc}")

st.markdown("---")
st.markdown("**Quick sample reviews**")

# safe load-sample using on_click callback
def _load_sample():
    st.session_state["review_text"] = "Great food, fast service — would come again!"
    st.session_state["rating"] = 5
    # no rerun call needed — Streamlit auto-runs after callback

if st.button("Load sample review", key="load_sample", on_click=_load_sample):
    pass