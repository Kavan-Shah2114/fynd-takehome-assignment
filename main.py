# main.py
import os
import re
import json
import ast
import sqlite3
from datetime import datetime, timezone
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# Import your Gemini-capable LLM client and the admin prompt template
# Ensure these files exist: llm_client2.py and prompts.py
from llm_client2 import generate_text  # expects generate_text(prompt, ...)
from prompts import ADMIN_FULLJSON_PROMPT

# -------------------------
# Configuration
# -------------------------
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, "submissions.db")

# Initialize DB (sqlite)
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

# -------------------------
# Utility: robust cleaning & parsing
# -------------------------
def _clean_llm_output(text: str) -> str:
    """
    Clean output so JSON extraction is easier:
    - Normalize line endings
    - Remove code fences (``` or ```json)
    - Strip BOM/invisible chars and leading/trailing whitespace
    - Trim to the first balanced JSON block if one exists
    - Remove stray whitespace/newlines immediately before quoted keys
    - Normalize single quotes to double quotes in simple cases
    """
    if not text:
        return ""

    # normalize line endings and remove BOM
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.lstrip("\ufeff").strip()

    # remove code fences
    text = re.sub(r"```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```\s*", "", text)

    # find the first JSON object and the last closing brace
    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        # trim to largest brace-delimited block (this drops any leading prose)
        text = text[first_brace:last_brace+1]
    else:
        # collapse repeated whitespace if no braces found
        text = re.sub(r'\s+', ' ', text).strip()

    # remove stray newlines immediately before quoted keys, e.g. '\n "predicted_stars"'
    text = re.sub(r'[\n\t ]+(?=["\'])', '', text)

    # if there are no double quotes but single quotes and braces exist, try a safe replace
    if '"' not in text and ("'" in text and "{" in text and "}" in text):
        try:
            text = text.replace("'", '"')
        except Exception:
            pass

    return text.strip()


def _safe_json_extract(text: str) -> dict:
    """
    Robustly attempt to extract a JSON-like dict from noisy LLM text.
    Strategies (in order):
     1) Clean and try json.loads(cleaned)
     2) Extract balanced {...} blocks (largest-first), try json.loads then ast.literal_eval
     3) Try normalized cleaned text with single->double quote swap
     4) As last resort, use regex heuristics to find expected fields
    Returns an empty dict on failure.
    """
    if not text or not isinstance(text, str):
        return {}

    # 1) clean and direct parse
    cleaned = _clean_llm_output(text)
    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass

    # 2) find balanced {...} blocks (including nested)
    # This regex attempts to capture JSON-like balanced blocks
    blocks = re.findall(r'\{(?:[^{}]|\{(?:[^{}]|\{[^{}]*\})*\})*\}', text, re.DOTALL)
    if blocks:
        # try largest block first
        for block in sorted(blocks, key=len, reverse=True):
            b = block.strip()
            # try JSON
            try:
                parsed = json.loads(b)
                if isinstance(parsed, dict):
                    return parsed
            except Exception:
                pass

            # try ast.literal_eval for single-quoted dicts
            try:
                parsed = ast.literal_eval(b)
                if isinstance(parsed, dict):
                    return parsed
            except Exception:
                pass

            # try a light normalization and parse
            try:
                normalized = b.replace("'", '"')
                parsed = json.loads(normalized)
                if isinstance(parsed, dict):
                    return parsed
            except Exception:
                pass

    # 3) try normalized cleaned text
    try:
        candidate = cleaned.replace("'", '"')
        parsed = json.loads(candidate)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass

    # 4) regex heuristics as a last resort to populate expected fields
    result = {}

    # predicted_stars
    m = re.search(r'["\']?predicted[_\s-]?stars["\']?\s*[:=]\s*([1-5])', text, re.IGNORECASE)
    if m:
        try:
            result["predicted_stars"] = int(m.group(1))
        except Exception:
            pass

    # explanation (short capture)
    m = re.search(r'explanation["\']?\s*[:=-]\s*["\']?(.{5,400}?)["\']?(?=[,\}\n]|$)', text, re.IGNORECASE)
    if m:
        result["explanation"] = m.group(1).strip()

    # ai_summary
    m = re.search(r'ai_summary["\']?\s*[:=-]\s*["\']?(.{5,300}?)["\']?(?=[,\}\n]|$)', text, re.IGNORECASE)
    if m:
        result["ai_summary"] = m.group(1).strip()

    # ai_recommendations (try to capture bracketed list)
    m = re.search(r'ai_recommendations["\']?\s*[:=-]\s*(\[[^\]]*\])', text, re.IGNORECASE | re.DOTALL)
    if m:
        arrtxt = m.group(1)
        try:
            result["ai_recommendations"] = json.loads(arrtxt)
        except Exception:
            items = re.split(r'[\n;,\|]+', arrtxt.strip("[] "))
            result["ai_recommendations"] = [it.strip(" \"'") for it in items if it.strip()]

    # ai_reply
    m = re.search(r'ai_reply["\']?\s*[:=-]\s*["\']?(.{5,500}?)["\']?(?=[,\}\n]|$)', text, re.IGNORECASE)
    if m:
        result["ai_reply"] = m.group(1).strip()

    return result

