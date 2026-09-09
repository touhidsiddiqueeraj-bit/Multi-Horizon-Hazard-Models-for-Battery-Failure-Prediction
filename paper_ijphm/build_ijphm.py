"""Build paper_ijphm/main.tex from paper_ieee_access/main_access.tex:
remove the embedded-prototype material, convert to IJPHM (PHMSociety)
format with APA citations, arabic sections, license footnote."""
import re
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
BS = chr(92)
src = open(os.path.join(ROOT, "..", "paper_ieee_access", "main_access.tex")).read()

# ---------------------------------------------------------------- remove blocks
def cut_between(s, start_marker, end_marker):
    a = s.index(start_marker)
    b = s.index(end_marker, a)
    return s[:a] + s[b:]

src = cut_between(src, "\\subsection{Embedded Deployment Architecture}", "\\section{Results}")
src = cut_between(src, "\\subsection{Embedded Deployment Validation}", "\\section{Discussion")

def drop_float(s, marker):
    a = s.find(marker)
    if a == -1:
        return s
    b = s.rfind("\\begin{", 0, a)
    e = s.find("\\end{", a)
    e = s.find("}", e) + 1
    return s[:b] + s[e:]

for marker in ["\\label{tab:deploy}", "\\label{fig:deploy}",
               "\\label{fig:pyc}", "\\label{fig:circuit}"]:
    while marker in src:
        src = drop_float(src, marker)

# ---------------------------------------------------------------- preamble
PREAMBLE = r"""% IJPHM submission -- International Journal of Prognostics and Health Management
% Built from the IEEE Access manuscript; the embedded-prototype material
% (hardware deployment, on-device validation) has been removed in full.
\documentclass[IJPHM, 2014, 00]{PHMSociety}

\usepackage{graphicx}
\usepackage{amsmath}
\usepackage{booktabs}
\setlength{\emergencystretch}{2em}
\binoppenalty=9000
\relpenalty=700

\graphicspath{{figs/}{../paper_ieee_access/figs/}}

\begin{document}

% Paper Title
\title{Multi-Horizon Failure-Risk Models for Battery Failure Prediction: How Much Cross-Chemistry Transfer Is a State-of-Health Shortcut?}

% Authors List
\author{%
	Hussain Touhid Siddiquee\authorNumber{1}, Jasimul Islam Chowdhury\authorNumber{2}, Farzana Hoque Eshica\authorNumber{3}, and Syeda Salsabil Islam Ariya\authorNumber{4}
}

% Author Affiliations
\address{%
	\affiliation{{1,2,3,4}}{Affiliation 1, City, State, Zip Code, Country}{ %
		{\email{touhidsiddiqueeraj@gmail.com}}\\
		{\email{chowdhuryjasimul@gmail.com}}\\
		{\email{ishicafhaque@gmail.com}}\\
		{\email{salsabil.ariyaa@gmail.com}}
		}
}

\maketitle
\pagestyle{fancy}
\thispagestyle{plain}

\phmLicenseFootnote{Hussain Touhid Siddiquee}

"""

# body: everything from \begin{abstract} to \end{document} of the journal source
a = src.index("\\begin{abstract}")
b = src.rindex("\\end{document}")
body = src[a:b]

# ---------------------------------------------------------------- abstract fix
body = re.sub(
    r"The truncation-prone isotonic calibrator.*?1~028 validation rows\.",
    "The truncation-prone isotonic calibrator largely fails to transfer, and "
    "cell-level bootstrap intervals replace cycle-level significance tests as "
    "the primary evidence. On the modeling side, a discrete-time hazard "
    "formulation restores the monotone risk-coherence that independent "
    "fixed-horizon classifiers lack.",
    body, flags=re.S)
body = body.replace("\\$H{=}20\\$", "$H{=}20$")

# ---------------------------------------------------------------- keywords
body = re.sub(
    r"\\begin\{keywords\}.*?\\end\{keywords\}",
    lambda m: (
        "\\medskip\\noindent\\textit{Keywords---}battery failure prediction, "
        "multi-horizon failure-risk classification, state-of-health shortcut, "
        "cross-chemistry transfer, dataset shift, probability calibration, "
        "discrete-time hazard model, SHAP."),
    body, flags=re.S)

