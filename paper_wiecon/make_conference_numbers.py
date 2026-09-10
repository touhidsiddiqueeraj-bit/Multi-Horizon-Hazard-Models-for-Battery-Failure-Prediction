"""Emit table bodies + number macros for the WIECON conference paper from
results_v2 (the same leakage-clean pipeline as the journal paper)."""
import json
import os
import numpy as np
import pandas as pd

_HERE = os.path.dirname(os.path.abspath(__file__))
_RES = os.path.join(_HERE, "..", "results_v2")
_OUT = os.path.join(_HERE, "generated")
os.makedirs(_OUT, exist_ok=True)

MODEL_LABEL = {"xgboost": "XGBoost", "lightgbm": "LightGBM",
               "random_forest": "Random Forest", "gru": "GRU"}
SOURCE_LABEL = {"nasa": "NASA", "calce": "CALCE", "nasa+calce": "NASA+CALCE"}
H_LIST = [10, 20, 30, 50]

trees = pd.read_csv(os.path.join(_RES, "within_trees.csv"))
gru_w = pd.read_csv(os.path.join(_RES, "gru_within.csv"))
transfer = pd.read_csv(os.path.join(_RES, "transfer_trees.csv"))
gru_t = pd.read_csv(os.path.join(_RES, "gru_transfer.csv"))
soh = pd.read_csv(os.path.join(_RES, "soh_ablation_tests.csv"))

NUM = {}

# ------------------------------------------------ Table II: within-dataset
rows = []
for model in ["xgboost", "lightgbm", "random_forest"]:
    for ds in ["nasa", "calce"]:
        sub = trees[(trees.model == model) & (trees.dataset == ds) & (trees.method == "platt")]
        cells = [MODEL_LABEL[model], "NASA" if ds == "nasa" else "CALCE"]
        vals = []
        for H in H_LIST:
            v = sub[sub.H == H]["AUC_fold_mean"]
            v = float(v.iloc[0]) if len(v) else np.nan
            vals.append(v)
            cells.append(f"{v:.3f}")
        mean = float(sub["AUC_fold_mean"].mean())
        brier = float(sub["Brier"].mean())
        cells += [f"{mean:.3f}", f"{brier:.3f}"]
        rows.append(" & ".join(cells) + r" \\")
        NUM[f"within_{ds}_{model}_mean"] = round(mean, 3)
for ds in ["nasa", "calce"]:
    sub = gru_w[(gru_w.dataset == ds) & (gru_w.method == "platt")]
    cells = ["GRU", "NASA" if ds == "nasa" else "CALCE"]
    vals = []
    for H in H_LIST:
        v = sub[sub.H == H]["AUC_fold_mean"]
        v = float(v.iloc[0]) if len(v) else np.nan
        vals.append(v)
        cells.append(f"{v:.3f}")
    mean = float(sub["AUC_fold_mean"].mean())
    brier = float(sub["Brier"].mean())
    cells += [f"{mean:.3f}", f"{brier:.3f}"]
    rows.append(" & ".join(cells) + r" \\")
    NUM[f"within_{ds}_gru_mean"] = round(mean, 3)
with open(os.path.join(_OUT, "tab_within.tex"), "w") as f:
    f.write("\n".join(r + r" \hline" for r in rows) + "\n")

# count of configurations with fold-mean AUC >= 0.85 (trees + GRU, both datasets)
count = 0
total = 0
for model in ["xgboost", "lightgbm", "random_forest"]:
    for ds in ["nasa", "calce"]:
        sub = trees[(trees.model == model) & (trees.dataset == ds) & (trees.method == "platt")]
        for H in H_LIST:
            v = sub[sub.H == H]["AUC_fold_mean"]
            if len(v):
                total += 1
                count += int(v.iloc[0] >= 0.85)
for ds in ["nasa", "calce"]:
    sub = gru_w[(gru_w.dataset == ds) & (gru_w.method == "platt")]
    for H in H_LIST:
        v = sub[sub.H == H]["AUC_fold_mean"]
        if len(v):
            total += 1
            count += int(v.iloc[0] >= 0.85)
NUM["within_ge085"] = count
NUM["within_total"] = total

