# app/backend/main.py
import os
import json
import sqlite3
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# import your LLM client and prompts
from app.shared.llm_client import generate_text
from app.shared.prompts import USER_REPLY_PROMPT, ADMIN_JSON_PROMPT

# config
DATA_DIR = os.path.join(os.getcwd(), "data")
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, "submissions.db")

# ensure DB exists and table created
def _init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rating INTEGER,
            review TEXT,
            ai_response TEXT,
            admin_json TEXT,
            created_at TEXT
        )
        """
    )
    conn.commit()
    conn.close()

_init_db()

app = FastAPI(title="Fynd - Backend")

# allow CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def _safe_format(template: str, **kwargs):
    """
    Replace only specific placeholders {user_review} and {user_rating}
    to avoid KeyError when templates contain JSON braces.
    """
    s = template
    for k, v in kwargs.items():
        # cast to string and replace the placeholder
        placeholder = "{" + k + "}"
        s = s.replace(placeholder, str(v))
    return s

@app.post("/submit")
async def submit(payload: dict):
    """
    Expected payload: {"user_rating": int, "user_review": str}
    Returns JSON with {"status":"ok","ai_response":..., "admin_json": {...}}
    On error returns JSON with error details.
    """
    try:
        # validate payload
        user_rating = int(payload.get("user_rating", -1))
        user_review = str(payload.get("user_review", "")).strip()

        if not user_review:
            return JSONResponse(status_code=400, content={"error":"validation","detail":"user_review empty"})

        # Build prompts safely
        user_prompt = _safe_format(USER_REPLY_PROMPT, user_review=user_review, user_rating=user_rating)
        admin_prompt = _safe_format(ADMIN_JSON_PROMPT, user_review=user_review, user_rating=user_rating)

        # Call LLMs (may raise) - keep reasonable timeout/handling inside generate_text
        try:
            ai_response_raw = generate_text(user_prompt)
        except Exception as e:
            # LLM failed — return a controlled error but not secret
            return JSONResponse(status_code=502, content={"error":"llm_error","detail":str(e)[:500]})

        try:
            admin_raw = generate_text(admin_prompt)
        except Exception as e:
            admin_raw = ""  # continue even if admin generation fails

        # Try to parse admin_raw as JSON for storing; if fails store raw string
        admin_json_obj = None
        try:
            admin_json_obj = json.loads(admin_raw) if admin_raw else {}
        except Exception:
            # fallback store the raw string inside a JSON wrapper
            admin_json_obj = {"raw": admin_raw}

        # Save into DB
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO submissions (rating, review, ai_response, admin_json, created_at) VALUES (?, ?, ?, ?, ?)",
            (
                user_rating,
                user_review,
                ai_response_raw,
                json.dumps(admin_json_obj, ensure_ascii=False),
                datetime.utcnow().isoformat()
            )
        )
        conn.commit()
        submission_id = cur.lastrowid
        conn.close()

        # Build response
        resp = {
            "status": "ok",
            "id": submission_id,
            "ai_response": ai_response_raw,
            "admin_json": admin_json_obj
        }
        return JSONResponse(status_code=200, content=resp)

    except Exception as e:
        # Catch-all safe JSON error (truncate details)
        msg = str(e)
        return JSONResponse(status_code=500, content={"error":"server_error","detail": msg[:800]})