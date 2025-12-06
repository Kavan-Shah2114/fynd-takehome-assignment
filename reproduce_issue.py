
from prompts import ADMIN_FULLJSON_PROMPT

try:
    print("Attempting to format prompt imported from prompts.py...")
    formatted = ADMIN_FULLJSON_PROMPT.format(user_review="Test review", user_rating=5)
    print("Formatting successful!")
    print(formatted[:100] + "...")
except Exception as e:
    print(f"Caught error: {repr(e)}")
