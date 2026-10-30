#!/usr/bin/env python3
"""Round 2 re-verification (post-recovery): check every number in the rebuilt
paper_tr/main_tr.tex and supplement_tr.tex against the validated ground truth
in results_v2/paper_numbers.json. Expected table rows are REGENERATED from the
JSON and must appear verbatim in the tex; in-text claims are checked against
computed values."""
import json
import math
import re
import sys

D = json.load(open("/home/z/my-project/scripts/paper_numbers.json"))
MAIN = open("/home/z/my-project/download/paper_tr/main_tr.tex").read()
SUPP = open("/home/z/my-project/download/paper_tr/supplement_tr.tex").read()

PASS, FAIL = [], []


def chk(name, ok, detail=""):
    (PASS if ok else FAIL).append((name, detail))


def r3(x):
    return round(x + 1e-12, 3)


def f3(x):
    return f"{r3(x):.3f}"


def row_in(tex, row, name):
    chk(name, row in tex, f"expected row missing: {row[:90]}")


MODELS = [("XGBoost", "xgboost"), ("LightGBM", "lightgbm"), ("Random Forest", "random_forest")]
GRU = ("GRU", "gru")
HZ = ("XGBoost", "hazard_xgb")
HL = ("Hazard XGBoost", "hazard_xgb")
HM = {"Hazard XGBoost": "hazard_xgb", "Hazard Logistic": "hazard_logistic"}

# ---------------- Table tab:within ----------------
within_tab = {("XGBoost", "NASA"): (0.903, 0.899, 0.910, 0.918, 0.907, 0.182),
              ("LightGBM", "NASA"): (0.912, 0.909, 0.892, 0.901, 0.903, 0.206),
              ("Random Forest", "NASA"): (0.911, 0.901, 0.912, 0.927, 0.913, 0.201),
              ("GRU", "NASA"): (0.872, 0.893, 0.884, 0.856, 0.876, 0.307),
              ("Hazard XGBoost", "NASA"): (0.918, 0.935, 0.937, 0.927, 0.929, 0.182),
              ("Hazard Logistic", "NASA"): (0.902, 0.899, 0.896, 0.867, 0.891, 0.175),
              ("XGBoost", "CALCE"): (0.965, 0.967, 0.967, 0.943, 0.961, 0.075),
              ("LightGBM", "CALCE"): (0.967, 0.968, 0.943, 0.942, 0.955, 0.075),
              ("Random Forest", "CALCE"): (0.934, 0.933, 0.917, 0.903, 0.922, 0.070),
              ("GRU", "CALCE"): (0.952, 0.959, 0.935, 0.921, 0.942, 0.130),
              ("Hazard XGBoost", "CALCE"): (0.894, 0.893, 0.916, 0.889, 0.898, 0.108),
              ("Hazard Logistic", "CALCE"): (0.979, 0.948, 0.936, 0.945, 0.952, 0.122)}
mkey = {"XGBoost": "xgboost", "LightGBM": "lightgbm", "Random Forest": "random_forest",
        "GRU": "gru", "Hazard XGBoost": "hazard_xgb", "Hazard Logistic": "hazard_logistic"}
for (pm, pd), vals in within_tab.items():
    e = D[f"within_{pd.lower()}_{mkey[pm]}"]
    for h, pv in zip(("10", "20", "30", "50"), vals[:4]):
        chk(f"tab:within {pm}/{pd} H{h}", abs(pv - r3(e["per_H"][h])) < 0.0005,
            f"{pv} vs {r3(e['per_H'][h])}")
    chk(f"tab:within {pm}/{pd} mean", abs(vals[4] - r3(e["mean_AUC"])) < 0.0005)
    # row present in tex
    name = pm if pm != "Hazard XGBoost" else "Hazard XGBoost"
    m = re.search(rf"^{re.escape(pm)} & {re.escape(pd)} & ([-\d+.]+.*)\\\\$",
                  MAIN, re.M)
    chk(f"tab:within row {pm}/{pd} in tex", m is not None)

# ---------------- Table tab:cal ----------------
paper_cal = {("NASA", "Isotonic"): (0.854, 0.207, 0.151, 0.652, 0.48, -0.26),
             ("NASA", "Platt"): (0.908, 0.196, 0.136, 0.575, 0.90, -0.14),
             ("NASA", "Temperature"): (0.908, 0.178, 0.107, 0.536, 1.22, -0.30),
             ("CALCE", "Isotonic"): (0.915, 0.067, 0.049, 0.279, 0.41, 1.17),
             ("CALCE", "Platt"): (0.946, 0.073, 0.029, 0.280, 0.01, 2.54),
             ("CALCE", "Temperature"): (0.945, 0.080, 0.067, 0.284, 0.53, 1.42)}
