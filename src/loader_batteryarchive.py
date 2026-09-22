"""Battery Archive cycle-test export loader (batteryarchive.org).

Source: the "Cycle Test Data" dashboard export stored in
batteryarchive_cycle_test_data_CSVs/ -- 75 cells (HNEI 18650 NMC/LCO,
SNL 18650 LFP / NCA / NMC), retrieved 2026-09-21 and verified against both the
rendered dashboard charts and the raw API (see the accompanying
VERIFICATION_REPORT.txt: 0 mismatches in 673 131 rows).

Per cycle the export carries charge/discharge capacity and energy, coulombic
and energy efficiency, and max / min / mean charge / mean discharge voltage.
It carries NO per-cycle current and NO temperature, so `avg_current` and
`avg_temp` are written empty and zero-imputed downstream, exactly as the CALCE
loader already does (documented in the paper's feature section). Per-cycle
duration is differenced from `test_time_s`.

Cleaning rules (pre-registered in study_materials/batteryarchive_protocol.md):
  1. admit only constant-protocol 0-100 % SOC cells; the 20-80 / 40-60 SOC
     window cells mix protocols, so their capacity is not comparable;
  2. drop leading formation cycles with coulombic efficiency far from 1
     (HNEI cycle 1 is a partial discharge with CE ~ 0.35, which otherwise
     makes every HNEI cell "fail" at cycle 1);
  3. Hampel despike on discharge capacity (11-cycle window, k=6 MAD, floored
     at 5 % of the local median) to remove check-up / RPT spikes;
  4. keep the prefix before the first *sustained* rise of the smoothed SOH,
     which is where several cells' late-life capacity doubles or triples;
  5. drop rows with non-physical voltage (min <= 0.5 V or min > max).
SOH and RUL then follow the paper's existing convention (Eq. 1): SOH is the
discharge capacity divided by the mean capacity of the first ten retained
cycles, RUL is the distance to the first cycle with SOH <= 0.80 (or to the end
of the trajectory when the cell is right-censored).

CLI:  python3 loader_batteryarchive.py
      -> data/ba_clean.csv   (admitted cells, pipeline-ready columns)
      -> data/ba_audit.csv   (all 75 cells: kept/dropped, reason, EOL, SOH)
"""
import os
import re
import sys

import numpy as np
import pandas as pd

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from composite_label import composite_fail_cycle, make_composite_fail_in_H  # noqa: E402

SRC_DIR = os.path.join(_HERE, "..", "batteryarchive_cycle_test_data_CSVs")
OUT_CLEAN = os.path.join(_HERE, "..", "data", "ba_clean.csv")
OUT_AUDIT = os.path.join(_HERE, "..", "data", "ba_audit.csv")

CAP_CSV = "01_energy_and_capacity_decay.csv"
EFF_CSV = "02_efficiencies.csv"
VOL_CSV = "03_max_min_mean_voltage_by_cycle.csv"

ADMITTED_WINDOW = "0-100"
CE_TOL = 0.25          # |CE - 1| above this = partial / formation cycle
CE_MAX_DROP = 10       # only the leading cycles are tested for the CE rule
HAMPEL_WIN = 11
HAMPEL_K = 6.0
HAMPEL_REL_FLOOR = 0.05
LEVEL_FRAC = 0.10      # sustained rise of smoothed SOH above its minimum
LEVEL_HOLD = 0.05      # ... without ever returning below min + LEVEL_HOLD
MIN_CYCLES = 20
VOLT_FLOOR = 0.5       # non-physical low-voltage guard

# (laboratory, chemistry) -> dataset key used by pipeline_core.DATASETS
GROUPS = {
    ("HNEI", "NMC_LCO"): "ba_nmc_hnei",
    ("SNL", "NCA"): "ba_nca_snl",
    ("SNL", "NMC"): "ba_nmc_snl",
    ("SNL", "LFP"): "ba_lfp_snl",
}
CHEM_LABEL = {"NMC_LCO": "NMC", "NMC": "NMC", "NCA": "NCA", "LFP": "LFP"}


def cell_meta(cell):
    """Parse laboratory, chemistry, chamber temperature, SOC window, rate."""
    lab = cell.split("_")[0]
    m = re.search(r"_(LFP|NCA|NMC_LCO|NMC)_", cell)
    chem = m.group(1) if m else "NMC_LCO"
    t = re.search(r"_(\d+)C_", cell)
    w = re.search(r"_\d+C_([0-9\-]+)_", cell)
    r = re.search(r"_([0-9.]+/[0-9.]+)C_", cell)
    return {
        "lab": lab,
        "chem": chem,
        "chem_label": CHEM_LABEL[chem],
        "temp_C": float(t.group(1)) if t else np.nan,
        "window": w.group(1) if w else "",
        "rate": r.group(1) if r else "",
    }