# ------------------------------------------------ Table III: calibration
rows = []
for ds in ["nasa", "calce"]:
    sub = trees[trees.dataset == ds]
    label = "NASA" if ds == "nasa" else "CALCE"
    for method, mlabel in [("iso", "Isotonic"), ("platt", "Platt"), ("temp", "Temperature")]:
        m = sub[sub.method == method]
        rows.append(
            f"{label} & {mlabel} & {m['AUC_fold_mean'].mean():.3f} & "
            f"{m['Brier'].mean():.3f} & {m['ECE10'].mean():.3f} & "
            f"{m['CalSlope'].mean():.2f} \\\\")
        NUM[f"cal_{ds}_{method}_auc"] = round(float(m["AUC_fold_mean"].mean()), 3)
        NUM[f"cal_{ds}_{method}_ece"] = round(float(m["ECE10"].mean()), 3)
with open(os.path.join(_OUT, "tab_calibration.tex"), "w") as f:
    f.write("\n".join(r + r" \hline" for r in rows) + "\n")

# ------------------------------------------------ Table IV: transfer H=20
rows = []
NUM["xfer_ox_all_xgb_with"] = None
for source in ["nasa", "calce", "nasa+calce"]:
    for model in ["xgboost", "lightgbm", "random_forest", "gru"]:
        cells = [SOURCE_LABEL[source], MODEL_LABEL[model]]
        for tgt in ["oxford", "severson"]:
            if model == "gru":
                r = gru_t[(gru_t.source == source) & (gru_t.target == tgt) &
                          (gru_t.feature_set == "common_with_soh") & (gru_t.H == 20)]
                n = gru_t[(gru_t.source == source) & (gru_t.target == tgt) &
                          (gru_t.feature_set == "common_no_soh") & (gru_t.H == 20)]
                w = r["raw_AUC"].mean() if len(r) else np.nan
                wo = n["raw_AUC"].mean() if len(n) else np.nan
            else:
                r = transfer[(transfer.source == source) & (transfer.target == tgt) &
                             (transfer.model == model) &
                             (transfer.feature_set == "with_soh") & (transfer.H == 20)]
                n = transfer[(transfer.source == source) & (transfer.target == tgt) &
                             (transfer.model == model) &
                             (transfer.feature_set == "no_soh") & (transfer.H == 20)]
                w = float(r["raw_AUC"].iloc[0]) if len(r) else np.nan
                wo = float(n["raw_AUC"].iloc[0]) if len(n) else np.nan
            cells.append(f"{w:.3f}")
            cells.append(f"{wo:.3f}")
            key = f"xfer_{tgt.split('o')[0]}_{source}_{model}".replace("sev", "severson_").replace("ox", "oxford_")
            if tgt == "oxford" and source == "nasa+calce" and model == "xgboost":
                NUM["xfer_ox_all_xgb_with"] = round(w, 3)
                NUM["xfer_ox_all_xgb_without"] = round(wo, 3)
        rows.append(" & ".join(cells) + r" \\")
with open(os.path.join(_OUT, "tab_transfer.tex"), "w") as f:
    f.write("\n".join(r + r" \hline" for r in rows) + "\n")

# with-SOH max / no-SOH max across tree configs at H=20
w_tree = transfer[(transfer.feature_set == "with_soh") & (transfer.H == 20) &
                  transfer.model.isin(["xgboost", "lightgbm", "random_forest"])]
n_tree = transfer[(transfer.feature_set == "no_soh") & (transfer.H == 20) &
                  transfer.model.isin(["xgboost", "lightgbm", "random_forest"])]
NUM["xfer_with_max"] = round(float(w_tree["raw_AUC"].max()), 2)
NUM["xfer_without_max_ox"] = round(float(n_tree[n_tree.target == "oxford"]["raw_AUC"].max()), 2)
NUM["xfer_without_min"] = round(float(n_tree["raw_AUC"].min()), 2)

