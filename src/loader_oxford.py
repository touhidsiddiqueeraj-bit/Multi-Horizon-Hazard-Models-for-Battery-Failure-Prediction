import os
import numpy as np
import pandas as pd
import scipy.io as sio

DATA_PATH = "../data/oxford"

CELL_NAMES = ["Cell1", "Cell2", "Cell3", "Cell4", "Cell5"]


def extract_cell_cycles(mat_file):
    all_records = []

    for cell_name in CELL_NAMES:
        # Load one cell at a time — avoids deeply-nested struct read errors
        try:
            mat = sio.loadmat(
                mat_file, squeeze_me=True, struct_as_record=False,
                variable_names=[cell_name]
            )
            cell = mat[cell_name]
        except (KeyError, ValueError, TypeError, OSError) as e:
            print(f"  Skipped {cell_name}: {e}")
            continue

        if not hasattr(cell, "_fieldnames"):
            continue

        cyc_fields = sorted(
            [f for f in cell._fieldnames if f.startswith("cyc")],
            key=lambda x: int(x.replace("cyc", ""))
        )

        if len(cyc_fields) < 3:
            print(f"  Skipped {cell_name}: only {len(cyc_fields)} cycles")
            continue

        records = []
        for cyc_name in cyc_fields:
            cyc = getattr(cell, cyc_name)
            if not hasattr(cyc, "_fieldnames"):
                continue

            cyc_num = int(cyc_name.replace("cyc", ""))

            c1dc = getattr(cyc, "C1dc", None)
            if c1dc is None or not hasattr(c1dc, "_fieldnames"):
                continue

            v_arr = np.atleast_1d(getattr(c1dc, "v", np.array([]))).astype(float).squeeze()
            q_arr = np.atleast_1d(getattr(c1dc, "q", np.array([]))).astype(float).squeeze()
            t_arr = np.atleast_1d(getattr(c1dc, "T", np.array([]))).astype(float).squeeze()
            tm_arr = np.atleast_1d(getattr(c1dc, "t", np.array([]))).astype(float).squeeze()
            i_arr = np.atleast_1d(getattr(c1dc, "i", np.array([]))).astype(float).squeeze()

            if v_arr.size < 5 or q_arr.size < 5:
                continue

            if q_arr.ndim == 0:
                cap_val = float(abs(q_arr))
            else:
                cap_val = float(abs(q_arr[-1] - q_arr[0]))

            if not np.isfinite(cap_val) or cap_val <= 0:
                continue

            if i_arr.size < 5:
                i_arr = np.gradient(q_arr, tm_arr) if tm_arr.size > 1 else np.array([np.nan])

            duration = float(tm_arr[-1] - tm_arr[0]) if tm_arr.size > 1 else np.nan

            records.append({
                "cycle": cyc_num,
                "capacity": cap_val,
                "avg_voltage": float(np.nanmean(v_arr)),
                "min_voltage": float(np.nanmin(v_arr)),
                "avg_current": float(np.nanmean(i_arr)),
                "avg_temp": float(np.nanmean(t_arr)),
                "duration": duration
            })

        if not records:
            print(f"  Skipped {cell_name}: no valid discharge cycles")
            continue

        cell_df = pd.DataFrame(records).sort_values("cycle")

        n_init = min(10, len(cell_df))
        initial_cap = cell_df["capacity"].iloc[:n_init].mean()
        if not np.isfinite(initial_cap) or initial_cap <= 0:
            print(f"  Skipped {cell_name}: bad initial capacity")
            continue

        cell_df["SOH"] = cell_df["capacity"] / initial_cap

        eol_idx = cell_df.index[cell_df["SOH"] <= 0.8]
        if len(eol_idx) > 0:
            eol_cycle = int(cell_df.loc[eol_idx[0], "cycle"])
            cell_df["RUL"] = (eol_cycle - cell_df["cycle"]).clip(lower=0)
        else:
            cell_df["RUL"] = cell_df["cycle"].max() - cell_df["cycle"]

        cell_df["cell"] = f"oxford_{cell_name}"
        all_records.append(cell_df)
        print(f"  {cell_name}: {len(cell_df)} cycles, "
              f"capacity={initial_cap:.3f}Ah, "
              f"SOH range={cell_df['SOH'].min():.3f}-{cell_df['SOH'].max():.3f}")

    return pd.concat(all_records, ignore_index=True) if all_records else pd.DataFrame()


def load_all_oxford():
    for root, _, files in os.walk(DATA_PATH):
        for f in files:
            if not f.lower().endswith(".mat"):
                continue
            path = os.path.join(root, f)
            print(f"Loading: {path}")
            try:
                df = extract_cell_cycles(path)
            except Exception as e:
                print(f"  Error: {e}")
                continue
            if df.empty or len(df) < 10:
                print(f"  Skipped: insufficient data")
                continue
            out_csv = "../data/oxford_clean.csv"
            df.to_csv(out_csv, index=False)
            print(f"Saved: {out_csv} with {len(df)} rows, {df['cell'].nunique()} cells")
            return df

    raise RuntimeError("No Oxford .mat file found. Check DATA_PATH.")


if __name__ == "__main__":
    load_all_oxford()
