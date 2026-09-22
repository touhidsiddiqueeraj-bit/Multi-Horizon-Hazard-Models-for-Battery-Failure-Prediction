#!/usr/bin/env python3
"""Assemble paper_ieee_access/main_access.tex from the template parts and
results_v2 numbers. Every @@TOKEN@@ is filled here; the script fails loudly
on any token it cannot fill, so no placeholder can reach the PDF."""
import json
import os
import re
import sys
import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(ROOT, "results_v2")
FRAG = os.path.join(RES, "tex_fragments")
PAPER = os.path.join(ROOT, "paper_ieee_access")

N = json.load(open(os.path.join(RES, "paper_numbers.json")))


def j(key, sub=None):
    v = N.get(key)
    if v is None:
        raise KeyError(f"paper_numbers.json missing {key!r}")
    if sub is not None:
        v = v[sub] if not isinstance(sub, list) else [v[s] for s in sub]
    return v


def rng(keys, sub=None, nd=2):
    vals = []
    for k in keys:
        v = j(k, sub)
        if v is not None and np.isfinite(v):
            vals.append(v)
    if not vals:
        return "---"
    return f"{min(vals):.{nd}f}--{max(vals):.{nd}f}"


def frag(name):
    path = os.path.join(FRAG, name)
    if not os.path.exists(path):
        raise FileNotFoundError(f"missing fragment {name}")
    return open(path).read().rstrip("\n")


def f3(x):
    return "---" if x is None or not np.isfinite(x) else f"{x:.3f}"


def ci(x, nd=3):
    lo, hi = x
    if lo is None or hi is None or not (np.isfinite(lo) and np.isfinite(hi)):
        return "---"
    return f"{lo:.{nd}f}--{hi:.{nd}f}"


# ---------------------------------------------------------------- token map
T = {}

# fragments
T["TAB_WITHIN"] = lambda: frag("tab_within.tex")
T["TAB_CAL"] = lambda: frag("tab_calibration.tex")
T["TAB_CROSS_WITH"] = lambda: frag("tab_cross_with.tex")
T["TAB_CROSS_NO"] = lambda: frag("tab_cross_no.tex")
T["TAB_GRU"] = lambda: frag("tab_gru_transfer.tex")
T["TAB_BASELINES"] = lambda: frag("tab_baselines.tex")
T["TAB_ABLATION"] = lambda: frag("tab_feature_ablation.tex")
T["TAB_FAILDEF"] = lambda: frag("tab_faildef.tex")
T["TAB_SAMECHEM"] = lambda: frag("tab_samechem.tex")
T["TAB_HAZARD"] = lambda: frag("tab_hazard_transfer.tex")
T["TAB_REC_A"] = lambda: frag("tab_rec_a.tex")
T["TAB_REC_B"] = lambda: frag("tab_rec_b.tex")
T["TAB_SOH_TESTS"] = lambda: frag("tab_soh_tests.tex")
T["TAB_OPER"] = lambda: frag("tab_operational.tex")
T["TAB_CROSSCHEM_NEW"] = lambda: frag("tab_crosschem_new.tex")
T["TAB_CONDSHIFT"] = lambda: frag("tab_condshift.tex")

# abstract / intro
T["N_TARGETS"] = lambda: "six"
T["N_SEV"] = lambda: "141"
T["WITHIN_MIN"] = lambda: rng([f"within_{d}_{m}" for d in ["nasa", "calce"]
                               for m in ["xgboost", "lightgbm", "random_forest"]], "mean_AUC")