# ------------------------------------------------ Table V: SOH ablation tests
rows = []
for tgt in ["oxford", "severson"]:
    for model in ["xgboost", "lightgbm", "random_forest"]:
        r = soh[(soh.target == tgt) & (soh.model == model) & (soh.H == 20)]
        if len(r) == 0:
            continue
        r = r.iloc[0]
        lo, hi = r["delta_lo"], r["delta_hi"]
        ci = (f" [{lo:.2f}, {hi:.2f}]" if np.isfinite(lo) and np.isfinite(hi)
              else " (5 cells)")
        rows.append(
            f"{'Oxford' if tgt == 'oxford' else 'Severson'} & {MODEL_LABEL[model]} & "
            f"{r['auc_with']:.3f} & {r['auc_without']:.3f} & "
            f"{r['delta_bootstrap']:+.3f}{ci} & "
            f"{'$<10^{-300}$' if r['delong_p_cyclelevel'] == 0 else '$' + format(r['delong_p_cyclelevel'], '.1e') + '$'} \\\\")
        NUM[f"delta_{tgt}_{model}"] = round(float(r["delta_bootstrap"]), 3)
with open(os.path.join(_OUT, "tab_soh.tex"), "w") as f:
    f.write("\n".join(r + r" \hline" for r in rows) + "\n")

# within-dataset model-comparison DeLong at H=20 from saved pooled predictions
from stats_utils import delong_roc_test
from pipeline_core import load_preds
drows = []
for ds in ["nasa", "calce"]:
    preds = {}
    for model in ["xgboost", "lightgbm", "random_forest", "gru"]:
        try:
            preds[model] = load_preds(f"within_{ds}_{model}_H20.csv")
        except FileNotFoundError:
            pass
    for a, b in [("xgboost", "lightgbm"), ("xgboost", "random_forest"),
                 ("lightgbm", "random_forest")]:
        if a in preds and b in preds:
            d = delong_roc_test(preds[a]["y"].to_numpy(),
                                preds[a]["p_raw"].to_numpy(),
                                preds[b]["p_raw"].to_numpy())
            drows.append(f"{'NASA' if ds == 'nasa' else 'CALCE'} & "
                         f"{MODEL_LABEL[a]} vs {MODEL_LABEL[b]} & {d['p_value']:.1e} \\\\")
            NUM[f"delong_{ds}_{a}_{b}"] = float(d["p_value"])
with open(os.path.join(_OUT, "tab_delong_within.tex"), "w") as f:
    f.write("\n".join(drows) + "\n")

# ------------------------------------------------ failure-definition ablation
fd = pd.read_csv(os.path.join(_RES, "faildef_ablation.csv"))
fd = fd[fd.source == "nasa+calce"]
endpoint_label = {"combined": "Combined (SOH or sag)", "soh_only": "SOH only",
                  "volt_only": "Voltage sag only"}
rows = []
for endpoint in ["combined", "soh_only", "volt_only"]:
    cells = [endpoint_label[endpoint]]
    for tgt in ["oxford", "severson"]:
        for fs in ["with_soh", "no_soh"]:
            r = fd[(fd.endpoint == endpoint) & (fd.feature_set == fs) &
                   (fd.target == tgt) & (fd.H == 20)]
            cells.append(f"{r['raw_AUC'].iloc[0]:.3f}" if len(r) else "---")
            if len(r):
                NUM[f"fd_{endpoint}_{tgt}_{fs}"] = round(float(r["raw_AUC"].iloc[0]), 3)
    rows.append(" & ".join(cells) + r" \\")
with open(os.path.join(_OUT, "tab_faildef.tex"), "w") as f:
    f.write("\n".join(r + r" \hline" for r in rows) + "\n")

# ------------------------------------------------ same-chemistry controls
sc = pd.read_csv(os.path.join(_RES, "same_chem.csv"))
pair_label = {("nasa", "calce"): "NASA$\\to$CALCE (LCO$\\to$LCO)",
              ("calce", "nasa"): "CALCE$\\to$NASA (LCO$\\to$LCO)",
              ("severson", "oxford"): "Severson$\\to$Oxford (LFP$\\to$LFP)",
              ("oxford", "severson"): "Oxford$\\to$Severson (LFP$\\to$LFP)"}
rows = []
for (src, tgt), label in pair_label.items():
    cells = [label]
    for fs in ["with_soh", "no_soh"]:
        r = sc[(sc.source == src) & (sc.target == tgt) & (sc.feature_set == fs) & (sc.H == 20)]
        cells.append(f"{r['raw_AUC'].iloc[0]:.3f}" if len(r) else "---")
        if len(r):
            NUM[f"sc_{src}_{tgt}_{fs}"] = round(float(r["raw_AUC"].iloc[0]), 3)
    rows.append(" & ".join(cells) + r" \\")