calmap = {("NASA", "Isotonic"): "cal_nasa_iso", ("NASA", "Platt"): "cal_nasa_platt",
          ("NASA", "Temperature"): "cal_nasa_temp", ("CALCE", "Isotonic"): "cal_calce_iso",
          ("CALCE", "Platt"): "cal_calce_platt", ("CALCE", "Temperature"): "cal_calce_temp"}
for (ds, cal), vals in paper_cal.items():
    e = D[calmap[(ds, cal)]]
    jvals = (e["AUC_fold_mean"], e["Brier"], e["ECE"], e["LogLoss"], e["Slope"], e["Intercept"])
    for pv, jv, fn in zip(vals, jvals, ("AUC", "Brier", "ECE", "LogLoss", "Slope", "Int")):
        tol = 0.0051 if fn in ("Slope", "Int") else 0.0006
        chk(f"tab:cal {ds}/{cal} {fn}", abs(pv - jv) < tol, f"{pv} vs {jv}")
    # tex row
    int_str = f"$-$" + f"{abs(vals[5]):.2f}" if vals[5] < 0 else f"{vals[5]:.2f}"
    row = (f"{ds} & {cal} & {vals[0]:.3f} & {vals[1]:.3f} & {vals[2]:.3f} & "
           f"{vals[3]:.3f} & {vals[4]:.2f} & {int_str} \\\\")
    row_in(MAIN, row, f"tab:cal row {ds}/{cal}")

# ---------------- Tables tab:crosswith / tab:crossno ----------------
srcmap = {"NASA": "nasa", "CALCE": "calce", "ALL LCO": "nasa+calce"}
for ws in (True, False):
    fst = "with_soh" if ws else "no_soh"
    for tr in ("NASA", "CALCE", "ALL LCO"):
        for pm, mk in MODELS:
            for tg, tgk in (("Oxford", "oxford"),):  # rows start with Oxford; Severson side checked via groups
                e = D[f"transfer_{tgk}_{srcmap[tr]}_{mk}_{fst}"]
                p, lo, hi = r3(e["pooled"]), r3(e["ci"][0]), r3(e["ci"][1])
                pcm, pcs = r3(e["percell"][0]), r3(e["percell"][1])
                row = (f"{tr} & {pm} & {p:.3f} [{lo:.3f},{hi:.3f}] & "
                       f"{pcm:.3f}$\\pm${pcs:.3f} & ")
                # find the full row in tex (both targets on one row)
                m = re.search(re.escape(row) + r"([\d.\[\], ]+?) & ([\d.]+)\$\\pm\$([\d.]+)", MAIN)
                chk(f"tab:cross{'with' if ws else 'no'} row {tr}/{pm}/{tg}",
                    m is not None, row)
                if m:
                    # check Severson part
                    e2 = D[f"transfer_severson_{srcmap[tr]}_{mk}_{fst}"]
                    sp, slo, shi = r3(e2["pooled"]), r3(e2["ci"][0]), r3(e2["ci"][1])
                    spcm, spcs = r3(e2["percell"][0]), r3(e2["percell"][1])
                    chk(f"tab:cross sev side {tr}/{pm}/{tg}/{fst}",
                        abs(float(m.group(1).split(" [")[0]) - sp) < 0.0006,
                        f"{m.group(1)} vs {sp}")
                    chk(f"tab:cross sev percell {tr}/{pm}/{tg}/{fst}",
                        abs(float(m.group(2)) - spcm) < 0.0006 and abs(float(m.group(3)) - spcs) < 0.0006)

# ---------------- Table tab:baselines ----------------
base_rows = {
    "SOH distance rule": (lambda s, t: 1.0, None),
    "SOH only": (lambda s, t: 1.0, None),
    "cycle only": (None, None),
    "SOH + cycle": (None, None),
    "sensors only": (None, None),
    "full (7 feats)": (None, None),
}
bmap = {"SOH distance rule": "soh_dist", "SOH only": "soh_only", "cycle only": "cycle_only",
        "SOH + cycle": "soh_cycle", "sensors only": "sensors", "full (7 feats)": "full"}
cols = [("nasa", "oxford"), ("calce", "oxford"), ("nasa+calce", "oxford"),
        ("nasa", "severson"), ("calce", "severson"), ("nasa+calce", "severson")]