# ---------------------------------------------------------------- drop journal title machinery
body = body.replace("\\titlepgskip=-21pt\n", "")
body = body.replace("\\maketitle\n", "")
body = body.replace("\\emergencystretch=6em\n", "")
body = re.sub(r"\\makeatletter\\def\\UrlBreaks\{[^}]*\}\\makeatother\n", "", body)

# ---------------------------------------------------------------- deployment leftovers
body = body.replace(
    ", discrete-time hazard model, calibration under shift, embedded deployment",
    ", discrete-time hazard model, calibration under shift")
dep_item = re.compile(
    r"\\item a complete embedded deployment that packs all three ensembles into "
    r"one flat binary and runs them on an ESP32-S3 through a hand-written C tree "
    r"walker\.?\n?")
body = dep_item.sub("", body)
body = body.replace(
    " On explainability and deployment, TreeSHAP",
    " On explainability, TreeSHAP")
body = body.replace(
    " while edge inference removes latency, connectivity requirements, and "
    "privacy concerns.", ".")

# ---------------------------------------------------------------- organization paragraph
body = body.replace(
    "Section~II describes the methodology, including the failure labels and "
    "their endpoints, the datasets, the models including the discrete-time "
    "hazard formulation, the calibration and transfer protocols, and the "
    "deployment architecture. Section~III presents the experimental results. "
    "Section~IV discusses the analysis, implications, and limitations, and "
    "Section~V concludes.",
    "Section~2 describes the methodology, including the failure labels and "
    "their endpoints, the datasets, the models including the discrete-time "
    "hazard formulation, and the calibration and transfer protocols. "
    "Section~3 presents the experimental results. Section~4 discusses the "
    "analysis, implications, and limitations, and Section~5 concludes.")

# ---------------------------------------------------------------- conclusion deployment fragments
body = body.replace(
    " and a discrete-time hazard formulation that matches the fixed-horizon "
    "classifiers while keeping cumulative risks monotone in the horizon."
    "1\\times10^{-6}$ on a \\$12 ESP32-S3.",
    " and a discrete-time hazard formulation that matches the fixed-horizon "
    "classifiers while keeping cumulative risks monotone in the horizon.")
body = re.sub(r"\.1\\times10\^\{-6\}\$ on a \\\$12 ESP32-S3\.", ".", body)

# ---------------------------------------------------------------- prototype leftovers
body = body.replace(
    " That work left three gaps open.", " That work left two gaps open.")
body = body.replace(
    " Third, no path existed from a Python research prototype to the "
    "microcontroller where a battery management system actually runs.", "")
body = body.replace(
    ", and run on a \\$12 microcontroller in under a millisecond.", ".")
body = body.replace(
    "are reliable , with fold-mean AUC of 0.89 and above under Platt "
    "calibration, and run on a \\$12 microcontroller in under a "
    "millisecond.", "are reliable, with fold-mean AUC of 0.89 and above "
    "under Platt calibration.")
body = re.sub(r" and a 372~kB embedded deployment[^.]*\.", ".", body)

# ---------------------------------------------------------------- section cross-refs -> arabic
SECMAP = {
    "Sections~III-F and~III-G": "Sections 3.6 and 3.7",
    "Section~II-B": "Section~2.2", "Section~II-G": "Section~2.7",
    "Section~II-J": "Section~2.10", "Section~II-E": "Section~2.5",
    "Sections~III-C--III-G": "Sections~3.3--3.7",
    "Sections~III-C": "Sections~3.3", "Sections~III-F": "Sections~3.6",
    "Section~III-C": "Section~3.3", "Section~III-D": "Section~3.4",
    "Section~III-E": "Section~3.5", "Section~III-F": "Section~3.6",
    "Section~III-G": "Section~3.7", "Section~III-K": "Section~3.11",
    "Section~III-J": "Section~3.10", "Section~III-I": "Section~3.9", "Section~III-H": "Section~3.8",
    "Section~II-D": "Section~2.4", "Section~II-F": "Section~2.6",
    "Section~II-C": "Section~2.3", "Section~II-A": "Section~2.1",
}
for k, v in SECMAP.items():
    body = body.replace(k, v)
body = re.sub(r"Section[s]?~II-[A-Z]", "Section~2.x", body)
body = re.sub(r"Section[s]?~III-[A-Z]", "Section~3.x", body)

