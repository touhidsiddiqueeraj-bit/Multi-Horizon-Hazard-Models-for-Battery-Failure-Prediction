import os
import numpy as np
import scipy.io as sio
import pandas as pd

DATA_PATH = "../data/nasa"

def _get_battery_struct(mat):
    for k, v in mat.items():
        if k.startswith("__"):
            continue
        if hasattr(v, "cycle"):
            return v
    raise KeyError("Could not find battery struct with .cycle in this MAT file.")

def _to_str(x):
    if x is None:
        return ""
    if isinstance(x, bytes):
        return x.decode(errors="ignore")
    return str(x)

def _to_float_array(x):
    a = np.asarray(x)
    # Handle weird empty/missing cases safely
    if a.size == 0:
        return np.array([], dtype=float)
    return a.astype(float).squeeze()

def _capacity_scalar(cap):
    """
    Capacity can be:
    - scalar
    - vector (take last)
    - empty (return None)
    """
    cap_arr = _to_float_array(cap)
    if cap_arr.size == 0:
        return None
    if cap_arr.ndim == 0:
        val = float(cap_arr)
    else:
        val = float(cap_arr[-1])
    if not np.isfinite(val) or val <= 0:
        return None
    return val

def extract_cycles(mat_file):
    mat = sio.loadmat(mat_file, squeeze_me=True, struct_as_record=False)
    battery = _get_battery_struct(mat)

    records = []
    cyc_idx = 0

    for cyc in np.atleast_1d(battery.cycle):
        cyc_idx += 1

        ctype = _to_str(getattr(cyc, "type", None)).lower()
        if ctype != "discharge":
            continue

        data = getattr(cyc, "data", None)
        if data is None:
            continue

        cap = getattr(data, "Capacity", None)
        v = getattr(data, "Voltage_measured", None)
        i = getattr(data, "Current_measured", None)
        t = getattr(data, "Temperature_measured", None)
        tm = getattr(data, "Time", None)

        if cap is None or v is None or i is None or t is None or tm is None:
            continue

        cap_val = _capacity_scalar(cap)
        if cap_val is None:
            # skip this cycle if capacity is empty/invalid
            continue

        v = _to_float_array(v)
        i = _to_float_array(i)
        t = _to_float_array(t)
        tm = _to_float_array(tm)

        # skip if arrays are empty (corrupt cycle)
        if v.size == 0 or i.size == 0 or t.size == 0 or tm.size == 0:
            continue

        duration = np.nan
        if tm.size > 1:
            duration = float(tm[-1] - tm[0])

        records.append({
            "cycle": int(cyc_idx),
            "capacity": cap_val,
            "avg_voltage": float(np.nanmean(v)),
            "min_voltage": float(np.nanmin(v)),
            "avg_current": float(np.nanmean(i)),
            "avg_temp": float(np.nanmean(t)),
            "duration": duration
        })

    return pd.DataFrame(records)

def load_all():
    all_cells = []

    for root, _, files in os.walk(DATA_PATH):
        for f in files:
            if not f.lower().endswith(".mat"):
                continue

            path = os.path.join(root, f)
            df = extract_cycles(path)

            if df.empty or len(df) < 10:
                print(f"Skipped (too few valid discharge cycles): {path}")
                continue

            # Compute SOH using mean of first 10 discharge cycles (or fewer if <10)
            n_init = min(10, len(df))
            initial_cap = df["capacity"].iloc[:n_init].mean()
            if not np.isfinite(initial_cap) or initial_cap <= 0:
                print(f"Skipped (bad initial capacity): {path}")
                continue

            df["SOH"] = df["capacity"] / initial_cap

            # RUL to EOL (SOH <= 0.8); if no EOL, remaining to end
            eol_idx = df.index[df["SOH"] <= 0.8]
            if len(eol_idx) > 0:
                eol_cycle = int(df.loc[eol_idx[0], "cycle"])
                df["RUL"] = eol_cycle - df["cycle"]
            else:
                df["RUL"] = df["cycle"].max() - df["cycle"]

            # ✅ Unique cell naming: include folder name to avoid duplicates
            folder = os.path.basename(root)
            cellname = os.path.splitext(f)[0]
            df["cell"] = f"{folder}_{cellname}"

            # Traceability (helps debugging)
            df["source_folder"] = folder
            df["source_file"] = f
            df["source_path"] = path

            all_cells.append(df)

    if not all_cells:
        raise RuntimeError("No valid cells loaded. Check DATA_PATH and MAT file structure.")

    return pd.concat(all_cells, ignore_index=True)

if __name__ == "__main__":
    df = load_all()
    # Output filename matches what downstream pipeline reads
    # (benchmark_cv.py, export_esp32_models.py, generate_reference.py, full_validate.py).
    # The "_filtered" suffix reflects the cell-level filtering applied in load_all()
    # (cells with < 50 cycles or invalid SOH trajectories are dropped).
    out_csv = "../data/nasa_clean_filtered.csv"
    df.to_csv(out_csv, index=False)
    print(f"Saved {out_csv} with {len(df)} rows")