T["WITHIN_MAX"] = lambda: f"{max(v for k in [f'within_{d}_{m}' for d in ['nasa','calce'] for m in ['xgboost','lightgbm','random_forest']] for v in [(j(k, 'mean_AUC') or np.nan)]):.2f}"
T["XFER_WITH_MAX"] = lambda: f"{max(j(f'transfer_{t}_{s}_{m}_with_soh', 'pooled') for t in ['oxford','severson'] for s in ['nasa','calce','nasa+calce'] for m in ['xgboost','lightgbm','random_forest']):.2f}"
T["XFER_NO_MAX"] = lambda: f"{max(j(f'transfer_oxford_{s}_{m}_no_soh', 'pooled') for s in ['nasa','calce','nasa+calce'] for m in ['xgboost','lightgbm','random_forest']):.2f}"
T["XFER_WITH_SEV"] = lambda: f"{max(j(f'transfer_severson_{s}_{m}_with_soh', 'pooled') for s in ['nasa','calce','nasa+calce'] for m in ['xgboost','lightgbm','random_forest']):.2f}"
T["XFER_NO_SEV_MIN"] = lambda: f"{min(j(f'transfer_severson_{s}_{m}_no_soh', 'pooled') for s in ['nasa','calce','nasa+calce'] for m in ['xgboost','lightgbm','random_forest']):.2f}"
T["XFER_NO_SEV_MAX"] = lambda: f"{max(j(f'transfer_severson_{s}_{m}_no_soh', 'pooled') for s in ['nasa','calce','nasa+calce'] for m in ['xgboost','lightgbm','random_forest']):.2f}"
T["BASE_DIST_ALL_SEV"] = lambda: f3(j("base_nasa+calce_severson_soh_dist"))
T["BASE_SOH_ALL_SEV"] = lambda: f3(j("base_nasa+calce_severson_soh_only"))
T["BASE_SENSORS_NASA_SEV"] = lambda: f3(j("base_nasa_severson_sensors"))
T["BASE_CYCLE_CALCE"] = lambda: f3(j("base_within_calce_cycle_only"))
T["BASE_CYCLE_NASA"] = lambda: f3(j("base_within_nasa_cycle_only"))
T["TAB_MONO"] = lambda: frag("tab_monotonicity.tex")


def _mono_vals(prefix):
    return [v for k, v in N.items()
            if k.startswith(prefix) and v is not None and np.isfinite(v)]


T["MONO_WITHIN_RANGE"] = lambda: f"{100*min(_mono_vals('mono_within_')):.0f}--{100*max(_mono_vals('mono_within_')):.0f}\\%"
T["MONO_SEV_MAX"] = lambda: (lambda kv: f"{100*kv[1]:.1f}\\% ({kv[0]})")(max(
    ((f"{k.split('_')[2]}-trained {k.split('_')[-1]}", v) for k, v in N.items()
     if k.startswith("mono_transfer_") and "_severson_" in k
     and v is not None and np.isfinite(v)),
    key=lambda kv: kv[1]))

# calibration section
def _nasa_prauc(method):
    w = pd.read_csv(os.path.join(RES, "within_trees.csv"))
    s = w[(w.dataset == "nasa") &
          (w.model.isin(["xgboost", "lightgbm", "random_forest"])) &
          (w.method == method)]["PRAUC"]
    return float(s.mean())


T["NASA_PRAUC_RAW"] = lambda: f3(_nasa_prauc("raw"))
T["NASA_PRAUC_ISO"] = lambda: f3(_nasa_prauc("iso"))
T["CALCE_PLATT_ECE"] = lambda: f3(j("cal_calce_platt")["ECE"])
T["CALCE_ISO_ECE"] = lambda: f3(j("cal_calce_iso")["ECE"])
T["CALCE_PLATT_SLOPE"] = lambda: f3(j("cal_calce_platt")["Slope"])
T["NASA_TEMP_SLOPE"] = lambda: f3(j("cal_nasa_temp")["Slope"])
T["NASA_TEMP_BRIER"] = lambda: f3(j("cal_nasa_temp")["Brier"])

# GRU
def _gru_sev(fs):
    import subprocess
    tr = pd.read_csv(os.path.join(RES, "gru_transfer.csv"))
    r = tr[(tr.target == "severson") & (tr.feature_set == fs) & (tr.H == 20)]
    return r["raw_AUC_percell_mean"].mean(), (r["raw_AUC_percell_mean"].std(ddof=1) if len(r) > 1 else np.nan)


T["GRU_SEV_NO_SOH"] = lambda: f3(_gru_sev("common_no_soh")[0])
T["GRU_SEV_NO_SOH_STD"] = lambda: f3(_gru_sev("common_no_soh")[1])
T["GRU_SEV_WITH_SOH"] = lambda: f3(_gru_sev("common_with_soh")[0])

# ablation
_NO_SOH_COMBOS = ["no_soh", "no_soh_no_cycle", "sensors_only", "cycle_only"]
T["ABL_MAX_NO_SOH"] = lambda: f"{max(j(f'abl_{s}_{t}_{c}') for s in ['nasa','calce','nasa+calce'] for t in ['oxford','severson'] for c in _NO_SOH_COMBOS):.2f}"
T["ABL_SENSORS_ONLY"] = lambda: f3(j("abl_nasa+calce_severson_sensors_only"))