# ---------------------------------------------------------------- dashes pass 2
DASHES2 = [
 ("reliability analysis of probability calibration under shift --- Platt, isotonic, and temperature scaling, all fitted on out-of-fold source scores --- including recalibration",
  "reliability analysis of probability calibration under shift (Platt, isotonic, and temperature scaling, all fitted on out-of-fold source scores), including recalibration"),
 ("the feature set is reduced to the common, unit-safe set --- cycle number, average voltage, minimum voltage, and SOH when enabled --- standardized",
  "the feature set is reduced to the common, unit-safe set (cycle number, average voltage, minimum voltage, and SOH when enabled), standardized"),
 ("the ensembles contribute little beyond reading the health state --- which is precisely",
  "the ensembles contribute little beyond reading the health state, which is precisely"),
 ("One pooled classifier --- XGBoost with the same hyperparameters as above, and a logistic regression --- is fit",
  "One pooled classifier (XGBoost with the same hyperparameters as above, and a logistic regression) is fit"),
 ("stays entirely on one side of every split --- train, calibration, and test are cell-disjoint by construction",
  "stays entirely on one side of every split: train, calibration, and test are cell-disjoint by construction"),
 ("Paired comparisons --- above all with-SOH versus without-SOH --- use the same cell resamples",
  "Paired comparisons (above all with-SOH versus without-SOH) use the same cell resamples"),
 ("with Severson between 0.53 and 0.75 --- and several configurations fall below 0.5, i.e., the remaining",
  "with Severson between 0.53 and 0.75, and several configurations fall below 0.5; the remaining"),
 ("across seeds --- seed-to-seed swings span near-chance to near-oracle, so the model is unstable under shift rather than consistently bad --- against",
  "across seeds (seed-to-seed swings span near-chance to near-oracle, so the model is unstable under shift rather than consistently bad), against"),
 ("is 0.786$\\pm$0.332 across seeds --- seed-to-seed swings span near-chance to near-oracle, so the model is unstable under shift rather than consistently bad --- against 0.984$\\pm$0.02 with SOH",
  "is 0.786$\\pm$0.332 across seeds (seed-to-seed swings span near-chance to near-oracle, so the model is unstable under shift rather than consistently bad), against 0.984$\\pm$0.02 with SOH"),
 ("SOH appears on both sides of the learning problem --- in the feature vector and inside the label definition --- so high",
  "SOH appears on both sides of the learning problem (in the feature vector and inside the label definition), so high"),
 ("at pooled AUC 0.912 [CI] for the ALL-LCO source --- within the confidence range of the tuned ensembles",
  "at pooled AUC 0.912 [CI] for the ALL-LCO source, within the confidence range of the tuned ensembles"),
 ("does not diminish the ensembles' within-dataset value --- there they beat every minimal baseline --- but it does mean",
  "does not diminish the ensembles' within-dataset value, where they beat every minimal baseline, but it does mean"),
 ("Cycle-only is competitive on Oxford --- whose five cells fail at well-separated raw cycle counts, so the cycle index is a between-cell aging proxy --- but the pattern",
  "Cycle-only is competitive on Oxford (whose five cells fail at well-separated raw cycle counts, so the cycle index is a between-cell aging proxy), but the pattern"),
 ("relabels failure by a single endpoint at a time --- SOH $\\le 0.80$ only, voltage sag only, or both --- and repeats",
  "relabels failure by a single endpoint at a time (SOH $\\le 0.80$ only, voltage sag only, or both) and repeats"),
 ("When SOH alone defines failure --- the model is, in effect, reading the label criterion --- transfer to Severson is 0.985",
  "When SOH alone defines failure (the model is, in effect, reading the label criterion), transfer to Severson is 0.985"),
 ("falls to 0.723 --- a drop of roughly a quarter, with the",
  "falls to 0.723, a drop of roughly a quarter, with the"),
 ("the distinction nearly vanishes --- on NASA, under the SOH-defined label, the with-SOH model",
  "the distinction nearly vanishes: on NASA, under the SOH-defined label, the with-SOH model"),
 ("tracks the label at 0.797 --- because within one laboratory the sensor features already",
  "tracks the label at 0.797, because within one laboratory the sensor features already"),
 ("a property of \\emph{dataset shift} --- different laboratories, protocols, and logging conventions --- that chemistry change adds",
  "a property of \\emph{dataset shift} (different laboratories, protocols, and logging conventions), which chemistry change adds"),
 ("inherits the same SOH dependence as everything else --- the formulation of a model does not exempt its inputs from dataset shift --- but it behaves",
  "inherits the same SOH dependence as everything else (the formulation of a model does not exempt its inputs from dataset shift) but it behaves"),
 ("pooled ranking degrades accordingly --- in Table~\\ref{tab:crosswith}, isotonic calibration costs",
  "pooled ranking degrades accordingly: in Table~\\ref{tab:crosswith}, isotonic calibration costs"),
 ("are astronomically small --- and, as Section~2.10 explains, inflated by",
  "are astronomically small and, as Section~2.10 explains, inflated by"),
 ("across three model families, and --- decisively --- on the failure-definition",
  "across three model families and, decisively, on the failure-definition"),
 ("collapses to near-zero SHAP spread --- matching, in the model's internal accounting, the",
  "collapses to near-zero SHAP spread, matching in the model's internal accounting the"),
 ("supports a precise statement --- more precise, and more useful, than the earlier version",
  "supports a precise statement, more precise and more useful than the earlier version"),
 ("a weak, real health-state signal --- a cell far below nominal capacity is genuinely closer to",
  "a weak, real health-state signal: a cell far below nominal capacity is genuinely closer to"),
 ("with an explicit cost model --- then verify, because Section~3.11 shows",
  "with an explicit cost model, then verify, because Section~3.11 shows"),
 ("relabeling failure by voltage sag alone --- a criterion SOH does not define --- removes most of the",
  "relabeling failure by voltage sag alone (a criterion SOH does not define) removes most of the"),
]
for oldD, newD in DASHES2:
    if oldD in body:
        body = body.replace(oldD, newD)

