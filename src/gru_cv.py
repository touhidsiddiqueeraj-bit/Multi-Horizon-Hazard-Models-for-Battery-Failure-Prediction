import os
import warnings
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
from sklearn.metrics import brier_score_loss, roc_auc_score
from sklearn.model_selection import GroupKFold
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from composite_label import make_composite_fail_in_H

_HERE = os.path.dirname(os.path.abspath(__file__))
_DATA_DIR = os.path.join(_HERE, "..", "data")

WINDOW_WIDTH = 10
FEATURES = ["cycle", "avg_voltage", "min_voltage", "avg_current", "avg_temp", "duration", "SOH"]
REQUIRED_COLS = ["cycle", "SOH", "cell", "RUL"]
H_LIST = [10, 20, 30, 50]
N_SPLITS = 5
SEEDS = [0]  # single seed for quick iteration; bump to range(3) or range(10) for full rigor.

# Unlike tree models, GRU cross-chem excludes avg_current (unit mismatch A vs mA),
# avg_temp and duration (always NaN for CALCE). Tree models include these because
# constant features produce no splits; GRU's standardization amplifies them as noise.
CROSS_CHEM_FEATURES_WITH_SOH = ["cycle", "avg_voltage", "min_voltage", "SOH"]
CROSS_CHEM_FEATURES_NO_SOH = ["cycle", "avg_voltage", "min_voltage"]

DATASETS = {
    "nasa": os.path.join(_DATA_DIR, "nasa_clean_filtered.csv"),
    "calce": os.path.join(_DATA_DIR, "calce_clean.csv"),
}

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
warnings.filterwarnings("ignore")


def safe_auc(y_true, p):
    return roc_auc_score(y_true, p) if len(np.unique(y_true)) > 1 else np.nan


def clean_df(df):
    cols_available = [c for c in FEATURES if c in df.columns]
    df = df.replace([np.inf, -np.inf], np.nan)
    df = df.dropna(subset=REQUIRED_COLS).copy()
    df = df[(df["SOH"] > 0) & (df["SOH"] < 1.2)].copy()
    df = df[(df["RUL"] >= 0)].copy()
    df = df.sort_values(["cell", "cycle"]).copy()
    df[cols_available] = df[cols_available].fillna(0)
    return df


def create_windows(df, features, window_width=WINDOW_WIDTH):
    windows, cells = [], []
    for cell_name, g in df.groupby("cell", sort=False):
        g = g.sort_values("cycle")
        vals = g[features].values.astype(np.float64)
        n = len(vals)
        if n < window_width:
            continue
        for i in range(n - window_width + 1):
            windows.append(vals[i : i + window_width])
            cells.append(cell_name)
    if not windows:
        return np.empty((0, window_width, len(features))), np.empty(0, dtype=object)
    return np.array(windows), np.array(cells, dtype=object)


class GRUBinaryClassifier(nn.Module):
    def __init__(self, input_size, hidden_size=8):
        super().__init__()
        self.gru = nn.GRU(input_size, hidden_size, batch_first=True)
        self.fc = nn.Linear(hidden_size, 1)

    def forward(self, x):
        out, _ = self.gru(x)
        logits = self.fc(out[:, -1, :]).squeeze(-1)
        return logits


def train_gru(model, X_tr, y_tr, max_epochs=50, lr=0.005, batch_size=32, pos_weight=None, seed=None):
    if seed is not None:
        torch.manual_seed(seed)
    dataset = TensorDataset(
        torch.tensor(X_tr, dtype=torch.float32),
        torch.tensor(y_tr, dtype=torch.float32),
    )
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=True)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)

    if pos_weight is not None:
        loss_fn = nn.BCEWithLogitsLoss(pos_weight=torch.tensor([pos_weight], device=DEVICE))
    else:
        loss_fn = nn.BCEWithLogitsLoss()

    model.to(DEVICE)
    best_loss = np.inf
    best_state = None
    stall = 0

    for epoch in range(max_epochs):
        model.train()
        epoch_loss = 0.0
        n_batches = 0
        for Xb, yb in loader:
            Xb, yb = Xb.to(DEVICE), yb.to(DEVICE)
            optimizer.zero_grad()
            logits = model(Xb)
            loss = loss_fn(logits, yb)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()
            epoch_loss += loss.item()
            n_batches += 1

        epoch_loss /= n_batches
        if not np.isfinite(epoch_loss):
            stall += 1
            if stall > 10:
                break
            continue

        if epoch_loss < best_loss:
            best_loss = epoch_loss
            best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
            stall = 0
        else:
            stall += 1

        if stall >= 10:
            break

    if best_state is not None:
        model.load_state_dict(best_state)
    model.to(DEVICE)
    model.eval()
    return model


