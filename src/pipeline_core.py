"""Shared pipeline core: leakage-clean (cross-fitted) calibration, metric
bundles, feature sets, and data loading.

Calibration protocol (review point 5): calibrators are NEVER fit on the
scores of the rows they are applied to. Trees use cross-fitted out-of-fold
scores: an inner GroupKFold over the training cells produces OOF scores for
every training row, and Platt/isotonic/temperature are fit on those. At
transfer time the source model trains on all source cells while its
calibrators are fit on source OOF scores, then applied to untouched target
cells. Every split in this file is cell-disjoint (review point 4).
"""
import os
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.model_selection import GroupKFold
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from scipy.optimize import minimize_scalar
from scipy.special import logit, expit

from composite_label import make_composite_fail_in_H
from stats_utils import metric_bundle, safe_auc

_HERE = os.path.dirname(os.path.abspath(__file__))
_DATA_DIR = os.path.join(_HERE, "..", "data")
_RESULTS_DIR = os.path.join(_HERE, "..", "results_v2")
_PREDS_DIR = os.path.join(_HERE, "..", "results_v2", "preds")

FULL_FEATURES = ["cycle", "avg_voltage", "min_voltage", "avg_current", "avg_temp", "duration", "SOH"]
SENSOR_FEATURES = ["avg_voltage", "min_voltage", "avg_current", "avg_temp", "duration"]
COMMON_FEATURES_WITH_SOH = ["cycle", "avg_voltage", "min_voltage", "SOH"]
COMMON_FEATURES_NO_SOH = ["cycle", "avg_voltage", "min_voltage"]

FEATURE_SETS = {
    "with_soh": FULL_FEATURES,
    "full": FULL_FEATURES,  # alias used by the ablation grid
    "no_soh": [c for c in FULL_FEATURES if c != "SOH"],
    "no_cycle": [c for c in FULL_FEATURES if c != "cycle"],
    "no_soh_no_cycle": [c for c in FULL_FEATURES if c not in ("SOH", "cycle")],
    "soh_only": ["SOH"],
    "cycle_only": ["cycle"],
    "sensors_only": SENSOR_FEATURES,
    "common_with_soh": COMMON_FEATURES_WITH_SOH,
    "common_no_soh": COMMON_FEATURES_NO_SOH,
}

REQUIRED_COLS = ["cycle", "SOH", "cell", "RUL"]
H_LIST = [10, 20, 30, 50]

DATASETS = {
    "nasa": os.path.join(_DATA_DIR, "nasa_clean_filtered.csv"),
    "calce": os.path.join(_DATA_DIR, "calce_clean.csv"),
    "oxford": os.path.join(_DATA_DIR, "oxford_clean.csv"),
    "severson": os.path.join(_DATA_DIR, "severson_clean.csv"),
}

LCO_SOURCES = {
    "nasa": ["nasa"],
    "calce": ["calce"],
    "nasa+calce": ["nasa", "calce"],
}


def get_models():
    from xgboost import XGBClassifier
    from lightgbm import LGBMClassifier
    from sklearn.ensemble import RandomForestClassifier
    # n_jobs kept low: datasets are small and nested CV with joblib workers
    # can deadlock under thread oversubscription (observed with RF n_jobs=4).
    return {
        "xgboost": XGBClassifier(
            max_depth=4, learning_rate=0.05, n_estimators=300, subsample=0.8,
            colsample_bytree=0.8, min_child_weight=5, objective="binary:logistic",
            eval_metric="logloss", random_state=42, verbosity=0, n_jobs=2),
        "lightgbm": LGBMClassifier(
            max_depth=4, learning_rate=0.05, n_estimators=300, subsample=0.8,
            colsample_bytree=0.8, min_child_samples=20, random_state=42,
            verbosity=-1, n_jobs=2),
        "random_forest": RandomForestClassifier(
            n_estimators=300, max_depth=6, random_state=42, n_jobs=1),
    }


def load_clean(ds_name):
    df = pd.read_csv(DATASETS[ds_name])
    df = df.replace([np.inf, -np.inf], np.nan)
    df = df.dropna(subset=[c for c in REQUIRED_COLS if c in df.columns]).copy()
    df = df[(df["SOH"] > 0) & (df["SOH"] < 1.2)].copy()
    df = df[df["RUL"] >= 0].copy()
    df = df.sort_values(["cell", "cycle"]).reset_index(drop=True)
    avail = [c for c in FULL_FEATURES if c in df.columns]
    df[avail] = df[avail].fillna(0)
    return df


def load_source(source_key):
    if source_key in LCO_SOURCES:
        parts = [load_clean(n) for n in LCO_SOURCES[source_key]]
        return parts[0] if len(parts) == 1 else pd.concat(parts, ignore_index=True)
    if source_key in DATASETS:
        return load_clean(source_key)
    raise KeyError(f"unknown source {source_key!r}")


