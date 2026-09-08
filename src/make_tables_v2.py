"""Build every paper number from results_v2 (+ legacy recalibration CSV).

Writes:
  results_v2/paper_numbers.json   -- all headline numbers for the text
  results_v2/tex_fragments/*.tex  -- ready-to-paste tabular bodies
Run after all experiment scripts finish.
"""
import json
import os
import numpy as np
import pandas as pd

_HERE = os.path.dirname(os.path.abspath(__file__))
_RES = os.path.join(_HERE, "..", "results_v2")
_FRAG = os.path.join(_RES, "tex_fragments")
_RECAL = os.path.join(_HERE, "..", "results", "recalibration", "recalibration_reduced.csv")

TREE_ORDER = ["xgboost", "lightgbm", "random_forest"]
MODEL_LABEL = {"xgboost": "XGBoost", "lightgbm": "LightGBM", "random_forest": "Random Forest",
               "gru": "GRU", "hazard_xgb": "Hazard XGBoost", "hazard_logistic": "Hazard Logistic"}
TARGET_LABEL = {"oxford": "Oxford", "severson": "Severson"}
SOURCE_LABEL = {"nasa": "NASA", "calce": "CALCE", "nasa+calce": "ALL LCO"}
FEATSET_LABEL = {"with_soh": "with SOH", "no_soh": "no SOH",
                 "common_with_soh": "common w/ SOH", "common_no_soh": "common no SOH",
                 "full": "full", "no_cycle": "$-$cycle", "no_soh_no_cycle": "$-$SOH$-$cycle",
                 "soh_only": "SOH only", "cycle_only": "cycle only", "sensors_only": "sensors"}
NUM = json.load(open(os.path.join(_RES, "paper_numbers.json"))) if os.path.exists(
    os.path.join(_RES, "paper_numbers.json")) else {}


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
    print(f"wrote tex_fragments/{name}")


# ------------------------------------------------------------------ within
def _read_csv(path):
    return pd.read_csv(path) if os.path.exists(path) else pd.DataFrame()


def within_table():
    trees = _read_csv(os.path.join(_RES, "within_trees.csv"))
    gru = _read_csv(os.path.join(_RES, "gru_within.csv"))
    haz = _read_csv(os.path.join(_RES, "hazard_within.csv"))
    rows_tex = []
    js = {}
    for ds in ["nasa", "calce"]:
        for model in TREE_ORDER + ["gru", "hazard_xgb", "hazard_logistic"]:
            src = None
            if model in TREE_ORDER and len(trees):
                src = trees[(trees.dataset == ds) & (trees.model == model) & (trees.method == "platt")]
            elif model == "gru" and len(gru):
                src = gru[(gru.dataset == ds) & (gru.method == "platt")]
            elif len(haz):
                src = haz[(haz.dataset == ds) & (haz.model == model)]
            if src is None or len(src) == 0:
                continue
            src = src.sort_values("H")
            cells = [MODEL_LABEL[model], "NASA" if ds == "nasa" else "CALCE"]
            aucs = []
            for H in [10, 20, 30, 50]:
                r = src[src.H == H]
                if len(r) == 0:
                    cells.append("---")
                    continue
                m = r["AUC_fold_mean"].iloc[0] if "AUC_fold_mean" in r else r["AUC"].iloc[0]
                s = r["AUC_fold_std"].iloc[0] if "AUC_fold_std" in r and np.isfinite(r["AUC_fold_std"].iloc[0]) else None
                aucs.append(m)
                cells.append(f"{m:.3f}" + (f"$\\pm${s:.3f}" if s is not None else ""))
            mean_auc = np.mean(aucs) if aucs else np.nan
            cells.append(f"{mean_auc:.3f}" if np.isfinite(mean_auc) else "---")
            b = src["Brier"].mean() if "Brier" in src else np.nan
            cells.append(f"{b:.3f}" if np.isfinite(b) else "---")
            rows_tex.append(" & ".join(cells) + r" \\")
            js[f"within_{ds}_{model}"] = {"per_H": {int(r.H): float(r["AUC_fold_mean"]) for _, r in src.iterrows()} if "AUC_fold_mean" in src else {},
                                          "mean_AUC": float(mean_auc) if np.isfinite(mean_auc) else None}
    save_fragment("tab_within.tex", "\n".join(rows_tex) + "\n")
    return js


