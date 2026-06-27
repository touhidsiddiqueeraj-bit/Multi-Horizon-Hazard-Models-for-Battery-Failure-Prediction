"""SHAP feature importance — one figure per model for cross-chemistry (NASA -> Oxford, H=20, with SOH)."""
import os
import sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.base import clone
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier
from lightgbm import LGBMClassifier

from composite_label import make_composite_fail_in_H

try:
    import shap
except ImportError:
    print("shap not installed. Run: pip install shap")
    sys.exit(0)

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT, "data")

FEATURES = ["cycle", "avg_voltage", "min_voltage", "avg_current", "avg_temp", "duration", "SOH"]
FEATURES_NO_SOH = ["cycle", "avg_voltage", "min_voltage", "avg_current", "avg_temp", "duration"]
H = 20

# With-SOH figures (existing Fig06a/b/c)
OUTPUTS = {
    "XGBoost": os.path.join(DATA_DIR, "Fig06a_XGBoost_SHAP.png"),
    "LightGBM": os.path.join(DATA_DIR, "Fig06b_LightGBM_SHAP.png"),
    "Random Forest": os.path.join(DATA_DIR, "Fig06c_RandomForest_SHAP.png"),
}
# Without-SOH figures (new Fig06d/e/f)
OUTPUTS_NO_SOH = {
    "XGBoost": os.path.join(DATA_DIR, "Fig06d_XGBoost_SHAP_noSOH.png"),
    "LightGBM": os.path.join(DATA_DIR, "Fig06e_LightGBM_SHAP_noSOH.png"),
    "Random Forest": os.path.join(DATA_DIR, "Fig06f_RandomForest_SHAP_noSOH.png"),
}
# Combined comparison figure
OUTPUT_COMBINED = os.path.join(DATA_DIR, "Fig06_SHAP_comparison.png")

def get_models():
    return {
        "XGBoost": XGBClassifier(max_depth=4, learning_rate=0.05, n_estimators=300,
                                  subsample=0.8, colsample_bytree=0.8, min_child_weight=5,
                                  objective="binary:logistic", eval_metric="logloss",
                                  random_state=42, verbosity=0),
        "LightGBM": LGBMClassifier(max_depth=4, learning_rate=0.05, n_estimators=300,
                                    subsample=0.8, colsample_bytree=0.8, min_child_samples=20,
                                    random_state=42, verbosity=-1),
        "Random Forest": RandomForestClassifier(n_estimators=300, max_depth=6,
                                                 random_state=42, n_jobs=-1),
    }

def clean_df(df):
    cols = [c for c in FEATURES if c in df.columns]
    df = df.replace([np.inf, -np.inf], np.nan)
    df = df.dropna(subset=["cycle", "SOH", "cell", "RUL"]).copy()
    df = df[(df["SOH"] > 0) & (df["SOH"] < 1.2)].copy()
    df = df[df["RUL"] >= 0].copy()
    df = df.sort_values(["cell", "cycle"]).copy()
    df[cols] = df[cols].fillna(0)
    return df

def _model_shap(model, X_train, y_train, X_test):
    m = clone(model)
    m.fit(X_train, y_train)
    explainer = shap.TreeExplainer(m)
    sv = explainer.shap_values(X_test)
    if isinstance(sv, list):
        sv = sv[1]
    if isinstance(sv, np.ndarray) and sv.ndim == 3:
        sv = sv[:, :, 1]
    return sv

def _generate_shap_figure(name, model, X_train, y_train, X_test, feature_names, title, path):
    shap_values = _model_shap(model, X_train, y_train, X_test)
    shap.summary_plot(
        shap_values, X_test, feature_names=feature_names,
        show=False, max_display=7, alpha=0.6,
    )
    fig_i = plt.gcf()
    fig_i.axes[0].set_title(title, fontsize=12)
    fig_i.set_size_inches(9, 5)
    fig_i.tight_layout()
    fig_i.savefig(path, dpi=300, bbox_inches="tight")
    plt.close(fig_i)
    print(f"Saved: {path}")


def main():
    nasa = clean_df(pd.read_csv(os.path.join(DATA_DIR, "nasa_clean_filtered.csv")))
    oxford = clean_df(pd.read_csv(os.path.join(DATA_DIR, "oxford_clean.csv")))

    y_train = make_composite_fail_in_H(nasa, H)
    models = get_models()

    # ---- Phase 1: with-SOH SHAP figures (Fig06a/b/c) ----
    X_train_with = nasa[FEATURES].values
    X_test_with = oxford[FEATURES].values

    for name, model in models.items():
        _generate_shap_figure(
            name, model, X_train_with, y_train, X_test_with,
            FEATURES, f"SHAP — {name}\nNASA → Oxford, H=20, with SOH",
            OUTPUTS[name],
        )

    # ---- Phase 2: without-SOH SHAP figures (Fig06d/e/f) ----
    X_train_no = nasa[FEATURES_NO_SOH].values
    X_test_no = oxford[FEATURES_NO_SOH].values

    for name, model in models.items():
        _generate_shap_figure(
            name, model, X_train_no, y_train, X_test_no,
            FEATURES_NO_SOH, f"SHAP — {name}\nNASA → Oxford, H=20, without SOH",
            OUTPUTS_NO_SOH[name],
        )

    print("6 SHAP figures saved (3 with SOH, 3 without SOH)")


if __name__ == "__main__":
    main()
