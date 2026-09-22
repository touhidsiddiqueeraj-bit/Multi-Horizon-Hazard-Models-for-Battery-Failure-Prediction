"""Battery Archive chemistry extension: fragments + numbers for the papers.

Called from make_tables_v2.main() so every new number lands in the same
results_v2/paper_numbers.json and results_v2/tex_fragments/ as the rest of the
study. Reads (all optional -- missing files simply skip their table):

  results_v2/within_trees_ba.csv        src/benchmark_cv.py within_ba
  results_v2/transfer_ba.csv            src/benchmark_cv.py transfer_ba
  results_v2/soh_ablation_tests_ba.csv  src/benchmark_cv.py ablation_tests_ba
  results_v2/condition_shift.csv        src/condition_shift.py
  data/ba_audit.csv, data/ba_clean.csv  src/loader_batteryarchive.py
"""
import os

import numpy as np
import pandas as pd

_HERE = os.path.dirname(os.path.abspath(__file__))
_RES = os.path.join(_HERE, "..", "results_v2")
_DATA = os.path.join(_HERE, "..", "data")
_FRAG = os.path.join(_RES, "tex_fragments")

TREE_ORDER = ["xgboost", "lightgbm", "random_forest"]
MODEL_LABEL = {"xgboost": "XGBoost", "lightgbm": "LightGBM", "random_forest": "Random Forest"}
H_LIST = [10, 20, 30, 50]
BA_GROUPS = ["ba_nmc_hnei", "ba_nca_snl", "ba_nmc_snl", "ba_lfp_snl"]
GROUP_LABEL = {
    "ba_nmc_hnei": "HNEI NMC",
    "ba_nca_snl": "SNL NCA",
    "ba_nmc_snl": "SNL NMC",
    "ba_lfp_snl": "SNL LFP",
}
SOURCE_LABEL = {"nasa": "NASA", "calce": "CALCE", "nasa+calce": "ALL LCO",
                "ba_lfp_snl": "SNL LFP", "ba_nca_snl": "SNL NCA",
                "ba_nmc_hnei": "HNEI NMC", "nmc_all": "ALL NMC", "ba_all": "Battery Arch."}
PAIR_LABEL = {
    ("ba_lfp_snl", "severson"): "SNL$\\to$Severson (LFP$\\to$LFP)",
    ("severson", "ba_lfp_snl"): "Severson$\\to$SNL (LFP$\\to$LFP)",
    ("ba_lfp_snl", "oxford"): "SNL$\\to$Oxford (LFP$\\to$LFP)",
    ("oxford", "ba_lfp_snl"): "Oxford$\\to$SNL (LFP$\\to$LFP)",
    ("ba_nmc_hnei", "ba_nmc_snl"): "HNEI$\\to$SNL (NMC$\\to$NMC)",
    ("ba_nmc_snl", "ba_nmc_hnei"): "SNL$\\to$HNEI (NMC$\\to$NMC)",
    ("ba_nca_snl", "ba_nmc_snl"): "SNL NCA$\\to$SNL NMC (same lab)",
    ("ba_nmc_snl", "ba_nca_snl"): "SNL NMC$\\to$SNL NCA (same lab)",
}


def f(x, nd=3):
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "---"
    return f"{x:.{nd}f}"


def ci(lo, hi, nd=3):
    if lo is None or hi is None or not (np.isfinite(lo) and np.isfinite(hi)):
        return ""
    return f"[{lo:.{nd}f},{hi:.{nd}f}]"


def save_fragment(name, text):
    os.makedirs(_FRAG, exist_ok=True)
    with open(os.path.join(_FRAG, name), "w") as fh:
        fh.write(text)


def _read(path):
    return pd.read_csv(path) if os.path.exists(path) else pd.DataFrame()


