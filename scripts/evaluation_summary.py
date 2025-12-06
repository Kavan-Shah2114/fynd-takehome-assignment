# scripts/evaluation_summary.py
import json
import statistics
from collections import Counter

IN = "task1_results.json"
OUT_JSON = "evaluation_summary.json"
OUT_MD = "evaluation_table.md"

def is_valid_json_and_star(s):
    if not s or not isinstance(s, str):
        return False, None
    try:
        j = json.loads(s)
        if isinstance(j, dict) and "predicted_stars" in j:
            try:
                v = int(j["predicted_stars"])
                return 1 <= v <= 5, v
            except Exception:
                return False, None
        # if top-level has numeric value somewhere
        return False, None
    except Exception:
        return False, None

R = json.load(open(IN, "r", encoding="utf-8"))
prompts = list(R.get("prompts", {}).keys())

table = []
summary = {"prompts": {}}

for p in prompts:
    info = R["prompts"][p]
    raws = info.get("raws", [])
    # RAWS may be only 3 samples in current script. If you stored full raw outputs, use that; else re-run with full raw capture.
    # But task1_results.json probably contains raws for sampled items under 'raws' or 'raw_outputs_example'.
    # We'll try both keys:
    raw_examples = info.get("raws") or info.get("raw_outputs_example") or []
    # Compute JSON validity rate over the stored raw_examples (best-effort)
    valid_count = 0
    total = len(raw_examples)
    extracted_stars = []
    for r in raw_examples:
        ok, v = is_valid_json_and_star(r)
        if ok:
            valid_count += 1
            extracted_stars.append(v)
    json_validity = (valid_count / total) if total>0 else None

    # If your saved file doesn't include per-run raw outputs for each sample, we can only compute validity on examples.
    # For reliability (consensus) we need per-sample per-run outputs — if you collected those, add them as 'all_raws' in results.
    # We will compute consensus if 'all_raws' exists:
    consensus = None
    if "all_raws" in info:
        # info["all_raws"] should be list of lists: per-sample list of raw outputs from each run
        per_sample = info["all_raws"]
        agrees = 0
        for sample_runs in per_sample:
            preds = []
            for r in sample_runs:
                ok, v = is_valid_json_and_star(r)
                preds.append(v if ok else None)
            # consensus if all non-None identical
            nonnull = [x for x in preds if x is not None]
            if nonnull and all(x==nonnull[0] for x in nonnull):
                agrees += 1
        consensus = agrees / len(per_sample) if len(per_sample)>0 else None

    # gather metrics we already have: accuracy, within_one
    acc = info.get("accuracy")
    w1 = info.get("within_one_accuracy")
    table.append({
        "prompt": p,
        "accuracy": acc,
        "within_one": w1,
        "json_validity": json_validity,
        "consensus": consensus
    })
    summary["prompts"][p] = {
        "accuracy": acc,
        "within_one": w1,
        "json_validity": json_validity,
        "consensus": consensus
    }

# Write json summary
with open(OUT_JSON,"w",encoding="utf-8") as f:
    json.dump(summary,f,indent=2,ensure_ascii=False)

# Write markdown table
lines = []
lines.append("| Prompt | Exact Acc | Within±1 | JSON validity (sample) | Consensus (if computed) |")
lines.append("|---|---:|---:|---:|---:|")
for t in table:
    lines.append(f"| {t['prompt']} | {t['accuracy']} | {t['within_one']} | {t['json_validity']} | {t['consensus']} |")

md = "\n".join(lines)
open(OUT_MD,"w",encoding="utf-8").write(md)
print("Wrote", OUT_JSON, "and", OUT_MD)
print(md)