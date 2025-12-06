
import pandas as pd
import json

# Mock data simulating mixed types causing PyArrow crash
data = [
    {"id": 1, "rating": 5, "review": "Great!", "admin_json": '{"predicted_stars": 5}'},
    {"id": 2, "rating": 3, "review": "Okay.", "admin_json": '{"predicted_stars": "N/A"}'},
    {"id": 3, "rating": 1, "review": "Bad.", "admin_json": '{}'} # Missing key
]

def safe_parse_json(text):
    if isinstance(text, dict): return text
    if not text: return {}
    try: return json.loads(text)
    except: return {}

print("Processing mock submissions...")
df = pd.DataFrame(data)
df["ai_admin_json"] = df.get("admin_json", "{}")
df["parsed_admin"] = df["ai_admin_json"].apply(safe_parse_json)

# Simulate the processing logic from admin_dashboard.py
try:
    df["predicted_stars"] = df["parsed_admin"].apply(
        lambda x: x.get("predicted_stars", "N/A")
    ).astype(str)
    
    print("Column 'predicted_stars' created. Dtypes:")
    print(df.dtypes)
    
    # Simulate display dataframe creation
    display_df = df[[
        "id",
        "rating",
        "review",
        "predicted_stars"
    ]].copy()
    display_df["predicted_stars"] = display_df["predicted_stars"].astype(str)
    
    print("\nDisplay DataFrame 'predicted_stars' values:")
    print(display_df["predicted_stars"])
    
    # Check if pyarrow (if available) would accept it
    try:
        import pyarrow as pa
        table = pa.Table.from_pandas(display_df)
        print("\nPyArrow conversion SUCCESS!")
    except ImportError:
        print("\nPyArrow not installed, skipping pyarrow check.")
    except Exception as e:
        print(f"\nPyArrow conversion FAILED: {e}")

except Exception as e:
    print(f"Processing failed: {e}")