# ------------------------------------------------------------- calibration
def calibration_table():
    trees = pd.read_csv(os.path.join(_RES, "within_trees.csv"))
    trees = trees[trees.model.isin(TREE_ORDER)]
    rows_tex, js = [], {}
    for ds in ["nasa", "calce"]:
        sub = trees[trees.dataset == ds]
        for method, label in [("iso", "Isotonic"), ("platt", "Platt"), ("temp", "Temperature")]:
            m = sub[sub.method == method]
            r = {
                "AUC_fold_mean": float(m["AUC_fold_mean"].mean()) if m["AUC_fold_mean"].notna().any() else float(m["AUC"].mean()),
                "Brier": float(m["Brier"].mean()),
                "ECE": float(m["ECE10"].mean()),
                "LogLoss": float(m["LogLoss"].mean()),
                "Slope": float(m["CalSlope"].mean()),
                "Intercept": float(m["CalIntercept"].mean()),
                "PRAUC": float(m["PRAUC"].mean()),
            }
            js[f"cal_{ds}_{method}"] = r
            rows_tex.append(
                f"{'NASA' if ds=='nasa' else 'CALCE'} & {label} & "
                f"{r['AUC_fold_mean']:.3f} & {r['Brier']:.3f} & {r['ECE']:.3f} & "
                f"{r['LogLoss']:.3f} & {r['Slope']:.2f} & {r['Intercept']:.2f} \\\\")
    save_fragment("tab_calibration.tex", "\n".join(rows_tex) + "\n")
    return js


# ---------------------------------------------------------------- transfer
def transfer_tables():
    tr = _read_csv(os.path.join(_RES, "transfer_trees.csv"))
    gru = _read_csv(os.path.join(_RES, "gru_transfer.csv"))
    js = {}
    if len(tr) == 0:
        save_fragment("tab_cross_with.tex", "")
        save_fragment("tab_cross_no.tex", "")
        save_fragment("tab_gru_transfer.tex", "")
        return js
    for fs, frag in [("with_soh", "tab_cross_with.tex"), ("no_soh", "tab_cross_no.tex")]:
        rows_tex = []
        for source in ["nasa", "calce", "nasa+calce"]:
            for model in TREE_ORDER:
                cells = [SOURCE_LABEL[source], MODEL_LABEL[model]]
                for tgt in ["oxford", "severson"]:
                    r = tr[(tr.source == source) & (tr.target == tgt) &
                           (tr.model == model) & (tr.feature_set == fs) & (tr.H == 20)]
                    if len(r) == 0:
                        cells += ["---", "---"]
                        continue
                    r = r.iloc[0]
                    cells.append(f"{r['raw_AUC']:.3f} [{r['raw_AUC_lo']:.3f},\\,{r['raw_AUC_hi']:.3f}]")
                    cells.append(f"{r['raw_AUC_percell_mean']:.3f}$\\pm${r['raw_AUC_percell_std']:.3f}")
                    js[f"transfer_{tgt}_{source}_{model}_{fs}"] = {
                        "pooled": float(r["raw_AUC"]),
                        "ci": [float(r["raw_AUC_lo"]), float(r["raw_AUC_hi"])],
                        "percell": [float(r["raw_AUC_percell_mean"]), float(r["raw_AUC_percell_std"])]}
                rows_tex.append(" & ".join(cells) + r" \\")
        save_fragment(frag, "\n".join(rows_tex) + "\n")
    # GRU transfer, seed-averaged
    rows_tex = []
    if len(gru) == 0:
        save_fragment("tab_gru_transfer.tex", "")
        return js
    for source in ["nasa", "calce", "nasa+calce"]:
        for fs in ["common_with_soh", "common_no_soh"]:
            cells = [SOURCE_LABEL[source], FEATSET_LABEL[fs]]
            for tgt in ["oxford", "severson"]:
                r = gru[(gru.source == source) & (gru.target == tgt) &
                        (gru.feature_set == fs) & (gru.H == 20)]
                if len(r) == 0:
                    cells.append("---")
                    continue
                m = r["raw_AUC_percell_mean"].mean()
                s = r["raw_AUC_percell_mean"].std(ddof=1) if len(r) > 1 else np.nan
                cells.append(f"{m:.3f}$\\pm${s:.3f}" if np.isfinite(s) else f"{m:.3f}")
            rows_tex.append(" & ".join(cells) + r" \\")
    save_fragment("tab_gru_transfer.tex", "\n".join(rows_tex) + "\n")
    return js