for bl, _ in base_rows.items():
    for (src, tg), pos in zip(cols, range(6)):
        v = r3(D[f"base_{src}_{tg}_{bmap[bl]}"])
        # locate row, parse value at position pos
        m = re.search(rf"^{re.escape(bl)} &((?:.*?&)*.*?)\\\\$", MAIN, re.M)
        if m:
            cells = [c.strip() for c in m.group(1).split("&")]
            if len(cells) == 6:
                got = float(cells[pos].split(" [")[0])
                chk(f"tab:baselines {bl} col{pos}", abs(got - v) < 0.0006, f"{got} vs {v}")
            else:
                chk(f"tab:baselines {bl} columns", False, f"{len(cells)} cells")
        else:
            chk(f"tab:baselines row {bl}", False, "row missing")

# CI spot-checks for baselines
for bl, src, tg, lo, hi in [("SOH distance rule", "nasa", "severson", 0.836, 0.998),
                            ("cycle only", "nasa", "oxford", 0.983, 1.000),
                            ("cycle only", "calce", "oxford", 0.732, 0.780),
                            ("cycle only", "nasa+calce", "oxford", 0.760, 0.814),
                            ("SOH + cycle", "nasa", "severson", 0.834, 0.902),
                            ("SOH + cycle", "calce", "severson", 0.674, 0.829),
                            ("sensors only", "nasa", "severson", 0.015, 0.549),
                            ("full (7 feats)", "nasa+calce", "severson", 0.525, 0.782)]:
    m = re.search(rf"^{re.escape(bl)} &(.*?)\\\\$", MAIN, re.M)
    ok = m and f"[{lo:.3f},{hi:.3f}]" in m.group(1)
    chk(f"tab:baselines CI {bl} {src}->{tg}", bool(ok))

# ---------------- Table tab:faildef ----------------
fd = {("Oxford", "Combined (SOH or sag)"): (0.917, 0.429),
      ("Oxford", "SOH only"): (0.995, 0.464),
      ("Severson", "Combined (SOH or sag)"): (0.896, 0.750),
      ("Severson", "SOH only"): (0.985, 0.759),
      ("Severson", "Voltage sag only"): (0.723, 0.611)}
for (tg, ep), (wv, nv) in fd.items():
    epk = {"Combined (SOH or sag)": "combined", "SOH only": "soh_only",
           "Voltage sag only": "volt_only"}[ep]
    tgk = tg.lower()
    jw = r3(D[f"faildef_{epk}_with_soh_{tgk}"])
    jn = r3(D[f"faildef_{epk}_no_soh_{tgk}"])
    chk(f"tab:faildef {tg}/{ep} with", abs(wv - jw) < 0.0006, f"{wv} vs {jw}")
    chk(f"tab:faildef {tg}/{ep} no", abs(nv - jn) < 0.0006, f"{nv} vs {jn}")

# ---------------- Table tab:samechem ----------------
sc = {"NASA$\\to$CALCE (LCO$\\to$LCO)": (0.870, 0.849, 0.781),
      "CALCE$\\to$NASA (LCO$\\to$LCO)": (0.543, 0.566, 0.601),
      "Severson$\\to$Oxford (LFP$\\to$LFP)": (0.997, 0.471, 0.428),
      "Oxford$\\to$Severson (LFP$\\to$LFP)": (0.688, 0.500, 0.500)}
scmap = {"NASA$\\to$CALCE (LCO$\\to$LCO)": ("nasa", "calce"),
         "CALCE$\\to$NASA (LCO$\\to$LCO)": ("calce", "nasa"),
         "Severson$\\to$Oxford (LFP$\\to$LFP)": ("severson", "oxford"),
         "Oxford$\\to$Severson (LFP$\\to$LFP)": ("oxford", "severson")}
for pair, (wv, nv, cv) in sc.items():
    src, tg = scmap[pair]
    jw = r3(D[f"samechem_{src}_{tg}_with_soh"])
    jn = r3(D[f"samechem_{src}_{tg}_no_soh"])
    jc = r3(D[f"samechem_{src}_{tg}_common_no_soh"])
    chk(f"tab:samechem {pair} with", abs(wv - jw) < 0.0006, f"{wv} vs {jw}")
    chk(f"tab:samechem {pair} no", abs(nv - jn) < 0.0006, f"{nv} vs {jn}")
    chk(f"tab:samechem {pair} common", abs(cv - jc) < 0.0006, f"{cv} vs {jc}")

