"""SHAP feature importance — single-panel figures sized for a journal column.

One panel per figure, so the text stays legible at column width (no 2-panel
stacking squeezed into the paper). Six outputs:

  Fig06a_XGBoost_SHAP.png         with SOH    (NASA -> Oxford, H=20)
  Fig06b_LightGBM_SHAP.png        with SOH
  Fig06c_RandomForest_SHAP.png    with SOH
  Fig06d_XGBoost_SHAP_noSOH.png   without SOH
  Fig06e_LightGBM_SHAP_noSOH.png  without SOH
  Fig06f_RandomForest_SHAP_noSOH.png without SOH
"""
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

MODELS = {
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

OUT = {
    "XGBoost": os.path.join(DATA_DIR, "Fig06a_XGBoost_SHAP.png"),
    "LightGBM": os.path.join(DATA_DIR, "Fig06b_LightGBM_SHAP.png"),
    "Random Forest": os.path.join(DATA_DIR, "Fig06c_RandomForest_SHAP.png"),
}
OUT_NO = {
    "XGBoost": os.path.join(DATA_DIR, "Fig06d_XGBoost_SHAP_noSOH.png"),
    "LightGBM": os.path.join(DATA_DIR, "Fig06e_LightGBM_SHAP_noSOH.png"),
    "Random Forest": os.path.join(DATA_DIR, "Fig06f_RandomForest_SHAP_noSOH.png"),
}

# Fonts sized for a ~5.5 inch saved figure that is placed at ~3.5 inch column
# width (~0.63x), so the effective on-page text lands around 9-10 pt.
plt.rcParams.update({
    "font.size": 13,
    "font.family": "DejaVu Sans",
    "axes.labelsize": 12,
    "axes.titlesize": 13,
    "xtick.labelsize": 11,
    "ytick.labelsize": 12,
    "legend.fontsize": 11,
})

FIG_W, FIG_H = 4.4, 3.7


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
        sv = sv[1] if len(sv) > 1 else sv[0]
    if isinstance(sv, np.ndarray) and sv.ndim == 3:
        sv = sv[:, :, 1]
    return sv


def _render(shap_values, X, feature_names, title, path):
    shap.summary_plot(shap_values, X, feature_names=feature_names,
                      show=False, max_display=7, alpha=0.7, plot_size=(FIG_W, FIG_H))
    fig = plt.gcf()
    ax = fig.axes[0]
    ax.margins(y=0.06)                      # keep violins from clipping at top/bottom
    ax.set_title(title, fontsize=13, fontweight="bold", pad=8)
    for lab in ax.get_yticklabels():
        lab.set_fontsize(12)
        lab.set_fontweight("bold")
    ax.set_xlabel("SHAP value (impact on model output)", fontsize=12)
    if len(fig.axes) > 1:
        cb = fig.axes[-1]
        cb.tick_params(labelsize=10)
        cb.set_ylabel("Feature value", fontsize=11)
        for la in cb.get_yticklabels():
            la.set_fontsize(10)
    plt.tight_layout()
    fig.savefig(path, dpi=300)
    plt.close(fig)
    print(f"Saved: {path}")


def main():
    nasa = clean_df(pd.read_csv(os.path.join(DATA_DIR, "nasa_clean_filtered.csv")))
    oxford = clean_df(pd.read_csv(os.path.join(DATA_DIR, "oxford_clean.csv")))

    y_train = make_composite_fail_in_H(nasa, H)

    X_train_with = nasa[FEATURES].values
    X_test_with = oxford[FEATURES].values
    X_train_no = nasa[FEATURES_NO_SOH].values
    X_test_no = oxford[FEATURES_NO_SOH].values

    for name, model in MODELS.items():
        sv_with = _model_shap(model, X_train_with, y_train, X_test_with)
        _render(sv_with, X_test_with, FEATURES,
                f"{name}, with SOH", OUT[name])

        sv_no = _model_shap(model, X_train_no, y_train, X_test_no)
        _render(sv_no, X_test_no, FEATURES_NO_SOH,
                f"{name}, without SOH", OUT_NO[name])

    print("6 single-panel SHAP figures saved.")


if __name__ == "__main__":
    main()