# ---------------------------------------------------------------- layout fixes
# allow URL breaking at hyphens (url package loaded by apacite)
body = body.replace(
    "publicly available at \\url{https://github.com/touhidsiddiqueeraj-bit/"
    "Multi-Horizon-Hazard-Models-for-Battery-Failure-Prediction}",
    "publicly available at \\texttt{https://github.com/\\allowbreak{}"
    "touhidsiddiqueeraj-bit/\\allowbreak{}Multi-Horizon-\\allowbreak{}"
    "Hazard-Models-for-Battery-\\allowbreak{}Failure-Prediction}")
# break opportunities for long chemistry arrows
body = body.replace("NASA$\\leftrightarrow$CALCE",
                    "NASA$\\leftrightarrow$\\allowbreak{}CALCE")
body = body.replace("Severson$\\to$Oxford", "Severson$\\to$\\allowbreak{}Oxford")
body = body.replace("NASA$\\to$CALCE", "NASA$\\to$\\allowbreak{}CALCE")
body = body.replace("CALCE$\\to$NASA", "CALCE$\\to$\\allowbreak{}NASA")
# allow hyphenation of cross-validation
body = body.replace("cross-validation", "cross\\-validation")
# prototype leftovers that only appear post-transform
body = body.replace(
    "are reliable, with fold-mean AUC of 0.87 and above with Platt calibration "
    "--- and run on a \\$12 microcontroller in under a millisecond.",
    "are reliable, with fold-mean AUC of 0.87 and above under Platt "
    "calibration.")
body = body.replace(
    "across seeds --- seed-to-seed swings span near-chance to near-oracle, so "
    "the sequence model is unstable under shift rather than consistently bad "
    "--- against",
    "across seeds (seed-to-seed swings span near-chance to near-oracle, so "
    "the sequence model is unstable under shift rather than consistently "
    "bad), against")
body = body.replace("against 0.984$\\pm$0.02 with SOH",
                    "against 0.984$\\pm$0.024 with SOH")
body = body.replace("the target cells, which , which per Sections 3.3",
                    "the target cells, which per Sections 3.3")
body = body.replace(
    "removing SOH collapses every model class toward or below chance, with "
    "sensor features sometimes inverting",
    "removing SOH cuts pooled transfer on Oxford to at best 0.58 and on "
    "Severson to 0.53--0.77, with sensor features sometimes inverting")
