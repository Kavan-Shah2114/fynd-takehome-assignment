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
You are an AI operations analyst. Evaluate a customer's review + rating.

Input:
- Review: "{user_review}"
- User Rating: {user_rating}

Return ONLY a JSON object with:

predicted_stars : integer 1–5  
explanation : 10–20 words  
ai_summary : 15-word summary  
ai_recommendations : array of 2–3 short business improvement actions  
ai_reply : friendly 1–2 sentence response for customer

RULES:
- DO NOT wrap output inside ```json
- DO NOT add commentary outside JSON
- Output MUST be pure JSON

Generate the JSON now.
"""