def ablation_table():
    js = {}
    p = os.path.join(_RES, "soh_ablation_tests.csv")
    if os.path.exists(p):
        d = pd.read_csv(p)
        rows_tex = []
        for tgt in ["oxford", "severson"]:
            for model in TREE_ORDER:
                dmm = d[(d.target == tgt) & (d.model == model)].sort_values("H")
                for _, r in dmm.iterrows():
                    rows_tex.append(
                        f"{TARGET_LABEL[tgt]} & {MODEL_LABEL[model]} & {int(r['H'])} & "
                        f"{r['auc_with']:.3f} & {r['auc_without']:.3f} & "
                        f"{r['delta_bootstrap']:+.3f} [{r['delta_lo']:.3f}, {r['delta_hi']:.3f}] & "
                        f"${r['delong_p_cyclelevel']:.1e}$ \\\\")
                    js[f"soh_delta_{tgt}_{model}_{int(r['H'])}"] = {
                        "delta": float(r["delta_bootstrap"]),
                        "ci": [float(r["delta_lo"]), float(r["delta_hi"])],
                        "delong_p": float(r["delong_p_cyclelevel"])}
        save_fragment("tab_soh_tests.tex", "\n".join(rows_tex) + "\n")
    return js


def feature_ablation_table():
    p = os.path.join(_RES, "feature_ablation.csv")
    js = {}
    if not os.path.exists(p):
        return js
    d = pd.read_csv(p)
    rows_tex = []
    for fs in ["full", "no_soh", "no_cycle", "no_soh_no_cycle", "soh_only", "cycle_only", "sensors_only"]:
        cells = [FEATSET_LABEL[fs]]
        for source in ["nasa", "calce", "nasa+calce"]:
            for tgt in ["oxford", "severson"]:
                r = d[(d.feature_set == fs) & (d.source == source) & (d.target == tgt) & (d.H == 20)]
                if len(r) == 0:
                    cells.append("---")
                    continue
                r = r.iloc[0]
                cells.append(f"{r['raw_AUC']:.3f} {ci(r['raw_AUC_lo'], r['raw_AUC_hi'])}")
                js[f"abl_{source}_{tgt}_{fs}"] = float(r["raw_AUC"])
        rows_tex.append(" & ".join(cells) + r" \\")
    save_fragment("tab_feature_ablation.tex", "\n".join(rows_tex) + "\n")
    return js


def faildef_table():
    p = os.path.join(_RES, "faildef_ablation.csv")
    js = {}
    if not os.path.exists(p):
        return js
    d = pd.read_csv(p)
    dtr = d[d.source.notna()]
    dwithin = d[d.source.isna()] if "source" in d.columns else d.iloc[0:0]
    for _, r in dwithin.iterrows():
        auc = r.get("AUC", np.nan)
        if "endpoint" in r and np.isfinite(auc):
            js[f"faildefwithin_{r['endpoint']}_{r['dataset']}_{r['feature_set']}"] = float(auc)
    d = dtr  # transfer rows only
    rows_tex = []
    for endpoint in ["combined", "soh_only", "volt_only"]:
        cells = [endpoint]
        for fs in ["with_soh", "no_soh"]:
            for source in ["nasa+calce"]:
                for tgt in ["oxford", "severson"]:
                    r = d[(d.endpoint == endpoint) & (d.feature_set == fs) &
                          (d.source == source) & (d.target == tgt) & (d.H == 20)]
                    if len(r) == 0:
                        cells.append("---")
                        continue
                    r = r.iloc[0]
                    cells.append(f"{r['raw_AUC']:.3f} {ci(r['raw_AUC_lo'], r['raw_AUC_hi'])}")
                    js[f"faildef_{endpoint}_{fs}_{tgt}"] = float(r["raw_AUC"])
        rows_tex.append(" & ".join(cells) + r" \\")
    save_fragment("tab_faildef.tex", "\n".join(rows_tex) + "\n")
    return js


def samechem_table():
    p = os.path.join(_RES, "same_chem.csv")
    js = {}
    if not os.path.exists(p):
        return js
    d = pd.read_csv(p)
    rows_tex = []
    pair_label = {("nasa", "calce"): "NASA$\\to$CALCE (LCO$\\to$LCO)",
                  ("calce", "nasa"): "CALCE$\\to$NASA (LCO$\\to$LCO)",
                  ("severson", "oxford"): "Severson$\\to$Oxford (LFP$\\to$LFP)",
                  ("oxford", "severson"): "Oxford$\\to$Severson (LFP$\\to$LFP)"}
    for src, tgt in pair_label:
        cells = [pair_label[(src, tgt)]]
        for fs in ["with_soh", "no_soh", "common_no_soh"]:
            r = d[(d.source == src) & (d.target == tgt) & (d.feature_set == fs) & (d.H == 20)]
            if len(r) == 0:
                cells.append("---")
                continue
            r = r.iloc[0]
            cells.append(f"{r['raw_AUC']:.3f} {ci(r['raw_AUC_lo'], r['raw_AUC_hi'])}")
            js[f"samechem_{src}_{tgt}_{fs}"] = float(r["raw_AUC"])
        rows_tex.append(" & ".join(cells) + r" \\")
    save_fragment("tab_samechem.tex", "\n".join(rows_tex) + "\n")
    return js


