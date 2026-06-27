import os
import h5py
import numpy as np
import pandas as pd

DATA_PATH = "../data/severson"
OUTPUT_CSV = "../data/severson_clean.csv"

# From https://data.matr.io/1/projects/5c48dd2bc625d700019f7e4f
# Severson et al. Nature Energy 2019 — 124 LFP cells under fast-charging conditions
BATCH_FILES = [
    "2017-05-12_batchdata_updated_struct_errorcorrect.mat",
    "2018-02-20_batchdata_updated_struct_errorcorrect.mat",
    "2018-04-03_varcharge_batchdata_updated_struct_errorcorrect.mat",
    "2018-04-12_batchdata_updated_struct_errorcorrect.mat",
]


def extract_discharge_indices(I_arr, threshold=-0.01):
    return np.where(I_arr < threshold)[0]


def compute_cycle_features(V_arr, I_arr, t_arr, T_arr):
    dis_idx = extract_discharge_indices(I_arr)
    if len(dis_idx) < 5:
        return None
    V_dis = V_arr[dis_idx]
    I_dis = I_arr[dis_idx]
    t_dis = t_arr[dis_idx]
    T_dis = T_arr[dis_idx]
    duration = float(t_dis[-1] - t_dis[0]) if len(t_dis) > 1 else np.nan
    return {
        "avg_voltage": float(np.nanmean(V_dis)),
        "min_voltage": float(np.nanmin(V_dis)),
        "avg_current": float(np.nanmean(np.abs(I_dis))),
        "avg_temp": float(np.nanmean(T_dis)),
        "duration": duration,
    }


def process_batch(h5_path, batch_label):
    f = h5py.File(h5_path, "r")
    batch = f["batch"]
    n_cells = len(batch["cycle_life"])
    all_records = []

    for i in range(n_cells):
        # --- cycle_life ---
        cl_ref = batch["cycle_life"][i, 0]
        cycle_life_arr = f[cl_ref][:]
        if cycle_life_arr.size == 0 or np.isnan(cycle_life_arr[0, 0]):
            cycle_life = None
        else:
            cycle_life = int(cycle_life_arr[0, 0])

        # --- summary ---
        summary = f[batch["summary"][i, 0]]
        cycles_arr = summary["cycle"][0, :]
        Qd_arr = summary["QDischarge"][0, :]
        Tavg_arr = summary["Tavg"][0, :]
        chargetime_arr = summary["chargetime"][0, :]

        # --- cycles (per-cycle V, I, T, t) ---
        cycles_group = f[batch["cycles"][i, 0]]

        n_cycles = len(cycles_arr)
        cell_records = []

        for j in range(n_cycles):
            cyc_num = int(cycles_arr[j])
            Qd = float(Qd_arr[j])

            if cyc_num == 0 or Qd <= 0:
                continue

            Tavg = float(Tavg_arr[j])
            chargetime = float(chargetime_arr[j])

            # Extract per-cycle raw data
            V_ref = cycles_group["V"][j, 0]
            I_ref = cycles_group["I"][j, 0]
            t_ref = cycles_group["t"][j, 0]
            T_ref = cycles_group["T"][j, 0]

            try:
                V = np.atleast_1d(f[V_ref][:]).astype(float).squeeze()
                I = np.atleast_1d(f[I_ref][:]).astype(float).squeeze()
                t = np.atleast_1d(f[t_ref][:]).astype(float).squeeze()
                T = np.atleast_1d(f[T_ref][:]).astype(float).squeeze()
            except Exception:
                continue

            if V.ndim == 0 or V.size < 10:
                continue

            feat = compute_cycle_features(V, I, t, T)
            if feat is None:
                continue

            feat["cycle"] = cyc_num
            feat["capacity"] = Qd
            feat["cell"] = f"severson_b{batch_label}_c{i}"
            cell_records.append(feat)

        if not cell_records:
            print(f"  Skipped cell {i} (b{batch_label}_c{i}): no valid cycles")
            continue

        cell_df = pd.DataFrame(cell_records).sort_values("cycle")

        # SOH: initial capacity = mean of first 10 cycles
        n_init = min(10, len(cell_df))
        initial_cap = cell_df["capacity"].iloc[:n_init].mean()
        if not np.isfinite(initial_cap) or initial_cap <= 0:
            print(f"  Skipped cell {i} (b{batch_label}_c{i}): bad initial capacity")
            continue

        # SOH: initial capacity = mean of first 10 cycles. No clip — other loaders
        # (NASA, CALCE, Oxford) leave SOH uncapped, so for cross-chemistry consistency
        # we do the same here. A 1.2 guard is applied later in benchmark_cv.py / gru_cv.py.
        cell_df["SOH"] = cell_df["capacity"] / initial_cap
        if len(eol_idx) > 0:
            eol_cycle = int(cell_df.loc[eol_idx[0], "cycle"])
            cell_df["RUL"] = (eol_cycle - cell_df["cycle"]).clip(lower=0)
        else:
            cell_df["RUL"] = cell_df["cycle"].max() - cell_df["cycle"]

        all_records.append(cell_df)
        print(f"  b{batch_label}_c{i}: {len(cell_df)} cycles, "
              f"capacity={initial_cap:.4f}Ah, "
              f"SOH range={cell_df['SOH'].min():.4f}-{cell_df['SOH'].max():.4f}, "
              f"cycle_life={cycle_life}")

    f.close()
    return pd.concat(all_records, ignore_index=True) if all_records else pd.DataFrame()


def load_all_severson():
    all_dfs = []
    for fname in BATCH_FILES:
        path = os.path.join(DATA_PATH, fname)
        if not os.path.exists(path):
            print(f"Skipped {fname}: not found at {path}")
            continue
        batch_label = BATCH_FILES.index(fname) + 1
        print(f"\nLoading: {fname} (batch {batch_label})")
        df = process_batch(path, batch_label)
        if df.empty:
            print(f"  No data extracted from {fname}")
            continue
        all_dfs.append(df)
        print(f"  -> {len(df)} rows from batch {batch_label}")

    if not all_dfs:
        print("ERROR: no Severson data loaded")
        return pd.DataFrame()

    final_df = pd.concat(all_dfs, ignore_index=True)
    final_df = final_df[["cycle", "avg_voltage", "min_voltage", "avg_current",
                         "avg_temp", "duration", "capacity", "SOH", "RUL", "cell"]]
    final_df.to_csv(OUTPUT_CSV, index=False)
    print(f"\nSaved: {OUTPUT_CSV}")
    print(f"  {len(final_df)} cycles, {final_df['cell'].nunique()} cells")
    print(f"  SOH range: {final_df['SOH'].min():.4f}-{final_df['SOH'].max():.4f}")
    print(f"  RUL range: {final_df['RUL'].min()}-{final_df['RUL'].max()}")
    print(f"  Cells: {sorted(final_df['cell'].unique())}")
    return final_df


if __name__ == "__main__":
    load_all_severson()