body = body.replace(
    "cuts with-SOH transfer by a quarter (0.90 to 0.72 pooled on Severson "
    "at $H{=}20$).",
    "cuts pooled with-SOH transfer on Severson from 0.90 to 0.72 at "
    "$H{=}20$.")

# ---------------------------------------------------------------- page compression (IJPHM full papers: 10-15 pages)
def drop_float_by_label(body, label):
    a = body.find("\\label{" + label + "}")
    if a == -1:
        return body
    b = body.rfind("\\begin{figure", 0, a)
    b2 = body.rfind("\\begin{table", 0, a)
    start = max(b, b2)
    e = body.find("\\end{", a)
    e = body.find("}", e) + 1
    return body[:start] + body[e:]

# drop figures whose content is fully carried by tables/text
for lbl in ["fig:within", "fig:prauc", "fig:netbenefit", "fig:rec-r1",
            "fig:rec-r2", "fig:rec-r3", "fig:shap_lgbm", "fig:shap_rf",
            "fig:shap_nolgbm", "fig:shap_norf"]:
    body = drop_float_by_label(body, lbl)

# drop the operational table (numbers quoted in text)
body = drop_float_by_label(body, "tab:operational")

# fix references to dropped floats
body = body.replace("Table~\\ref{tab:within} and Fig.~\\ref{fig:within} summarize",
                    "Table~\\ref{tab:within} summarizes")
body = body.replace("(precision-recall behavior is discussed below and in Fig.~\\ref{fig:prauc})", "")
body = body.replace(
    "Fig.~\\ref{fig:netbenefit} shows the corresponding decision-curve view on Severson without SOH: the net-benefit curves plunge far below zero across the plausible threshold range, so alerting on these scores destroys value at any operating point.",
    "On the decision-curve view the no-SOH net-benefit curves plunge far below zero across the plausible threshold range: alerting on these scores destroys value at any operating point.")
body = body.replace(
    "Figs.~\\ref{fig:shap_xgb}--\\ref{fig:shap_rf} show the attributions",
    "Fig.~\\ref{fig:shap_xgb} shows the attributions")
body = body.replace(
    "Figs.~\\ref{fig:shap_noxgb}--\\ref{fig:shap_norf} repeat the comparison",
    "Fig.~\\ref{fig:shap_noxgb} repeats the comparison")
body = body.replace(" and Fig.~\\ref{fig:rec-r2} summarize this calibration-only trade-off",
                    " summarizes this calibration-only trade-off")
body = body.replace(", and Fig.~\\ref{fig:rec-r1} shows the full seed-averaged trajectory",
                    "")
body = body.replace(", and Fig.~\\ref{fig:rec-r3} shows the heatmap view",
                    "")

# ---------------------------------------------------------------- round-2 fixes
# C1: orphaned reference to the removed operational table
body = body.replace(" and apply it unchanged to the target (Table~\\ref{tab:oper}).",
                    " and apply it unchanged to the target.")
# C2/M2: rewrite the SHAP section to describe the regenerated figures
shap_old = ("TreeSHAP \\cite{lundberg2020from} gives a direct view of the mechanism, and it comes with a "
            "caution about what attributions mean. Figs.~\\ref{fig:shap_xgb}--\\ref{fig:shap_rf} show "
            "the attributions for the three tree models in NASA-to-Oxford transfer at H=20 with SOH kept: "
            "SOH dominates by a wide margin, cycle index a distant second, and the voltage, current, "
            "temperature, and duration features contribute little. "
            "Figs.~\\ref{fig:shap_noxgb}--\\ref{fig:shap_norf} repeat the comparison with SOH removed: "
            "min_voltage and the cycle index retain sizeable in-model attributions, yet the corresponding "
            "transfer AUC collapses (Table~\\ref{tab:abl}). Large attributions, in other words, reflect "
            "within-dataset importance, not transferable signal.")
shap_new = ("TreeSHAP \\cite{lundberg2020from} gives a direct view of the mechanism, with a caution about "
            "what attributions mean. Fig.~\\ref{fig:shap_xgb} shows the attributions for XGBoost in "
            "NASA-to-Oxford transfer at H=20 with SOH kept: $\\bar{V}_{\\min}$ ranks first by mean "
            "attribution magnitude and SOH second, with by far the widest spread across cells. "
            "Fig.~\\ref{fig:shap_noxgb} repeats the comparison with SOH removed: $\\bar{V}_{\\min}$ and "
            "the cycle index retain sizeable in-model attributions, yet the corresponding transfer AUC "
            "collapses (Table~\\ref{tab:abl}). Large attributions, in other words, reflect within-dataset "
            "importance, not transferable signal.")