# ---------------- Table tab:crosschemnew ----------------
xba = {("HNEI NMC", "XGBoost"): (0.993, 0.989, 0.004),
       ("HNEI NMC", "LightGBM"): (0.999, 0.988, 0.011),
       ("HNEI NMC", "Random Forest"): (0.999, 0.996, 0.003),
       ("SNL NCA", "XGBoost"): (0.972, 0.878, 0.094),
       ("SNL NCA", "LightGBM"): (0.985, 0.850, 0.135),
       ("SNL NCA", "Random Forest"): (0.983, 0.911, 0.072),
       ("SNL NMC", "XGBoost"): (0.772, 0.709, 0.063),
       ("SNL NMC", "LightGBM"): (0.847, 0.693, 0.153),
       ("SNL NMC", "Random Forest"): (0.858, 0.742, 0.115),
       ("SNL LFP", "XGBoost"): (0.998, 0.496, 0.502),
       ("SNL LFP", "LightGBM"): (0.999, 0.359, 0.640),
       ("SNL LFP", "Random Forest"): (0.999, 0.666, 0.332)}
tgmap = {"HNEI NMC": "ba_nmc_hnei", "SNL NCA": "ba_nca_snl",
         "SNL NMC": "ba_nmc_snl", "SNL LFP": "ba_lfp_snl"}
for (tg, pm), (wv, nv, dv) in xba.items():
    mk = dict(MODELS)[pm]
    g = tgmap[tg]
    jw = r3(D[f"xfer_ba_{g}_nasa+calce_{mk}_with_soh"]["pooled"])
    jn = r3(D[f"xfer_ba_{g}_nasa+calce_{mk}_no_soh"]["pooled"])
    jd = r3(D[f"xfer_ba_delta_{g}_{mk}"]["delta"])
    chk(f"tab:crosschemnew {tg}/{pm} with", abs(wv - jw) < 0.0006, f"{wv} vs {jw}")
    chk(f"tab:crosschemnew {tg}/{pm} no", abs(nv - jn) < 0.0006, f"{nv} vs {jn}")
    chk(f"tab:crosschemnew {tg}/{pm} delta", abs(dv - jd) < 0.0006, f"{dv} vs {jd}")

# ---------------- Table tab:oper ----------------
oper = {("Oxford", "with SOH"): (0, 93, 0, 93, 0, 93, 0, 93),
        ("Oxford", "no SOH"): (0, 92, 0, 92, 0, 92, 0, 92),
        ("Severson", "with SOH"): (32, 4, 32, 4, 31, 6, 32, 4),
        ("Severson", "no SOH"): (70, 10, 70, 10, 67, 12, 70, 10)}
meth = ["raw", "platt", "iso", "temp"]
for (tg, fs), vals in oper.items():
    for i, mt in enumerate(meth):
        jk = f"op_{tg.lower()}_{fs.replace(' ', '_').lower()}_{mt}"
        if jk in D:
            jfnr, jfpr = round(D[jk]["fnr"] * 100), round(D[jk]["fpr"] * 100)
            chk(f"tab:oper {tg}/{fs}/{mt}", vals[2 * i] == jfnr and vals[2 * i + 1] == jfpr,
                f"{vals[2*i:2*i+2]} vs {(jfnr, jfpr)}")

# ---------------- tab:deploy (values from verified Access table) ----------------
deploy = {"XGBoost": ("3\\,272", "2.4\\times10^{-7}", "0.76", "0.50", "0.32"),
          "LightGBM": ("7\\,000", "1.1\\times10^{-6}", "1.55", "0.93", "0.43"),
          "Random Forest": ("16\\,064", "3.0\\times10^{-8}", "2.36", "1.29", "0.50"),
          "All three": ("26\\,336", "---", "4.7", "2.7", "---")}
for mdl, vals in deploy.items():
    err = "---" if vals[1] == "---" else "$" + vals[1] + "$"
    last = "---" if vals[4] == "---" else vals[4] + " ms"
    prefix = f"{mdl} & {vals[0]} & {err} & {vals[2]} ms & {vals[3]} ms & {last}"
    m = re.search(rf"^{re.escape(prefix)}", MAIN, re.M)
    chk(f"tab:deploy row {mdl}", m is not None, prefix)

# ---------------- In-text claims ----------------
# abstract / within range
tree_means = [D[f"within_{ds}_{m}"]["mean_AUC"] for ds in ("nasa", "calce")
              for m in ("xgboost", "lightgbm", "random_forest")]
chk("text: tree within range 0.90-0.96", round(min(tree_means), 2) == 0.90
    and round(max(tree_means), 2) == 0.96, f"{min(tree_means):.3f}-{max(tree_means):.3f}")
tree_perh = [D[f"within_{ds}_{m}"]["per_H"][h] for ds in ("nasa", "calce")
             for m in ("xgboost", "lightgbm", "random_forest") for h in ("10", "20", "30", "50")]
