# db.py (Corrected Path)

import aiosqlite
import os
import json
from datetime import datetime, timezone

# --- CORRECTED PATH ---
# Path is now relative to the root of the project where the 'data' folder is
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data/submissions.db")
DB_PATH = os.path.abspath(DB_PATH)

# Ensure data directory exists
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

async def init_db():
    """Initializes the SQLite database schema."""
    async with aiosqlite.connect(DB_PATH) as conn:
        # Schema to hold the conversational reply and the structured admin JSON
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                user_rating INTEGER,
                user_review TEXT,
                ai_response TEXT,    # User-facing conversational reply
                ai_admin_raw TEXT,   # Placeholder for raw output (optional)
                ai_admin_json TEXT,  # Structured JSON (Summary + Actions)
                status TEXT
            )
        ''')
        await conn.commit()

async def create_and_update_submission(user_rating: int, user_review: str, ai_response: str, admin_json: dict):
    """Inserts a new submission with all AI-generated fields."""
    ts = datetime.now(timezone.utc).isoformat()
    ai_admin_json_text = json.dumps(admin_json, ensure_ascii=False)
    
    async with aiosqlite.connect(DB_PATH) as conn:
        cur = await conn.execute(
            'INSERT INTO submissions (timestamp, user_rating, user_review, ai_response, ai_admin_raw, ai_admin_json, status) VALUES (?, ?, ?, ?, ?, ?, ?)',
            (ts, user_rating, user_review, ai_response, "Structured Output", ai_admin_json_text, 'done')
        )
        await conn.commit()
        return cur.lastrowid

async def get_all_submissions():
    """Retrieves all submissions for the Admin Dashboard."""
    async with aiosqlite.connect(DB_PATH) as conn:
        # Select all columns needed by the Admin Dashboard
        cur = await conn.execute('SELECT id, timestamp, user_rating, user_review, ai_response, ai_admin_json, status FROM submissions ORDER BY timestamp DESC')
        rows = await cur.fetchall()
        
        cols = ['id', 'timestamp', 'user_rating', 'user_review', 'ai_response', 'ai_admin_json', 'status']
        
        # Convert to list of dictionaries
        submissions = [
            dict(zip(cols, row)) for row in rows
        ]
        return submissions