def predict_gru(model, X):
    model.eval()
    with torch.no_grad():
        logits = model(torch.tensor(X, dtype=torch.float32).to(DEVICE))
        probs = torch.sigmoid(logits).cpu().numpy()
    return probs


def compute_window_labels(df, y, X_windows):
    labels = np.empty(len(X_windows), dtype=np.float64)
    idx = 0
    for _, g in df.groupby("cell", sort=False):
        g = g.sort_values("cycle")
        cy = y[g.index]
        n = len(cy)
        if n < WINDOW_WIDTH:
            continue
        for i in range(n - WINDOW_WIDTH + 1):
            labels[idx] = cy[i + WINDOW_WIDTH - 1]
            idx += 1
    return labels


def standardize_windows(X_train, X_test):
    n_tr, seq_len, n_feat = X_train.shape
    scaler = StandardScaler()
    X_tr_flat = X_train.reshape(-1, n_feat)
    scaler.fit(X_tr_flat)
    X_tr_scaled = scaler.transform(X_tr_flat).reshape(n_tr, seq_len, n_feat)
    n_te = X_test.shape[0]
    if n_te > 0:
        X_te_flat = X_test.reshape(-1, n_feat)
        X_te_scaled = scaler.transform(X_te_flat).reshape(n_te, seq_len, n_feat)
    else:
        X_te_scaled = X_test
    return X_tr_scaled, X_te_scaled


def run_cv(df, H, hidden_size=8, seed=42):
    torch.manual_seed(seed)
    y = make_composite_fail_in_H(df, H)
    features = [c for c in FEATURES if c in df.columns]
    X_windows, cells = create_windows(df, features)

    if len(X_windows) == 0:
        return {k: np.nan for k in ["AUC_raw", "AUC_cal_iso", "AUC_cal_platt", "Brier_cal_iso", "Brier_cal_platt"]}

    window_labels = compute_window_labels(df, y, X_windows)
    n_cells = df["cell"].nunique()
    n_splits = min(N_SPLITS, n_cells)

    val_cells_list = []
    for _, test_cells in GroupKFold(n_splits=n_splits).split(
        np.unique(cells), groups=np.unique(cells)
    ):
        val_cells_list.append(np.unique(cells)[test_cells])

    auc_raw_list, auc_iso_list, auc_platt_list = [], [], []
    brier_iso_list, brier_platt_list = [], []

    for val_cells in val_cells_list:
        tr_mask = ~np.isin(cells, val_cells)
        te_mask = np.isin(cells, val_cells)

        X_tr, X_te = X_windows[tr_mask], X_windows[te_mask]
        y_tr, y_te = window_labels[tr_mask], window_labels[te_mask]

        X_tr, X_te = standardize_windows(X_tr, X_te)

        n_pos = y_tr.sum()
        n_neg = len(y_tr) - n_pos
        pw = n_neg / n_pos if n_pos > 0 else None
        n_feat = X_tr.shape[2]

        model = GRUBinaryClassifier(input_size=n_feat, hidden_size=hidden_size)
        model = train_gru(model, X_tr, y_tr, pos_weight=pw, seed=seed)

        p_raw = predict_gru(model, X_te)
        p_tr = predict_gru(model, X_tr)
        if np.any(np.isnan(p_raw)) or np.any(np.isnan(p_tr)):
            continue
        a_raw = safe_auc(y_te, p_raw)

        # Isotonic calibration
        if len(np.unique(y_tr)) < 2:
            p_cal_iso = p_raw.copy()
        else:
            iso = IsotonicRegression(out_of_bounds="clip")
            iso.fit(p_tr, y_tr)
            p_cal_iso = iso.transform(p_raw)

        a_iso = safe_auc(y_te, p_cal_iso)
        b_iso = brier_score_loss(y_te, p_cal_iso)

        # Platt calibration
        if len(np.unique(y_tr)) < 2:
            p_cal_platt = p_raw.copy()
        else:
            platt = LogisticRegression(C=1e10, solver="lbfgs", random_state=42)
            platt.fit(p_tr.reshape(-1, 1), y_tr)
            p_cal_platt = platt.predict_proba(p_raw.reshape(-1, 1))[:, 1]

        a_platt = safe_auc(y_te, p_cal_platt)
        b_platt = brier_score_loss(y_te, p_cal_platt)

        if not np.isnan(a_raw):
            auc_raw_list.append(a_raw)
        if not np.isnan(a_iso):
            auc_iso_list.append(a_iso)
        if not np.isnan(a_platt):
            auc_platt_list.append(a_platt)
        if not np.isnan(b_iso):
            brier_iso_list.append(b_iso)
        if not np.isnan(b_platt):
            brier_platt_list.append(b_platt)

    return {
        "AUC_raw": np.mean(auc_raw_list) if auc_raw_list else np.nan,
        "AUC_cal_iso": np.mean(auc_iso_list) if auc_iso_list else np.nan,
        "AUC_cal_platt": np.mean(auc_platt_list) if auc_platt_list else np.nan,
        "Brier_cal_iso": np.mean(brier_iso_list),
        "Brier_cal_platt": np.mean(brier_platt_list),
    }


