# task1_notebook_script.py (UPDATED: load dataset directly from data/yelp_reviews.csv)
import os
import time
from dotenv import load_dotenv
load_dotenv()

import json
import re
from datetime import datetime, timezone
from collections import Counter

import pandas as pd
from sklearn.metrics import accuracy_score, confusion_matrix

# Import the LLM helper and the model name constant exported by llm_client
from llm_client2 import generate_text, GEMINI_MODEL as LLM_MODEL
from prompts import PROMPT_MAP

# ---------- Config ----------
SAMPLE_SIZE = int(os.environ.get("SAMPLE_SIZE", "200"))
OUTPUT_RESULTS = "task1_results.json"
PROMPT_KEYS = ["base", "fewshot", "rubric_cot"]
PROMPTS = {f"P{i+1}_{k}": PROMPT_MAP.get(k) for i, k in enumerate(PROMPT_KEYS)}

ENSEMBLE_RUNS = int(os.environ.get("ENSEMBLE_RUNS", "1"))
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
PREFERRED_CSV = os.path.join(DATA_DIR, "yelp_reviews.csv")
FALLBACK_CSV = os.path.join(DATA_DIR, "sample_yelp.csv")

# LLM client settings
LLM_TIMEOUT = int(os.environ.get("LLM_TIMEOUT", "20"))  # seconds for each call
LLM_MAX_TOKENS = int(os.environ.get("LLM_MAX_TOKENS", "512"))
LLM_TEMPERATURE = float(os.environ.get("LLM_TEMPERATURE", "0.0"))
# ----------------------------

def load_local_dataset():
    """
    Load dataset from data/ folder. Expect columns 'review_text' and optionally 'true_stars'.
    This function:
     - prefers PREFERRED_CSV (data/yelp_reviews.csv),
     - falls back to sample_yelp.csv if present,
     - raises a clear FileNotFoundError if neither exists.
    It also normalizes common column names to 'review_text' and 'true_stars'.
    """
    csv_path = None
    if os.path.exists(PREFERRED_CSV):
        csv_path = PREFERRED_CSV
    elif os.path.exists(FALLBACK_CSV):
        csv_path = FALLBACK_CSV

    if csv_path is None:
        raise FileNotFoundError(
            f"No dataset found. Place '{os.path.basename(PREFERRED_CSV)}' in the folder: '{DATA_DIR}'. "
            "Your repository must include the CSV file (e.g. data/yelp_reviews.csv)."
        )

    try:
        # Be tolerant: skip bad lines, infer encoding where possible
        df = pd.read_csv(csv_path, encoding="utf-8", on_bad_lines='skip')
    except Exception as e:
        raise RuntimeError(f"Failed to read CSV '{csv_path}': {e}")

    # Normalize common column names to 'review_text' and 'true_stars'
    df = df.rename(columns={
        'text': 'review_text',
        'review': 'review_text',
        'review_text': 'review_text',
        'stars': 'true_stars',
        'rating': 'true_stars'
    }, errors='ignore')

    # If there is a column like 'reviewText' or 'Review', detect it (case-insensitive)
    lower_cols = {c.lower(): c for c in df.columns}
    if 'reviewtext' in lower_cols and 'review_text' not in df.columns:
        df = df.rename(columns={lower_cols['reviewtext']: 'review_text'})
    if 'stars' in lower_cols and 'true_stars' not in df.columns:
        df = df.rename(columns={lower_cols['stars']: 'true_stars'})

    if 'review_text' not in df.columns:
        # attempt more heuristics: pick the longest text-like column
        text_cols = [c for c in df.columns if df[c].dtype == object]
        if not text_cols:
            raise RuntimeError(f"CSV at '{csv_path}' contains no text columns to use as reviews.")
        # choose column with largest average length
        best = max(text_cols, key=lambda c: df[c].astype(str).map(len).mean() if len(df)>0 else 0)
        # warn but proceed
        print(f"[warning] No explicit 'review_text' column. Using '{best}' as review column.")
        df = df.rename(columns={best: 'review_text'})

    # keep only relevant columns
    if 'true_stars' in df.columns:
        df = df[['review_text', 'true_stars']]
    else:
        df = df[['review_text']]

    # drop rows with missing reviews
    df = df.dropna(subset=['review_text']).reset_index(drop=True)

    # quick preview
    print(f"Loaded CSV '{csv_path}' → {len(df)} rows. Preview:")
    preview = df['review_text'].astype(str).head(3).tolist()
    for i, t in enumerate(preview, 1):
        print(f"  {i}. {t[:200].replace('\\n', ' ')}{'...' if len(t)>200 else ''}")

    return df

