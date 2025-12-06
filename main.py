import os
import json
import re
import sqlite3
from datetime import datetime, timezone
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from llm_client2 import generate_text
from prompts import ADMIN_FULLJSON_PROMPT

# =============================================
# DB SETUP
# =============================================
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, "submissions.db")


def _init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS submissions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        rating INTEGER,
        review TEXT,
        ai_response TEXT,
        admin_json TEXT,
        created_at TEXT
    )
    """)
    conn.commit()
    conn.close()


_init_db()

# =============================================
# HELPERS
# =============================================

def _clean_llm_output(text: str) -> str:
    """
    Remove markdown code fences ```json or ``` which break JSON parsing.
    """
    if not text:
        return ""
    return re.sub(r"```[a-zA-Z]*\n?|```", "", text).strip()


def _safe_json_extract(text: str) -> dict:
    """
    Extract the first valid JSON object from possibly messy LLM output.
    """
    if not text:
        return {}

    # Find anything that looks like a JSON object
    candidates = re.findall(r'\{(?:[^{}]|(?:\{[^{}]*\}))*\}', text, re.DOTALL)

    for block in candidates:
        try:
            return json.loads(block)
        except:
            continue

    return {}  # absolute fallback if nothing parses


# =============================================
# FASTAPI APP
# =============================================
app = FastAPI(title="Review Intelligence Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)


@app.get("/")
async def root():
    return {"message": "Backend running successfully."}


# =============================================
# GET ALL SUBMISSIONS (FOR ADMIN DASHBOARD)
# =============================================
@app.get("/submissions")
async def get_submissions():
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()

        cur.execute(
            "SELECT id, rating, review, ai_response, admin_json, created_at FROM submissions ORDER BY id DESC"
        )
        rows = cur.fetchall()
        cols = [column[0] for column in cur.description]

        conn.close()

        submissions = [dict(zip(cols, row)) for row in rows]

        return JSONResponse(
            status_code=200,
            content={"status": "ok", "submissions": submissions}
        )

    except Exception as e:
        print("Error loading submissions:", e)
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"Could not load submissions: {str(e)}"}
        )


# =============================================
# SUBMIT REVIEW ENDPOINT
# =============================================
@app.post("/submit")
async def submit_review(request: Request):
    try:
        # ----------------------------------------------
        # 1. Debug: show raw body
        # ----------------------------------------------
        raw_body = await request.body()
        body_text = raw_body.decode("utf-8") if raw_body else ""
        print("---- RAW BODY RECEIVED ----")
        print(body_text)
        print("---------------------------")

        # ----------------------------------------------
        # 2. Parse JSON safely
        # ----------------------------------------------
        try:
            data = await request.json()
        except:
            data = None

        if not data:
            return JSONResponse(
                status_code=400,
                content={"status": "error",
                         "message": "Invalid request. Must send JSON with 'rating' and 'review'."}
            )

        # Extract inputs
        user_review = data.get("review")
        rating_raw = data.get("rating")

        try:
            user_rating = int(rating_raw)
        except:
            user_rating = None

        if not user_review or not isinstance(user_rating, int) or not (1 <= user_rating <= 5):
            return JSONResponse(
                status_code=400,
                content={"status": "error", "message": "Invalid rating or review."}
            )

        # ----------------------------------------------
        # 3. Build prompt + call LLM
        # ----------------------------------------------
        prompt = ADMIN_FULLJSON_PROMPT.format(
            user_review=user_review,
            user_rating=user_rating
        )

        try:
            llm_output = generate_text(prompt, temperature=0.0)
        except Exception as e:
            return JSONResponse(
                status_code=502,
                content={"status": "error", "message": f"LLM failure: {str(e)}"}
            )

        print("---- RAW LLM OUTPUT ----")
        print(llm_output)
        print("------------------------")

        # ----------------------------------------------
        # 4. Clean + extract JSON
        # ----------------------------------------------
        cleaned_output = _clean_llm_output(llm_output)
        admin_obj = _safe_json_extract(cleaned_output)

        # ----------------------------------------------
        # 5. SAFE FALLBACKS (No crash even if JSON fails)
        # ----------------------------------------------
        predicted_stars = admin_obj.get("predicted_stars", user_rating)
        explanation = admin_obj.get("explanation", "Model did not provide explanation.")
        ai_summary = admin_obj.get("ai_summary", "No summary generated.")
        ai_recommendations = admin_obj.get("ai_recommendations", [])
        ai_reply = admin_obj.get(
            "ai_reply",
            "Thank you for your feedback! We appreciate your time."
        )

        # ----------------------------------------------
        # 6. Save to DB
        # ----------------------------------------------
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO submissions (rating, review, ai_response, admin_json, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            user_rating,
            user_review,
            ai_reply,
            json.dumps(admin_obj, ensure_ascii=False),
            datetime.now(timezone.utc).isoformat()
        ))

        conn.commit()
        sid = cur.lastrowid
        conn.close()

        # ----------------------------------------------
        # 7. Return JSON Response
        # ----------------------------------------------
        return JSONResponse(
            status_code=200,
            content={
                "status": "ok",
                "id": sid,
                "predicted_stars": predicted_stars,
                "explanation": explanation,
                "ai_summary": ai_summary,
                "ai_recommendations": ai_recommendations,
                "ai_reply": ai_reply,
                "admin_json": admin_obj
            }
        )

    except Exception as e:
        print("CRITICAL ERROR:", e)
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"Server error: {str(e)}"}
        )   