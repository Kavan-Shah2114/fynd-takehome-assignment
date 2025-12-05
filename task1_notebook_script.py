# task1_notebook_script.py

import os
from dotenv import load_dotenv
load_dotenv()  

import json
import re
from datetime import datetime
from collections import Counter

import pandas as pd
from sklearn.metrics import accuracy_score, confusion_matrix

from app.shared.data_io import load_dataset
from app.shared.llm_client import generate_text
from app.shared.prompts import BASE_STRICT, FEWSHOT_STRICT, RUBRIC_STRICT

from datetime import timezone

# ---------- Config ----------
SAMPLE_SIZE = int(os.environ.get("SAMPLE_SIZE", "200"))
OUTPUT_RESULTS = "task1_results.json"
PROMPTS = {
    "base": BASE_STRICT,
    "fewshot": FEWSHOT_STRICT,
    "rubric": RUBRIC_STRICT
}
ENSEMBLE_RUNS = int(os.environ.get("ENSEMBLE_RUNS", "3"))
# ----------------------------

def extract_star(text: str):
    """Extract predicted star 1-5 from model output. Return int 1-5 or -1 if not found."""
    if not text or not isinstance(text, str):
        return -1
    # try JSON parse
    try:
        j = json.loads(text)
        if isinstance(j, dict):
            for k in ("predicted_stars", "predicted_star", "stars", "rating"):
                if k in j:
                    try:
                        v = int(j[k])
                        if 1 <= v <= 5:
                            return v
                    except Exception:
                        pass
            for v in j.values():
                if isinstance(v, (int, float)) and 1 <= int(v) <= 5:
                    return int(v)
    except Exception:
        pass
    # regex fallback
    patterns = [
        r'["\']?predicted[_\s-]?stars["\']?\s*[:=]\s*([1-5])',
        r'["\']?stars["\']?\s*[:=]\s*([1-5])',
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

def generate_majority(prompt: str, runs: int = ENSEMBLE_RUNS):
    """Call generate_text multiple times and return majority predicted_star and raw outputs."""
    raws = []
    preds = []
    for _ in range(runs):
        out = generate_text(prompt)
        raws.append(out)
        p = extract_star(out)
        preds.append(p if p != -1 else None)
    # majority vote ignoring None
    counts = Counter([p for p in preds if p is not None])
    if counts:
        most_common = counts.most_common(1)[0][0]
        return most_common, raws
    # fallback: choose first non-None, else -1
    for p in preds:
        if p is not None:
            return p, raws
    return -1, raws

def within_one_accuracy(true_list, pred_list):
    total = 0
    valid = 0
    for t, p in zip(true_list, pred_list):
        if t == -1:
            continue
        total += 1
        if p == -1:
            continue
        if abs(t - p) <= 1:
            valid += 1
    return (valid / total) if total > 0 else None

def run():
    print("=== Task1: loading dataset ===")
    df = load_dataset()
    if df is None or df.shape[0] == 0:
        raise SystemExit("No data loaded. Put data/yelp_reviews.csv or data/sample_yelp.csv in the data/ folder.")

    n = min(SAMPLE_SIZE, len(df))
    sample_df = df.sample(n=n, random_state=42).reset_index(drop=True)
    print(f"Loaded dataset rows={len(df)} — sampling n={n}")

    results = {"meta": {"generated_at": datetime.now(timezone.utc).isoformat(), "sample_size": n}, "prompts": {}}

    for name, template in PROMPTS.items():
        print(f"\n--- Running prompt: {name} ---")
        preds = []
        raw_examples = []
        parsed_count = 0

        for idx, row in sample_df.iterrows():
            review = str(row.get("review_text", ""))
            prompt = template.replace("{review_text}", review)
            try:
                pred, raws = generate_majority(prompt, runs=ENSEMBLE_RUNS)
            except Exception as e:
                # keep going on error, record empty
                print(f"[warning] LLM call failed at idx={idx}: {e}")
                pred, raws = -1, [""]
            raw_examples.append(raws[0] if raws else "")
            if 1 <= pred <= 5:
                parsed_count += 1
            preds.append(pred if pred != -1 else -1)

        # compute accuracy & within-one
        acc = None
        cm = None
        w1 = None
        if "true_stars" in sample_df.columns:
            true_list = sample_df["true_stars"].fillna(-1).astype(int).tolist()
            if len(true_list) != len(preds):
                true_list = true_list[:len(preds)]
            try:
                acc = accuracy_score(true_list, preds)
                cm = confusion_matrix(true_list, preds, labels=[1,2,3,4,5])
                w1 = within_one_accuracy(true_list, preds)
            except Exception:
                acc = None
                cm = None
                w1 = None

        results["prompts"][name] = {
            "parsed_count": parsed_count,
            "parsed_percent": parsed_count / len(preds) if len(preds) > 0 else 0.0,
            "accuracy": acc,
            "within_one_accuracy": w1,
            "confusion": cm.tolist() if cm is not None else None,
            "raw_outputs_example": raw_examples[:3]
        }
        print(f"{name} -> parsed {parsed_count}/{len(preds)} ({results['prompts'][name]['parsed_percent']:.2%})  "
              f"accuracy={acc}  within±1={w1}")

    # save compact results
    with open(OUTPUT_RESULTS, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\nSaved results -> {OUTPUT_RESULTS}")
    print("=== Summary ===")
    for k, v in results["prompts"].items():
        print(f" {k}: parsed%={v['parsed_percent']:.2%}  accuracy={v['accuracy']}  within±1={v['within_one_accuracy']}")

if __name__ == "__main__":
    run()