# failure definition
def _faildef(fs, tgt, endpoint):
    return j(f"faildef_{endpoint}_{fs}_{tgt}")


T["FAILDEF_ADV_COMBINED"] = lambda: f"{_faildef('with_soh','severson','combined') - _faildef('no_soh','severson','combined'):+.2f}"
T["FAILDEF_ADV_VOLT"] = lambda: f"{_faildef('with_soh','severson','volt_only') - _faildef('no_soh','severson','volt_only'):+.2f}"
T["FAILDEF_ADV_DROP"] = lambda: "most"
T["FAILDEF_VOLT_WITH"] = lambda: f3(_faildef("with_soh", "severson", "volt_only"))
T["FAILDEF_VOLT_NO"] = lambda: f3(_faildef("no_soh", "severson", "volt_only"))
T["FAILDEF_WITH_SOHLABEL"] = lambda: f3(_faildef("with_soh", "severson", "soh_only"))
T["FAILDEF_WITH_COMBINED"] = lambda: f3(_faildef("with_soh", "severson", "combined"))


def _faildef_within(endpoint, ds, fs):
    v = j(f"faildefwithin_{endpoint}_{ds}_{fs}")
    return v


T["FAILDEF_WITHIN_SOH"] = lambda: f3(_faildef_within("soh_only", "nasa", "with_soh"))
T["FAILDEF_WITHIN_NO"] = lambda: f3(_faildef_within("soh_only", "nasa", "no_soh"))
T["FAILDEF_WITHIN_GAP"] = lambda: f"{_faildef_within('soh_only','nasa','with_soh') - _faildef_within('soh_only','nasa','no_soh'):+.2f}"
T["FAILDEF_WITHIN_SENSORS"] = lambda: f3(j("base_within_nasa_sensors"))

# calibration transfer / recalibration
def _iso_loss_max(target=None):
    tr = pd.read_csv(os.path.join(RES, "transfer_trees.csv"))
    w = tr[(tr.feature_set == "with_soh") & (tr.H == 20)]
    if target is not None:
        w = w[w.target == target]
    return float((w["raw_AUC"] - w["iso_AUC"]).max())


T["ISO_LOSS_MAX"] = lambda: f"{_iso_loss_max():.2f}"
T["ISO_LOSS_OXF"] = lambda: f"{_iso_loss_max('oxford'):.2f}"
T["ISO_LOSS_SEV"] = lambda: f"{_iso_loss_max('severson'):.2f}"
T["ARM_A_ECE0"] = lambda: f3(j("armA", "5")["ece_zero"])
T["ARM_A_ECE5_ISO"] = lambda: f3(j("armA", "5")["ece_iso"])
T["ARM_A_ECE5_PLATT"] = lambda: f3(j("armA", "5")["ece_platt"])
T["ARM_A_ECE5_TEMP"] = lambda: f3(j("armA", "5")["ece_temp"])
T["ARM_A_AUC5"] = lambda: f"{np.mean([j('armA','5')['auc_' + m] for m in ['iso', 'platt']]):.2f}"
T["ARMB_NASA_XGB_ZERO"] = lambda: f3(j("armB", "nasa_xgboost")["auc_zero"])
T["ARMB_NASA_XGB_AFTER"] = lambda: f3(j("armB", "nasa_xgboost")["auc_after"])
T["ARMB_NASA_XGB_REC"] = lambda: f"{j('armB','nasa_xgboost')['recovery']:.2f}"
T["ARMB_CALCE_RET0"] = lambda: f3(j("armB", "calce_xgboost")["retention_before"])
T["ARMB_CALCE_RET1"] = lambda: f3(j("armB", "calce_xgboost")["retention_after"])

# statistics / operational
T["SOH_DELTA_SEV_XGB"] = lambda: (lambda d: f"{d['delta']:.2f} [{d['ci'][0]:.2f}, {d['ci'][1]:.2f}]")(j("soh_delta_severson_xgboost_20"))
T["OP_FNR_SEV_WITH"] = lambda: f"{100*j('op_severson_with_soh_raw')['fnr']:.0f}\\%"
T["OP_FPR_SEV_WITH"] = lambda: f"{100*j('op_severson_with_soh_raw')['fpr']:.0f}\\%"
T["OP_FNR_SEV_NO"] = lambda: f"{100*j('op_severson_no_soh_raw')['fnr']:.0f}\\%"
T["OP_FPR_SEV_NO"] = lambda: f"{100*j('op_severson_no_soh_raw')['fpr']:.0f}\\%"


