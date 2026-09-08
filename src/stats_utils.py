"""Statistical utilities for the failure-risk paper.

Primary inference tool: cell-level bootstrap (the cell is the experimental
unit; cycles within a cell are correlated). DeLong is kept only as a
secondary, cycle-level test and its p-values should be reported with a
pseudoreplication caveat.
"""
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score, average_precision_score, log_loss, brier_score_loss
from sklearn.linear_model import LogisticRegression


def delong_roc_test(y_true, y_pred_a, y_pred_b):
    """Two-tailed p-value for H0: AUC_a == AUC_b (cycle-level, no clustering).

    NOTE: treats every row as an independent observation. Within-cell
    correlation inflates significance (pseudoreplication); use
    paired_cell_bootstrap_delta for the primary analysis.
    """
    y_true = np.asarray(y_true, dtype=bool).ravel()
    y_pred_a = np.asarray(y_pred_a).ravel()
    y_pred_b = np.asarray(y_pred_b).ravel()

    n_pos = np.sum(y_true)
    n_neg = len(y_true) - n_pos

    if n_pos < 1 or n_neg < 1:
        return {"auc_a": np.nan, "auc_b": np.nan,
                "z_stat": np.nan, "p_value": np.nan,
                "significant_0.05": False}

    auc_a = roc_auc_score(y_true, y_pred_a)
    auc_b = roc_auc_score(y_true, y_pred_b)

    pos_idx = np.where(y_true == 1)[0]
    neg_idx = np.where(y_true == 0)[0]

    def placement_values(scores):
        V10 = np.array([np.mean(scores[pi] > scores[neg_idx]) +
                        0.5 * np.mean(scores[pi] == scores[neg_idx]) for pi in pos_idx])
        V01 = np.array([np.mean(scores[pos_idx] > scores[nj]) +
                        0.5 * np.mean(scores[pos_idx] == scores[nj]) for nj in neg_idx])
        return V10, V01

    V10_a, V01_a = placement_values(y_pred_a)
    V10_b, V01_b = placement_values(y_pred_b)

    S10 = np.cov(V10_a, V10_b, ddof=1) if n_pos > 1 else np.zeros((2, 2))
    S01 = np.cov(V01_a, V01_b, ddof=1) if n_neg > 1 else np.zeros((2, 2))

    var_a = S10[0, 0] / n_pos + S01[0, 0] / n_neg
    var_b = S10[1, 1] / n_pos + S01[1, 1] / n_neg
    cov_ab = S10[0, 1] / n_pos + S01[0, 1] / n_neg
    var_diff = var_a + var_b - 2 * cov_ab

    if var_diff <= 0 or auc_a == auc_b:
        return {"auc_a": auc_a, "auc_b": auc_b,
                "z_stat": 0.0, "p_value": 1.0,
                "significant_0.05": False}

    z_stat = (auc_a - auc_b) / np.sqrt(var_diff)
    from scipy.stats import norm
    p_value = 2 * norm.sf(abs(z_stat))

    return {"auc_a": auc_a, "auc_b": auc_b, "z_stat": z_stat,
            "p_value": p_value, "significant_0.05": p_value < 0.05}


def safe_auc(y_true, p):
    y_true = np.asarray(y_true).ravel()
    return roc_auc_score(y_true, p) if len(np.unique(y_true)) > 1 else np.nan


def _cell_resample_indices(cells, rng):
    """Yield index arrays obtained by resampling cells with replacement."""
    uniq = np.unique(cells)
    cell_to_idx = {c: np.where(cells == c)[0] for c in uniq}
    n_cells = len(uniq)
    for _ in range(n_cells):
        draw = rng.choice(uniq, size=n_cells, replace=True)
        idx = np.concatenate([cell_to_idx[c] for c in draw])
        yield idx


