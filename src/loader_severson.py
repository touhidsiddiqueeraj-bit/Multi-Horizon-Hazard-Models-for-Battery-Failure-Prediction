import os
import h5py
import numpy as np
import pandas as pd

DATA_PATH = "../data/severson"
OUTPUT_CSV = "../data/severson_clean.csv"

# From https://data.matr.io/1/projects/5c48dd2bc625d700019f7e4f
# Severson et al. Nature Energy 2019 — 124 LFP cells under fast-charging conditions


def process_batch(batch_name):
    """Load a single .mat file (one cell per HDF5 group)."""
    mat_path = os.path.join(DATA_PATH, batch_name)
    print(f"Loading {mat_path}...")

    f = h5py.File(mat_path, "r")
    # Batch cycles are stored as group attributes
    batch_data = f["batch"]
    num_cells = batch_data.attrs["num_cells"].item()
    batch_label = batch_name.split(".")[0].split("batch")[-1]

    cell_cycle_lives = batch_data.attrs["cycle_lives"]

    all_records = []

    for i in range(num_cells):
        cell_group = batch_data[f"cycle_life_{i+1}"]
        cell_keys = [k for k in cell_group.keys() if k.startswith("cycle_")]

        # cell_keys are string keys inside HDF5 group
        # We need to match cycles in sorted order
        if not cell_keys:
            print(f"  Skipped cell {i} (b{batch_label}_c{i}): no data groups")
            continue

        cell_records = []
        for cyc_key in sorted(cell_keys, key=lambda x: int(x.split("_")[1])):
            cyc_data = cell_group[cyc_key]
            cyc_num = cyc_data.attrs["cycle"].item()
            if "QDischarge" in cyc_data.keys():
                Qd = cyc_data["QDischarge"][()].item()  # capacity in Ah
            else:
                continue  # no discharge capacity

            feat = {}
            for col in ["I", "T", "t", "V", "QCharge", "QDischarge"]:
                if col in cyc_data.keys():
                    data_ref = cyc_data[col][()]
                    if hasattr(data_ref, "shape") and len(data_ref.shape) > 0:
                        arr = f[data_ref][:]
                    else:
                        arr = np.array([data_ref])
                    arr = np.squeeze(arr)
                    # Take mean for scalar features — other loaders do this too
                    feat[col.lower()] = float(np.mean(arr))
                else:
                    feat[col.lower()] = np.nan

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
        eol_idx = cell_df.index[cell_df["SOH"] <= 0.8]
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


if __name__ == "__main__":
    # batch1.mat (124 cells) and batch2.mat (43 cells) from Severson dataset
    for batch in ["batch1.mat", "batch2.mat"]:
        if not os.path.exists(os.path.join(DATA_PATH, batch)):
            print(f"Skipping {batch} — not found")
            continue
        df = process_batch(batch)
        if len(df) > 0:
            df.to_csv(OUTPUT_CSV, index=False)
            print(f"Saved {len(df)} rows to {OUTPUT_CSV}")
        else:
            print(f"No data for {batch}")