def _oper_other(model, fs, col):
    oc = pd.read_csv(os.path.join(RES, "operational_costs.csv"))
    r = oc[(oc.target == "severson") & (oc.model == model) &
           (oc.feature_set == fs) & (oc.method == "raw")]
    return float(r.iloc[0][col])


T["OP_FPR_SEV_WITH_LGBM"] = lambda: f"{100*_oper_other('lightgbm', 'with_soh', 'tgt_fpr'):.0f}\\%"
T["OP_FNR_SEV_WITH_RF"] = lambda: f"{100*_oper_other('random_forest', 'with_soh', 'tgt_fnr'):.0f}\\%"

# ------------------------------------------------- prognosis split (Phase 1)
def _prog(target, source, model, fs):
    d = pd.read_csv(os.path.join(RES, "prognosis_split.csv"))
    r = d[(d.target == target) & (d.source == source) & (d.model == model) &
          (d.fs == fs) & (d.H == 20)]
    if len(r) == 0:
        raise KeyError(f"prognosis_split lacks {target}/{source}/{model}/{fs}")
    return r.iloc[0]


def _prog_pair(target, source="nasa+calce", model="xgboost", fs="with_soh"):
    r = _prog(target, source, model, fs)
    return f"{r['all_auc']:.3f} to {r['prog_auc']:.3f} ({r['frac_above']:.0%} above)"


def _prog_ci(target, source="nasa+calce", model="xgboost", fs="with_soh"):
    r = _prog(target, source, model, fs)
    return f"{r['prog_auc']:.3f} [{r['prog_lo']:.3f}, {r['prog_hi']:.3f}]"


T["TAB_PROGNOSIS"] = lambda: frag("tab_prognosis.tex")
T["PROG_SEV_ALL"] = lambda: f"{_prog('severson', 'nasa+calce', 'xgboost', 'with_soh')['all_auc']:.3f}"
T["PROG_SEV"] = lambda: _prog_ci("severson")
T["PROG_SEV_NO_ALL"] = lambda: f"{_prog('severson', 'nasa+calce', 'xgboost', 'no_soh')['all_auc']:.3f}"
T["PROG_SEV_NO"] = lambda: _prog_ci("severson", fs="no_soh")
T["PROG_DIST_ALL"] = lambda: f"{_prog('severson', 'nasa+calce', 'logreg', 'base_soh_dist')['all_auc']:.3f}"
T["PROG_DIST"] = lambda: f"{_prog('severson', 'nasa+calce', 'logreg', 'base_soh_dist')['prog_auc']:.3f}"
T["PROG_HNEI"] = lambda: _prog_pair("ba_nmc_hnei")
T["PROG_NCA"] = lambda: _prog_pair("ba_nca_snl")
T["PROG_NMC"] = lambda: _prog_pair("ba_nmc_snl")
T["PROG_LFP"] = lambda: _prog_pair("ba_lfp_snl")
T["PROG_BA"] = lambda: (lambda vs: f"{min(vs):.2f}--{max(vs):.2f}")([
    _prog(t, "nasa+calce", "xgboost", "with_soh")["prog_auc"]
    for t in ["ba_nmc_hnei", "ba_nca_snl", "ba_nmc_snl", "ba_lfp_snl"]])

# ------------------------------------------------- Battery Archive extension
def _ba(key, default=np.nan):
    v = N.get(key, default)
    if not np.isfinite(v):
        raise KeyError(f"paper_numbers.json lacks key '{key}' (run make_tables_v2 first)")
    return v


def _ba_xfer(fs, key="pooled"):
    """Values of a transfer metric across LCO -> {NCA, NMC, LFP-SNL} configs."""
    vals = []
    for grp in ["ba_nca_snl", "ba_nmc_snl", "ba_nmc_hnei", "ba_lfp_snl"]:
        for m in ["xgboost", "lightgbm", "random_forest"]:
            rec = N.get(f"xfer_ba_{grp}_nasa+calce_{m}_{fs}")
            if rec is not None:
                vals.append(float(rec[key]))
    return vals