def extract_star_from_dict_or_text(out):
    """
    Extracts a star rating (1-5) from the prediction output.
    """
    if isinstance(out, dict):
        # Prioritize 'predicted_stars' key
        for k in ("predicted_stars", "predicted_star", "stars", "rating"):
            if k in out:
                try:
                    v = int(out[k])
                    if 1 <= v <= 5:
                        return v
                except Exception:
                    pass
        # Sometimes the model returns nested JSON under 'result' or similar
        for k in ("result", "data", "output"):
            if k in out and isinstance(out[k], (str, dict)):
                sub = extract_star_from_dict_or_text(out[k])
                if sub != -1:
                    return sub
        return -1

    text = str(out or "")
    # Fallback to regex extraction: try to find explicit "predicted_stars: N" or standalone digit 1-5
    patterns = [
        r'["\']?predicted[_\s-]?stars["\']?\s*[:=]\s*([1-5])',
        r'\b([1-5])\b'
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            try:
                val = int(m.group(1))
                if 1 <= val <= 5:
                    return val
            except Exception:
                continue
    return -1

def generate_task1_prediction_local(review_text: str, prompt_template: str):
    """
    Local wrapper to call generate_text() from llm_client.
    - If prompt_template contains '{review}', it will be formatted with that placeholder.
    - Otherwise the review is appended to the prompt_template with a separator.
    - Attempts to parse JSON from the LLM response; if not JSON, returns raw text.
    """
    # Build final prompt
    if not prompt_template:
        prompt = f"Rate the following review from 1 to 5 stars:\n\n{review_text}\n\nReturn a JSON with key 'predicted_stars'."
    else:
        if "{review}" in prompt_template:
            try:
                prompt = prompt_template.format(review=review_text)
            except Exception:
                prompt = f"{prompt_template}\n\nReview:\n{review_text}"
        else:
            prompt = f"{prompt_template}\n\nReview:\n{review_text}"

    try:
        raw = generate_text(prompt, max_output_tokens=LLM_MAX_TOKENS, temperature=LLM_TEMPERATURE, timeout=LLM_TIMEOUT)
    except Exception as e:
        return {"error": f"LLM call failed: {e}"}

    # Try to parse JSON from the response
    if not raw:
        return {"error": "empty_response", "raw": ""}

    if isinstance(raw, (dict, list)):
        return raw

    txt = str(raw).strip()
    # Try to find JSON substring inside text (some LLMs return explanations + JSON)
    try:
        json_obj = json.loads(txt)
        return json_obj
    except Exception:
        start = txt.find("{")
        end = txt.rfind("}") + 1
        if start != -1 and end != -1 and end > start:
            try:
                candidate = txt[start:end]
                json_obj = json.loads(candidate)
                return json_obj
            except Exception:
                pass

    # fallback: return raw text
    return {"raw_text": txt}

def generate_majority_prediction(review_text: str, prompt_template: str, runs: int = ENSEMBLE_RUNS):
    """
    Call the local generate_task1_prediction multiple times and return majority vote plus raw outputs.
    """
    raws = []
    preds = []
    for _ in range(runs):
        out = generate_task1_prediction_local(review_text, prompt_template)
        raws.append(out)
        p = extract_star_from_dict_or_text(out)
        preds.append(p if p != -1 else None)

    # majority vote among non-None
    counts = Counter([p for p in preds if p is not None])
    if counts:
        return counts.most_common(1)[0][0], raws

    # fallback: -1
    return -1, raws

def within_one_accuracy(true_list, pred_list):
    """Compute within-1 accuracy over valid pairs."""
    valid_pairs = [(t, p) for t, p in zip(true_list, pred_list) if isinstance(t, int) and 1 <= t <=5 and isinstance(p, int) and 1 <= p <=5]
    if not valid_pairs:
        return None
    valid = sum(1 for t,p in valid_pairs if abs(t - p) <= 1)
    return valid / len(valid_pairs)

def run():
    print("Loading dataset from data/ ...")
    df = load_local_dataset()

    n = min(SAMPLE_SIZE, len(df))
    sample_df = df.drop_duplicates(subset=['review_text']).sample(n=n, random_state=42).reset_index(drop=True)
    print(f"Loaded {len(df)} rows; sampling n={n}")
    
    # Print which LLM model string is being used (imported from llm_client)
    print(f"Using LLM Model: {LLM_MODEL}")

    results = {
        "metadata": {"sample_size": n, "generated_at": datetime.now(timezone.utc).isoformat()},
        "prompts": {}
    }

    # Iterate over prompts
    for name, prompt_template in PROMPTS.items():
        if not prompt_template:
            print(f"Skipping prompt '{name}': Template value is None. Check PROMPT_MAP keys in prompts.py.")
            continue
            
        print(f"\n--- Running Prompt: {name} ---")
        preds = []
        raw_examples = []
        parsed_count = 0

        for i, row in sample_df.iterrows():
            review = str(row.get("review_text", ""))
            try:
                # Use the majority prediction helper for ensemble runs
                pred, raws = generate_majority_prediction(review, prompt_template, runs=ENSEMBLE_RUNS)
            except Exception as e:
                print(f"[warning] LLM call failed at idx={i}: {e}")
                pred, raws = -1, [{}]

            # Store the first run's raw output for examples
            raw_examples.append(raws[0] if raws else {})
            
            if isinstance(pred, int) and 1 <= pred <= 5:
                parsed_count += 1
            preds.append(pred if isinstance(pred, int) else -1)

            # --- RATE LIMITING (GEMINI FREE TIER FIX) ---
            # Sleep 4 seconds to ensure we stay under ~15 RPM (60s/15 = 4s)
            time.sleep(4)

            if (i + 1) % 50 == 0 or (i + 1) == n:
                print(f"  Processed {i+1}/{n}")

        # --- Metrics Calculation ---
        acc, w1, cm = None, None, None
        
        if 'true_stars' in sample_df.columns:
            true_list = []
            for v in sample_df['true_stars'].tolist()[:len(preds)]:
                try:
                    iv = int(v)
                    true_list.append(iv if 1 <= iv <= 5 else -1)
                except Exception:
                    true_list.append(-1)

            valid_idx = [i for i, (t, p) in enumerate(zip(true_list, preds)) if isinstance(t, int) and 1 <= t <=5 and isinstance(p, int) and 1 <= p <=5]
            
            if valid_idx:
                y_true = [true_list[i] for i in valid_idx]
                y_pred = [preds[i] for i in valid_idx]
                try:
                    acc = accuracy_score(y_true, y_pred)
                    cm = confusion_matrix(y_true, y_pred, labels=[1,2,3,4,5])
                    w1 = within_one_accuracy(y_true, y_pred)
                except Exception as e:
                    print(f"[warning] metrics failed for prompt={name}: {e}")

        results["prompts"][name] = {
            "parsed_count": parsed_count,
            "parsed_percent": parsed_count / len(preds) if preds else 0.0,
            "accuracy": acc,
            "within_one_accuracy": w1,
            "confusion": cm.tolist() if cm is not None else None,
            "raw_outputs_example": raw_examples[:3]
        }
        print(f"{name} -> parsed {parsed_count}/{len(preds)} ({results['prompts'][name]['parsed_percent']:.2%}) "
              f"accuracy={acc} within±1={w1}")

    # Ensure output folder exists if OUTPUT_RESULTS contains a path
    output_dir = os.path.dirname(OUTPUT_RESULTS)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        
    # save results
    with open(OUTPUT_RESULTS, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\nSaved results -> {OUTPUT_RESULTS}")
    print("=== Summary ===")
    for k, v in results['prompts'].items():
        print(f"- {k}: Acc={v['accuracy']} | Parsed={v['parsed_percent']:.2%}")


if __name__ == "__main__":
    run()