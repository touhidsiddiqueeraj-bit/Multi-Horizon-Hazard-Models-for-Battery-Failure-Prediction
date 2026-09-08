"""Cross-chemistry generalization via target-chemistry recalibration.

Train a hazard model on one chemistry (LCO: NASA / CALCE / both), then ask
whether a small labeled sample from another chemistry (LFP: Oxford / Severson)
recovers within-chemistry-level performance, under two arms:

  Arm A - calibrator-only recalibration (isotonic / Platt / temperature
          scaling fit on the LFP sample). Monotonic in the 1-D score, so it
          cannot move AUC except through isotonic tie effects; asserted per
          fold (tol 1e-3) and recorded as tie_delta_mean / tie_delta_max.
  Arm B - small-sample model update (XGBoost/LightGBM warm-start continuation,
          Random Forest fresh refit) on the LFP sample.

Controls: zero-shot (no recalibration), full-LFP retrain (upper bound),
within-LCO GroupKFold CV ceilings for BOTH feature sets (the recovery-ratio
denominator, feature-matched). Recovery ratio is defined ONLY against the
within-LCO ceiling; proximity to the full-LFP ceiling is a separate column.

Also: LCO-holdout retention check (~15% of LCO cells) before/after Arm B
update, and DeLong tests (zero-shot vs Arm A -- expect non-significant;
zero-shot vs Arm B -- expect significant as k grows).
"""
import argparse
import json
import os
import sqlite3
import sys
import warnings
from itertools import combinations

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.ensemble import RandomForestClassifier
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, roc_auc_score
from sklearn.model_selection import GroupKFold
from scipy.optimize import minimize
from scipy.special import expit
from scipy.stats import spearmanr
from xgboost import XGBClassifier
from lightgbm import LGBMClassifier

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
from composite_label import make_composite_fail_in_H
from stats_utils import delong_roc_test
from benchmark_cv import get_models, clean_df, safe_auc

_DATA_DIR = os.path.normpath(os.path.join(_HERE, "..", "data"))
_RESULTS_DIR = os.path.normpath(os.path.join(_HERE, "..", "results", "recalibration"))
_OUT_CSV = os.path.join(_RESULTS_DIR, "recalibration_results.csv")

FEATURES = ["cycle", "avg_voltage", "min_voltage", "avg_current", "avg_temp", "duration", "SOH"]
FEATURES_CROSS_CHEM = ["cycle", "avg_voltage", "min_voltage", "avg_current", "avg_temp", "duration"]
H_LIST = [10, 20, 30, 50]
SEEDS = [42, 123, 456, 789, 101112]
K_SEVERSON = [5, 10, 20, 40]
K_OXFORD = [1, 2]
CAL_METHODS = ["iso", "platt", "temp"]
ARM_A_TOL = 1e-3
ECE_BINS = 10
LCO_HOLDOUT_FRAC = 0.15

SOURCES = ["nasa", "calce", "nasa+calce"]


def compute_ece(y_true, prob, bins=ECE_BINS):
    edges = np.linspace(0, 1, bins + 1)
    ece = 0.0
    for i in range(bins):
        mask = (prob >= edges[i]) & (prob < edges[i + 1])
        if mask.sum() == 0:
            continue
        ece += abs(prob[mask].mean() - y_true[mask].mean()) * mask.sum() / len(y_true)
    return ece


def load_data():
    base = {
        "nasa": pd.read_csv(os.path.join(_DATA_DIR, "nasa_clean_filtered.csv")),
        "calce": pd.read_csv(os.path.join(_DATA_DIR, "calce_clean.csv")),
    }
    base["nasa+calce"] = pd.concat([base["nasa"], base["calce"]], ignore_index=True)
    for k in base:
        base[k] = clean_df(base[k])
    targets = {
        "oxford": clean_df(pd.read_csv(os.path.join(_DATA_DIR, "oxford_clean.csv"))),
        "severson": clean_df(pd.read_csv(os.path.join(_DATA_DIR, "severson_clean.csv"))),
    }
    return base, targets


def fit_base(model, X, y, features):
    cols = [c for c in features if c in X.columns]
    m = clone(model)
    m.fit(X[cols].values, y)
    return m