if shap_old in body:
    body = body.replace(shap_old, shap_new)
else:
    # fall back: rewrite whatever the SHAP paragraph currently is (from 'TreeSHAP' to the next paragraph break)
    a_i = body.find("TreeSHAP \\cite{lundberg2020from} gives a direct view of the mechanism")
    if a_i > -1:
        e_i = body.find("\n\n", a_i)
        body = body[:a_i] + shap_new + body[e_i:]
# M1: surviving roman cross-references
body = body.replace("See Section II-B", "See Section 2.2")
body = body.replace("Sections 3.6 and III-G", "Sections 3.6 and 3.7")
body = body.replace("Sections 3.3--III-E", "Sections 3.3--3.5")
body = re.sub(r"Section[s]?~?III-[A-Z]", lambda m: "Section 3." + str(ord(m.group(0)[-1]) - ord('A') + 1), body)
body = re.sub(r"Section[s]?~?II-[A-Z]", lambda m: "Section 2." + str(ord(m.group(0)[-1]) - ord('A') + 1), body)
# minors: space before punctuation, garbled ending, number consistency, clearpage
body = re.sub(r" ,", ",", body)
body = re.sub(r" ;", ";", body)
body = body.replace("monotone in the horizon,.1", "monotone in the horizon.")
body = body.replace("monotone in the horizon,.", "monotone in the horizon.")
body = body.replace("on Severson to 0.53--0.77", "on Severson to 0.53--0.75")
body = body.replace("\n\\clearpage\n", "\n")

# ---------------------------------------------------------------- citations
# narrative sites: author name already in the sentence -> (Year) only
for pat in [
    "Shikdar and Laaksonen \\cite{shikdar2026learning}",
    "Niculescu-Mizil and Caruana \\cite{niculescu2005predicting}",
    "Huang et al. \\cite{huang2020experimental}",
    "Ibraheem et al. \\cite{ibraheem2025}",
    "Li et al. \\cite{li2024}",
    "Yao et al. \\cite{yao2024}",
    "Pang et al. \\cite{pang2026}",
]:
    body = body.replace(pat, pat.replace("\\cite{", "\\shortcite{"))

# literature table rows: names already present -> (Year) only, scoped to the table
ta = body.index("\\label{tab:lit}")
tb = body.index("\\end{table*}", ta)
lit = body[ta:tb]
lit = re.sub(r"\\cite\{([a-z0-9]+)\}",
             lambda m: "\\shortcite{" + m.group(1) + "}", lit)
body = body[:ta] + lit + body[tb:]

# apacite's \shortcite does not suppress authors here -> use (\citeyear)
body = re.sub(r"\\shortcite\{([a-z0-9]+)\}",
              lambda m: "\\citeyear{" + m.group(1) + "}", body)

# grzesik (edge computing) no longer cited anywhere
body = body.replace(" \\cite{grzesik2024combining}", "")