def _ba_deltas():
    vals = []
    for grp in ["ba_nca_snl", "ba_nmc_snl", "ba_nmc_hnei", "ba_lfp_snl"]:
        for m in ["xgboost", "lightgbm", "random_forest"]:
            rec = N.get(f"xfer_ba_delta_{grp}_{m}")
            if rec is not None:
                vals.append(float(rec["delta"]))
    return vals


def _rng(vals, nd=2, space=","):
    vals = [v for v in vals if np.isfinite(v)]
    if not vals:
        return "---"
    return f"{min(vals):.{nd}f}{space}{max(vals):.{nd}f}"


N_BA_WORDS = {15: "15", 18: "18", 21: "21", 60: "60", 106787: "106\\,787"}

T["N_DATASETS"] = lambda: "eight"
T["N_CHEM"] = lambda: "four"
T["BA_CELLS_TOTAL"] = lambda: str(int(_ba("ba_cells_total")))
T["BA_CELLS_NMC"] = lambda: str(int(_ba("ba_cells_ba_nmc_hnei") + _ba("ba_cells_ba_nmc_snl")))
T["BA_CELLS_HNEI"] = lambda: str(int(_ba("ba_cells_ba_nmc_hnei")))
T["BA_CELLS_NMCSNL"] = lambda: str(int(_ba("ba_cells_ba_nmc_snl")))
T["BA_CELLS_AUDIT"] = lambda: str(int(_ba("ba_cells_total") + _ba("ba_cells_excluded")))
T["BA_VOLT_FIRST"] = lambda: str(int(_ba("ba_volt_first")))
T["BA_CELLS_NCA"] = lambda: str(int(_ba("ba_cells_ba_nca_snl")))
T["BA_CELLS_LFP"] = lambda: str(int(_ba("ba_cells_ba_lfp_snl")))
T["BA_CELLS_EXCLUDED"] = lambda: str(int(_ba("ba_cells_excluded")))
T["BA_ROWS_TOTAL"] = lambda: N_BA_WORDS.get(int(_ba("ba_rows_total")),
                                            f"{int(_ba('ba_rows_total')):,}".replace(",", "\\,"))
T["BA_CYC_NMC"] = lambda: _rng([_ba("ba_cycles_min_ba_nmc_hnei"),
                                _ba("ba_cycles_max_ba_nmc_hnei"),
                                _ba("ba_cycles_min_ba_nmc_snl"),
                                _ba("ba_cycles_max_ba_nmc_snl")], nd=0, space="--")
T["BA_CYC_NMC_HNEI"] = lambda: _rng([_ba("ba_cycles_min_ba_nmc_hnei"),
                                     _ba("ba_cycles_max_ba_nmc_hnei")], nd=0, space="--")
T["BA_CYC_NMC_SNL"] = lambda: _rng([_ba("ba_cycles_min_ba_nmc_snl"),
                                    _ba("ba_cycles_max_ba_nmc_snl")], nd=0, space="--")
T["BA_CYC_NCA"] = lambda: _rng([_ba("ba_cycles_min_ba_nca_snl"),
                                _ba("ba_cycles_max_ba_nca_snl")], nd=0, space="--")
T["BA_CYC_LFP"] = lambda: _rng([_ba("ba_cycles_min_ba_lfp_snl"),
                                _ba("ba_cycles_max_ba_lfp_snl")], nd=0, space="--")
T["BA_EOL_CELLS"] = lambda: str(int(sum(float(_ba(f"ba_eol_cells_{g}")) for g in
                                        ["ba_nmc_hnei", "ba_nca_snl", "ba_nmc_snl",
                                         "ba_lfp_snl"])))
T["BA_EOL_LFP"] = lambda: str(int(_ba("ba_eol_cells_ba_lfp_snl")))
T["BA_PREV_NMC"] = lambda: f"{0.5*(float(_ba('ba_prev_ba_nmc_hnei_H20')) + float(_ba('ba_prev_ba_nmc_snl_H20'))):.2f}"
T["BA_PREV_NCA"] = lambda: f"{float(_ba('ba_prev_ba_nca_snl_H20')):.2f}"
T["BA_PREV_LFP"] = lambda: f"{float(_ba('ba_prev_ba_lfp_snl_H20')):.3f}"

