"""Generate Fig02: Isotonic vs Platt calibration comparison (2 panels: NASA + CALCE)"""
import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv("../data/benchmark_results.csv")

model_order = ["xgboost", "lightgbm", "random_forest", "gru"]
model_labels = ["XGBoost", "LightGBM", "Random Forest", "GRU"]
model_colors = ["#E24A33", "#348ABD", "#988ED5", "#2ECC40"]

fig, axes = plt.subplots(1, 2, figsize=(9, 3.2))

for ax, (eval_type, ds, title) in zip(axes, [
    ("within", "nasa", "NASA"),
    ("within", "calce", "CALCE"),
]):
    sub = df[(df["eval"] == eval_type) & (df["dataset"] == ds)]
    for i, model in enumerate(model_order):
        msub = sub[sub["model"] == model]
        iso = msub[msub["method"] == "iso"].sort_values("H")
        pla = msub[msub["method"] == "platt"].sort_values("H")
        ax.plot(iso["H"], iso["Brier_cal"], linestyle="--", marker="o",
                color=model_colors[i], label=f"{model_labels[i]} iso")
        ax.plot(pla["H"], pla["Brier_cal"], linestyle="-", marker="s",
                color=model_colors[i], label=f"{model_labels[i]} Platt")
    ax.set_xlabel("Horizon H (cycles)", fontsize=10)
    ax.set_ylabel("Brier (calibrated)", fontsize=10)
    ax.set_title(title, fontsize=11, pad=8)
    ax.legend(fontsize=6.5, loc="upper right", ncol=1)
    ax.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig("../data/Fig02_Calibration_Comparison.png", dpi=300, bbox_inches="tight")
print("Saved: Fig02_Calibration_Comparison.png")