# ------------------------------------------------------------------ within
def within_ba_table():
    """Within-dataset reliability on the four new groups (Platt, fold-mean)."""
    d = _read(os.path.join(_RES, "within_trees_ba.csv"))
    js = {}
    if len(d) == 0:
        return js
    rows_tex = []
    n_ge, n_tot = 0, 0
    for model in TREE_ORDER:
        for grp in BA_GROUPS:
            sub = d[(d.model == model) & (d.dataset == grp) & (d.method == "platt")]
            cells = [MODEL_LABEL[model], GROUP_LABEL[grp]]
            vals = []
            for H in H_LIST:
                v = sub[sub.H == H]["AUC_fold_mean"]
                if len(v):
                    vals.append(float(v.iloc[0]))
                    cells.append(f"{float(v.iloc[0]):.3f}")
                    n_tot += 1
                    n_ge += int(float(v.iloc[0]) >= 0.85)
                    js[f"within_ba_{grp}_{model}_H{H}"] = float(v.iloc[0])
                else:
                    cells.append("---")
            if vals:
                js[f"within_ba_{grp}_{model}_min"] = float(min(vals))
            mean = float(np.mean(vals)) if vals else np.nan
            brier = float(sub["Brier"].mean()) if len(sub) else np.nan
            cells += [f"{mean:.3f}" if np.isfinite(mean) else "---",
                      f"{brier:.3f}" if np.isfinite(brier) else "---"]
            if np.isfinite(mean):
                js[f"within_ba_{grp}_{model}"] = {"mean_AUC": mean, "brier": brier}
            rows_tex.append(" & ".join(cells) + r" \\")
    save_fragment("tab_within_ba.tex", "\n".join(rows_tex) + "\n")
    js["within_ba_ge085"] = n_ge
    js["within_ba_total"] = n_tot
    return js


# ------------------------------------------------------------------ transfer
def crosschem_ba_table():
    """LCO -> {new chemistries} at H=20, with and without SOH."""
    d = _read(os.path.join(_RES, "transfer_ba.csv"))
    ab = _read(os.path.join(_RES, "soh_ablation_tests_ba.csv"))
    js = {}
    if len(d) == 0:
        return js
    rows_tex = []
    source = "nasa+calce"
    for grp in BA_GROUPS:
        for model in TREE_ORDER:
            cells = [GROUP_LABEL[grp], MODEL_LABEL[model]]
            for fs in ["with_soh", "no_soh"]:
                r = d[(d.source == source) & (d.target == grp) & (d.model == model) &
                      (d.feature_set == fs) & (d.H == 20)]
                if len(r) == 0:
                    cells.append("---")
                    continue
                r = r.iloc[0]
                cells.append(f"{r['raw_AUC']:.3f} {ci(r['raw_AUC_lo'], r['raw_AUC_hi'])}")
                js[f"xfer_ba_{grp}_{source}_{model}_{fs}"] = {
                    "pooled": float(r["raw_AUC"]),
                    "ci": [float(r["raw_AUC_lo"]), float(r["raw_AUC_hi"])],
                    "percell": [float(r["raw_AUC_percell_mean"]),
                                float(r["raw_AUC_percell_std"])]}
            t = ab[(ab.source == source) & (ab.target == grp) & (ab.model == model) &
                   (ab.H == 20)] if len(ab) else pd.DataFrame()
            if len(t):
                t = t.iloc[0]
                cells.append(f"{t['delta_bootstrap']:+.3f} "
                             f"{ci(t['delta_lo'], t['delta_hi'])}")
                js[f"xfer_ba_delta_{grp}_{model}"] = {
                    "delta": float(t["delta_bootstrap"]),
                    "ci": [float(t["delta_lo"]), float(t["delta_hi"])],
                    "auc_with": float(t["auc_with"]),
                    "auc_without": float(t["auc_without"])}
            else:
                cells.append("---")
            rows_tex.append(" & ".join(cells) + r" \\")
    save_fragment("tab_crosschem_new.tex", "\n".join(rows_tex) + "\n")
    return js


def samechem_ba_table():
    """Same-chemistry / same-laboratory controls built on the new datasets."""
    d = _read(os.path.join(_RES, "transfer_ba.csv"))
    js = {}
    if len(d) == 0:
        return js
    rows_tex = []
    for (src, tgt), label in PAIR_LABEL.items():
        cells = [label]
        for fs in ["with_soh", "no_soh", "common_no_soh"]:
            r = d[(d.source == src) & (d.target == tgt) & (d.feature_set == fs) &
                  (d.H == 20)]
            if len(r) == 0:
                cells.append("---")
                continue
            r = r.iloc[0]
            cells.append(f"{r['raw_AUC']:.3f} {ci(r['raw_AUC_lo'], r['raw_AUC_hi'])}")
            js[f"samechem_ba_{src}_{tgt}_{fs}"] = float(r["raw_AUC"])
        rows_tex.append(" & ".join(cells) + r" \\")
    save_fragment("tab_samechem_ba.tex", "\n".join(rows_tex) + "\n")
    return js


