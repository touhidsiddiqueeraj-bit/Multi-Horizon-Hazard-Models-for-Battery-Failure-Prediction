import numpy as np
from sklearn.metrics import roc_auc_score


def delong_roc_test(y_true, y_pred_a, y_pred_b):
    """Two-tailed p-value for H0: AUC_a == AUC_b.

    Implements DeLong, DeLong & Clarke-Pearson (1988)
    ``Comparing the Areas under Two Correlated ROC Curves''.

    Parameters
    ----------
    y_true : array-like, shape (n_samples,)
        True binary labels.
    y_pred_a : array-like, shape (n_samples,)
        Predicted scores from model A.
    y_pred_b : array-like, shape (n_samples,)
        Predicted scores from model B.

    Returns
    -------
    dict with keys: auc_a, auc_b, z_stat, p_value, significant_0.05
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

    # Placement values for model A
    V10_a = np.zeros(n_pos)
    V01_a = np.zeros(n_neg)
    for i, pi in enumerate(pos_idx):
        V10_a[i] = np.mean(y_pred_a[pi] > y_pred_a[neg_idx]) + 0.5 * np.mean(y_pred_a[pi] == y_pred_a[neg_idx])
    for j, nj in enumerate(neg_idx):
        V01_a[j] = np.mean(y_pred_a[pos_idx] > y_pred_a[nj]) + 0.5 * np.mean(y_pred_a[pos_idx] == y_pred_a[nj])

    V10_b = np.zeros(n_pos)
    V01_b = np.zeros(n_neg)
    for i, pi in enumerate(pos_idx):
        V10_b[i] = np.mean(y_pred_b[pi] > y_pred_b[neg_idx]) + 0.5 * np.mean(y_pred_b[pi] == y_pred_b[neg_idx])
    for j, nj in enumerate(neg_idx):
        V01_b[j] = np.mean(y_pred_b[pos_idx] > y_pred_b[nj]) + 0.5 * np.mean(y_pred_b[pos_idx] == y_pred_b[nj])

    # Variance components
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

    return {
        "auc_a": auc_a,
        "auc_b": auc_b,
        "z_stat": z_stat,
        "p_value": p_value,
        "significant_0.05": p_value < 0.05,
    }