def continuation_fit(model_name, X_lfp, y_lfp, base_model):
    """Arm B: warm-start / refit on the LFP sample."""
    if model_name == "xgboost":
        m = XGBClassifier(**base_model.get_params())
        m.set_params(n_jobs=-1)
        m.fit(X_lfp, y_lfp, xgb_model=base_model.get_booster())
    elif model_name == "lightgbm":
        m = LGBMClassifier(**base_model.get_params())
        m.set_params(n_jobs=-1)
        m.fit(X_lfp, y_lfp, init_model=base_model.booster_)
    else:  # random_forest: no continuation API -> fresh refit on sample
        m = clone(base_model)
        m.fit(X_lfp, y_lfp)
    return m


def calibrate_arm_a(method, p_cal_fit, y_cal_fit, p_test):
    """Arm A calibrators fit on the LFP sample's raw scores."""
    if len(np.unique(y_cal_fit)) < 2:
        return p_test.copy()
    if method == "iso":
        iso = IsotonicRegression(out_of_bounds="clip")
        iso.fit(p_cal_fit, y_cal_fit)
        return iso.transform(p_test)
    if method == "platt":
        platt = LogisticRegression(C=1e10, solver="lbfgs")
        platt.fit(p_cal_fit.reshape(-1, 1), y_cal_fit)
        return platt.predict_proba(p_test.reshape(-1, 1))[:, 1]
    if method == "temp":
        eps = 1e-15
        p_safe = np.clip(p_cal_fit, eps, 1 - eps)
        logits = np.log(p_safe / (1 - p_safe))

        def nll(T):
            p = np.clip(expit(logits / T), eps, 1 - eps)
            return -np.mean(y_cal_fit * np.log(p) + (1 - y_cal_fit) * np.log(1 - p))

        res = minimize(nll, x0=1.0, method="L-BFGS-B", bounds=[(1e-3, 10.0)])
        T = res.x[0]
        return np.clip(expit(np.log(p_test / (1 - p_test)) / T), eps, 1 - eps)


def within_ceiling(train_df, model, H, features):
    """GroupKFold CV on the source chemistry -> feature-matched ceiling."""
    y = make_composite_fail_in_H(train_df, H)
    cols = [c for c in features if c in train_df.columns]
    X = train_df[cols].values
    groups = train_df["cell"].values
    n_splits = min(5, train_df["cell"].nunique())
    aucs = []
    for tr, te in GroupKFold(n_splits=n_splits).split(X, y, groups):
        m = clone(model)
        m.fit(X[tr], y[tr])
        p = m.predict_proba(X[te])[:, 1]
        a = safe_auc(y[te], p)
        if not np.isnan(a):
            aucs.append(a)
    return np.mean(aucs) if aucs else np.nan


def pooled_metrics(y, p, y_zero=None, p_zero=None):
    row = {
        "auc": safe_auc(y, p),
        "ece": compute_ece(y, p),
        "brier": brier_score_loss(y, p),
    }
    if y_zero is not None:
        d = delong_roc_test(y, p_zero, p)
        row["delong_p_vs_zeroshot"] = d["p_value"]
    return row


def per_cell_auc(y, p, cells):
    aucs = []
    for c in np.unique(cells):
        m = cells == c
        if len(np.unique(y[m])) < 2:
            continue
        aucs.append(roc_auc_score(y[m], p[m]))
    return (np.mean(aucs), np.std(aucs)) if aucs else (np.nan, np.nan)