T["WITHIN_BA_TOTAL"] = lambda: str(int(_ba("within_ba_ge085")))
T["WITHIN_BA_COMBOS"] = lambda: str(int(_ba("within_ba_total")))
T["WITHIN_BA_GE085"] = lambda: str(int(_ba("within_ba_ge085")))
T["WITHIN_BA_RANGE"] = lambda: _rng([_ba(f"within_ba_{g}_{m}_min", np.nan)
                                     for g in ["ba_nca_snl", "ba_nmc_snl",
                                               "ba_nmc_hnei", "ba_lfp_snl"]
                                     for m in ["xgboost", "lightgbm",
                                               "random_forest"]],
                                    nd=2, space="--")
T["XFER_BA_WITH"] = lambda: _rng(_ba_xfer("with_soh"), nd=2, space="--")
T["XFER_BA_NO"] = lambda: _rng(_ba_xfer("no_soh"), nd=2, space="--")
T["XFER_BA_COMMON_NO"] = lambda: _rng(_ba_xfer("common_no_soh"), nd=2, space="--")
T["XFER_BA_DELTA"] = lambda: _rng(_ba_deltas(), nd=2, space="--")
T["XFER_BA_DELTA_MIN"] = lambda: f"{min(_ba_deltas() or [np.nan]):+.2f}"
T["COND_DROP_WITH_MAX"] = lambda: f"{float(_ba('condshift_drop_with_max')):.2f}"
T["COND_DROP_NO_MAX"] = lambda: f"{float(_ba('condshift_drop_no_max')):.2f}"
T["COND_NCA_TEMPRATE"] = lambda: f"{float(_ba('condshift_ba_nca_snl_temp_rate_with_soh')):.2f}"
T["COND_NCA_TEMPRATE_NO"] = lambda: f"{float(_ba('condshift_ba_nca_snl_temp_rate_no_soh')):.2f}"
T["COND_NCA_REF"] = lambda: f"{float(_ba('condshift_ref_ba_nca_snl_with_soh')):.2f}"
T["COND_NMC_TEMPRATE"] = lambda: f"{float(_ba('condshift_ba_nmc_snl_temp_rate_with_soh')):.2f}"
T["COND_NMC_TEMPRATE_NO"] = lambda: f"{float(_ba('condshift_ba_nmc_snl_temp_rate_no_soh')):.2f}"
T["COND_DIST_MIN"] = lambda: f"{float(_ba('condshift_dist_min')):.3f}"
T["COND_DIST_MAX"] = lambda: f"{float(_ba('condshift_dist_max')):.3f}"
T["COND_NMC_MIXED"] = lambda: f"{float(_ba('condshift_ref_ba_nmc_snl_with_soh')):.2f}"
T["BA_WITHIN_NMC_MIN"] = lambda: f"{float(_ba('within_ba_ba_nmc_snl_xgboost_min')):.2f}"
T["SAME_LAB_NCA_NMC_WITH"] = lambda: f"{float(_ba('samechem_ba_ba_nca_snl_ba_nmc_snl_with_soh')):.2f}"
T["SAME_LAB_NCA_NMC_NO"] = lambda: f"{float(_ba('samechem_ba_ba_nca_snl_ba_nmc_snl_no_soh')):.2f}"
T["SAME_CHEM_LFP_SNL_SEV_WITH"] = lambda: f"{float(_ba('samechem_ba_ba_lfp_snl_severson_with_soh')):.2f}"
T["SAME_CHEM_LFP_SNL_SEV_NO"] = lambda: f"{float(_ba('samechem_ba_ba_lfp_snl_severson_no_soh')):.2f}"


def main():
    text = open(os.path.join(ROOT, "paper", "paper_v2_template_part1.tex")).read() + \
        open(os.path.join(ROOT, "paper", "paper_v2_template_part2.tex")).read()
    tokens = set(re.findall(r"@@([A-Z_0-9]+)@@", text))
    missing = [t for t in sorted(tokens) if t not in T]
    if missing:
        print("NO FILL RULE FOR TOKENS:", missing)
        sys.exit(1)
    for t in sorted(tokens):
        try:
            text = text.replace(f"@@{t}@@", T[t]())
        except Exception as e:
            print(f"FAILED to fill {t}: {e}")
            sys.exit(1)
    leftover = re.findall(r"@@[A-Z_0-9]+@@", text)
    if leftover:
        print("LEFTOVER TOKENS:", leftover)
        sys.exit(1)
    out = os.path.join(PAPER, "main_access.tex")
    open(out, "w").write(text)
    print(f"wrote {out} ({len(text)} bytes, all {len(tokens)} tokens filled)")


if __name__ == "__main__":
    main()