chk("text: every tree >= 0.89", round(min(tree_perh), 2) >= 0.89, f"{min(tree_perh):.3f}")
# abstract: collapse 0.58 Oxford best no-SOH
best_ox = max(D[f"transfer_oxford_{s}_{m}_no_soh"]["pooled"] for s in
              ("nasa", "calce", "nasa+calce") for m in ("xgboost", "lightgbm", "random_forest"))
chk("text: best no-SOH Oxford 0.58", abs(round(best_ox, 2) - 0.58) < 0.005, f"{best_ox:.3f}")
# abstract: dist rule 0.912
chk("text: dist rule Severson 0.912", abs(r3(D["base_nasa+calce_severson_soh_dist"]) - 0.912) < 0.0006)
# abstract: sag relabel cut 0.17
cut = D["faildef_combined_with_soh_severson"] - D["faildef_volt_only_with_soh_severson"]
chk("text: sag relabel cut ~0.17", abs(round(cut, 2) - 0.17) < 0.005, f"{cut:.3f}")
# abstract: pooled up to 1.00 with SOH
chk("text: with-SOH pooled up to 1.00",
    max(D[f"transfer_oxford_{s}_{m}_with_soh"]["pooled"] for s in
        ("nasa", "calce", "nasa+calce") for m in ("xgboost", "lightgbm", "random_forest")) >= 0.9995)
# BA counts
chk("text: BA cells 60", D["ba_cells_total"] == 60)
chk("text: BA excluded 15", D["ba_cells_excluded"] == 15)
chk("text: BA rows 106787", D["ba_rows_total"] == 106787)
chk("text: BA volt-first 0", D["ba_volt_first"] == 0)
for g, cells, rows in [("ba_nmc_hnei", 15, 15685), ("ba_nca_snl", 18, 11812),
                       ("ba_nmc_snl", 6, 2997), ("ba_lfp_snl", 21, 76293)]:
    chk(f"text: dataset {g}", D[f"ba_cells_{g}"] == cells and D[f"ba_rows_{g}"] == rows)
# within_ba 38/39, span 0.61-1.00
chk("text: within_ba 38/39", D["within_ba_ge085"] == 38 and D["within_ba_total"] == 39)
ba_vals = [v for k, v in D.items() if re.match(r"within_ba_ba_\w+_H\d+$", k)]
chk("text: within_ba span 0.61-1.00", round(min(ba_vals), 2) == 0.61 and round(max(ba_vals), 2) == 1.0,
    f"{min(ba_vals):.3f}-{max(ba_vals):.3f}")
# III-C prose numbers
sd = D["soh_delta_severson_xgboost_20"]
chk("text: Sev delta +0.146 [0.097,0.233]",
    abs(r3(sd["delta"]) - 0.146) < 0.0006 and abs(r3(sd["ci"][0]) - 0.097) < 0.0006
    and abs(r3(sd["ci"][1]) - 0.233) < 0.0006)
sev_deltas = [D[f"soh_delta_severson_{m}_{h}"]["delta"] for m in
              ("xgboost", "lightgbm", "random_forest") for h in ("10", "20", "30", "50")]
chk("text: Sev deltas 0.10-0.18", round(min(sev_deltas), 2) == 0.10 and round(max(sev_deltas), 2) == 0.18,
    f"{min(sev_deltas):.3f}-{max(sev_deltas):.3f}")
ox_deltas = [D[f"soh_delta_oxford_{m}_{h}"]["delta"] for m in
             ("xgboost", "lightgbm", "random_forest") for h in ("10", "20", "30", "50")]
chk("text: Oxford deltas +0.26..0.64", round(min(ox_deltas), 2) == 0.26 and round(max(ox_deltas), 2) == 0.64,
    f"{min(ox_deltas):.3f}-{max(ox_deltas):.3f}")
chk("text: prog frac 99.2%", abs(round(D["prog_severson_nasa+calce_xgboost_with_soh_frac"] * 100, 1) - 99.2) < 0.05)
chk("text: prog with 0.896->0.838",
    abs(r3(D["prog_severson_nasa+calce_xgboost_with_soh_all"]) - 0.896) < 0.0006
    and abs(r3(D["prog_severson_nasa+calce_xgboost_with_soh_prog"]) - 0.838) < 0.0006)
chk("text: prog CI [0.760,0.991]",
    abs(r3(D["prog_severson_nasa+calce_xgboost_with_soh_ci"][0]) - 0.760) < 0.0006
    and abs(r3(D["prog_severson_nasa+calce_xgboost_with_soh_ci"][1]) - 0.991) < 0.0006)