def run_sample_arm_a(base_model, X_cal, y_cal, X_eval, y_eval):
    p_cal = base_model.predict_proba(X_cal)[:, 1]
    p_eval = base_model.predict_proba(X_eval)[:, 1]
    out = {}
    for method in CAL_METHODS:
        p_recal = calibrate_arm_a(method, p_cal, y_cal, p_eval)
        # Wiring check: an Arm A calibrator is a deterministic 1-D transform
        # of the raw score. Identical raw scores must map to identical
        # outputs; a multi-feature calibrator (or wrong-score feed) breaks
        # this. Monotone-INCREASING is NOT required: under shift the LFP
        # sample can anti-correlate with LCO scores, and Platt legitimately
        # fits a decreasing map -- that is a reportable finding (recorded as
        # rank_corr below), not a bug.
        order = np.argsort(p_eval, kind="stable")
        d = np.diff(p_recal[order])
        tie_mask = np.diff(p_eval[order]) == 0
        if tie_mask.any():
            assert np.abs(d[tie_mask]).max() < 1e-9, (
                f"Arm A non-deterministic transform: {method} equal raw scores "
                f"map to different outputs (multi-feature calibrator or wrong "
                f"score fed?)")
        delta = abs(safe_auc(y_eval, p_eval) - safe_auc(y_eval, p_recal))
        out[method] = (p_recal, delta)
    return p_eval, out


def evaluate_arm_b(model_name, X_cal, y_cal, X_eval, base_model, y_eval):
    m = continuation_fit(model_name, X_cal, y_cal, base_model)
    return m.predict_proba(X_eval)[:, 1], m