with open(os.path.join(_OUT, "tab_samechem.tex"), "w") as f:
    f.write("\n".join(r + r" \hline" for r in rows) + "\n")

# ------------------------------------------------ hazard vs fixed-horizon
haz = pd.read_csv(os.path.join(_RES, "hazard_within.csv"))
hazt = pd.read_csv(os.path.join(_RES, "hazard_transfer.csv"))
mono = pd.read_csv(os.path.join(_RES, "monotonicity.csv"))
rows = []
# within fold-mean at H=20/50: hazard vs fixed-horizon xgboost
for ds in ["nasa", "calce"]:
    hx = haz[(haz.dataset == ds) & (haz.model == "hazard_xgb")]
    fx = trees[(trees.dataset == ds) & (trees.model == "xgboost") & (trees.method == "platt")]
    cells = [f"{'NASA' if ds == 'nasa' else 'CALCE'}",
             f"{fx[fx.H == 20]['AUC_fold_mean'].iloc[0]:.3f}",
             f"{hx[hx.H == 20]['AUC_fold_mean'].iloc[0]:.3f}",
             f"{fx[fx.H == 50]['AUC_fold_mean'].iloc[0]:.3f}",
             f"{hx[hx.H == 50]['AUC_fold_mean'].iloc[0]:.3f}"]
    rows.append(" & ".join(cells) + r" \\")
for source in ["nasa", "calce", "nasa+calce"]:
    for tgt in ["oxford", "severson"]:
        h = hazt[(hazt.source == source) & (hazt.target == tgt) &
                 (hazt.model == "hazard_xgb") & (hazt.H == 20)]
        t = transfer[(transfer.source == source) & (transfer.target == tgt) &
                     (transfer.model == "xgboost") &
                     (transfer.feature_set == "with_soh") & (transfer.H == 20)]
        if len(h) and len(t):
            rows.append(f"{SOURCE_LABEL[source]}$\\to$\\textit{{{tgt.capitalize()}}} & "
                        f"{t['raw_AUC'].iloc[0]:.3f} & {h['AUC'].iloc[0]:.3f} & --- & --- \\\\")
with open(os.path.join(_OUT, "tab_hazard.tex"), "w") as f:
    f.write("\n".join(r + r" \hline" for r in rows) + "\n")

# monotonicity violation summary
m_w = mono[(mono.setting == "within") & (mono.model == "xgboost")]
m_t = mono[(mono.setting.str.startswith("transfer")) & (mono.dataset == "severson") &
           (mono.model == "xgboost")]
NUM["mono_within_xgb"] = round(float(m_w["monotonicity_violation_rate"].max()), 3)
NUM["mono_transfer_sev_xgb"] = round(float(m_t["monotonicity_violation_rate"].max()), 3)

# ------------------------------------------------ operational (Severson, XGBoost)
op = pd.read_csv(os.path.join(_RES, "operational_costs.csv"))
op = op[(op.model == "xgboost")]
rows = []
for tgt in ["oxford", "severson"]:
    for fs in ["with_soh", "no_soh"]:
        cells = [f"{'Oxford' if tgt == 'oxford' else 'Severson'}",
                 "with SOH" if fs == "with_soh" else "no SOH"]
        for method in ["raw", "platt", "iso"]:
            r = op[(op.target == tgt) & (op.feature_set == fs) & (op.method == method)]
            if len(r):
                r = r.iloc[0]
                cells.append(f"{100*r['tgt_fnr']:.0f} / {100*r['tgt_fpr']:.0f}")
                NUM[f"op_{tgt}_{fs}_{method}_fnr"] = round(100 * float(r["tgt_fnr"]))
            else:
                cells.append("---")
        rows.append(" & ".join(cells) + r" \\")
with open(os.path.join(_OUT, "tab_operational.tex"), "w") as f:
    f.write("\n".join(r + r" \hline" for r in rows) + "\n")

with open(os.path.join(_OUT, "numbers.json"), "w") as f:
    json.dump(NUM, f, indent=1)
print(json.dumps(NUM, indent=1))