def condshift_table():
    """Leave-one-condition-out vs ordinary mixed-cell folds, at H=20.

    The mixed-fold raw reference is only meaningful where pooled raw scores
    separate cells at all; on the 6-cell NMC group it is not (near-chance raw
    ties), so the reference column is shown as --- there and reference-based
    drops are computed only for the well-behaved groups (NCA, LFP).
    """
    d = _read(os.path.join(_RES, "condition_shift.csv"))
    js = {}
    if len(d) == 0:
        return js
    axis_label = {"temp_rate": "temp $\\times$ rate", "temp": "temperature",
                  "rate": "C-rate"}
    rows_tex = []
    drops = {"with_soh": [], "no_soh": []}
    pooled = d[d.setting == "leave_condition_out_pooled"]
    for grp in ["ba_nca_snl", "ba_nmc_snl", "ba_lfp_snl"]:
        for mode in ["temp_rate", "temp", "rate"]:
            cells = [GROUP_LABEL[grp], axis_label[mode]]
            for fs in ["with_soh", "no_soh"]:
                r = pooled[(pooled.dataset == grp) & (pooled["mode"] == mode) &
                           (pooled.feature_set == fs) & (pooled.H == 20)]
                ref = d[(d.dataset == grp) & (d.setting == "within_cells_grouped") &
                        (d.feature_set == fs) & (d.H == 20) &
                        (d.model == "xgboost")]
                if len(r) == 0:
                    cells += ["---", "---"]
                    continue
                r = r.iloc[0]
                cells.append(f"{r['AUC_raw']:.3f} "
                             f"{ci(r['AUC_raw_lo'], r['AUC_raw_hi'])}")
                js[f"condshift_{grp}_{mode}_{fs}"] = float(r["AUC_raw"])
                js[f"condshift_{grp}_{mode}_{fs}_dist_rule"] = float(r["AUC_dist_rule"])
                if len(ref):
                    ref = ref.iloc[0]
                    if float(ref["AUC_raw"]) >= 0.8:
                        cells.append(f"{float(ref['AUC_raw']):.3f}")
                        drops[fs].append(float(ref["AUC_raw"]) - float(r["AUC_raw"]))
                        js[f"condshift_ref_{grp}_{fs}"] = float(ref["AUC_raw"])
                    else:
                        cells.append("---")
                        js[f"condshift_ref_{grp}_{fs}"] = float(ref["AUC_raw"])
                        js["condshift_ref_uninterpretable"] = js.get(
                            "condshift_ref_uninterpretable", 0) + 1
                else:
                    cells.append("---")
            rows_tex.append(" & ".join(cells) + r" \\")
    save_fragment("tab_condshift.tex", "\n".join(rows_tex) + "\n")
    dist = pooled[pooled.H == 20]["AUC_dist_rule"]
    if len(dist):
        js["condshift_dist_min"] = float(dist.min())
        js["condshift_dist_max"] = float(dist.max())
    if drops["with_soh"]:
        js["condshift_drop_with_max"] = float(np.max(drops["with_soh"]))
    if drops["no_soh"]:
        js["condshift_drop_no_max"] = float(np.max(drops["no_soh"]))
        js["condshift_drop_no_min"] = float(np.min(drops["no_soh"]))
    return js


def audit_numbers():
    """Dataset-inventory numbers for the datasets table and its paragraph."""
    js = {}
    clean = _read(os.path.join(_DATA, "ba_clean.csv"))
    audit = _read(os.path.join(_DATA, "ba_audit.csv"))
    if len(audit) == 0:
        return js
    js["ba_cells_total"] = int(audit["admitted"].sum())
    js["ba_cells_excluded"] = int((~audit["admitted"]).sum())
    js["ba_rows_total"] = int(clean.shape[0])
    js["ba_volt_first"] = 0
    for grp in BA_GROUPS:
        ok = audit[(audit.dataset == grp) & audit.admitted]
        js[f"ba_cells_{grp}"] = int(len(ok))
        js[f"ba_rows_{grp}"] = int(ok["n_kept"].sum())
        js[f"ba_cycles_min_{grp}"] = int(ok["n_kept"].min())
        js[f"ba_cycles_max_{grp}"] = int(ok["n_kept"].max())
        js[f"ba_eol_cells_{grp}"] = int(np.isfinite(ok["eol_cycle"]).sum())
    # count cells whose SOH endpoint fires strictly before the voltage endpoint
    import sys
    if _HERE not in sys.path:
        sys.path.insert(0, _HERE)
    from composite_label import make_composite_fail_in_H  # noqa: E402
    ok_all = audit[audit.admitted]
    js["ba_volt_first"] = int(
        (ok_all["t_fail_volt"] < ok_all["t_fail_soh"]).sum())
    for grp in BA_GROUPS:
        sub = clean[clean.dataset == grp]
        if len(sub):
            js[f"ba_prev_{grp}_H20"] = float(make_composite_fail_in_H(sub, 20).mean())
    return js
