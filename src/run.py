"""Orchestration script: run experiments, generate figures, then produce paper + presentation."""
import subprocess
import sys
import os

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(PROJECT)

# ── Bootstrap check ─────────────────────────────────────────────────────
missing = []
for mod_name in ["pandas", "numpy", "xgboost", "lightgbm", "torch", "shap",
                  "sklearn", "matplotlib", "seaborn", "docx", "pptx"]:
    try:
        __import__(mod_name)
    except ImportError:
        missing.append(mod_name)

if missing:
    print(f"Missing dependencies: {missing}")
    print("Run: pip install -r requirements.txt")
    sys.exit(1)

for csv_file in ["data/nasa_clean_filtered.csv", "data/calce_clean.csv", "data/oxford_clean.csv"]:
    if not os.path.exists(csv_file):
        print(f"Missing data file: {csv_file}")
        sys.exit(1)

print(f"Python {sys.version}")
print(f"cuda available: {__import__('torch').cuda.is_available()}")

# ── Pipeline steps ──────────────────────────────────────────────────────
# ── Pipeline steps ──────────────────────────────────────────────────────
steps = [
    ("Benchmark CV (XGB/LGBM/RF, all datasets)", "python src/benchmark_cv.py"),
    ("GRU sequence experiments", "python src/gru_cv.py"),
    ("Fig 1, 3, 4 heatmaps", "python src/plot_fig01_fig03_fig04.py"),
    ("Fig 2 multi-horizon", "python src/plot_fig02.py"),
    ("Fig 5 ablation", "python src/plot_fig05.py"),
    ("Dual AUC heatmap (H=20)", "python src/plot_dual_heatmap.py"),
    ("Calibration comparison", "python src/plot_calibration_comparison.py"),
    ("SHAP importance figures", "python src/plot_shap.py"),

    ("Generate paper", "python src/generate_paper.py"),
    ("Generate presentation (full)", "python src/generate_presentation.py"),
    ("Generate presentation (simple)", "python src/generate_presentation_simple.py"),
]

for label, cmd in steps:
    print(f"\n--- {label} ---")
    ret = subprocess.run(cmd, shell=True)
    if ret.returncode != 0:
        print(f"FAILED: {cmd}", file=sys.stderr)
        sys.exit(1)

print("\nAll steps completed successfully.")