def hazard_table():
    p = os.path.join(_RES, "hazard_transfer.csv")
    js = {}
    if not os.path.exists(p):
        return js
    d = pd.read_csv(p)
    rows_tex = []
    for source in ["nasa", "calce", "nasa+calce"]:
        for model in ["hazard_xgb", "hazard_logistic"]:
            cells = [SOURCE_LABEL[source], MODEL_LABEL[model]]
            for tgt in ["oxford", "severson"]:
                r = d[(d.source == source) & (d.target == tgt) & (d.model == model) & (d.H == 20)]
                if len(r) == 0:
                    cells += ["---", "---"]
                    continue
                r = r.iloc[0]
                cells.append(f"{r['AUC']:.3f} {ci(r['AUC_lo'], r['AUC_hi'])}")
                js[f"hazard_{source}_{tgt}_{model}"] = float(r["AUC"])
            rows_tex.append(" & ".join(cells) + r" \\")
    save_fragment("tab_hazard_transfer.tex", "\n".join(rows_tex) + "\n")
    return js


def baselines_table():
    p = os.path.join(_RES, "baselines_transfer.csv")
    js = {}
    if not os.path.exists(p):
        return js
    d = pd.read_csv(p)
    pw = os.path.join(_RES, "baselines_within.csv")
    if os.path.exists(pw):
        dw = pd.read_csv(pw)
        for _, r in dw.iterrows():
            js[f"base_within_{r['dataset']}_{r['baseline']}"] = float(r["AUC"])
    rows_tex = []
    bl_label = {"soh_dist": "SOH distance rule", "soh_only": "SOH only", "cycle_only": "cycle only",
                "soh_cycle": "SOH + cycle", "sensors": "sensors only", "full": "full (7 feats)"}
    for b in ["soh_dist", "soh_only", "cycle_only", "soh_cycle", "sensors", "full"]:
        cells = [bl_label[b]]
        for source in ["nasa", "calce", "nasa+calce"]:
            for tgt in ["oxford", "severson"]:
                r = d[(d.baseline == b) & (d.source == source) & (d.target == tgt) & (d.H == 20)]
                if len(r) == 0:
                    cells.append("---")
                    continue
                r = r.iloc[0]
                cells.append(f"{r['AUC']:.3f} {ci(r['AUC_lo'], r['AUC_hi'])}")
                js[f"base_{source}_{tgt}_{b}"] = float(r["AUC"])
        rows_tex.append(" & ".join(cells) + r" \\")
    save_fragment("tab_baselines.tex", "\n".join(rows_tex) + "\n")
    return js


def operational_table():
    p = os.path.join(_RES, "operational_costs.csv")
    js = {}
    if not os.path.exists(p):
        return js
    d = pd.read_csv(p)
    d = d[(d.C_FN == 20.0) & (d.model == "xgboost")]
    rows_tex = []
    for tgt in ["oxford", "severson"]:
        for fs in ["with_soh", "no_soh"]:
            r = d[(d.target == tgt) & (d.feature_set == fs)]
            if len(r) == 0:
                continue
            r = r.iloc[0]
            cells = [TARGET_LABEL[tgt], FEATSET_LABEL[fs]]
            for method in ["raw", "platt", "iso", "temp"]:
                cells.append(f"{r[f'cost_{method}']:.4f}")
                cells.append(f"{int(round(100*r[f'fnr_{method}']))}\\%")
            rows_tex.append(" & ".join(cells) + r" \\")
            js[f"cost_{tgt}_{fs}"] = {m: float(r[f"cost_{m}"]) for m in ["raw", "platt", "iso", "temp"]}
    save_fragment("tab_operational.tex", "\n".join(rows_tex) + "\n")
    return js


