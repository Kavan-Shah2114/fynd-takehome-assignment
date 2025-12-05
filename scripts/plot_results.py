# scripts/plot_results.py
import json
import matplotlib.pyplot as plt

R = json.load(open("task1_results.json"))
prompts = list(R["prompts"].keys())
acc = [R["prompts"][p]["accuracy"] or 0 for p in prompts]
w1  = [R["prompts"][p]["within_one_accuracy"] or 0 for p in prompts]

x = range(len(prompts))
plt.figure(figsize=(6,3))
plt.bar([i-0.15 for i in x], acc, width=0.3, label="Exact acc")
plt.bar([i+0.15 for i in x], w1, width=0.3, label="Within±1")
plt.xticks(x, prompts)
plt.ylabel("Accuracy")
plt.legend()
plt.tight_layout()
plt.savefig("plots/accuracy_compare.png", dpi=150)
print("Saved plots/accuracy_compare.png")