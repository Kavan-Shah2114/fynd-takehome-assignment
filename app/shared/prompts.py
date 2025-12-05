# app/shared/prompts.py

# --- Task1: Strict prompts ---
BASE_STRICT = """
You are a classifier. Input is a single customer review. Return ONLY a JSON object with two fields:
{
  "predicted_stars": <integer 1-5>,
  "explanation": "<one-sentence justification, 6-15 words>"
}
Choose the single best integer according to this rule:
- 5 = explicit praise and recommendation ("highly recommend", "best", "loved")
- 4 = mostly positive with small complaint
- 3 = mixed or neutral ("okay", "average", "not bad")
- 2 = negative but not catastrophic
- 1 = extreme negative or safety issue
Review: "{review_text}"
Return valid JSON only, nothing else.
"""

FEWSHOT_STRICT = """
You are a classifier. Return ONLY a JSON object like:
{"predicted_stars": <1-5>, "explanation": "short reason"}.

Examples:
Review: "Amazing pizza — best in town, will come again." -> {"predicted_stars": 5, "explanation": "explicit praise and recommendation"}
Review: "Good food but a bit slow service." -> {"predicted_stars": 4, "explanation": "mostly positive with small complaint"}
Review: "Okay place; nothing special." -> {"predicted_stars": 3, "explanation": "neutral/mixed comments"}
Review: "Bad experience, food was cold." -> {"predicted_stars": 2, "explanation": "negative but not extreme"}
Review: "I got food poisoning, never again." -> {"predicted_stars": 1, "explanation": "severe negative/safety issue"}

Now classify the review below:
Review: "{review_text}"
Return ONLY valid JSON.
"""

RUBRIC_STRICT = """
You are a classifier that must follow this rubric EXACTLY:
- 5: glowing recommendation, words like 'best', 'highly recommend', 'loved'
- 4: mostly positive, minor complaint
- 3: neutral or mixed language e.g., 'okay', 'average'
- 2: negative, dissatisfaction
- 1: severe negative, health/safety or strong condemnation
Review: "{review_text}"
Return ONLY: {"predicted_stars": <1-5>, "explanation": "<1-line reason>"}
"""

# --- Task2 (app/backend) prompts ---
USER_REPLY_PROMPT = """
You are a friendly customer-support AI who replies briefly to a review, thanking the user and summarizing next steps.
Return only a short 1-2 sentence reply.
Review: "{user_review}"
User rating: {user_rating}
"""

ADMIN_JSON_PROMPT = """
You are an assistant that reads a user review and outputs JSON with fields:
{
  "ai_summary": "1-2 line summary of the review",
  "ai_recommendations": ["Actionable bullet 1", "Actionable bullet 2"]
}
Review: "{user_review}"
Rating: {user_rating}
Return ONLY valid JSON.
"""

DEBUG_PROMPT = """
Review: "{review_text}"
Return a one-line label: positive / neutral / negative
"""