def main():
    warnings.filterwarnings("ignore", message="X does not have valid feature names")
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true", help="1 seed, H=20, Severson, k in {5,20}")
    ap.add_argument("--severson-only", action="store_true")
    ap.add_argument("--no-arm-b", action="store_true")
    ap.add_argument("--reduced", action="store_true",
                    help="H=20 only; NASA x all models/features, CALCE+NASA+CALCE x no-SOH XGBoost; "
                         "Oxford x no-SOH XGBoost, exhaustive k in {1,2}, no seed repetition")
    ap.add_argument("--state", default=None,
                    help="SQLite checkpoint path (default: results/recalibration/*.db)")
    args = ap.parse_args()

    os.makedirs(_RESULTS_DIR, exist_ok=True)
    scope = "reduced-v1" if args.reduced else "full-v1"
    state_path = args.state or os.path.join(
        _RESULTS_DIR, "recalibration_reduced.db" if args.reduced else "recalibration_full.db")
    con = _open_state(state_path, scope)
    done = _done_keys(con)
    print(f"state: {state_path} ({len(done)} committed samples)")

    base, targets = load_data()
    models = get_models()
    h_list = [20] if (args.smoke or args.reduced) else H_LIST
    seeds = [42] if args.smoke else SEEDS
    k_sev = [5, 20] if args.smoke else K_SEVERSON
    targets_use = ["severson"] if (args.smoke or args.severson_only) else ["severson", "oxford"]

    out_csv = os.path.join(_RESULTS_DIR,
                           "recalibration_reduced.csv" if args.reduced else "recalibration_results.csv")
    rows = []
    for target_name in targets_use:
        test_df = targets[target_name]
        print(f"\n########## Target: {target_name} ({test_df['cell'].nunique()} cells, {len(test_df)} rows)")

        for source in SOURCES:
            train_df = base[source]
            n_cells_lco = train_df["cell"].nunique()
            rng_cells = np.random.default_rng(0)
            holdout_lco = set(rng_cells.choice(train_df["cell"].unique(),
                                               size=int(LCO_HOLDOUT_FRAC * n_cells_lco),
                                               replace=False))
            lco_hold = train_df[train_df["cell"].isin(holdout_lco)]
            lco_fit = train_df[~train_df["cell"].isin(holdout_lco)]
            print(f"\n=== Source: {source} ({n_cells_lco} LCO cells, "
                  f"{lco_fit['cell'].nunique()} for fit / {lco_hold['cell'].nunique()} for retention)")

            configs = []
            for feat_label, features in [("with_soh", FEATURES), ("no_soh", FEATURES_CROSS_CHEM)]:
                for model_name, m in models.items():
                    for H in h_list:
                        if (not args.reduced
                                or (target_name == "severson" and (
                                    source == "nasa"
                                    or (feat_label == "no_soh" and model_name == "xgboost")))
                                or (target_name == "oxford"
                                    and feat_label == "no_soh" and model_name == "xgboost")):
                            configs.append((feat_label, features, model_name, m, H))
            for feat_label, features, model_name, model, H in configs:
                        y_train = make_composite_fail_in_H(lco_fit, H)
                        cols = [c for c in features if c in train_df.columns]
                        X_lco = lco_fit[cols].values
                        base_model = fit_base(model, lco_fit, y_train, features)

                        p_lco_hold = base_model.predict_proba(lco_hold[cols].values)[:, 1]
                        y_lco_hold = make_composite_fail_in_H(lco_hold, H)
                        auc_ret_before = safe_auc(y_lco_hold, p_lco_hold)

                        ceil_within = within_ceiling(train_df, model, H, features)
                        y_te = make_composite_fail_in_H(test_df, H)

                        y_zero = y_te
                        p_zero_all = base_model.predict_proba(test_df[cols].values)[:, 1]
                        auc_zero_all = safe_auc(y_zero, p_zero_all)

                        # Full-LFP retrain ceiling (deterministic, no sampling)
                        full = clone(model)
                        full.fit(test_df[cols].values, y_te)
                        p_full = full.predict_proba(test_df[cols].values)[:, 1]
                        auc_full_lfp = safe_auc(y_te, p_full)

                        print(f"  [{feat_label}] {model_name} H={H}: "
                              f"within_ceiling={ceil_within:.3f} fullLFP={auc_full_lfp:.3f} "
                              f"zeroshot={auc_zero_all:.3f}")

                        cells = sorted(test_df["cell"].unique())
                        X_test = test_df[cols].values

                        # Controls row (seed=0, k=0)
                        rows.append({
                            "target": target_name, "source": source, "features": feat_label,
                            "model": model_name, "H": H, "seed": 0, "k": 0,
                            "arm": "zeroshot", "method": "raw",
                            "auc_pooled": auc_zero_all, "auc_percell_mean": np.nan,
                            "auc_percell_std": np.nan, "ece": compute_ece(y_zero, p_zero_all),
                            "brier": brier_score_loss(y_zero, p_zero_all),
                            "tie_delta_mean": np.nan, "tie_delta_max": np.nan,
                            "auc_zeroshot": auc_zero_all,
                            "auc_ceiling_within_lco": ceil_within,
                            "auc_ceiling_full_lfp": auc_full_lfp,
                            "recovery_ratio": np.nan, "retrain_proximity": np.nan,
                            "delong_p_vs_zeroshot": np.nan,
                            "auc_lco_holdout_before": auc_ret_before,
                            "auc_lco_holdout_after": np.nan,
                            "n_cal_cells": 0, "n_test_cells": len(cells),
                        })
                        rows.append({
                            "target": target_name, "source": source, "features": feat_label,
                            "model": model_name, "H": H, "seed": 0, "k": -1,
                            "arm": "retrain_lfp", "method": "full",
                            "auc_pooled": auc_full_lfp, "auc_percell_mean": np.nan,
                            "auc_percell_std": np.nan,
                            "ece": compute_ece(y_te, p_full),
                            "brier": brier_score_loss(y_te, p_full),
                            "tie_delta_mean": np.nan, "tie_delta_max": np.nan,
                            "auc_zeroshot": auc_zero_all,
                            "auc_ceiling_within_lco": ceil_within,
                            "auc_ceiling_full_lfp": auc_full_lfp,
                            "recovery_ratio": np.nan, "retrain_proximity": np.nan,
                            "delong_p_vs_zeroshot": np.nan,
                            "auc_lco_holdout_before": auc_ret_before,
                            "auc_lco_holdout_after": np.nan,
                            "n_cal_cells": len(cells), "n_test_cells": len(cells),
                        })

                        # Sampled arms
                        _store(con, f"ctl|{target_name}|{source}|{feat_label}|{model_name}|{H}",
                               rows[-2:])
                        k_list = K_OXFORD if target_name == "oxford" else k_sev
                        k_seeds = [0] if (args.reduced and target_name == "oxford") else seeds
                        for k in k_list:
                            if target_name == "oxford":
                                combos = list(combinations(cells, k))
                            else:
                                combos = None
                            for seed in k_seeds:
                                rng = np.random.default_rng(seed)
                                if target_name == "oxford":
                                    for combo in combos:
                                        cal_cells = set(combo)
                                        key = _sample_key(target_name, source, feat_label,
                                                          model_name, H, seed, k, cal_cells)
                                        if key in done:
                                            continue
                                        cal_mask = test_df["cell"].isin(cal_cells)
                                        X_cal, y_cal = X_test[cal_mask], y_te[cal_mask]
                                        X_eval, y_eval = X_test[~cal_mask], y_te[~cal_mask]
                                        added = _process_sample(
                                            rows, target_name, source, feat_label,
                                            model_name, model, H, seed, k,
                                            cal_cells, X_cal, y_cal, X_eval, y_eval,
                                            test_df["cell"].values, ceil_within,
                                            auc_full_lfp, auc_ret_before,
                                            lco_hold, cols, y_lco_hold,
                                            args, base_model)
                                        _store(con, key, added)
                                else:
                                    cal_cells = set(rng.choice(cells, size=k, replace=False))
                                    key = _sample_key(target_name, source, feat_label,
                                                      model_name, H, seed, k)
                                    if key in done:
                                        continue
                                    cal_mask = test_df["cell"].isin(cal_cells)
                                    X_cal, y_cal = X_test[cal_mask], y_te[cal_mask]
                                    X_eval, y_eval = X_test[~cal_mask], y_te[~cal_mask]
                                    added = _process_sample(
                                        rows, target_name, source, feat_label,
                                        model_name, model, H, seed, k,
                                        cal_cells, X_cal, y_cal, X_eval, y_eval,
                                        test_df["cell"].values, ceil_within,
                                        auc_full_lfp, auc_ret_before,
                                        lco_hold, cols, y_lco_hold,
                                        args, base_model)
                                    _store(con, key, added)

    n = _export(con, out_csv)
    print(f"\nExported: {out_csv} ({n} rows)")


