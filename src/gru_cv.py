"""GRU sequence classifier: within-dataset CV and cross-chemistry transfer.

Calibration protocol (matches the tree pipeline's leakage-clean guarantee,
with a cell-holdout variant because inner cross-fitting a GRU is
prohibitively expensive):
  within:  per outer cell fold, train cells are split into model cells
           (~3/4) and calibration cells (~1/4); calibrators fit on the
           calibration cells' scores from the model-cell-trained GRU.
  transfer: two GRUs are trained per (source, feature set, H, seed) --
           one on ALL source cells (used to score the target) and one on a
           75% cell subset (used to generate calibration scores on the
           held-out 25% of source cells, on which the calibrators fit).
Transfer is run with seeds {42, 1, 7}; within-dataset uses seed 42.

Outputs: results_v2/gru_within.csv, results_v2/gru_transfer.csv,
preds/transfer_<target>_<source>_<fs>_gru_H<H>.csv (seed 42)
"""
import os
import argparse
import numpy as np
import pandas as pd
import torch
from sklearn.metrics import brier_score_loss
from sklearn.model_selection import GroupKFold
from sklearn.preprocessing import StandardScaler

from composite_label import make_composite_fail_in_H
from pipeline_core import (load_clean, load_source, fit_calibrators,
                           apply_calibrators, summarize, save_preds,
                           results_path, FEATURE_SETS, H_LIST, LCO_SOURCES,
                           COMMON_FEATURES_WITH_SOH, COMMON_FEATURES_NO_SOH)
from stats_utils import bootstrap_cis_methods
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

_HERE = os.path.dirname(os.path.abspath(__file__))
WINDOW_WIDTH = 10
HIDDEN = 8
WITHIN_SEED = 42
TRANSFER_SEEDS = [42, 1, 7]
TRANSFER_FEATURE_SETS = ["common_with_soh", "common_no_soh"]
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
import warnings
warnings.filterwarnings("ignore")


def safe_auc(y, p):
    from sklearn.metrics import roc_auc_score
    y = np.asarray(y).ravel()
    return roc_auc_score(y, p) if len(np.unique(y)) > 1 else np.nan


class GRUBinaryClassifier(nn.Module):
    def __init__(self, input_size, hidden_size=HIDDEN):
        super().__init__()
        self.gru = nn.GRU(input_size, hidden_size, batch_first=True)
        self.fc = nn.Linear(hidden_size, 1)

    def forward(self, x):
        out, _ = self.gru(x)
        return self.fc(out[:, -1, :]).squeeze(-1)


def train_gru(model, X, y, max_epochs=50, lr=0.005, batch_size=32, seed=42):
    torch.manual_seed(seed)
    pos = max(y.sum(), 1)
    loss_fn = nn.BCEWithLogitsLoss(pos_weight=torch.tensor([(len(y) - pos) / pos],
                                                           device=DEVICE))
    loader = DataLoader(TensorDataset(torch.tensor(X, dtype=torch.float32),
                                      torch.tensor(y, dtype=torch.float32)),
                        batch_size=batch_size, shuffle=True)
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    best, best_state, stall = np.inf, None, 0
    for _ in range(max_epochs):
        model.train()
        tot, nb = 0.0, 0
        for Xb, yb in loader:
            Xb, yb = Xb.to(DEVICE), yb.to(DEVICE)
            opt.zero_grad()
            loss = loss_fn(model(Xb), yb)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            tot += loss.item()
            nb += 1
        ep = tot / max(nb, 1)
        if not np.isfinite(ep):
            stall += 1
        elif ep < best:
            best, stall = ep, 0
            best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
        else:
            stall += 1
        if stall >= 10:
            break
    if best_state is not None:
        model.load_state_dict(best_state)
    model.to(DEVICE).eval()
    return model


def predict_gru(model, X):
    with torch.no_grad():
        return torch.sigmoid(model(torch.tensor(X, dtype=torch.float32).to(DEVICE))).cpu().numpy()


def make_windows(df, features):
    """Windows, window->cell map, window labels (labels aligned to df rows)."""
    X, cells, labels, cycle_idx = [], [], [], []
    for cell, g in df.groupby("cell", sort=False):
        g = g.sort_values("cycle")
        vals = g[features].values.astype(np.float64)
        n = len(vals)
        if n < WINDOW_WIDTH:
            continue
        for i in range(n - WINDOW_WIDTH + 1):
            X.append(vals[i:i + WINDOW_WIDTH])
            cells.append(cell)
            cycle_idx.append(g["cycle"].iloc[i + WINDOW_WIDTH - 1])
    if not X:
        return (np.empty((0, WINDOW_WIDTH, len(features))),
                np.empty(0, dtype=object), np.empty(0), np.empty(0))
    return np.array(X), np.array(cells, dtype=object), None, np.array(cycle_idx)