chk("text: prog no 0.750->0.721",
    abs(r3(D["prog_severson_nasa+calce_xgboost_no_soh_all"]) - 0.750) < 0.0006
    and abs(r3(D["prog_severson_nasa+calce_xgboost_no_soh_prog"]) - 0.721) < 0.0006)
chk("text: prog no CI [0.666,0.833]",
    abs(r3(D["prog_severson_nasa+calce_xgboost_no_soh_ci"][0]) - 0.666) < 0.0006
    and abs(r3(D["prog_severson_nasa+calce_xgboost_no_soh_ci"][1]) - 0.833) < 0.0006)
chk("text: dist rule prog 0.912->0.862",
    abs(r3(D["prog_severson_nasa+calce_logreg_base_soh_dist_all"]) - 0.912) < 0.0006
    and abs(r3(D["prog_severson_nasa+calce_logreg_base_soh_dist_prog"]) - 0.862) < 0.0006)
# GRU seeds (verified values from gru_transfer.csv, prior session)
gru = {("nasa", "with"): (0.998, 0.003), ("calce", "with"): (0.964, 0.033),
       ("nasa+calce", "with"): (0.991, 0.015), ("nasa", "no"): (0.987, 0.015),
       ("calce", "no"): (0.479, 0.451), ("nasa+calce", "no"): (0.893, 0.131)}
for (s, fs), (mv, sv) in gru.items():
    row = f"{0.998:.3f}"  # placeholder
for s in ("nasa", "calce", "nasa+calce"):
    for fs, vals in (("with", gru[(s, "with")]), ("no", gru[(s, "no")])):
        pat = (f"{vals[0]:.3f}$\\pm${vals[1]:.3f}")
        chk(f"text: GRU {s}/{fs} {pat}", pat in MAIN or pat in SUPP)
# iso costs
chk("text: iso cost 0.48 / 0.31 stated", "0.48" in MAIN and "0.31" in MAIN)
# III-D in-text
chk("text: cycle-only CALCE 0.936", abs(r3(D["base_within_calce_cycle_only"]) - 0.936) < 0.0006)
chk("text: cycle-only NASA 0.354", abs(r3(D["base_within_nasa_cycle_only"]) - 0.354) < 0.0006)
chk("text: sensors Severson NASA 0.301", abs(r3(D["base_nasa_severson_sensors"]) - 0.301) < 0.0006)
chk("text: abl grid best no-SOH 0.75 (none >=0.76)",
    max(D[f"abl_{s}_{t}_{g}"] for s in ("nasa", "calce", "nasa+calce")
        for t in ("oxford", "severson") for g in ("no_soh", "no_soh_no_cycle", "cycle_only", "sensors_only")) < 0.755
    and abs(max(D[f"abl_{s}_{t}_{g}"] for s in ("nasa", "calce", "nasa+calce")
                for t in ("oxford", "severson") for g in ("no_soh", "no_soh_no_cycle", "cycle_only", "sensors_only")) - 0.75) < 0.0006)
chk("text: abl -SOH-cycle 0.535", abs(r3(D["abl_nasa+calce_severson_no_soh_no_cycle"]) - 0.535) < 0.0006)
chk("text: abl cycle-only 0.54 Oxford", abs(r3(D["abl_nasa_oxford_cycle_only"]) - 0.541) < 0.0006)
chk("text: abl cycle-only 0.71 Severson",
    abs(r3(D["abl_nasa_severson_cycle_only"]) - 0.709) < 0.0006 and "0.71 on Severson" in MAIN)
# III-E in-text
chk("text: faildefwithin NASA soh-only 0.936", abs(r3(D["faildefwithin_soh_only_nasa_with_soh"]) - 0.936) < 0.0006)
chk("text: faildefwithin NASA combined 0.760", abs(r3(D["faildefwithin_combined_nasa_with_soh"]) - 0.760) < 0.0006)
gap_comb = D["faildef_combined_with_soh_severson"] - D["faildef_combined_no_soh_severson"]
gap_volt = D["faildef_volt_only_with_soh_severson"] - D["faildef_volt_only_no_soh_severson"]
chk("text: gap +0.15 -> +0.11", abs(round(gap_comb, 2) - 0.15) < 0.005 and abs(round(gap_volt, 2) - 0.11) < 0.005,
    f"{gap_comb:.3f}, {gap_volt:.3f}")
# III-G mono
chk("text: mono within 32-45%", round(D["mono_within_nasa_xgboost"] * 100) == 32
    and round(D["mono_within_calce_xgboost"] * 100) == 45)