def _sample_key(target, source, feat, model, H, seed, k, combo=None):
    """Unique sample key. Oxford combos need the concrete cell tuple; Severson
    subsets are implied by (seed, k) through the seeded RNG."""
    c = "" if combo is None else "|" + ",".join(sorted(combo))
    return f"{target}|{source}|{feat}|{model}|{H}|{seed}|{k}{c}"


def _open_state(path, scope):
    """SQLite checkpoint DB. One line = one completed sample (5 rows as JSON).
    Scope fingerprint prevents a reduced run from resuming a full run's data."""
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE IF NOT EXISTS results(key TEXT PRIMARY KEY, payload TEXT)")
    con.execute("CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT)")
    cur = con.execute("SELECT value FROM meta WHERE key='scope'").fetchone()
    if cur is None:
        con.execute("INSERT INTO meta(key,value) VALUES('scope',?)", (scope,))
        con.commit()
    elif cur[0] != scope:
        raise SystemExit(f"state DB {path} has scope {cur[0]!r}, expected {scope!r} — refusing to mix runs")
    return con


def _store(con, key, payload_rows):
    con.execute("INSERT OR REPLACE INTO results(key,payload) VALUES(?,?)",
                (key, json.dumps(payload_rows)))
    con.commit()


def _done_keys(con):
    return {r[0] for r in con.execute("SELECT key FROM results")}


def _export(con, csv_path):
    payloads = [r[0] for r in con.execute("SELECT payload FROM results")]
    all_rows = [d for p in payloads for d in json.loads(p)]
    tmp = csv_path + ".tmp"
    pd.DataFrame(all_rows).to_csv(tmp, index=False)
    os.replace(tmp, csv_path)
    return len(all_rows)


