# prompts.py
# ============================================
# TASK 1 PROMPTS (STRICT JSON STAR PREDICTION)
# ============================================

# 1. BASE STRICT PROMPT
BASE_STRICT = """
You are a highly concise star rating classifier. Your task is to analyze a customer review and assign a star rating (1–5).

Return ONLY a JSON object with these keys:
  predicted_stars: integer 1–5
  explanation: one short sentence (6–16 words)

Rating Logic:
5 = strong praise or explicit recommendation
4 = positive with a minor issue
3 = neutral or mixed
2 = multiple issues or clearly negative
1 = severe failure or danger

Review: "{review_text}"
Return ONLY valid JSON with no extra text.
"""

# 2. FEWSHOT STRICT PROMPT
FEWSHOT_STRICT = """
You are a reliable star rating classifier. Analyze the review and assign a rating (1–5).

Return ONLY a JSON object with:
  predicted_stars: int
  explanation: short reason

Examples:
Review: "Amazing food, loved everything!"
Output: { "predicted_stars": 5, "explanation": "Strong praise and clear satisfaction." }

Review: "Food was good but service slow."
Output: { "predicted_stars": 4, "explanation": "Positive overall with a minor issue." }

Review: "Not bad, not great."
Output: { "predicted_stars": 3, "explanation": "Neutral, average experience." }

Review: "Wrong order, rude staff."
Output: { "predicted_stars": 2, "explanation": "Multiple service problems." }

Review: "Hair in my food, horrible hygiene."
Output: { "predicted_stars": 1, "explanation": "Severe hygiene violation." }

Review: "{review_text}"
Return ONLY valid JSON.
"""

# 3. RUBRIC-STRICT PROMPT (Chain-of-thought structured)
RUBRIC_STRICT = """
You are an expert review classifier. Rate the review using the rubric:

1 star: severe issue, danger, sickness, strong negative
2 stars: major problems, rude service, multiple complaints
3 stars: mixed or neutral
4 stars: mostly positive, small issue
5 stars: strong praise, highly positive

Return ONLY JSON:
{
  "predicted_stars": (1–5),
  "explanation": "short justification"
}

Review: "{review_text}"

Return ONLY valid JSON with no explanations.
"""

# ===================================================
# TASK 1 PROMPT MAP (required by task1 script)
# ===================================================
PROMPT_MAP = {
    "base": BASE_STRICT,
    "fewshot": FEWSHOT_STRICT,
    "rubric_cot": RUBRIC_STRICT
}

# ===================================================
# TASK 2 PROMPT (ADMIN + USER DASHBOARD)
# ===================================================
ADMIN_FULLJSON_PROMPT = """
You are a helpful assistant that must analyze a single customer review and return a JSON object ONLY (no extra text).
Do NOT output any explanation outside the JSON. The JSON must be valid and parsable by a strict JSON parser.

Input fields:
- user_review: the text of the customer's review (string)
- user_rating: the numeric rating the user supplied (integer 1-5)

Return EXACTLY one JSON object with the following keys (use these exact key names):

{{
  "predicted_stars": integer between 1 and 5,
  "explanation": string (10-40 words) - short reasoning why the predicted_stars was chosen,
  "ai_summary": string (10-20 words) - a concise summary of the review,
  "ai_recommendations": array of 2-4 short recommendation strings (each 3-10 words),
  "ai_reply": string (10-40 words) - friendly reply to the customer,
}}

Rules:
1. Output MUST be **only** the JSON object (no surrounding backticks, no markdown, no commentary).
2. All fields MUST be non-empty. If you cannot infer a meaningful recommendation, return "No recommendation available" as an item in the array.
3. predicted_stars MUST be your model's best prediction (do not copy user_rating unless the review strongly supports it).
4. Use temperature 0.0 behavior (deterministic).
5. Keep explanation/summary concise and factual; do NOT hallucinate facts.

Example output (for guidance only):
{{
  "predicted_stars": 2,
  "explanation": "Food was cold on arrival and staff were unresponsive, indicating poor service quality.",
  "ai_summary": "Cold food and slow, unhelpful service.",
  "ai_recommendations": ["Improve delivery packaging", "Train staff on response times"],
  "ai_reply": "We're sorry your experience was poor — we'll investigate and improve our service."
}}

Now produce the JSON for the following input:
user_review: \"{user_review}\"
user_rating: {user_rating}
"""