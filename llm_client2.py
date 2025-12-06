# llm_client2.py (GEMINI VERSION)
import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

MOCK = os.environ.get("MOCK_LLM", "0") == "1"

# GEMINI CONFIG
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", None)

if not MOCK and not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY not found in .env file!")

# Google REST endpoint for Gemini
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"

def generate_text(prompt: str, max_output_tokens=512, temperature: float = 0.0, timeout: int = 120):
    """
    Sends prompt to Gemini API using REST.
    Returns the text output from the model.
    """

    # --------------------------
    # MOCK MODE
    # --------------------------
    if MOCK:
        print("--- GEMINI CLIENT: Returning Mock Response (MOCK_LLM='1') ---")
        return json.dumps({
            "predicted_stars": 5,
            "explanation": "Mock explanation.",
            "ai_summary": "Mock summary.",
            "ai_recommendations": ["Mock recommendation 1"],
            "ai_reply": "Thank you for your feedback! (MOCK)"
        })

    # --------------------------
    # GEMINI API PAYLOAD
    # --------------------------
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

    try:
        response = requests.post(
            GEMINI_URL,
            json=payload,
            timeout=timeout
        )
        response.raise_for_status()

        data = response.json()

        # Extract text
        try:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except Exception:
            return json.dumps(data)

    except requests.exceptions.RequestException as req_exc:
        error_msg = (
            f"GEMINI Client ERROR: Could not connect to Gemini service. "
            f"Error: {req_exc}"
        )
        print(error_msg)
        raise RuntimeError(error_msg)