def monotonicity_summary():
    p = os.path.join(_RES, "monotonicity.csv")
    js = {}
    if not os.path.exists(p):
        return js
    d = pd.read_csv(p)
    for _, r in d.iterrows():
        js[f"mono_{r['setting']}_{r['dataset']}_{r['model']}"] = float(r["monotonicity_violation_rate"]) \
            if np.isfinite(r["monotonicity_violation_rate"]) else None
    return js


def recal_tables():
    if not os.path.exists(_RECAL):
        return {}
    d = pd.read_csv(_RECAL)
    js = {}
    # Arm A on Severson, no SOH, averaged over sources+tree models
    a = d[(d.target == "severson") & (d.arm == "arm_a") & (d.features == "no_soh")]
    a = a[a.model.isin(TREE_ORDER)]
    js["armA"] = {}
    rows_a = []
    z = d[(d.target == "severson") & (d.arm == "zeroshot") & (d.features == "no_soh")
          & d.model.isin(TREE_ORDER) & (d.k == 5)]
    ece_zero = float(z["ece"].mean())
    for k in [5, 10, 20, 40]:
        s = a[a.k == k]
        row = {
            "ece_zero": ece_zero,
            "ece_iso": float(s[s.method == "iso"]["ece"].mean()),
            "ece_platt": float(s[s.method == "platt"]["ece"].mean()),
            "ece_temp": float(s[s.method == "temp"]["ece"].mean()),
            "auc_iso": float(s[s.method == "iso"]["auc_pooled"].mean()),
            "auc_platt": float(s[s.method == "platt"]["auc_pooled"].mean()),
            "auc_temp": float(s[s.method == "temp"]["auc_pooled"].mean()),
        }
        js["armA"][k] = row
        rows_a.append(f"{k} & {row['ece_zero']:.3f} & {row['ece_iso']:.3f} & "
                      f"{row['ece_platt']:.3f} & {row['ece_temp']:.3f} & "
                      f"{row['auc_iso']:.3f} & {row['auc_platt']:.3f} & {row['auc_temp']:.3f} \\\\")
    save_fragment("tab_rec_a.tex", "\n".join(rows_a) + "\n")
    b = d[(d.target == "severson") & (d.arm == "arm_b") & (d.features == "no_soh") & (d.k == 5)]
    js["armB"] = {}
    rows_b = []
    for src in ["nasa", "calce", "nasa+calce"]:
        for model in ["xgboost", "lightgbm", "random_forest"]:
            r = b[(b.source == src) & (b.model == model)]
            if len(r) == 0:
                continue
            r = r.iloc[0]
            auc_zero = float(r["auc_zeroshot"]) if np.isfinite(r["auc_zeroshot"]) else np.nan
            p_dl = float(r["delong_p_vs_zeroshot"]) if np.isfinite(r["delong_p_vs_zeroshot"]) else np.nan
            if np.isfinite(p_dl) and p_dl < 1e-3:
                p_tex = "$<10^{-3}$"
            elif np.isfinite(p_dl):
                p_tex = f"${p_dl:.3f}$"
            else:
                p_tex = "---"
            row = {
                "auc_zero": auc_zero,
                "auc_after": float(r["auc_pooled"]),
                "recovery": float(r["recovery_ratio"]) if np.isfinite(r["recovery_ratio"]) else np.nan,
                "retention_before": float(r["auc_lco_holdout_before"]),
                "retention_after": float(r["auc_lco_holdout_after"]),
                "delong_p": p_dl,
            }
            js["armB"][f"{src}_{model}"] = row
            rows_b.append(
                f"{SOURCE_LABEL[src]} & {MODEL_LABEL[model]} & "
                f"{auc_zero:.3f} & {row['auc_after']:.3f} & "
                f"{row['recovery']:+.2f} & {p_tex} & "
                f"{row['retention_before']:.3f} $\\rightarrow$ {row['retention_after']:.3f} \\\\")
    save_fragment("tab_rec_b.tex", "\n".join(rows_b) + "\n")
    return js


def main():
    out = {}
    for fn in [within_table, calibration_table, transfer_tables, ablation_table,
               feature_ablation_table, faildef_table, samechem_table, hazard_table,
               baselines_table, operational_table, monotonicity_summary, recal_tables]:
        try:
            out.update(fn() or {})
        except FileNotFoundError as e:
            print(f"SKIP {fn.__name__}: missing file {e}")
    with open(os.path.join(_RES, "paper_numbers.json"), "w") as fh:
        json.dump(out, fh, indent=1, default=float)
    print(f"wrote paper_numbers.json with {len(out)} entries")


if __name__ == "__main__":
    main()
