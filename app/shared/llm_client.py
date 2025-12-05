# app/shared/llm_client.py
import os, json, random

# If MOCK_LLM=1, use mocked responses (no network calls).
MOCK = os.getenv("MOCK_LLM", "0") == "1"

def _mock_response(prompt: str) -> str:
    text = prompt.lower()
    # simple heuristics for demo responses
    if any(w in text for w in ["terrible", "worst", "sick", "poison"]):
        s = 1
    elif any(w in text for w in ["not bad", "okay", "average"]):
        s = 3
    elif any(w in text for w in ["good", "great", "loved", "excellent", "amazing"]):
        s = 5
    else:
        s = random.choice([2,3,4])
    return json.dumps({
        "predicted_stars": s,
        "explanation": f"Mocked: detected cues -> assigned {s} star(s)."
    })

def generate_text(prompt: str, max_output_tokens: int = 256, debug: bool = False) -> str:
    if MOCK:
        return _mock_response(prompt)
    # If mock disabled and real call required, raise a clear error
    raise RuntimeError("Real LLM disabled in mock client. Set MOCK_LLM=1 to use mocked responses.")