def cell_bootstrap_auc_ci(y_true, scores, cells, n_boot=2000, seed=42, alpha=0.05):
    """Percentile CI for AUC by resampling cells with replacement."""
    y_true = np.asarray(y_true).ravel()
    scores = np.asarray(scores).ravel()
    cells = np.asarray(cells).ravel()
    point = safe_auc(y_true, scores)
    rng = np.random.default_rng(seed)
    boots = []
    for idx in _cell_resample_indices(cells, rng):
        a = safe_auc(y_true[idx], scores[idx])
        if np.isfinite(a):
            boots.append(a)
    if len(boots) < 100:
        return point, np.nan, np.nan
    lo, hi = np.percentile(boots, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return point, lo, hi


def paired_cell_bootstrap_delta(y_true, scores_a, scores_b, cells,
                                n_boot=2000, seed=42, alpha=0.05):
    """CI for AUC_a - AUC_b with the same cell resamples for both models."""
    y_true = np.asarray(y_true).ravel()
    scores_a = np.asarray(scores_a).ravel()
    scores_b = np.asarray(scores_b).ravel()
    cells = np.asarray(cells).ravel()
    point = safe_auc(y_true, scores_a) - safe_auc(y_true, scores_b)
    rng = np.random.default_rng(seed)
    boots = []
    for idx in _cell_resample_indices(cells, rng):
        a = safe_auc(y_true[idx], scores_a[idx])
        b = safe_auc(y_true[idx], scores_b[idx])
        if np.isfinite(a) and np.isfinite(b):
            boots.append(a - b)
    if len(boots) < 100:
        return point, np.nan, np.nan
    lo, hi = np.percentile(boots, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return point, lo, hi


def bootstrap_cis_methods(y_true, preds_by_method, cells, methods=None,
                          n_boot=1000, seed=42, alpha=0.05):
    """Percentile CIs for AUC of several score vectors on SHARED cell resamples.

    preds_by_method: dict method -> score array (row-aligned).
    Returns {method: (auc_point, lo, hi)}.
    """
    y_true = np.asarray(y_true).ravel()
    cells = np.asarray(cells).ravel()
    methods = list(methods if methods is not None else preds_by_method.keys())
    scores = {m: np.asarray(preds_by_method[m]).ravel() for m in methods}
    points = {m: safe_auc(y_true, scores[m]) for m in methods}
    uniq = np.unique(cells)
    cell_to_idx = {c: np.where(cells == c)[0] for c in uniq}
    rng = np.random.default_rng(seed)
    boots = {m: [] for m in methods}
    for _ in range(n_boot):
        draw = rng.choice(uniq, size=len(uniq), replace=True)
        idx = np.concatenate([cell_to_idx[c] for c in draw])
        yt = y_true[idx]
        if len(np.unique(yt)) < 2:
            continue
        for m in methods:
            a = safe_auc(yt, scores[m][idx])
            if np.isfinite(a):
                boots[m].append(a)
    out = {}
    for m in methods:
        if len(boots[m]) < 100:
            out[m] = (points[m], np.nan, np.nan)
        else:
            lo, hi = np.percentile(boots[m], [100 * alpha / 2, 100 * (1 - alpha / 2)])
            out[m] = (points[m], lo, hi)
    return out


def expected_cost(y_true, p, threshold, c_fn=20.0, c_fp=1.0):
    """C(tau) = C_FN * FN(tau) + C_FP * FP(tau), normalized per row."""
    y_true = np.asarray(y_true).ravel()
    pred = (np.asarray(p).ravel() >= threshold).astype(int)
    fn = np.sum((y_true == 1) & (pred == 0))
    fp = np.sum((y_true == 0) & (pred == 1))
    return (c_fn * fn + c_fp * fp) / len(y_true)


def optimal_threshold_on_source(y_src, p_src, c_fn=20.0, c_fp=1.0):
    """Pick the decision threshold minimizing expected cost on source data."""
    p_src = np.asarray(p_src).ravel()
    grid = np.unique(np.quantile(p_src, np.linspace(0.01, 0.99, 99)))
    costs = [expected_cost(y_src, p_src, t, c_fn, c_fp) for t in grid]
    return float(grid[int(np.argmin(costs))])


def net_benefit(y_true, p, thresholds):
    """Decision-curve net benefit: TP/n - FP/n * (pt/(1-pt))."""
    y_true = np.asarray(y_true).ravel()
    p = np.asarray(p).ravel()
    n = len(y_true)
    out = []
    for pt in thresholds:
        pred = p >= pt
        tp = np.sum(pred & (y_true == 1))
        fp = np.sum(pred & (y_true == 0))
        if pt >= 1.0:
            nb = np.nan
        else:
            nb = tp / n - fp / n * (pt / (1.0 - pt))
        out.append(nb)
    return np.array(out)


def ece(y_true, p, n_bins=10):
    """Equal-width-bin expected calibration error."""
    y_true = np.asarray(y_true, dtype=float).ravel()
    p = np.asarray(p, dtype=float).ravel()
    bins = np.clip((p * n_bins).astype(int), 0, n_bins - 1)
    total = 0.0
    for b in range(n_bins):
        m = bins == b
        if m.sum() == 0:
            continue
        total += m.mean() * abs(y_true[m].mean() - p[m].mean())
    return float(total)


def calibration_slope_intercept(y_true, p, eps=1e-6):
    """Logistic recalibration: y ~ logit(p). Slope 1 / intercept 0 = perfect."""
    p = np.clip(np.asarray(p, dtype=float).ravel(), eps, 1 - eps)
    logit = np.log(p / (1 - p)).reshape(-1, 1)
    y_true = np.asarray(y_true).ravel()
    if len(np.unique(y_true)) < 2:
        return np.nan, np.nan
    lr = LogisticRegression(C=1e6, solver="lbfgs", max_iter=1000)
    lr.fit(logit, y_true)
    return float(lr.coef_[0, 0]), float(lr.intercept_[0])


def reliability_curve(y_true, p, n_bins=10):
    """(mean_p, observed_rate, count) per equal-width bin, for diagrams."""
    y_true = np.asarray(y_true, dtype=float).ravel()
    p = np.asarray(p, dtype=float).ravel()
    bins = np.clip((p * n_bins).astype(int), 0, n_bins - 1)
    rows = []
    for b in range(n_bins):
        m = bins == b
        if m.sum() == 0:
            continue
        rows.append((float(p[m].mean()), float(y_true[m].mean()), int(m.sum())))
    return rows


def sens_at_fpr(y_true, p, fpr_target=0.1):
    """Sensitivity at a fixed false-positive rate (ROC sweep)."""
    y_true = np.asarray(y_true).ravel()
    p = np.asarray(p).ravel()
    order = np.argsort(-p)
    y_sorted = y_true[order]
    n_pos = y_sorted.sum()
    n_neg = len(y_sorted) - n_pos
    if n_pos == 0 or n_neg == 0:
        return np.nan
    tp = np.cumsum(y_sorted)
    fp = np.cumsum(1 - y_sorted)
    tpr = tp / n_pos
    fpr = fp / n_neg
    valid = fpr <= fpr_target
    if not valid.any():
        return 0.0
    return float(tpr[valid][-1])


def metric_bundle(y_true, p, cells=None, n_boot=0, seed=42):
    """Standard metric set for one score vector.

    With n_boot > 0 and cells given, adds a cell-bootstrap 95% CI for AUC.
    """
    y_true = np.asarray(y_true).ravel()
    p = np.asarray(p, dtype=float).ravel()
    # probability metrics only make sense for scores in [0, 1]; rule-based
    # baselines (e.g. distance-to-threshold) contribute ranking metrics only
    is_prob = (p.min() >= 0.0) and (p.max() <= 1.0) and len(np.unique(y_true)) > 1
    out = {
        "AUC": safe_auc(y_true, p),
        "Brier": brier_score_loss(y_true, p) if is_prob else np.nan,
        "ECE10": ece(y_true, p) if is_prob else np.nan,
        "LogLoss": log_loss(y_true, np.clip(p, 1e-6, 1 - 1e-6)) if is_prob else np.nan,
        "PRAUC": average_precision_score(y_true, p) if len(np.unique(y_true)) > 1 else np.nan,
        "SensAtFPR10": sens_at_fpr(y_true, p, 0.1),
        "CalSlope": np.nan,
        "CalIntercept": np.nan,
        "AUC_lo": np.nan,
        "AUC_hi": np.nan,
    }
    if is_prob:
        slope, intercept = calibration_slope_intercept(y_true, p)
        out["CalSlope"], out["CalIntercept"] = slope, intercept
    if n_boot > 0 and cells is not None:
        _, lo, hi = cell_bootstrap_auc_ci(y_true, p, cells, n_boot=n_boot, seed=seed)
        out["AUC_lo"], out["AUC_hi"] = lo, hi
    return out


def monotonicity_violation_rate(pred_by_H, H_list=(10, 20, 30, 50)):
    """Fraction of rows where cumulative predictions decrease with H.

    pred_by_H: dict H -> score array; arrays must be row-aligned.
    Returns (rate, n_rows) over consecutive horizon pairs.
    """
    Hs = sorted(H_list)
    viol = 0
    n = 0
    for lo, hi in zip(Hs[:-1], Hs[1:]):
        a = np.asarray(pred_by_H[lo], dtype=float).ravel()
        b = np.asarray(pred_by_H[hi], dtype=float).ravel()
        viol += int(np.sum(b < a - 1e-12))
        n += len(a)
    return viol / n if n else np.nan, n