def load_raw(src_dir=SRC_DIR):
    """Merge the capacity, voltage and efficiency exports into one frame."""
    cap = pd.read_csv(os.path.join(src_dir, CAP_CSV))
    eff = pd.read_csv(os.path.join(src_dir, EFF_CSV))
    vol = pd.read_csv(os.path.join(src_dir, VOL_CSV))
    df = cap.merge(
        vol[["cell_id", "cycle_index", "voltage_max_V", "voltage_min_V",
             "charge_voltage_mean_V", "discharge_voltage_mean_V"]],
        on=["cell_id", "cycle_index"], how="left")
    df = df.merge(eff, on=["cell_id", "cycle_index"], how="left")
    df = df.rename(columns={"cell_id": "cell", "cycle_index": "cycle"})
    meta = pd.DataFrame([dict(cell=c, **cell_meta(c)) for c in df["cell"].unique()])
    return df.merge(meta, on="cell", how="left").sort_values(
        ["cell", "cycle"]).reset_index(drop=True)


def _hampel_mask(q):
    """Boolean mask of capacity points consistent with a local median (11-cycle)."""
    s = pd.Series(np.asarray(q, dtype=float))
    med = s.rolling(HAMPEL_WIN, center=True, min_periods=3).median().to_numpy(dtype=float)
    mad = s.sub(s.rolling(HAMPEL_WIN, center=True, min_periods=3).median()).abs() \
        .rolling(HAMPEL_WIN, center=True, min_periods=3).median().to_numpy(dtype=float)
    tol = np.maximum(HAMPEL_K * 1.4826 * mad, HAMPEL_REL_FLOOR * np.abs(med))
    with np.errstate(invalid="ignore"):
        keep = np.abs(np.asarray(q, dtype=float) - med) <= tol
    return keep & np.isfinite(q)


def _drop_formation(g):
    """Drop leading partial/formation cycles (coulombic efficiency far from 1)."""
    ce = g["coulombic_efficiency"].to_numpy(dtype=float)
    limit = max(0, min(CE_MAX_DROP, len(g) - MIN_CYCLES))
    i = 0
    while i < limit:
        if np.isfinite(ce[i]) and abs(ce[i] - 1.0) <= CE_TOL:
            break
        i += 1
    return g.iloc[i:].reset_index(drop=True), i


def _prefix_before_level_shift(g):
    """Length of the prefix preceding a sustained rise of the smoothed SOH.

    Several cells' late-life capacity doubles or triples relative to their own
    early cycles (check-up / RPT contamination or unit artefacts). Those tails
    are not degradation data, so the trajectory is cut where the smoothed SOH
    leaves the degrading regime for good.
    """
    q = g["discharge_capacity_Ah"].to_numpy(dtype=float)
    base = float(np.mean(q[:min(10, len(q))]))
    soh = q / base
    sm = pd.Series(soh).rolling(21, center=True, min_periods=5) \
        .median().to_numpy(dtype=float)
    mn = float(np.nanmin(sm))
    start = max(10, int(0.25 * len(q)))
    for k in range(start, len(q)):
        tail = sm[k:][np.isfinite(sm[k:])]
        if tail.size and tail.min() > mn + LEVEL_HOLD and tail.max() > mn + LEVEL_FRAC:
            return k
    return len(q)


def clean_cell(g):
    """Apply the pre-registered cleaning rules to one raw cell trajectory.

    Returns (cleaned frame, reason, n_raw), where `reason` is None on success.
    """
    g = g.sort_values("cycle").reset_index(drop=True)
    n_raw = len(g)
    if n_raw < MIN_CYCLES:
        return None, "too_short_raw", n_raw
    g, _ = _drop_formation(g)
    if len(g) < MIN_CYCLES:
        return None, "too_short_after_formation_drop", n_raw
    g = g[_hampel_mask(g["discharge_capacity_Ah"].to_numpy(dtype=float))] \
        .reset_index(drop=True)
    vmin = g["voltage_min_V"].to_numpy(dtype=float)
    vmax = g["voltage_max_V"].to_numpy(dtype=float)
    g = g[np.isfinite(vmin) & (vmin > VOLT_FLOOR) & (vmin <= vmax)].reset_index(drop=True)
    if len(g) < MIN_CYCLES:
        return None, "too_short_after_despike", n_raw
    g = g.iloc[:_prefix_before_level_shift(g)].reset_index(drop=True)
    if len(g) < MIN_CYCLES:
        return None, "too_short_after_level_shift_cut", n_raw
    return g, None, n_raw