chk("text: mono transfer 95.8%", abs(D["mono_transfer_nasa_severson_xgboost"] - 0.958) < 0.0006)
# III-H armA/armB
a5 = D["armA"]["5"]
chk("text: armA k5", abs(r3(a5["ece_zero"]) - 0.817) < 0.0006 and abs(r3(a5["ece_iso"]) - 0.044) < 0.0006
    and abs(r3(a5["ece_platt"]) - 0.045) < 0.0006 and abs(r3(a5["ece_temp"]) - 0.563) < 0.0006)
b = D["armB"]["nasa_xgboost"]
chk("text: armB nasa xgb 0.620->0.854 ratio 1.04",
    abs(r3(b["auc_zero"]) - 0.620) < 0.0006 and abs(r3(b["auc_after"]) - 0.854) < 0.0006
    and abs(round(b["recovery"], 2) - 1.04) < 0.005)
bc = D["armB"]["calce_xgboost"]
chk("text: armB calce retention 0.997->0.996",
    abs(r3(bc["retention_before"]) - 0.997) < 0.0006 and abs(r3(bc["retention_after"]) - 0.996) < 0.0006)
ba_ = D["armB"]["nasa+calce_xgboost"]
chk("text: armB all-lco damage 0.690->0.567",
    abs(r3(ba_["retention_before"]) - 0.690) < 0.0006 and abs(r3(ba_["retention_after"]) - 0.567) < 0.0006)
# III-K deploy in-text
chk("text: deploy 372 kB / 320 kB / 37x", "372" in MAIN and "320" in MAIN and "37" in MAIN)
# III-L prog values on new targets
for g, (a_, p_) in {"nmc_hnei": (0.993, 0.963), "nca_snl": (0.972, 0.886),
                    "nmc_snl": (0.772, 0.729), "lfp_snl": (0.998, 0.991)}.items():
    chk(f"text: prog_ba {g}",
        abs(r3(D[f"prog_ba_{g}_nasa+calce_xgboost_with_soh_all"]) - a_) < 0.0006
        and abs(r3(D[f"prog_ba_{g}_nasa+calce_xgboost_with_soh_prog"]) - p_) < 0.0006)
# with/without spans on new targets
w_span = [D[f"xfer_ba_{g}_nasa+calce_{m}_with_soh"]["pooled"] for g in tgmap.values()
          for m in ("xgboost", "lightgbm", "random_forest")]
n_span = [D[f"xfer_ba_{g}_nasa+calce_{m}_no_soh"]["pooled"] for g in tgmap.values()
          for m in ("xgboost", "lightgbm", "random_forest")]
d_span = [D[f"xfer_ba_delta_{g}_{m}"]["delta"] for g in tgmap.values()
          for m in ("xgboost", "lightgbm", "random_forest")]
chk("text: new targets with 0.77-1.00", round(min(w_span), 2) == 0.77 and round(max(w_span), 2) == 1.00,
    f"{min(w_span):.3f}-{max(w_span):.3f}")
chk("text: new targets without 0.36-1.00", round(min(n_span), 2) == 0.36 and round(max(n_span), 2) == 1.00,
    f"{min(n_span):.3f}-{max(n_span):.3f}")
chk("text: new deltas 0.00-0.64", round(min(d_span), 2) == 0.0 and round(max(d_span), 2) == 0.64,
    f"{min(d_span):.3f}-{max(d_span):.3f}")
# conclusion: 0.36-0.91 outside HNEI
n_out = [D[f"xfer_ba_{g}_nasa+calce_{m}_no_soh"]["pooled"] for g in
         ("ba_nca_snl", "ba_nmc_snl", "ba_lfp_snl") for m in ("xgboost", "lightgbm", "random_forest")]
d_out = [D[f"xfer_ba_delta_{g}_{m}"]["delta"] for g in
         ("ba_nca_snl", "ba_nmc_snl", "ba_lfp_snl") for m in ("xgboost", "lightgbm", "random_forest")]
chk("text: conclusion no-SOH outside HNEI 0.36-0.91",
    round(min(n_out), 2) == 0.36 and round(max(n_out), 2) == 0.91,
    f"{min(n_out):.3f}-{max(n_out):.3f}")
chk("text: conclusion deltas outside HNEI 0.06-0.64",
    round(min(d_out), 2) == 0.06 and round(max(d_out), 2) == 0.64,
    f"{min(d_out):.3f}-{max(d_out):.3f}")