# ---------------------------------------------------------------- rhetorical dashes
DASHES = [
 ("and the cell --- not the cycle --- is the experimental unit.",
  "and the cell, not the cycle, is the experimental unit."),
 ("""cycles). We consider two feature settings --- the full feature set and
SOH removed --- to test whether""",
  """cycles). We consider two feature settings, the full feature set and
SOH removed, to test whether"""),
 ("Platt's fitted slope on CALCE is only 0.01 --- under",
  "Platt's fitted slope on CALCE is only 0.01: under"),
 ("""achieving calibration error comparable to or better than isotonic} ---
a materially weaker and more defensible claim than ``Platt is the
better calibrator'' --- and raw scores remain the safest ranking
signal whenever the operating context is uncertain""",
  """achieving calibration error comparable to or better than isotonic},
a materially weaker and more defensible claim than ``Platt is the
better calibrator'', and raw scores remain the safest ranking signal
whenever the operating context is uncertain"""),
 ("0.77 on Severson, and several fall below chance --- the remaining",
  "0.77 on Severson, and several fall below chance: the remaining"),
 ("""source --- within the confidence range of the tuned ensembles --- so
most of the apparent transfer is the SOH coordinate itself.""",
  """source, within the confidence range of the tuned ensembles, so most
of the apparent transfer is the SOH coordinate itself."""),
 ("""endpoint at a time --- SOH $\\le 0.80$ only, voltage sag only, or both
--- and its signature is clean:""",
  """endpoint at a time (SOH $\\le 0.80$ only, voltage sag only, or both),
and its signature is clean:"""),
 ("cuts it to 0.723 --- a drop of roughly a quarter.",
  "cuts it to 0.723, a drop of roughly a quarter."),
 ("""cross-chemistry shifts --- 0.997 with SOH collapsing to 0.471 without,
an inverted 0.428 on the common feature set --- and NASA$\\to$CALCE""",
  """cross-chemistry shifts: 0.997 with SOH collapsing to 0.471 without,
an inverted 0.428 on the common feature set; NASA$\\to$CALCE"""),
 ("on the transferred Severson target --- for a hazard-style output, an",
  "on the transferred Severson target: for a hazard-style output, an"),
 ("""same SOH dependence as every other model --- formulating the output
does not exempt the inputs from dataset shift --- and behaves""",
  """same SOH dependence as every other model (formulating the output does
not exempt the inputs from dataset shift) and behaves"""),
 ("scores differ only marginally --- under shift the ranking is the asset",
  "scores differ only marginally: under shift the ranking is the asset"),
 ("""to SOH --- partly because SOH defines the failure criterion itself,
which the failure-endpoint ablation quantifies --- rather than to""",
  """to SOH, partly because SOH defines the failure criterion itself
(quantified by the failure-endpoint ablation), rather than to"""),
 ("""with SOH available the scores support a usable operating point on both targets. Without SOH, no threshold""",
  """with SOH available the scores support a usable operating point on both targets. Without SOH, no threshold"""),
 ("--- the operationally honest choice, since no target labels exist at deployment ---",
  ", the operationally honest choice since no target labels exist at deployment,"),
 ("--- the operating point survives the shift with margin to spare.",
  "; the operating point survives the shift with margin to spare."),
 ("--- that target offers no room for a discriminating operating point at all",
  "; that target offers no room for a discriminating operating point at all"),
 ("--- a materially weaker and more defensible claim than",
  ", a materially weaker and more defensible claim than"),
 ("--- nothing in this paper convicts the architecture, only this instance of it.",
  "; nothing in this paper convicts the architecture, only this instance of it."),
 ("--- effectively four for per-cell statistics ---",
  ", effectively four for per-cell statistics,"),
 ("--- fold-mean AUC of 0.89 and above with Platt calibration ---",
  ", with fold-mean AUC of 0.89 and above under Platt calibration,"),
 ("--- per Sections~3.3--3.7 ---",
  ", which per Sections~3.3--3.7 "),
 ("reliable --- fold-mean AUC", "reliable, with fold-mean AUC"),
]
for oldD, newD in DASHES:
    if oldD in body:
        body = body.replace(oldD, newD)

# any remaining rhetorical dashes -> em dash character is not wanted; flag them
leftover = [m.start() for m in re.finditer(r"---", body)]
if leftover:
    print("WARNING: %d rhetorical dashes remain:" % len(leftover))
    for pos in leftover:
        print("   ...", body[max(0, pos-60):pos+60].replace("\n", " "), "...")

# ---------------------------------------------------------------- emit
# drop the Grzesik row (edge computing, deployment-adjacent)
body = re.sub(r"Grzesik and Mrozek[^\n]*\n", "", body)
# drop the IEEE Access end-of-data marker
body = body.replace("\\EOD", "")

# drop the journal's numbered bibliography (apacite generates the reference list)
body = re.sub(r"\\begin\{thebibliography\}.*?\\end\{thebibliography\}", "", body, flags=re.S)
# grzesik (edge computing) citation in the related-work paragraph
body = body.replace(" privacy concerns \\cite{grzesik2024combining}", " privacy concerns")
body = body.replace("privacy concerns \\cite{grzesik2024combining}.", "privacy concerns.")

out = (PREAMBLE + body +
       "\n\n\\bibliographystyle{apacite}\n\\PHMbibliography{ijphm}\n\n"
       "\\end{document}\n")

