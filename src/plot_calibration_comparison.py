import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv("../data/benchmark_results.csv")

model_order = ["xgboost", "lightgbm", "random_forest", "gru"]
model_labels = ["XGBoost", "LightGBM", "Random Forest", "GRU"]
model_colors = ["#E24A33", "#348ABD", "#988ED5", "#2ECC40"]

panels = [
    {"key": ("within", "nasa"),           "title": "NASA (within)"},
    {"key": ("within", "calce"),          "title": "CALCE (within)"},
    {"key": ("train_nasa_no_soh", "oxford"), "title": "NASA\u2192Oxford no SOH"},
]

fig, axes = plt.subplots(1, 3, figsize=(13, 3.5))

for ax, panel in zip(axes, panels):
    eval_type, ds = panel["key"]
    sub = df[(df["eval"] == eval_type) & (df["dataset"] == ds)]
    for i, model in enumerate(model_order):
        msub = sub[sub["model"] == model]
        iso_row = msub[msub["method"] == "iso"].sort_values("H")
        pla_row = msub[msub["method"] == "platt"].sort_values("H")
        ax.plot(iso_row["H"], iso_row["Brier_cal"],
                linestyle="--", marker="o", color=model_colors[i],
                label=f"{model_labels[i]} iso")
        ax.plot(pla_row["H"], pla_row["Brier_cal"],
                linestyle="-",  marker="s", color=model_colors[i],
                label=f"{model_labels[i]} Platt")
    ax.set_xlabel("Horizon H (cycles)", fontsize=10)
    ax.set_ylabel("Brier (calibrated)", fontsize=10)
    ax.set_title(panel["title"], fontsize=11, pad=8)
    ax.legend(fontsize=6, loc="upper right", ncol=1)
    ax.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig("../data/calibration_comparison.png", dpi=300, bbox_inches="tight")
print("Saved: ../data/calibration_comparison.png")
