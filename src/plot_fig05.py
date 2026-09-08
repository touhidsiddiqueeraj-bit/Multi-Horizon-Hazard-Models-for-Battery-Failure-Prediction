"""Generate Fig05: Multi-horizon AUC curves (NASA, Platt calibrated)"""
import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv("../data/benchmark_results.csv")

sub = df[(df["eval"] == "within") & (df["dataset"] == "nasa") & (df["method"] == "platt")]

model_order = ["xgboost", "lightgbm", "random_forest", "gru"]
model_labels = ["XGBoost", "LightGBM", "Random Forest", "GRU"]
model_colors = ["#E24A33", "#348ABD", "#988ED5", "#2ECC40"]

fig, ax = plt.subplots(figsize=(5, 3.2))

for i, model in enumerate(model_order):
    msub = sub[sub["model"] == model].sort_values("H")
    ax.plot(msub["H"], msub["AUC_cal"], marker="s", color=model_colors[i],
            label=model_labels[i])

ax.set_xlabel("Horizon H (cycles)", fontsize=10, fontweight="bold")
ax.set_ylabel("AUC (calibrated, Platt)", fontsize=10, fontweight="bold")
ax.set_title("Multi-Horizon AUC — NASA (Platt cal.)", fontsize=11, pad=8, fontweight="bold")
ax.legend(fontsize=9)
for text in ax.legend().get_texts():
    text.set_fontweight("bold")
ax.grid(True, alpha=0.3)
ax.set_ylim(0.75, 0.95)
ax.set_xticks([10, 20, 30, 50])
ax.tick_params(axis="both", which="major", labelsize=9)
for label in ax.get_xticklabels() + ax.get_yticklabels():
    label.set_fontweight("bold")

plt.tight_layout()
plt.savefig("../data/Fig05_MultiHorizon_AUC.png", dpi=600, bbox_inches="tight")
print("Saved: Fig05_MultiHorizon_AUC.png")