def window_labels(df, y_row, features):
    """Labels for each window (label of its last row), matching make_windows."""
    df = df.reset_index(drop=True)  # positional labels: y_row is row-ordered
    out = []
    for cell, g in df.groupby("cell", sort=False):
        g = g.sort_values("cycle")
        n = len(g)
        if n < WINDOW_WIDTH:
            continue
        out.append(y_row[(g.index)[WINDOW_WIDTH - 1:]])
    return np.concatenate(out) if out else np.empty(0)


def scale(X_tr, *others):
    nf = X_tr.shape[2]
    sc = StandardScaler().fit(X_tr.reshape(-1, nf))
    out = [sc.transform(X_tr.reshape(-1, nf)).reshape(X_tr.shape)]
    for Xo in others:
        out.append(sc.transform(Xo.reshape(-1, nf)).reshape(Xo.shape) if len(Xo) else Xo)
    return out


# ------------------------------------------------------------------ within
def gru_within(ds_name, H, seed=WITHIN_SEED):
    df = load_clean(ds_name)
    y_row = make_composite_fail_in_H(df, H)
    features = [c for c in FEATURE_SETS["with_soh"] if c in df.columns]
    X, cells, _, cyc = make_windows(df, features)
    if len(X) == 0:
        return None
    y_win = window_labels(df, y_row, features)
    uniq = pd.unique(cells)
    outer_k = len(uniq) if len(uniq) <= 8 else 5

    pooled = {"raw": [], "iso": [], "platt": [], "temp": []}
    ys, cs = [], []
    fold_aucs = {k: [] for k in pooled}
    gkf = GroupKFold(n_splits=outer_k)
    dummy = np.zeros((len(uniq), 1))
    for _, te_pos in gkf.split(dummy, groups=uniq):
        te_cells = uniq[te_pos]
        tr_cells = np.setdiff1d(uniq, te_cells)
        # cell-holdout calibration split: GroupKFold(4) over train cells,
        # first val split = calibration cells
        gkf_in = GroupKFold(n_splits=min(4, len(tr_cells)))
        sp = list(gkf_in.split(np.zeros((len(tr_cells), 1)), groups=tr_cells))
        cal_cells = tr_cells[sp[0][1]]
        fit_cells = tr_cells[sp[0][0]]
        m_fit = np.isin(cells, fit_cells)
        m_cal = np.isin(cells, cal_cells)
        m_te = np.isin(cells, te_cells)
        if m_fit.sum() == 0 or m_cal.sum() == 0 or m_te.sum() == 0:
            continue
        if len(np.unique(y_win[m_fit])) < 2 or len(np.unique(y_win[m_cal])) < 2:
            continue
        X_fit, X_cal, X_te = scale(X[m_fit], X[m_cal], X[m_te])
        net = GRUBinaryClassifier(input_size=X_fit.shape[2])
        train_gru(net, X_fit, y_win[m_fit], seed=seed)
        p_cal = predict_gru(net, X_cal)
        cal = fit_calibrators(p_cal, y_win[m_cal])
        if cal is None:
            continue
        p_te = predict_gru(net, X_te)
        preds = apply_calibrators(cal, p_te)
        for k in pooled:
            pooled[k].append(preds[k])
            a = safe_auc(y_win[m_te], preds[k])
            if np.isfinite(a):
                fold_aucs[k].append(a)
        ys.append(y_win[m_te])
        cs.append(cells[m_te])
    if not ys:
        return None
    y_all = np.concatenate(ys)
    c_all = np.concatenate(cs)
    preds = {k: np.concatenate(v) for k, v in pooled.items()}
    rows = []
    for k in ["raw", "iso", "platt", "temp"]:
        r = summarize(y_all, preds[k], c_all)
        r.update(dataset=ds_name, model="gru", H=H, method=k, seed=seed,
                 AUC_fold_mean=float(np.mean(fold_aucs[k])) if fold_aucs[k] else np.nan,
                 AUC_fold_std=float(np.std(fold_aucs[k], ddof=1)) if len(fold_aucs[k]) > 1 else np.nan)
        rows.append(r)
    return y_all, c_all, preds, rows


def cmd_within():
    out = []
    for ds_name in ["nasa", "calce"]:
        for H in H_LIST:
            res = gru_within(ds_name, H)
            if res is None:
                print(f"  gru {ds_name} H={H}: skipped", flush=True)
                continue
            y_all, c_all, preds, rows = res
            out.extend(rows)
            if H == 20:
                save_preds(f"within_{ds_name}_gru_H20.csv",
                           pd.DataFrame({"cell": c_all, "y": y_all, **preds}))
            print(f"  gru {ds_name} H={H}: raw={rows[0]['AUC']:.3f} "
                  f"platt={rows[2]['AUC']:.3f}", flush=True)
    pd.DataFrame(out).to_csv(results_path("gru_within.csv"), index=False)
    print("saved gru_within.csv", flush=True)