def run_cross_chem(train_df, test_df, H, features, hidden_size=8, seed=42):
    torch.manual_seed(seed)
    train_df = train_df.reset_index(drop=True)
    test_df = test_df.reset_index(drop=True)
    y_train = make_composite_fail_in_H(train_df, H)
    y_test = make_composite_fail_in_H(test_df, H)

    if len(np.unique(y_test)) < 2:
        return {k: np.nan for k in ["AUC_raw", "AUC_cal_iso", "AUC_cal_platt", "Brier_cal_iso", "Brier_cal_platt"]}

    X_train_windows, _ = create_windows(train_df, features)
    X_test_windows, _ = create_windows(test_df, features)

    if len(X_train_windows) == 0 or len(X_test_windows) == 0:
        return {k: np.nan for k in ["AUC_raw", "AUC_cal_iso", "AUC_cal_platt", "Brier_cal_iso", "Brier_cal_platt"]}

    train_labels = compute_window_labels(train_df, y_train, X_train_windows)
    test_labels = compute_window_labels(test_df, y_test, X_test_windows)

    X_train, X_test = standardize_windows(X_train_windows, X_test_windows)

    n_pos = train_labels.sum()
    n_neg = len(train_labels) - n_pos
    pw = n_neg / n_pos if n_pos > 0 else None
    n_feat = X_train.shape[2]

    model = GRUBinaryClassifier(input_size=n_feat, hidden_size=hidden_size)
    model = train_gru(model, X_train, train_labels, pos_weight=pw, seed=seed)

    p_raw = predict_gru(model, X_test)
    p_tr = predict_gru(model, X_train)
    if np.any(np.isnan(p_raw)) or np.any(np.isnan(p_tr)):
        return {k: np.nan for k in ["AUC_raw", "AUC_cal_iso", "AUC_cal_platt", "Brier_cal_iso", "Brier_cal_platt"]}
    a_raw = safe_auc(test_labels, p_raw)

    # Isotonic
    if len(np.unique(train_labels)) < 2:
        p_cal_iso = p_raw.copy()
    else:
        iso = IsotonicRegression(out_of_bounds="clip")
        iso.fit(p_tr, train_labels)
        p_cal_iso = iso.transform(p_raw)

    a_iso = safe_auc(test_labels, p_cal_iso)
    b_iso = brier_score_loss(test_labels, p_cal_iso)

    # Platt
    if len(np.unique(train_labels)) < 2:
        p_cal_platt = p_raw.copy()
    else:
        platt = LogisticRegression(C=1e10, solver="lbfgs", random_state=42)
        platt.fit(p_tr.reshape(-1, 1), train_labels)
        p_cal_platt = platt.predict_proba(p_raw.reshape(-1, 1))[:, 1]

    a_platt = safe_auc(test_labels, p_cal_platt)
    b_platt = brier_score_loss(test_labels, p_cal_platt)

    return {
        "AUC_raw": a_raw,
        "AUC_cal_iso": a_iso,
        "AUC_cal_platt": a_platt,
        "Brier_cal_iso": b_iso,
        "Brier_cal_platt": b_platt,
    }