def inner_cell_splits(df, k):
    """Deterministic cell-grouped splits of df rows into k folds.

    Returns list of (tr_rows, va_rows) positional index arrays.
    """
    cells = df["cell"].to_numpy()
    uniq = pd.unique(cells)
    k = max(2, min(k, len(uniq)))
    gkf = GroupKFold(n_splits=k)
    splits = []
    X_dummy = np.zeros((len(df), 1))
    for tr, va in gkf.split(X_dummy, groups=cells):
        splits.append((tr, va))
    return splits


class TemperatureScaler:
    def __init__(self, T=1.0):
        self.T = T

    def transform(self, p):
        p = np.clip(np.asarray(p, dtype=float), 1e-6, 1 - 1e-6)
        return expit(logit(p) / self.T)


def fit_temperature(p, y):
    p = np.clip(np.asarray(p, dtype=float), 1e-6, 1 - 1e-6)
    from sklearn.metrics import log_loss

    def nll(log_T):
        return log_loss(y, expit(logit(p) / np.exp(log_T)))

    res = minimize_scalar(nll, bounds=(np.log(0.05), np.log(20.0)), method="bounded")
    return TemperatureScaler(T=float(np.exp(res.x)))


def fit_calibrators(scores, y):
    """Fit isotonic, Platt, and temperature on (OOF) scores."""
    cal = {}
    if len(np.unique(y)) < 2:
        return None
    cal["iso"] = IsotonicRegression(out_of_bounds="clip").fit(scores, y)
    cal["platt"] = LogisticRegression(C=1e10, solver="lbfgs", random_state=42).fit(
        np.asarray(scores, dtype=float).reshape(-1, 1), y)
    cal["temp"] = fit_temperature(scores, y)
    return cal


def apply_calibrators(cal, scores):
    s = np.asarray(scores, dtype=float)
    return {
        "raw": s,
        "iso": cal["iso"].transform(s),
        "platt": cal["platt"].predict_proba(s.reshape(-1, 1))[:, 1],
        "temp": cal["temp"].transform(s),
    }


def cross_fitted_oof(df, model, features, H, endpoint="combined", inner_k=4):
    """OOF scores for every row of df via an inner GroupKFold over cells.

    Returns (oof_scores, y, cells) aligned with df's row order.
    """
    y = make_composite_fail_in_H(df, H, endpoint=endpoint)
    X = df[features].values
    cells = df["cell"].to_numpy()
    oof = np.full(len(df), np.nan)
    for tr, va in inner_cell_splits(df, inner_k):
        if len(np.unique(y[tr])) < 2:
            continue
        m = clone(model)
        m.fit(X[tr], y[tr])
        oof[va] = m.predict_proba(X[va])[:, 1]
    # Rows whose inner folds were untrainable (single-class) fall back to the
    # full-data model score so calibrators still see complete coverage.
    if np.isnan(oof).any():
        if len(np.unique(y)) < 2:
            return np.full(len(df), 0.5), y, cells
        m = clone(model)
        m.fit(X, y)
        oof[np.isnan(oof)] = m.predict_proba(X[np.isnan(oof)])[:, 1]
    return oof, y, cells


def per_cell_aucs(y, p, cells):
    """List of (cell, auc) — NaN when a cell has a single class."""
    out = []
    df = pd.DataFrame({"y": np.asarray(y).ravel(), "p": np.asarray(p).ravel(),
                       "cell": np.asarray(cells).ravel()})
    for c, g in df.groupby("cell", sort=True):
        out.append((c, safe_auc(g["y"].to_numpy(), g["p"].to_numpy())))
    return out


def summarize(y, p, cells, n_boot=0, seed=42):
    """Pooled metric bundle + per-cell mean/std of AUC."""
    row = metric_bundle(y, p, cells=cells, n_boot=n_boot, seed=seed)
    per_cell = np.array([a for _, a in per_cell_aucs(y, p, cells)], dtype=float)
    valid = per_cell[np.isfinite(per_cell)]
    row["AUC_percell_mean"] = float(valid.mean()) if len(valid) else np.nan
    row["AUC_percell_std"] = float(valid.std(ddof=1)) if len(valid) > 1 else np.nan
    row["n_cells_valid"] = int(len(valid))
    return row


def save_preds(name, df_preds):
    os.makedirs(_PREDS_DIR, exist_ok=True)
    df_preds.to_csv(os.path.join(_PREDS_DIR, name), index=False)


def load_preds(name):
    return pd.read_csv(os.path.join(_PREDS_DIR, name))


def results_path(fname):
    os.makedirs(_RESULTS_DIR, exist_ok=True)
    return os.path.join(_RESULTS_DIR, fname)