# ------------------------------------------------------------------ transfer
def gru_transfer(source_key, target_name, H, feature_set, seed):
    features = FEATURE_SETS[feature_set]
    train_df = load_source(source_key).reset_index(drop=True)
    test_df = load_clean(target_name).reset_index(drop=True)
    features = [c for c in features if c in train_df.columns and c in test_df.columns]
    y_test_row = make_composite_fail_in_H(test_df, H)
    if len(np.unique(y_test_row)) < 2:
        return None

    # scored model: ALL source cells
    X_tr, _, _, _ = make_windows(train_df, features)
    y_tr = window_labels(train_df, make_composite_fail_in_H(train_df, H), features)
    X_te, te_cells, _, _ = make_windows(test_df, features)
    y_te = window_labels(test_df, y_test_row, features)
    if len(X_tr) == 0 or len(X_te) == 0:
        return None
    X_tr_s, X_te_s = scale(X_tr, X_te)
    net_full = GRUBinaryClassifier(input_size=X_tr_s.shape[2])
    train_gru(net_full, X_tr_s, y_tr, seed=seed)
    p_te = predict_gru(net_full, X_te_s)

    # calibration model: 75% of source cells; calibrators on the other 25%
    uniq = pd.unique(train_df["cell"])
    gkf = GroupKFold(n_splits=4)
    sp = list(gkf.split(np.zeros((len(uniq), 1)), groups=uniq))
    cal_cells, fit_cells = uniq[sp[0][1]], uniq[sp[0][0]]
    tr_cal_df = train_df[np.isin(train_df["cell"], cal_cells)]
    tr_fit_df = train_df[np.isin(train_df["cell"], fit_cells)]
    X_f, _, _, _ = make_windows(tr_fit_df, features)
    y_f = window_labels(tr_fit_df, make_composite_fail_in_H(tr_fit_df, H), features)
    X_c, _, _, _ = make_windows(tr_cal_df, features)
    y_c = window_labels(tr_cal_df, make_composite_fail_in_H(tr_cal_df, H), features)
    if len(np.unique(y_c)) < 2 or len(X_f) == 0 or len(X_c) == 0:
        return None
    X_f_s, X_c_s = scale(X_f, X_c)
    net_cal = GRUBinaryClassifier(input_size=X_f_s.shape[2])
    train_gru(net_cal, X_f_s, y_f, seed=seed)
    cal = fit_calibrators(predict_gru(net_cal, X_c_s), y_c)
    if cal is None:
        return None
    preds = apply_calibrators(cal, p_te)

    out = {"source": source_key, "target": target_name, "H": H,
           "feature_set": feature_set, "model": "gru", "seed": seed}
    for method in ["raw", "iso", "platt", "temp"]:
        r = summarize(y_te, preds[method], te_cells)
        for k, v in r.items():
            out[f"{method}_{k}"] = v
    cis = bootstrap_cis_methods(y_te, preds, te_cells, methods=["raw", "platt"],
                                n_boot=400 if len(y_te) > 20000 else 1000)
    for method, (_, lo, hi) in cis.items():
        out[f"{method}_AUC_lo"], out[f"{method}_AUC_hi"] = lo, hi
    pooled = None
    if seed == WITHIN_SEED:
        pooled = pd.DataFrame({"cell": te_cells, "y": y_te, **preds})
    return out, pooled


def cmd_transfer():
    out = []
    for target_name in ["oxford", "severson"]:
        print(f"=== GRU transfer -> {target_name} ===", flush=True)
        for source_key in LCO_SOURCES:
            for feature_set in TRANSFER_FEATURE_SETS:
                for H in H_LIST:
                    for seed in TRANSFER_SEEDS:
                        res = gru_transfer(source_key, target_name, H, feature_set, seed)
                        if res is None:
                            continue
                        row, pooled = res
                        out.append(row)
                        if pooled is not None:
                            save_preds(f"transfer_{target_name}_{source_key}_{feature_set}_gru_H{H}.csv",
                                       pooled)
                        print(f"  {source_key:10s} {feature_set:16s} H={H} seed={seed}: "
                              f"raw={row['raw_AUC']:.3f} platt={row['platt_AUC']:.3f}", flush=True)
    pd.DataFrame(out).to_csv(results_path("gru_transfer.csv"), index=False)
    print("saved gru_transfer.csv", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["within", "transfer", "all"])
    args = ap.parse_args()
    if args.cmd in ("within", "all"):
        cmd_within()
    if args.cmd in ("transfer", "all"):
        cmd_transfer()


if __name__ == "__main__":
    main()
