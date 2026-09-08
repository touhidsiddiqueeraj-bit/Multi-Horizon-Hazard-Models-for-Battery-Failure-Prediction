import os
import numpy as np
import pandas as pd

from sklearn.model_selection import GroupKFold
from sklearn.metrics import brier_score_loss, roc_auc_score
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.isotonic import IsotonicRegression

from composite_label import make_composite_fail_in_H

# =========================
# Discrete-Time Hazard CV
# (UPDATED + CORRECTED + CLEANING ADDED)
# =========================

os.makedirs("../data", exist_ok=True)

FEATURES = ["cycle", "avg_voltage", "min_voltage", "avg_current", "avg_temp", "duration", "SOH"]
H_LIST = [10, 20, 30, 50]
N_SPLITS = 5

def safe_auc(y_true, p):
    return roc_auc_score(y_true, p) if len(np.unique(y_true)) > 1 else np.nan

def main():
    # DEPRECATED: This script is not part of the active pipeline.
    # benchmark_cv.py covers all reported models (XGB, LGBM, RF, GRU).
    # hazard_cv.py uses HistGradientBoostingClassifier (different model class)
    # and writes to a separate output file never consumed by the paper generator.
    import warnings
    warnings.warn("hazard_cv.py is deprecated. Use benchmark_cv.py instead.", DeprecationWarning)
    df = pd.read_csv("../data/nasa_clean_filtered.csv")


    # -----------------------------
    # Clean (IMPORTANT)
    # -----------------------------
    df = df.replace([np.inf, -np.inf], np.nan)
    df = df.dropna(subset=FEATURES + ["cell", "RUL"]).copy()

    # ✅ remove corrupted SOH + negative RUL
    df = df[(df["SOH"] > 0) & (df["SOH"] < 1.2)].copy()
    df = df[df["RUL"] >= 0].copy()

    # Fixed order
    df = df.sort_values(["cell", "cycle"]).copy()

    X = df[FEATURES].values
    groups = df["cell"].values

    gkf = GroupKFold(n_splits=N_SPLITS)

    summary_rows = []
    oof_frames = []

    for H in H_LIST:
        y = make_composite_fail_in_H(df, H)

        # Out-of-fold storage
        p_raw_oof = np.zeros(len(df), dtype=float)
        p_cal_oof = np.zeros(len(df), dtype=float)

        brier_raw_folds, brier_cal_folds = [], []
        auc_raw_folds, auc_cal_folds = [], []

        for fold, (tr, te) in enumerate(gkf.split(X, y, groups), start=1):
            X_tr, X_te = X[tr], X[te]
            y_tr, y_te = y[tr], y[te]

            clf = HistGradientBoostingClassifier(
                max_depth=3,
                learning_rate=0.05,
                max_iter=500,
                random_state=42
            )
            clf.fit(X_tr, y_tr)

            p_raw_te = clf.predict_proba(X_te)[:, 1]
            p_raw_oof[te] = p_raw_te

            # Calibration (fit on training predictions)
            p_raw_tr = clf.predict_proba(X_tr)[:, 1]

            # If training fold has only one class, isotonic cannot fit
            if len(np.unique(y_tr)) < 2:
                p_cal_te = p_raw_te.copy()
            else:
                iso = IsotonicRegression(out_of_bounds="clip")
                iso.fit(p_raw_tr, y_tr)
                p_cal_te = iso.transform(p_raw_te)

            p_cal_oof[te] = p_cal_te

            b_raw = brier_score_loss(y_te, p_raw_te)
            b_cal = brier_score_loss(y_te, p_cal_te)

            a_raw = safe_auc(y_te, p_raw_te)
            a_cal = safe_auc(y_te, p_cal_te)

            brier_raw_folds.append(b_raw)
            brier_cal_folds.append(b_cal)

            if not np.isnan(a_raw):
                auc_raw_folds.append(a_raw)
            if not np.isnan(a_cal):
                auc_cal_folds.append(a_cal)

            print(f"H={H:>2} Fold {fold}: "
                  f"Brier raw={b_raw:.3f} cal={b_cal:.3f} | "
                  f"AUC raw={a_raw:.3f} cal={a_cal:.3f}")

        summary_rows.append({
            "H": H,
            "Brier_raw_mean": float(np.mean(brier_raw_folds)),
            "Brier_raw_std": float(np.std(brier_raw_folds)),
            "Brier_cal_mean": float(np.mean(brier_cal_folds)),
            "Brier_cal_std": float(np.std(brier_cal_folds)),
            "AUC_raw_mean": float(np.mean(auc_raw_folds)) if len(auc_raw_folds) else np.nan,
            "AUC_cal_mean": float(np.mean(auc_cal_folds)) if len(auc_cal_folds) else np.nan,
        })

        # Save out-of-fold predictions for this H
        oof = df[["cell", "cycle", "SOH", "RUL"]].copy()
        oof[f"y_fail_{H}"] = y
        oof[f"p_fail_raw_{H}"] = p_raw_oof
        oof[f"p_fail_cal_{H}"] = p_cal_oof
        oof_frames.append(oof)

        print(f"== H={H} Summary: "
              f"Brier raw {summary_rows[-1]['Brier_raw_mean']:.3f} "
              f"cal {summary_rows[-1]['Brier_cal_mean']:.3f} | "
              f"AUC raw {summary_rows[-1]['AUC_raw_mean']:.3f} "
              f"cal {summary_rows[-1]['AUC_cal_mean']:.3f}\n")

    # Save summary
    summary = pd.DataFrame(summary_rows)
    summary.to_csv("../data/hazard_cv_summary.csv", index=False)
    print("Saved: ../data/hazard_cv_summary.csv")

    # Merge OOF tables into one wide table
    merged = oof_frames[0]
    for o in oof_frames[1:]:
        merged = merged.merge(o, on=["cell", "cycle", "SOH", "RUL"], how="left")

    merged.to_csv("../data/hazard_oof_preds.csv", index=False)
    print("Saved: ../data/hazard_oof_preds.csv")

if __name__ == "__main__":
    main()