# -------------------------
# FastAPI app init
# -------------------------
app = FastAPI(title="Review Intelligence Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # adjust for production
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)


@app.get("/")
async def root():
    return {"message": "Backend running successfully."}


# -------------------------
# GET all submissions (admin dashboard)
# -------------------------
@app.get("/submissions")
async def get_submissions():
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT id, rating, review, ai_response, admin_json, created_at FROM submissions ORDER BY id DESC")
        rows = cur.fetchall()
        cols = [column[0] for column in cur.description]
        conn.close()

        submissions = [dict(zip(cols, row)) for row in rows]
        return JSONResponse(status_code=200, content={"status": "ok", "submissions": submissions})
    except Exception as e:
        print("Error loading submissions:", e)
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


# -------------------------
# Submit endpoint: main logic
# -------------------------
@app.post("/submit")
async def submit_review(request: Request):
    try:
        # read raw body and log
        raw_body = await request.body()
        body_text = raw_body.decode("utf-8") if raw_body else ""
        print("---- RAW BODY RECEIVED ----")
        print(body_text)
        print("---------------------------")

        # parse JSON payload
        try:
            data = await request.json()
        except Exception:
            data = None

        if not data:
            return JSONResponse(status_code=400, content={"status": "error", "message": "Invalid request. Must send JSON with 'rating' and 'review'."})

        user_review = data.get("review")
        rating_raw = data.get("rating")

        try:
            user_rating = int(rating_raw)
        except Exception:
            user_rating = None

        if not user_review or not isinstance(user_rating, int) or not (1 <= user_rating <= 5):
            return JSONResponse(status_code=400, content={"status": "error", "message": "Invalid rating or review."})

        # build prompt using ADMIN_FULLJSON_PROMPT from prompts.py
        prompt = ADMIN_FULLJSON_PROMPT.format(user_review=user_review, user_rating=user_rating)
        print("PROMPT SENT (clipped):", prompt[:1000])

        # call the LLM (uses llm_client2.generate_text)
        try:
            llm_output = generate_text(prompt, temperature=0.0)
        except Exception as e:
            print("LLM call exception:", e)
            return JSONResponse(status_code=502, content={"status": "error", "message": f"LLM failure: {str(e)}"})

        print("---- RAW LLM OUTPUT ----")
        print(llm_output)
        print("------------------------")

        # robust parsing without raising unexpected exceptions
        admin_obj = {}
        try:
            cleaned_output = _clean_llm_output(llm_output)
            admin_obj = _safe_json_extract(cleaned_output) or _safe_json_extract(llm_output)
            if not admin_obj:
                # try ast.literal_eval on any {...} block as another attempt
                blocks = re.findall(r'\{(?:[^{}]|\{(?:[^{}]|\{[^{}]*\})*\})*\}', llm_output, re.DOTALL)
                for b in sorted(blocks, key=len, reverse=True):
                    try:
                        candidate = ast.literal_eval(b)
                        if isinstance(candidate, dict) and candidate:
                            admin_obj = candidate
                            break
                    except Exception:
                        continue
        except Exception as e:
            print("Parsing helper unexpected exception (ignored):", e)
            admin_obj = {}

        # fallback empty dict if nothing parsed
        if not isinstance(admin_obj, dict):
            admin_obj = {}

        # SAFETY: extract fields with defaults
        predicted_stars = admin_obj.get("predicted_stars")
        explanation = admin_obj.get("explanation")
        ai_summary = admin_obj.get("ai_summary")
        ai_recommendations = admin_obj.get("ai_recommendations")
        ai_reply = admin_obj.get("ai_reply")

        # If predicted_stars missing, try strict digit extraction, else fallback to user_rating
        if predicted_stars is None:
            m = re.search(r'\b([1-5])\b', llm_output)
            if m:
                try:
                    predicted_stars = int(m.group(1))
                except:
                    predicted_stars = user_rating
            else:
                predicted_stars = user_rating

        # Provide sensible human-friendly fallbacks if fields empty
        if not explanation:
            explanation = admin_obj.get("explanation", None) or "No detailed explanation returned by model."

        if not ai_summary:
            ai_summary = admin_obj.get("ai_summary", None) or "No summary returned by model."

        if not ai_recommendations or (isinstance(ai_recommendations, list) and len(ai_recommendations) == 0):
            ai_recommendations = admin_obj.get("ai_recommendations", None) or ["No recommendations returned by model."]

        if not ai_reply:
            ai_reply = admin_obj.get("ai_reply", None) or "Thank you for your feedback."

        # persist to sqlite DB (ai_response stores the friendly reply shown to user; admin_json stores raw object)
        try:
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
        except Exception as e:
            print("DB write failed:", e)
            return JSONResponse(status_code=500, content={"status": "error", "message": "Failed to save submission."})

        # return structured response
        return JSONResponse(status_code=200, content={
            "status": "ok",
            "id": sid,
            "predicted_stars": predicted_stars,
            "explanation": explanation,
            "ai_summary": ai_summary,
            "ai_recommendations": ai_recommendations,
            "ai_reply": ai_reply,
            "admin_json": admin_obj
        })

    except Exception as e:
        print("CRITICAL ERROR:", e)
        return JSONResponse(status_code=500, content={"status": "error", "message": f"Server error: {str(e)}"})