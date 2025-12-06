# llm_client2.py (GEMINI client — improved robustness & retry/backoff)
import os
import json
import time
import requests
from dotenv import load_dotenv

load_dotenv()

MOCK = os.environ.get("MOCK_LLM", "0") == "1"

# GEMINI CONFIG
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
# Strip accidental quotes around key in .env (users sometimes put "..." which breaks requests)
_raw_key = os.environ.get("GEMINI_API_KEY", None)
if isinstance(_raw_key, str):
    GEMINI_API_KEY = _raw_key.strip().strip('"').strip("'")
else:
    GEMINI_API_KEY = _raw_key

if not MOCK and not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY not found in .env file!")

# Google REST endpoint for Gemini
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"

def _extract_text_from_response_json(data: dict) -> str:
    """
    Try various known response shapes to extract textual output.
    """
    # direct candidates path (typical)
    try:
        candidates = data.get("candidates")
        if candidates and isinstance(candidates, list):
            parts = candidates[0].get("content", {}).get("parts", [])
            if parts:
                return "".join(p.get("text", "") for p in parts if isinstance(p, dict))
            # fallback to joining candidate strings
            if isinstance(candidates[0], dict):
                # try nested fields
                for v in ["output", "text", "content"]:
                    if v in candidates[0]:
                        return str(candidates[0][v])
            return json.dumps(candidates[0])
    except Exception:
        pass

    # older/newer shapes: check top-level 'output' or 'candidates' alternative
    for key in ("output", "text", "result", "candidates"):
        if key in data:
            try:
                val = data[key]
                if isinstance(val, str):
                    return val
                if isinstance(val, dict):
                    # try to find text inside dict
                    for sub in ("text", "content", "message", "parts"):
                        if sub in val:
                            return str(val[sub])
                return json.dumps(val)
            except Exception:
                continue

    # Fallback: scan recursively for any "text" field
    def _rec_find_text(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k == "text" and isinstance(v, str):
                    return v
                res = _rec_find_text(v)
                if res:
                    return res
        elif isinstance(obj, list):
            for item in obj:
                res = _rec_find_text(item)
                if res:
                    return res
        return None

    rec = _rec_find_text(data)
    if rec:
        return rec

    # Last resort: return JSON dump
    return json.dumps(data)

def generate_text(prompt: str, max_output_tokens=512, temperature: float = 0.0, timeout: int = 120, max_retries: int = 4) -> str:
    """
    Sends prompt to Gemini API using REST with retries/backoff for 429 and network errors.
    Returns the text output from the model (raw string).
    """

    # MOCK mode: return a rich mock JSON string so downstream extractor can parse
    if MOCK:
        print("--- GEMINI CLIENT: Returning Mock Response (MOCK_LLM='1') ---")
        return json.dumps({
            "predicted_stars": 5,
            "explanation": "Mock explanation: Customer showed strong positive sentiment.",
            "ai_summary": "Customer very satisfied with product and service.",
            "ai_recommendations": ["Keep quality consistent", "Reward staff performance"],
            "ai_reply": "Thanks for the glowing review! We’re thrilled you enjoyed it."
        })

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_output_tokens
        }
    }

    attempt = 0
    while attempt <= max_retries:
        try:
            resp = requests.post(GEMINI_URL, json=payload, timeout=timeout)
            # raise for 4xx/5xx
            try:
                resp.raise_for_status()
            except requests.exceptions.HTTPError as http_err:
                status = getattr(resp, "status_code", None)
                text = resp.text[:1000] if resp.text else ""
                # If rate limited, backoff and retry
                if status == 429 and attempt < max_retries:
                    wait = 2 ** attempt
                    print(f"GEMINI 429 received — sleeping {wait}s then retrying (attempt {attempt+1}/{max_retries})")
                    time.sleep(wait)
                    attempt += 1
                    continue
                else:
                    raise RuntimeError(f"HTTP error: {http_err} | status={status} | body={text}")

            # success path
            data = resp.json()
            extracted = _extract_text_from_response_json(data)
            return extracted

        except requests.exceptions.RequestException as e:
            # network or timeout — retry up to max_retries with backoff
            if attempt < max_retries:
                wait = 2 ** attempt
                print(f"Network error calling Gemini: {e}. Retrying in {wait}s (attempt {attempt+1}/{max_retries})")
                time.sleep(wait)
                attempt += 1
                continue
            raise RuntimeError(f"GEMINI request failed after {attempt} retries: {e}")

    # fallback: raise if we exit loop without return
    raise RuntimeError("GEMINI request exhausted retries without success.")