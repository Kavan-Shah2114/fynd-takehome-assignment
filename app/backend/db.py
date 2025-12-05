# app/backend/db.py
import aiosqlite
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "../../data/submissions.db")
DB_PATH = os.path.abspath(DB_PATH)

async def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as conn:
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                user_rating INTEGER,
                user_review TEXT,
                ai_response TEXT,
                ai_admin_raw TEXT,
                ai_admin_json TEXT,
                status TEXT
            )
        ''')
        await conn.commit()

async def create_submission(user_rating, user_review):
    ts = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(DB_PATH) as conn:
        cur = await conn.execute(
            'INSERT INTO submissions (timestamp, user_rating, user_review, status) VALUES (?, ?, ?, ?)',
            (ts, user_rating, user_review, 'processing')
        )
        await conn.commit()
        return cur.lastrowid

async def update_submission_with_ai(rec_id, ai_response, ai_admin_raw, ai_admin_json_obj):
    ai_json_text = None
    import json
    if ai_admin_json_obj is not None:
        try:
            ai_json_text = json.dumps(ai_admin_json_obj)
        except Exception:
            ai_json_text = None
    async with aiosqlite.connect(DB_PATH) as conn:
        await conn.execute(
            'UPDATE submissions SET ai_response=?, ai_admin_raw=?, ai_admin_json=?, status=? WHERE id=?',
            (ai_response, ai_admin_raw, ai_json_text, 'done', rec_id)
        )
        await conn.commit()

async def get_all_submissions():
    async with aiosqlite.connect(DB_PATH) as conn:
        cur = await conn.execute('SELECT id, timestamp, user_rating, user_review, ai_response, ai_admin_raw, ai_admin_json, status FROM submissions ORDER BY id DESC')
        rows = await cur.fetchall()
        keys = ["id", "timestamp", "user_rating", "user_review", "ai_response", "ai_admin_raw", "ai_admin_json", "status"]
        res = [dict(zip(keys, r)) for r in rows]
        return res