def build_cell_features(g, cell, meta):
    """Emit the pipeline column contract for one cleaned cell trajectory."""
    q = g["discharge_capacity_Ah"].to_numpy(dtype=float)
    base10 = float(np.mean(q[:min(10, len(q))]))
    soh = q / base10
    cyc = g["cycle"].to_numpy(dtype=float)
    eol = cyc[soh <= 0.8]
    rul = np.clip(eol.min() - cyc, 0, None) if eol.size else (cyc.max() - cyc)

    vd = g["discharge_voltage_mean_V"].to_numpy(dtype=float)
    vc = g["charge_voltage_mean_V"].to_numpy(dtype=float)
    vmid = 0.5 * (g["voltage_max_V"].to_numpy(dtype=float)
                  + g["voltage_min_V"].to_numpy(dtype=float))
    avg_v = np.where(np.isfinite(vd), vd, np.where(np.isfinite(vc), vc, vmid))

    dur = g["test_time_s"].diff().to_numpy(dtype=float)
    dur[~np.isfinite(dur) | (dur <= 0)] = np.nan

    out = pd.DataFrame({
        "cycle": cyc,
        "capacity": q,
        "avg_voltage": avg_v,
        "min_voltage": g["voltage_min_V"].to_numpy(dtype=float),
        "avg_current": np.nan,       # not exported by the source dashboard
        "avg_temp": np.nan,          # not exported by the source dashboard
        "duration": dur,
        "SOH": soh,
        "RUL": rul,
        "cell": cell,
    })
    for k, v in meta.items():
        out[k] = v
    out["dataset"] = GROUPS.get((meta["lab"], meta["chem"]), "ba_excluded")
    return out


def build(src_dir=SRC_DIR, verbose=True):
    """Clean every cell; return (admitted feature frame, audit frame)."""
    raw = load_raw(src_dir)
    clean_parts, audit_rows = [], []
    for cell, g in raw.groupby("cell", sort=True):
        meta = cell_meta(cell)
        expected = GROUPS.get((meta["lab"], meta["chem"]), "ba_excluded")
        window_ok = meta["window"] == ADMITTED_WINDOW
        gc, reason, n_raw = clean_cell(g) if window_ok else (None, "soc_window_mixed", len(g))
        row = dict(cell=cell, lab=meta["lab"], chem_label=meta["chem_label"],
                   window=meta["window"], temp_C=meta["temp_C"], rate=meta["rate"],
                   dataset=expected, admitted=False, reason=reason,
                   n_raw=n_raw, n_kept=0, base10=np.nan, base_med20=np.nan,
                   eol_cycle=np.nan, t_fail_soh=np.nan, t_fail_volt=np.nan,
                   soh_min=np.nan, soh_end=np.nan)
        if gc is not None:
            feats = build_cell_features(gc, cell, meta)
            q = feats["capacity"].to_numpy(dtype=float)
            row.update(admitted=True, reason="",
                       n_kept=len(feats),
                       base10=float(np.mean(q[:min(10, len(q))])),
                       base_med20=float(np.median(q[:min(20, len(q))])),
                       soh_min=float(feats["SOH"].min()),
                       soh_end=float(feats["SOH"].iloc[-1]))
            fail = composite_fail_cycle(feats, endpoint="combined")
            row["t_fail_soh"] = float(composite_fail_cycle(feats, endpoint="soh_only").min())
            row["t_fail_volt"] = float(composite_fail_cycle(feats, endpoint="volt_only").min())
            row["eol_cycle"] = float(fail.min())
            clean_parts.append(feats)
        audit_rows.append(row)
    clean = pd.concat(clean_parts, ignore_index=True) if clean_parts else pd.DataFrame()
    audit = pd.DataFrame(audit_rows).sort_values(["chem_label", "cell"]).reset_index(drop=True)
    if verbose:
        _report(clean, audit)
    return clean, audit


def _report(clean, audit):
    """Print the audit summary used in the paper's data-quality paragraph."""
    ok = audit[audit.admitted]
    print("\n=== admitted cells / usable rows ===")
    tbl = ok.groupby(["dataset", "chem_label"]).agg(
        cells=("cell", "size"), rows=("n_kept", "sum"),
        cycles_med=("n_kept", "median"), eol_cells=("eol_cycle", lambda s: np.isfinite(s).sum()),
        soh_min_med=("soh_min", "median"))
    print(tbl.to_string())
    print("\n=== exclusions ===")
    print(audit[~audit.admitted].groupby(["chem_label", "reason"]).size().to_string())
    print("\n=== label prevalence (combined endpoint) ===")
    for ds, sub in clean.groupby("dataset"):
        r = []
        for H in (10, 20, 30, 50):
            r.append(f"H={H}: {make_composite_fail_in_H(sub, H).mean():.3f}")
        print(f"  {ds:14s} rows={len(sub):6d} cells={sub['cell'].nunique():3d}  " + "  ".join(r))
    print("\n=== failure criterion that fires first (admitted cells) ===")
    soh_first = (ok.t_fail_soh <= ok.t_fail_volt) | ~np.isfinite(ok.t_fail_volt)
    n_fail = np.isfinite(ok.eol_cycle).sum()
    print(f"  cells that fail: {n_fail}/{len(ok)}; SOH criterion first: "
          f"{int(soh_first.sum())}; voltage-sag criterion first: "
          f"{int((~soh_first).sum())}")


def main():
    clean, audit = build()
    os.makedirs(os.path.dirname(OUT_CLEAN), exist_ok=True)
    clean.to_csv(OUT_CLEAN, index=False)
    audit.to_csv(OUT_AUDIT, index=False)
    print(f"\nwrote {OUT_CLEAN}: {len(clean)} rows, {clean['cell'].nunique()} cells")
    print(f"wrote {OUT_AUDIT}: {len(audit)} rows")


if __name__ == "__main__":
    main()