def run_cross_chem_per_cell(train_df, test_df, H, features, hidden_size=8, seed=42):
    """Cross-chem transfer with per-cell evaluation on test cells.

    Trains GRU ONCE on all training data, then scores each test cell
    independently via fast forward-passes (no 141× redundant training).
    Returns mean +/- std across cells.
    """
    y_train = make_composite_fail_in_H(train_df, H)
    y_test = make_composite_fail_in_H(test_df, H)

    if len(np.unique(y_test)) < 2:
        return {k: np.nan for k in ["AUC_raw", "AUC_cal_iso", "AUC_cal_platt",
                                     "Brier_cal_iso", "Brier_cal_platt"]}

    X_train_windows, _ = create_windows(train_df, features)
    X_test_windows, test_cell_names = create_windows(test_df, features)

    if len(X_train_windows) == 0 or len(X_test_windows) == 0:
        return {k: np.nan for k in ["AUC_raw", "AUC_cal_iso", "AUC_cal_platt",
                                     "Brier_cal_iso", "Brier_cal_platt"]}

    train_labels = compute_window_labels(train_df, y_train, X_train_windows)
    test_labels = compute_window_labels(test_df, y_test, X_test_windows)

    X_train, X_test = standardize_windows(X_train_windows, X_test_windows)

    n_pos = train_labels.sum()
    n_neg = len(train_labels) - n_pos
    pw = n_neg / n_pos if n_pos > 0 else None
    n_feat = X_train.shape[2]

    model = GRUBinaryClassifier(input_size=n_feat, hidden_size=hidden_size)
    model = train_gru(model, X_train, train_labels, pos_weight=pw, seed=seed)

    p_tr = predict_gru(model, X_train)
    p_raw_all = predict_gru(model, X_test)

    if np.any(np.isnan(p_tr)) or np.any(np.isnan(p_raw_all)):
        return {k: np.nan for k in ["AUC_raw", "AUC_cal_iso", "AUC_cal_platt",
                                     "Brier_cal_iso", "Brier_cal_platt"]}

    if len(np.unique(train_labels)) >= 2:
        iso = IsotonicRegression(out_of_bounds="clip")
        iso.fit(p_tr, train_labels)
        platt = LogisticRegression(C=1e10, solver="lbfgs", random_state=42)
        platt.fit(p_tr.reshape(-1, 1), train_labels)

    cells = test_df["cell"].unique()
    per_cell = {k: [] for k in
                ["AUC_raw", "AUC_cal_iso", "AUC_cal_platt", "Brier_cal_iso", "Brier_cal_platt"]}
    cell_tags = []

    for cell in cells:
        mask = test_cell_names == cell
        if mask.sum() == 0:
            continue
        cell_tags.append(cell)

        p_raw = p_raw_all[mask]
        labels = test_labels[mask]

        a_raw = safe_auc(labels, p_raw)
        per_cell["AUC_raw"].append(a_raw)

        if len(np.unique(train_labels)) >= 2:
            p_cal_iso = iso.transform(p_raw)
            p_cal_platt = platt.predict_proba(p_raw.reshape(-1, 1))[:, 1]
        else:
            p_cal_iso = p_raw.copy()
            p_cal_platt = p_raw.copy()

        per_cell["AUC_cal_iso"].append(safe_auc(labels, p_cal_iso))
        per_cell["Brier_cal_iso"].append(brier_score_loss(labels, p_cal_iso))
        per_cell["AUC_cal_platt"].append(safe_auc(labels, p_cal_platt))
        per_cell["Brier_cal_platt"].append(brier_score_loss(labels, p_cal_platt))

    result = {}
    for k in per_cell:
        arr = np.array(per_cell[k], dtype=float)
        valid = arr[np.isfinite(arr)]
        result[k] = np.mean(valid) if len(valid) > 0 else np.nan
        result[f"{k}_std"] = np.std(valid) if len(valid) > 0 else np.nan

    result["cell_aucs_raw"] = str(
        [f"{c}:{r:.4f}" for c, r in zip(cell_tags, per_cell["AUC_raw"])])
    result["cell_aucs_platt"] = str(
        [f"{c}:{r:.4f}" for c, r in zip(cell_tags, per_cell["AUC_cal_platt"])])
    return result


def _save_seed_rows(srows):
    path = os.path.join(_DATA_DIR, "benchmark_results.csv")
    sdf = pd.DataFrame(srows)
    seed_val = srows[0]["seed"]
    if os.path.exists(path):
        existing = pd.read_csv(path)
        if "seed" in existing.columns:
            mask = ~((existing["model"] == "gru") & (existing["seed"] == seed_val))
            existing = existing[mask]
        combined = pd.concat([existing, sdf], ignore_index=True)
    else:
        combined = sdf
    combined.to_csv(path, index=False)
    print(f"  → Saved seed {seed_val} ({len(sdf)} rows)")


