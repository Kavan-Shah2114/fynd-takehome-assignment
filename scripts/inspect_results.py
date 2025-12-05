# scripts/inspect_results.py
import json, pandas as pd
from sklearn.metrics import confusion_matrix

R = json.load(open("task1_results.json", "r", encoding="utf-8"))
# pick prompt used for final analysis (e.g. "base")
prompt = "base"
res = R["prompts"][prompt]
print("Parsed %:", res["parsed_count"], "/", R["meta"]["sample_size"])
print("Accuracy:", res["accuracy"])
print("Within±1:", res["within_one_accuracy"])
# If you saved confusion as list, print nicely (if present)
if res.get("confusion"):
    cm = pd.DataFrame(res["confusion"], index=[1,2,3,4,5], columns=[1,2,3,4,5])
    print("Confusion matrix:\n", cm)