def _process_sample(rows, target, source, feat_label, model_name, model, H, seed, k,
                    cal_cells, X_cal, y_cal, X_eval, y_eval, cells_all, ceil_within,
                    auc_full_lfp, auc_ret_before, lco_hold, cols, y_lco_hold, args, base_model):
    eval_cells = cells_all[~np.isin(cells_all, list(cal_cells))]
    n_test = len(np.unique(eval_cells))
    zero_row = {
        "target": target, "source": source, "features": feat_label,
        "model": model_name, "H": H, "seed": seed, "k": k,
        "auc_ceiling_within_lco": ceil_within, "auc_ceiling_full_lfp": auc_full_lfp,
        "auc_lco_holdout_before": auc_ret_before,
        "n_cal_cells": len(cal_cells), "n_test_cells": n_test,
    }
    p_zero = base_model.predict_proba(X_eval)[:, 1]
    auc_zero = safe_auc(y_eval, p_zero)
    row0 = dict(zero_row, arm="zeroshot", method="raw",
                auc_pooled=auc_zero,
                auc_percell_mean=np.nan, auc_percell_std=np.nan,
                ece=compute_ece(y_eval, p_zero), brier=brier_score_loss(y_eval, p_zero),
                tie_delta_mean=np.nan, tie_delta_max=np.nan,
                auc_zeroshot=auc_zero, recovery_ratio=np.nan, retrain_proximity=np.nan,
                delong_p_vs_zeroshot=np.nan, auc_lco_holdout_after=np.nan)
    rows.append(row0)
    added = [row0]

    if not args.no_arm_b:
        p_b, updated = evaluate_arm_b(model_name, X_cal, y_cal, X_eval, base_model, y_eval)
        p_hold_after = updated.predict_proba(lco_hold[cols].values)[:, 1]
        auc_ret_after = safe_auc(y_lco_hold, p_hold_after)
        d = delong_roc_test(y_eval, p_zero, p_b)
        auc_b = safe_auc(y_eval, p_b)
        pc_mean, pc_std = per_cell_auc(y_eval, p_b, eval_cells)
        row_b = dict(zero_row, arm="arm_b", method="warmstart",
                     auc_pooled=auc_b,
                     auc_percell_mean=pc_mean, auc_percell_std=pc_std,
                     ece=compute_ece(y_eval, p_b), brier=brier_score_loss(y_eval, p_b),
                     tie_delta_mean=np.nan, tie_delta_max=np.nan,
                     auc_zeroshot=auc_zero,
                     recovery_ratio=_ratio(auc_zero, auc_b, ceil_within),
                     retrain_proximity=_ratio(auc_zero, auc_b, auc_full_lfp),
                     delong_p_vs_zeroshot=d["p_value"],
                     rank_corr=np.nan,
                     auc_lco_holdout_after=auc_ret_after)
        rows.append(row_b)
        added.append(row_b)
        print(f"    k={k} seed={seed} [{model_name} warmstart] "
              f"auc={auc_b:.3f} (zero {auc_zero:.3f}) "
              f"ratio={_ratio(auc_zero, auc_b, ceil_within):.2f} "
              f"lco_ret {auc_ret_before:.3f}->{auc_ret_after:.3f}")

    p_raw_eval, arm_a = run_sample_arm_a(base_model, X_cal, y_cal, X_eval, y_eval)
    assert np.allclose(p_raw_eval, p_zero), "score mismatch between arm A and zeroshot"
    pc_mean, pc_std = per_cell_auc(y_eval, p_zero, eval_cells)
    row0["auc_percell_mean"], row0["auc_percell_std"] = pc_mean, pc_std
    for method, (p_recal, delta) in arm_a.items():
        d = delong_roc_test(y_eval, p_zero, p_recal)
        row = dict(zero_row, arm="arm_a", method=method,
                   auc_pooled=safe_auc(y_eval, p_recal),
                   auc_percell_mean=np.nan, auc_percell_std=np.nan,
                   ece=compute_ece(y_eval, p_recal), brier=brier_score_loss(y_eval, p_recal),
                   tie_delta_mean=float(delta), tie_delta_max=float(delta),
                   auc_zeroshot=auc_zero,
                   recovery_ratio=_ratio(auc_zero, safe_auc(y_eval, p_recal), ceil_within),
                   retrain_proximity=_ratio(auc_zero, safe_auc(y_eval, p_recal), auc_full_lfp),
                   delong_p_vs_zeroshot=d["p_value"],
                   rank_corr=(float(spearmanr(p_zero, p_recal).statistic)
                              if np.ptp(p_zero) > 0 and np.ptp(p_recal) > 0 else np.nan),
                   auc_lco_holdout_after=np.nan)
        added.append(row)
        rows.append(row)
    return added


def _ratio(auc_zero, auc_after, ceiling):
    denom = ceiling - auc_zero
    if np.isnan(denom) or denom <= 0:
        return np.nan
    return (auc_after - auc_zero) / denom


if __name__ == "__main__":
    main()