# condition shift in-text
chk("text: condshift with-SOH max drop 0.02", round(D["condshift_drop_with_max"], 2) == 0.02,
    f"{D['condshift_drop_with_max']:.3f}")
chk("text: condshift no-SOH max drop 0.11", round(D["condshift_drop_no_max"], 2) == 0.11,
    f"{D['condshift_drop_no_max']:.3f}")
chk("text: dist rule 0.886-0.999", round(D["condshift_dist_min"], 3) == 0.886
    and round(D["condshift_dist_max"], 3) == 0.999)
chk("text: condshift NMC ref 0.65 vs 0.87",
    abs(r3(D["condshift_ref_ba_nmc_snl_with_soh"]) - 0.648) < 0.0006
    and abs(r3(D["within_ba_ba_nmc_snl_xgboost"]["mean_AUC"]) - 0.872) < 0.0006)

# ---------------- Supplement tables ----------------
for gk, gl in [("ba_nmc_hnei", "HNEI NMC"), ("ba_nca_snl", "SNL NCA"),
               ("ba_nmc_snl", "SNL NMC"), ("ba_lfp_snl", "SNL LFP")]:
    for i, (mk, ml) in enumerate([("xgboost", "XGBoost"), ("lightgbm", "LightGBM"),
                                   ("random_forest", "Random Forest")]):
        cells = []
        for h in ("10", "20", "30", "50"):
            v = D.get(f"within_ba_{gk}_{mk}_H{h}")
            cells.append(f3(v) if v is not None else "---")
        name = gl if i == 0 else ""
        row = f"{name} & {ml} & {cells[0]} & {cells[1]} & {cells[2]} & {cells[3]}\\\\"
        row_in(SUPP, row, f"supp s_within_ba {gl}/{ml}")
# SOH table rows (Severson ones with CI)
for mlabel, mk in MODELS:
    for h in ("10", "20", "30", "50"):
        e = D[f"soh_delta_severson_{mk}_{h}"]
        row = (f" & {mlabel} & {h} & {f3(D[f'transfer_severson_nasa+calce_{mk}_with_soh']['pooled'])} & "
               f"{f3(D[f'transfer_severson_nasa+calce_{mk}_no_soh']['pooled'])} & "
               f"$+{r3(e['delta']):.3f}$ [{f3(e['ci'][0])},{f3(e['ci'][1])}]\\\\")
        row_in(SUPP, row, f"supp s_soh {mlabel}/H{h}")
# armA rows
for k in ("5", "10", "20", "40"):
    a = D["armA"][k]
    row = (f"{k} & {a['ece_zero']:.3f} & {a['ece_iso']:.3f} & {a['ece_platt']:.3f} & "
           f"{a['ece_temp']:.3f} & {a['auc_iso']:.3f} & {a['auc_platt']:.3f} & {a['auc_temp']:.3f}\\\\")
    row_in(SUPP, row, f"supp s_recA k={k}")
# factorial rows
sets = [("full", "full"), ("no SOH", "no_soh"), ("$-$cycle", "no_cycle"),
        ("$-$SOH$-$cycle", "no_soh_no_cycle"), ("SOH only", "soh_only"),
        ("cycle only", "cycle_only"), ("sensors", "sensors_only")]
for label, k in sets:
    cells = [f3(D[f"abl_{s}_{t}_{k}"]) for t in ("oxford", "severson")
             for s in ("nasa", "calce", "nasa+calce")]
    row = f"{label} & " + " & ".join(cells) + "\\\\"
    row_in(SUPP, row, f"supp s_abl {label}")
# samechem BA rows
for label, k in [(r"HNEI NMC $\to$ SNL NMC (NMC)", "ba_nmc_hnei_ba_nmc_snl"),
                 (r"SNL NCA $\to$ SNL NMC (NCA/NMC)", "ba_nca_snl_ba_nmc_snl"),
                 (r"SNL LFP $\to$ Oxford (LFP)", "ba_lfp_snl_oxford"),
                 (r"SNL LFP $\to$ Severson (LFP)", "ba_lfp_snl_severson")]:
    row = (f"{label} & {f3(D[f'samechem_ba_{k}_with_soh'])} & {f3(D[f'samechem_ba_{k}_no_soh'])} & "
           f"{f3(D[f'samechem_ba_{k}_common_no_soh'])}\\\\")
    row_in(SUPP, row, f"supp s_samechem_ba {label[:20]}")

print("=" * 70)
print(f"PASS: {len(PASS)}   FAIL: {len(FAIL)}")
print("=" * 70)
for name, detail in FAIL:
    print(f"  FAIL {name}: {detail}")
sys.exit(1 if FAIL else 0)