def main():
    os.makedirs(_DATA_DIR, exist_ok=True)
    all_rows = []

    for seed in SEEDS:
        torch.manual_seed(seed)
        print(f"\n{'=' * 60}")
        print(f"Seed {seed}/{max(SEEDS)}")
        print(f"{'=' * 60}")

        # --- Within-dataset CV ---
        for ds_name, ds_path in DATASETS.items():
            if not os.path.exists(ds_path):
                print(f"SKIPPING {ds_name} -- file not found: {ds_path}")
                continue

            raw_df = pd.read_csv(ds_path)
            df = clean_df(raw_df)
            n_cells = df["cell"].nunique()
            if n_cells < 2:
                print(f"SKIPPING {ds_name} -- only {n_cells} cells (need >= 2)")
                continue

            print(f"\n=== Dataset: {ds_name} | {n_cells} cells, {len(df)} rows ===")

            for H in H_LIST:
                y = make_composite_fail_in_H(df, H)
                if len(np.unique(y)) < 2:
                    print(f"  GRU H={H} ... SKIP (no failures)")
                    continue

                print(f"  GRU H={H} ...", end=" ", flush=True)
                res = run_cv(df, H, hidden_size=8, seed=seed)
                if np.isnan(res["AUC_cal_iso"]) and np.isnan(res["AUC_cal_platt"]):
                    print("FAILED (NaN predictions)")
                    continue
                if res["AUC_cal_iso"] < 0.3 and res["AUC_cal_platt"] < 0.3:
                    print(f"FAILED (near-zero AUC)")
                    continue
                print(f"iso={res['AUC_cal_iso']:.3f}/{res['Brier_cal_iso']:.3f} "
                      f"platt={res['AUC_cal_platt']:.3f}/{res['Brier_cal_platt']:.3f}")

                for method in ["iso", "platt"]:
                    all_rows.append({
                        "dataset": ds_name,
                        "model": "gru",
                        "H": H,
                        "method": method,
                        "eval": "within",
                        "seed": seed,
                        "AUC_raw": res["AUC_raw"],
                        "AUC_cal": res[f"AUC_cal_{method}"],
                        "Brier_cal": res[f"Brier_cal_{method}"],
                    })

        # --- Cross-chemistry transfer: LCO -> LFP ---
        nasa_path = DATASETS["nasa"]
        calce_path = DATASETS["calce"]
        oxford_path = os.path.join(_DATA_DIR, "oxford_clean.csv")

        if os.path.exists(oxford_path):
            test_df = clean_df(pd.read_csv(oxford_path))
            transfer_sets = {
                "nasa": clean_df(pd.read_csv(nasa_path)),
                "calce": clean_df(pd.read_csv(calce_path)),
            }
            combined = pd.concat(
                [clean_df(pd.read_csv(nasa_path)), clean_df(pd.read_csv(calce_path))],
                ignore_index=True,
            )
            transfer_sets["nasa+calce"] = combined

            for features, feat_label in [
                (CROSS_CHEM_FEATURES_WITH_SOH, "with_soh"),
                (CROSS_CHEM_FEATURES_NO_SOH, "no_soh"),
            ]:
                print(f"\n=== Cross-chemistry transfer [{feat_label}]: LCO -> LFP ===")
                for train_name, train_df in transfer_sets.items():
                    n_cells = train_df["cell"].nunique()
                    print(f"  Train: {train_name} ({n_cells} cells) -> Test: Oxford (per-cell eval)")

                    for H in H_LIST:
                        y_test = make_composite_fail_in_H(test_df, H)
                        if len(np.unique(y_test)) < 2:
                            print(f"    GRU H={H} ... SKIP (no failures on test)")
                            continue

                        print(f"    GRU H={H} ...", end=" ", flush=True)
                        res = run_cross_chem_per_cell(train_df, test_df, H, features,
                                                      hidden_size=8, seed=seed)
                        if np.isnan(res["AUC_cal_iso"]) and np.isnan(res["AUC_cal_platt"]):
                            print("FAILED")
                            continue
                        print(f"iso={res['AUC_cal_iso']:.3f}±{res['AUC_cal_iso_std']:.3f} "
                              f"platt={res['AUC_cal_platt']:.3f}±{res['AUC_cal_platt_std']:.3f}")

                        for method in ["iso", "platt"]:
                            all_rows.append({
                                "dataset": "oxford",
                                "model": "gru",
                                "H": H,
                                "method": method,
                                "eval": f"train_{train_name}_{feat_label}",
                                "seed": seed,
                                "AUC_raw": res["AUC_raw"],
                                "AUC_cal": res[f"AUC_cal_{method}"],
                                "AUC_cal_std": res[f"AUC_cal_{method}_std"],
                                "Brier_cal": res[f"Brier_cal_{method}"],
                                "Brier_cal_std": res[f"Brier_cal_{method}_std"],
                            })
            # --- Cross-chemistry transfer: LCO -> Severson LFP ---
            severson_path = os.path.join(_DATA_DIR, "severson_clean.csv")
            if os.path.exists(severson_path):
                test_df_sev = clean_df(pd.read_csv(severson_path))

                for features, feat_label in [
                    (CROSS_CHEM_FEATURES_WITH_SOH, "with_soh"),
                    (CROSS_CHEM_FEATURES_NO_SOH, "no_soh"),
                ]:
                    print(f"\n=== Cross-chemistry transfer [{feat_label}]: LCO -> Severson LFP ===")
                    for train_name, train_df in transfer_sets.items():
                        n_cells = train_df["cell"].nunique()
                        print(f"  Train: {train_name} ({n_cells} cells) -> Test: Severson (per-cell eval)")

                        for H in H_LIST:
                            y_test = make_composite_fail_in_H(test_df_sev, H)
                            if len(np.unique(y_test)) < 2:
                                print(f"    GRU H={H} ... SKIP (no failures on test)")
                                continue

                            print(f"    GRU H={H} ...", end=" ", flush=True)
                            res = run_cross_chem_per_cell(train_df, test_df_sev, H, features,
                                                          hidden_size=8, seed=seed)
                            if np.isnan(res["AUC_cal_iso"]) and np.isnan(res["AUC_cal_platt"]):
                                print("FAILED")
                                continue
                            print(f"iso={res['AUC_cal_iso']:.3f}±{res['AUC_cal_iso_std']:.3f} "
                                  f"platt={res['AUC_cal_platt']:.3f}±{res['AUC_cal_platt_std']:.3f}")

                            for method in ["iso", "platt"]:
                                all_rows.append({
                                    "dataset": "severson",
                                    "model": "gru",
                                    "H": H,
                                    "method": method,
                                    "eval": f"train_{train_name}_{feat_label}",
                                    "seed": seed,
                                    "AUC_raw": res["AUC_raw"],
                                    "AUC_cal": res[f"AUC_cal_{method}"],
                                    "AUC_cal_std": res[f"AUC_cal_{method}_std"],
                                    "Brier_cal": res[f"Brier_cal_{method}"],
                                    "Brier_cal_std": res[f"Brier_cal_{method}_std"],
                                })
            else:
                print(f"SKIPPING Severson cross-chemistry -- file not found: {severson_path}")
        else:
            print(f"SKIPPING cross-chemistry -- Oxford file not found: {oxford_path}")

        # Incremental save — flush this seed's rows to disk
        seed_rows = [r for r in all_rows if r["seed"] == seed]
        if seed_rows:
            _save_seed_rows(seed_rows)

    # Print per-seed summary at H=20
    path = os.path.join(_DATA_DIR, "benchmark_results.csv")
    results = pd.read_csv(path) if os.path.exists(path) else pd.DataFrame()
    print("\n=== Multi-seed summary at H=20 ===")
    h20 = results[(results["H"] == 20) & (results["seed"].notna())].copy()
    if not h20.empty:
        for eval_name in h20["eval"].unique():
            ev = h20[h20["eval"] == eval_name]
            for method in ["iso", "platt"]:
                m = ev[ev["method"] == method]
                if len(m) == 0:
                    continue
                aucs = m["AUC_cal"].dropna().values
                if len(aucs) < 2:
                    print(f"  {eval_name:40s} {method:5s}  mean={np.mean(aucs):.3f}  (1 seed)")
                else:
                    print(f"  {eval_name:40s} {method:5s}  mean={np.mean(aucs):.3f} ± {np.std(aucs):.3f}  "
                          f"min={np.min(aucs):.3f} max={np.max(aucs):.3f}  n_seeds={len(aucs)}")

    # Print per-seed detail
    print("\n=== Per-seed detail at H=20 ===")
    for _, row in h20.iterrows():
        print(f"  seed={int(row['seed']):2d}  {row['eval']:40s}  {row['method']:5s}  "
              f"AUC={row['AUC_cal']:.4f}  Brier={row['Brier_cal']:.4f}")


if __name__ == "__main__":
    main()