# final safety pass on the emitted document
out = out.replace(
    "are reliable, with fold-mean AUC of 0.87 and above with Platt "
    "calibration --- and run on a \\$12 microcontroller in under a "
    "millisecond.", "are reliable, with fold-mean AUC of 0.87 and above "
    "under Platt calibration.")
out = out.replace(
    "across seeds --- seed-to-seed swings span near-chance to near-oracle, "
    "so the sequence model is unstable under shift rather than consistently "
    "bad --- against",
    "across seeds (seed-to-seed swings span near-chance to near-oracle, so "
    "the model is unstable under shift rather than consistently bad), "
    "against")


out = out.replace(
    "cuts with-SOH transfer by a quarter (0.90 to 0.72 pooled on Severson "
    "at $H{=}20$).",
    "cuts pooled with-SOH transfer on Severson from 0.90 to 0.72 at "
    "$H{=}20$.")
out = out.replace("against 0.984$\\pm$0.02 with SOH",
                  "against 0.984$\\pm$0.024 with SOH")
out = out.replace("cells, which , which per Sections", "cells, which per Sections")
out = out.replace(
    "removing SOH collapses every model class toward or below chance, with "
    "sensor features sometimes inverting",
    "removing SOH cuts pooled transfer on Oxford to at best 0.58 and on "
    "Severson to 0.53--0.77, with sensor features sometimes inverting")

bad = [w for w in ["ESP32", "deployment architecture", "Deployment Validation",
                   "microcontroller", "embedded deployment", "1~028 validation"]
       if w.lower() in out.lower()]
print("leftover prototype words:", bad if bad else "none")


# final-final: catch remaining prototype text (constructed to avoid escape drift)
_n1 = ("are reliable, with fold-mean AUC of 0.87 and above with Platt calibration "
       + BS*3 + "and run on a " + BS + "$12 microcontroller in under a millisecond.")
if _n1 in out:
    out = out.replace(_n1, "are reliable, with fold-mean AUC of 0.87 and above under Platt calibration.")
_n2 = ("across seeds " + BS*3 + " seed-to-seed swings span near-chance to near-oracle, so the sequence model is unstable under shift rather than consistently bad " + BS*3 + " against")
if _n2 in out:
    out = out.replace(_n2, "across seeds (seed-to-seed swings span near-chance to near-oracle, so the sequence model is unstable under shift rather than consistently bad), against")
for _probe, _fix in [("\\$12 microcontroller", BS + "$12 microcontroller")]:
    if _probe in out:
        print("STILL: microcontroller text present")

# final text normalizations (exact strings from the emitted document)
_old_shap = ("Fig.~" + BS + "ref{fig:shap_xgb} shows the attributions for the three tree models "
             "in NASA-to-Oxford transfer at H=20 with SOH kept: SOH dominates by a wide margin, "
             "cycle index a distant second, and the voltage, current, temperature, and duration "
             "features contribute little. Figs.~" + BS + "ref{fig:shap_noxgb}--" + BS +
             "ref{fig:shap_norf} repeat the same comparisons with SOH removed, and every remaining "
             "feature collapses to near-zero SHAP spread, matching in the model's internal "
             "accounting the quantitative collapse of Sections~3.3--III-E and the sensor-inversion "
             "of Section~3.4.")
_shap_pat = re.compile(re.escape(_old_shap).replace(r"\ ", r"\s+"), flags=re.S)
_new_shap = ("Fig.~" + BS + "ref{fig:shap_xgb} shows the attributions for XGBoost in NASA-to-Oxford "
             "transfer at H=20 with SOH kept: min" + BS + "_voltage ranks first by mean attribution "
             "magnitude and SOH second, with by far the widest spread across cells. "
             "Fig.~" + BS + "ref{fig:shap_noxgb} repeats the comparison with SOH removed: min" + BS +
             "_voltage and the cycle index retain sizeable in-model attributions, yet the "
             "corresponding transfer AUC collapses (Table~" + BS + "ref{tab:abl}) --- large "
             "attributions reflect within-dataset importance, not transferable signal.")
out = _shap_pat.sub(_new_shap.replace("\\", "\\\\"), out)

os.makedirs(os.path.join(ROOT, "figs"), exist_ok=True)
open(os.path.join(ROOT, "main.tex"), "w").write(out)
print("wrote paper_ijphm/main.tex (%d chars)" % len(out))
