# llm_client.py (UPDATED generate_text)
import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

MOCK = os.environ.get("MOCK_LLM", "0") == "1"

OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.1")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434/api/generate")

def generate_text(prompt: str, max_output_tokens=512, temperature: float = 0.0, timeout: int = 120) -> str:
    """
    Handles API calls to the LLM endpoint (configured for Ollama by default) or returns a mock response.
    Tries streaming first; if response yields nothing, falls back to full body read.
    """
    if MOCK:
        print("--- LLM CLIENT: Returning Mock Response (MOCK_LLM='1') ---")
        return json.dumps({
            "predicted_stars": 4,
            "explanation": "Mock response: Assumed positive experience for demonstration.",
            "ai_summary": "The user provided a generic, positive review.",
            "ai_recommendations": ["Acknowledge feedback.", "No action required."],
            "ai_reply": "Thank you so much for your positive review! We are glad you enjoyed your experience. We have logged your feedback internally."
        })

    url = os.environ.get("OLLAMA_URL", OLLAMA_URL)
    model = os.environ.get("OLLAMA_MODEL", OLLAMA_MODEL)

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": True,
        "options": {
            "temperature": temperature,
            "num_predict": int(max_output_tokens)
        }
    }

    try:
        # Try streaming
        r = requests.post(url, json=payload, stream=True, timeout=timeout)
        r.raise_for_status()

        full_text = ""
        try:
            for raw_line in r.iter_lines(decode_unicode=True, chunk_size=1024):
                if not raw_line:
                    continue
                # attempt to parse JSON chunk
                try:
                    chunk = json.loads(raw_line)
                except Exception:
                    # non-JSON chunk: append raw
                    full_text += raw_line
                    continue

                resp_piece = chunk.get("response") or ""
                if isinstance(resp_piece, str) and resp_piece:
                    full_text += resp_piece

                if chunk.get("done") is True:
                    break
        except Exception:
            # If streaming iteration fails, fall back to full text
            full_text = r.text

        # fallback
        if not full_text:
            full_text = r.text or ""

        return full_text

    except requests.exceptions.RequestException as req_exc:
        error_msg = f"LLM Client FATAL ERROR: Could not connect to LLM service at {url}. Ensure Ollama/Gemini is running. Error: {req_exc}"
        print(error_msg)
        raise RuntimeError(error_msg) from req_exc