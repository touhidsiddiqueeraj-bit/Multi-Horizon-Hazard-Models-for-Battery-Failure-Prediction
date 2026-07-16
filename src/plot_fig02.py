"""Generate Fig02a (NASA) and Fig02b (CALCE): Platt vs Isotonic calibration comparison"""
import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv("../data/benchmark_results.csv")

model_order = ["xgboost", "lightgbm", "random_forest", "gru"]
model_labels = ["XGBoost", "LightGBM", "Random Forest", "GRU"]
model_colors = ["#E24A33", "#348ABD", "#988ED5", "#2ECC40"]

for eval_type, ds, title, out in [
    ("within", "nasa", "NASA", "../data/Fig02a_Calibration_NASA.png"),
    ("within", "calce", "CALCE", "../data/Fig02b_Calibration_CALCE.png"),
]:
    fig, ax = plt.subplots(figsize=(5, 3.2))
    sub = df[(df["eval"] == eval_type) & (df["dataset"] == ds)]
    for i, model in enumerate(model_order):
        msub = sub[sub["model"] == model]
        iso = msub[msub["method"] == "iso"].sort_values("H")
        pla = msub[msub["method"] == "platt"].sort_values("H")
        ax.plot(iso["H"], iso["Brier_cal"], linestyle="--", marker="o",
                color=model_colors[i], label=f"{model_labels[i]} iso")
        ax.plot(pla["H"], pla["Brier_cal"], linestyle="-", marker="s",
                color=model_colors[i], label=f"{model_labels[i]} Platt")
    ax.set_xlabel("Horizon H (cycles)", fontsize=10, fontweight="bold")
    ax.set_ylabel("Brier (calibrated)", fontsize=10, fontweight="bold")
    ax.set_title(title, fontsize=11, pad=8, fontweight="bold")
    leg = ax.legend(fontsize=5.5, loc="upper right", ncol=2, handlelength=1.2, handletextpad=0.5, columnspacing=0.8)
    leg.get_frame().set_linewidth(0.5)
    for text in leg.get_texts():
        text.set_fontweight("bold")
    ax.grid(True, alpha=0.3)
    ax.tick_params(axis="both", which="major", labelsize=9)
    for label in ax.get_xticklabels() + ax.get_yticklabels():
        label.set_fontweight("bold")
    plt.tight_layout()
    plt.savefig(out, dpi=600, bbox_inches="tight")
    print(f"Saved: {out}")
