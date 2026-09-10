"""Build paper_ijphm/main.tex from paper_ieee_access/main_access.tex:
remove the embedded-prototype material, convert to IJPHM (PHMSociety)
format with APA citations, arabic sections, license footnote, and
compress to the venue's 10-15 page full-paper guideline."""
import re
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
BS = chr(92)   # one literal backslash
NL = chr(10)   # newline character

src = open(os.path.join(ROOT, "..", "paper_ieee_access", "main_access.tex")).read()

# ---------------------------------------------------------------- remove prototype blocks
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

# ---------------------------------------------------------------- IJPHM preamble
PREAMBLE = (
    "% IJPHM submission -- International Journal of Prognostics and Health Management\n"
    "% Built from the IEEE Access manuscript; the embedded-prototype material\n"
    "% (hardware deployment, on-device validation) has been removed in full.\n"
    "\\documentclass[IJPHM, 2014, 00]{PHMSociety}\n\n"
    "\\usepackage{graphicx}\n"
    "\\usepackage{amsmath}\n"
    "\\usepackage{booktabs}\n"
    "\\setlength{\\emergencystretch}{5em}\n"
    "\\binoppenalty=9000\n"
    "\\relpenalty=700\n\n"
    "\\graphicspath{{figs/}{../paper_ieee_access/figs/}}\n\n"
    "\\begin{document}\n\n"
    "\\title{Multi-Horizon Failure-Risk Models for Battery Failure Prediction: "
    "How Much Cross-Chemistry Transfer Is a State-of-Health Shortcut?}\n\n"
    "\\author{%\n"
    "\tHussain Touhid Siddiquee\\authorNumber{1}, "
    "Jasimul Islam Chowdhury\\authorNumber{2}, "
    "Farzana Hoque Eshica\\authorNumber{3}, and "
    "Syeda Salsabil Islam Ariya\\authorNumber{4}\n}\n\n"
    "\\address{%\n"
    "\t\\affiliation{{1,2,3,4}}{Leading University, Sylhet 3100, Bangladesh}{ %\n"
    "\t\t{\\email{touhidsiddiqueeraj@gmail.com}}" + NL +
    "\t\t{\\email{chowdhuryjasimul@gmail.com}}" + NL +
    "\t\t{\\email{ishicafhaque@gmail.com}}" + NL +
    "\t\t{\\email{salsabil.ariyaa@gmail.com}}" + NL +
    "\t\t}\n}\n\n"
    "\\maketitle\n"
    "\\pagestyle{fancy}\n"
    "\\thispagestyle{plain}\n\n"
    "\\phmLicenseFootnote{Hussain Touhid Siddiquee}\n\n"
)

# ---------------------------------------------------------------- body
a = src.index("\\begin{abstract}")
b = src.rindex("\\end{document}")
body = src[a:b]

# abstract: repair the deployment-fragment ending, fix escaped dollars
body = re.sub(
    r"The truncation-prone isotonic calibrator.*?1~028 validation rows\.",
    "The truncation-prone isotonic calibrator largely fails to transfer, and "
    "cell-level bootstrap intervals replace cycle-level significance tests as "
    "the primary evidence. On the modeling side, a discrete-time hazard "
    "formulation restores the monotone risk-coherence that independent "
    "fixed-horizon classifiers lack.",
    body, flags=re.S)
body = body.replace("\\$H{=}20\\$", "$H{=}20$")
body = body.replace(
    "cuts with-SOH transfer by a quarter (0.90 to 0.72 pooled on Severson at "
    "$H{=}20$).",
    "cuts pooled with-SOH transfer on Severson from 0.90 to 0.72 at $H{=}20$.")

# keywords: plain italic paragraph (template has no keywords environment)
body = re.sub(
    r"\\begin\{keywords\}.*?\\end\{keywords\}",
    lambda m: (
        "\\medskip\\noindent\\textit{Keywords---}battery failure prediction, "
        "multi-horizon failure-risk classification, state-of-health shortcut, "
        "cross-chemistry transfer, dataset shift, probability calibration, "
        "discrete-time hazard model, SHAP."),
    body, flags=re.S)

# drop the journal's title machinery (PHMSociety title block is in the preamble)
body = body.replace("\\titlepgskip=-21pt\n", "")
body = body.replace("\\maketitle\n", "")
body = body.replace("\\emergencystretch=6em\n", "")
body = re.sub(r"\\makeatletter\\def\\UrlBreaks\{[^}]*\}\\makeatother\n", "", body)

# ---------------------------------------------------------------- prototype leftovers
body = body.replace(
    " That work left three gaps open.", " That work left two gaps open.")
body = body.replace(
    " Third, no path existed from a Python research prototype to the "
    "microcontroller where a battery management system actually runs.", "")
body = body.replace(
    " a complete embedded deployment that packs all three ensembles into one "
    "flat binary and runs them on an ESP32-S3 through a hand-written C tree "
    "walker.", "")
body = re.sub(
    r"\\item a complete embedded deployment that packs all three ensembles into "
    r"one flat binary and runs them on an ESP32-S3 through a hand-written C tree "
    r"walker\.?\n?", "", body)
body = body.replace(
    " and the deployment results show that they run on a \\$12 microcontroller.",
    "")
body = body.replace(
    "are reliable, with fold-mean AUC of 0.87 and above with Platt calibration "
    "--- and run on a \\$12 microcontroller in under a millisecond.",
    "are reliable, with fold-mean AUC of 0.87 and above under Platt "
    "calibration.")
body = re.sub(r" and a 372~kB embedded deployment[^.]*\.", ".", body)
body = re.sub(r"\.1\\times10\^\{-6\}\$ on a \\\$12 ESP32-S3\.", ".", body)
body = body.replace(
    " On explainability and deployment, TreeSHAP",
    " On explainability, TreeSHAP")

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
    "Section~III-J": "Section~3.10", "Section~III-I": "Section~3.9",
    "Section~III-H": "Section~3.8",
    "Section~II-D": "Section~2.4", "Section~II-F": "Section~2.6",
    "Section~II-C": "Section~2.3", "Section~II-A": "Section~2.1",
}
for k, v in SECMAP.items():
    body = body.replace(k, v)
body = re.sub(r"Section[s]?~II-[A-Z]", "Section~2.x", body)
body = re.sub(r"Section[s]?~III-[A-Z]", "Section~3.x", body)

# ---------------------------------------------------------------- citations
NARRATIVE = [
    "Shikdar and Laaksonen \\cite{shikdar2026learning}",
    "Niculescu-Mizil and Caruana \\cite{niculescu2005predicting}",
    "Huang et al. \\cite{huang2020experimental}",
    "Ibraheem et al. \\cite{ibraheem2025}",
    "Li et al. \\cite{li2024}",
    "Yao et al. \\cite{yao2024}",
    "Pang et al. \\cite{pang2026}",
]
for pat in NARRATIVE:
    body = body.replace(pat, pat.replace("\\cite{", "\\citeyear{"))

ta = body.index("\\label{tab:lit}")
tb = body.index("\\end{table*}", ta)
lit = body[ta:tb]
lit = re.sub(r"\\cite\{([a-z0-9]+)\}", lambda m: "\\citeyear{" + m.group(1) + "}", lit)
body = body[:ta] + lit + body[tb:]

body = body.replace(" \\cite{grzesik2024combining}", "")
# drop the hand-written IEEE bibliography: apacite's redefined thebibliography
# machinery cannot digest its plain \bibitem entries (\@listctr errors).
if "\\begin{thebibliography}" in body:
    ta = body.index("\\begin{thebibliography}")
    tb = body.index("\\end{thebibliography}", ta) + len("\\end{thebibliography}")
    body = body[:ta] + body[tb:]
body = body.replace("\\EOD\n", "").replace("\\EOD", "")
# the prototype item removal leaves an empty \item at the end of the
# contributions list - drop it (judge-confirmed orphaned bullet)
body = body.replace("\\item\n\\end{itemize}", "\\end{itemize}")

# ---------------------------------------------------------------- Shikdar dedupe
# drop the companion-robustness citation (user: one Shikdar reference only);
# the recalibration arms are this paper's own experiments
body = body.replace(
    "A companion robustness study further found that under realistic operating "
    "perturbation the calibration layer is the primary point of failure, and "
    "that recalibration on a small sample of the operational data largely "
    "restores calibration \\cite{shikdar2026robustness}; whether the same "
    "repair survives a cross-chemistry shift is examined in this work.",
    "Whether recalibration on a small labeled sample of the operational data "
    "repairs calibration under cross-chemistry shift is examined directly in "
    "this work.")
body = body.replace(
    "The recalibration arms of the companion study "
    "\\cite{shikdar2026robustness} ask whether",
    "The recalibration arms ask whether")

# ---------------------------------------------------------------- lit table at body size
# the source wraps the table in \resizebox (scriptsize result); unwrap it and
# switch to wrapping p-columns that fill \textwidth at normal font size
_la = body.index("\\label{tab:lit}")
_ta = body.index("\\resizebox{\\textwidth}{!}{%", _la)
_tb = body.index("\\begin{tabular}", _ta)
_te = body.index("\\end{tabular}}", _tb) + len("\\end{tabular}}")
_seg = body[_tb:_te - 1].replace(
    "{lllp{0.27\\textwidth}}",
    "{p{0.28\\textwidth}p{0.14\\textwidth}p{0.11\\textwidth}"
    "p{0.35\\textwidth}}")
body = body[:_ta] + _seg + body[_te:]
body = body.replace(", calibration under shift, embedded deployment",
                    ", calibration under shift")
body = re.sub(r"Grzesik and Mrozek[^\\n]*\n", "", body)

# ---------------------------------------------------------------- rhetorical dashes
DASHES = [
 ("and the cell --- not the cycle --- is the experimental unit.",
  "and the cell, not the cycle, is the experimental unit."),
 ("two feature settings --- the full feature set and\nSOH removed --- to test whether",
  "two feature settings, the full feature set and SOH removed, to test whether"),
 ("Platt's fitted slope on CALCE is only 0.01 --- under",
  "Platt's fitted slope on CALCE is only 0.01: under"),
 ("comparable to or better than isotonic} ---", "comparable to or better than isotonic},"),
 ("better calibrator'' --- and raw scores", "better calibrator'', and raw scores"),
 ("0.77 on Severson, and several fall below chance --- the remaining",
  "0.77 on Severson, and several fall below chance: the remaining"),
 ("source --- within the confidence range of the tuned ensembles --- so",
  "source, within the confidence range of the tuned ensembles, so"),
 ("endpoint at a time --- SOH $\\le 0.80$ only, voltage sag only, or both",
  "endpoint at a time (SOH $\\le 0.80$ only, voltage sag only, or both)"),
 ("--- and its signature is clean:", ", and its signature is clean:"),
 ("cuts it to 0.723 --- a drop of roughly a quarter.",
  "cuts it to 0.723, a drop of roughly a fifth."),
 ("cross-chemistry shifts --- 0.997 with SOH collapsing to 0.471 without,",
  "cross-chemistry shifts: 0.997 with SOH collapsing to 0.471 without,"),
 ("an inverted 0.428 on the common feature set --- and NASA$\\to$CALCE",
  "an inverted 0.428 on the common feature set; NASA$\\to$CALCE"),
 ("on the transferred Severson target --- for a hazard-style output, an",
  "on the transferred Severson target: for a hazard-style output, an"),
 ("same SOH dependence as every other model --- formulating the output",
  "same SOH dependence as every other model (formulating the output"),
 ("does not exempt the inputs from dataset shift --- and behaves",
  "does not exempt the inputs from dataset shift) and behaves"),
 ("scores differ only marginally --- under shift the ranking is the asset",
  "scores differ only marginally: under shift the ranking is the asset"),
 ("to SOH --- partly because SOH defines the failure criterion itself,",
  "to SOH, partly because SOH defines the failure criterion itself,"),
 ("which the failure-endpoint ablation quantifies --- rather than to",
  "quantified by the failure-endpoint ablation, rather than to"),
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
 ("is 0.786$\\pm$0.332 across seeds --- seed-to-seed swings span near-chance to near-oracle, so the sequence model is unstable under shift rather than consistently bad --- against",
  "is 0.786$\\pm$0.332 across seeds (seed-to-seed swings span near-chance to near-oracle, so the sequence model is unstable under shift rather than consistently bad), against"),
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
  "falls to 0.723, a drop of roughly a fifth, with the"),
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
 ("0.53 and 0.75 --- and several configurations",
  "0.53 and 0.75, and several configurations"),
 ("voltage sag only, or both) --- and repeats the transfer",
  "voltage sag only, or both) and repeats the transfer"),
 ("dataset shift alone --- same chemistry, different laboratory and "
  "protocol --- is sufficient",
  "dataset shift alone (same chemistry, different laboratory and protocol) "
  "is sufficient"),
]
for oldD, newD in DASHES:
    if oldD in body:
        body = body.replace(oldD, newD)

leftover = [m.start() for m in re.finditer(r" --- ", body)]
if leftover:
    print("WARNING: %d rhetorical dashes remain in body" % len(leftover))
    for pos in leftover[:8]:
        print("   ...", body[max(0, pos-50):pos+50].replace("\n", " "), "...")

# ---------------------------------------------------------------- round-2 fixes
body = body.replace("See Section II-B", "See Section 2.2")
body = body.replace("Sections 3.6 and III-G", "Sections 3.6 and 3.7")
body = body.replace("Sections 3.3--III-E", "Sections 3.3--3.5")
body = re.sub(r"Section[s]?~?III-[A-Z]",
              lambda m: "Section 3." + str(ord(m.group(0)[-1]) - ord('A') + 1), body)
body = re.sub(r"Section[s]?~?II-[A-Z]",
              lambda m: "Section 2." + str(ord(m.group(0)[-1]) - ord('A') + 1), body)
body = body.replace(" ,", ",").replace(" ;", ";")
body = body.replace("monotone in the horizon,.1", "monotone in the horizon.")
body = body.replace("monotone in the horizon,.", "monotone in the horizon.")
body = body.replace("against 0.984$\\pm$0.02 with SOH",
                    "against 0.984$\\pm$0.024 with SOH")
body = body.replace(
    "removing SOH collapses every model class toward or below chance, with "
    "sensor features sometimes inverting",
    "removing SOH cuts pooled transfer on Oxford to at best 0.58 and on "
    "Severson to 0.53--0.75, with sensor features sometimes inverting")
body = body.replace(
    "cuts with-SOH transfer by a quarter (0.90 to 0.72 pooled on Severson "
    "at $H{=}20$).",
    "cuts pooled with-SOH transfer on Severson from 0.90 to 0.72 at $H{=}20$.")
body = body.replace(
    "Table~\\ref{tab:within} and Fig.~\\ref{fig:within} summarize",
    "Table~\\ref{tab:within} summarizes")
body = body.replace("their table 4 behavior", "their Table~IV behavior")
body = body.replace("the fitted-free score", "the training-free score")
body = body.replace("Table~\\ref{tab:gru}), and", "Table~\\ref{tab:gru}), and")
body = body.replace(
    "while CALCE-trained and ALL-LCO updates damage the source operating "
    "point (LCO-holdout retention falls from 0.997 to 0.613 for CALCE-trained "
    "XGBoost)",
    "while the NASA-trained Random Forest update and the ALL-LCO XGBoost "
    "update damage the source operating point (LCO-holdout retention falls "
    "from 0.959 to 0.314 and from 0.690 to 0.597, respectively)")
body = body.replace(
    "Fig.~\\ref{fig:netbenefit} shows the corresponding decision-curve view "
    "on Severson: with SOH the model buys net benefit across a wide threshold "
    "range; without SOH the curve hugs zero.",
    "On the decision-curve view (Fig.~\\ref{fig:netbenefit}) the no-SOH "
    "net-benefit curves plunge far below zero across the plausible threshold "
    "range: alerting on these scores destroys value at any operating point.")

# ---------------------------------------------------------------- SHAP section rewrite
# The source paragraph cites the four two-model figure ranges (shap_xgb--shap_rf,
# shap_noxgb--shap_norf); replace it wholesale with the six-figure version.
SHAP_NEW = (
    "TreeSHAP (SHapley Additive exPlanations) \\cite{lundberg2020from} gives a "
    "direct view of the mechanism. Fig.~\\ref{fig:shap_xgb} shows the "
    "attributions for XGBoost in NASA-to-Oxford transfer at $H{=}20$ with SOH "
    "kept: min\\_voltage ranks first by mean attribution magnitude and SOH "
    "second, with by far the widest spread across cells. "
    "Fig.~\\ref{fig:shap_noxgb} repeats the comparison with SOH removed: "
    "min\\_voltage and the cycle index retain sizeable in-model attributions, "
    "yet the corresponding transfer AUC collapses (Table~\\ref{tab:abl}). "
    "Large attributions, in other words, reflect within-dataset importance, "
    "not transferable signal.")
body = re.sub(r"TreeSHAP \(SHapley.*?sensor-inversion of Section[s]?[ ~]?[A-Z0-9.]*\.?",
              lambda m: SHAP_NEW, body, flags=re.S)

# ---------------------------------------------------------------- emit
out = (PREAMBLE + body +
       "\n\n\\bibliographystyle{apacite}\n\\PHMbibliography{ijphm}\n\n"
       "\\end{document}\n")

# ---------------------------------------------------------------- final normalizations
out = out.replace("are reliable, with fold-mean AUC of 0.87 and above with Platt "
                  "calibration --- and run on a \\$12 microcontroller in under a "
                  "millisecond.",
                  "are reliable, with fold-mean AUC of 0.87 and above under Platt "
                  "calibration.")
out = out.replace(
    "across seeds --- seed-to-seed swings span near-chance to near-oracle, so "
    "the sequence model is unstable under shift rather than consistently bad "
    "--- against",
    "across seeds (seed-to-seed swings span near-chance to near-oracle, so "
    "the sequence model is unstable under shift rather than consistently "
    "bad), against")
out = out.replace("against 0.984$\\pm$0.02 with SOH",
                  "against 0.984$\\pm$0.024 with SOH")
out = out.replace("Figs.Fig.~", "Fig.~")
out = out.replace("mechanism. Figs.Fig.~", "mechanism. Fig.~")
out = out.replace("cells, which , which per Sections", "cells, which per Sections")
out = out.replace("cells, which, which per Sections", "cells, which per Sections")
out = out.replace(
    "removing SOH collapses every model class toward or below chance, with "
    "sensor features sometimes inverting",
    "removing SOH cuts pooled transfer on Oxford to at best 0.58 and on "
    "Severson to 0.53--0.75, with sensor features sometimes inverting")
out = out.replace(
    "cuts with-SOH transfer by a quarter (0.90 to 0.72 pooled on Severson "
    "at $H{=}20$).",
    "cuts pooled with-SOH transfer on Severson from 0.90 to 0.72 at $H{=}20$.")
out = out.replace("See Section II-B", "See Section 2.2")
out = out.replace("Sections 3.6 and III-G", "Sections 3.6 and 3.7")
out = out.replace("Sections 3.3--III-E", "Sections 3.3--3.5")
out = out.replace(" and~III-G", " and 3.7")
out = re.sub(r"Section[s]?~?III-[A-Z]",
             lambda m: "Section 3." + str(ord(m.group(0)[-1]) - ord('A') + 1), out)
out = re.sub(r"Section[s]?~?II-[A-Z]",
             lambda m: "Section 2." + str(ord(m.group(0)[-1]) - ord('A') + 1), out)
out = out.replace("\\end{figure*}\n\nTable~\\ref{tab:within}",
                  "\\end{figure}\n\nTable~\\ref{tab:within}")

# wide data tables span both columns; restore scale-to-width except the lit table
parts = out.split("\\begin{table*}[!t]")
if len(parts) > 1:
    body2 = parts[0]
    resize_labels = ["tab:within", "tab:transfer", "tab:baselines", "tab:abl",
                     "tab:sohtests", "tab:hazard", "tab:crosswith", "tab:crossno"]
    for chunk in parts[1:]:
        head = chunk.split("\\begin{tabular}")[0]
        do_resize = any(r in head for r in resize_labels)
        if "tab:lit" in head:
            body2 += "\\begin{table*}[!t]" + chunk
            continue
        if do_resize:
            chunk = chunk.replace("\\centering",
                                  "\\centering\n\\resizebox{\\textwidth}{!}{%", 1)
            chunk = chunk.replace("\\end{tabular}", "\\end{tabular}}", 1)
        body2 += "\\begin{table*}[!t]" + chunk
    out = body2

# SHAP figures (main claim): pair the six full-width floats into three
# two-up floats to reclaim float-page whitespace; every figure keeps its
# own caption and label, so numbering and cross-references are unchanged.
_pat = (r"\\begin\{figure\*\}\[!t\]\s*\\centering\s*"
        r"\\includegraphics\[width=[\d.]+\\textwidth\]\{(Fig06[^}]*)\}\s*"
        r"\\caption\{(.*?)\}\s*\\label\{([^}]*)\}\s*\\end\{figure\*\}")
_spans = list(re.finditer(_pat, out, flags=re.S))
if len(_spans) == 6:
    _blocks = sorted([m.groups() for m in _spans], key=lambda b: b[0])
    _text = out[:_spans[0].start()]
    for _i in range(0, 6, 2):
        (_fa, _ca, _la), (_fb, _cb, _lb) = _blocks[_i], _blocks[_i + 1]
        _text += ("\\begin{figure*}[!t]\n"
                  "\\begin{minipage}[t]{0.495\\textwidth}\n\\centering\n"
                  "\\includegraphics[width=0.79\\linewidth]{" + _fa + "}\n"
                  "\\caption{" + _ca + "}\n\\label{" + _la + "}\n\\end{minipage}\\hfill\n"
                  "\\begin{minipage}[t]{0.495\\textwidth}\n\\centering\n"
                  "\\includegraphics[width=0.79\\linewidth]{" + _fb + "}\n"
                  "\\caption{" + _cb + "}\n\\label{" + _lb + "}\n\\end{minipage}\n"
                  "\\end{figure*}\n")
    _text += out[_spans[-1].end():]
    out = _text

bad = [w for w in ["ESP32", "microcontroller", "firmware", "embedded deployment",
                   "deployment architecture", "1~028 validation", "3.x",
                   "Table Table", "Fig. Fig"]
       if w.lower() in out.lower()]
if bad:
    print("WARNING still present:", bad)

out = out.replace(" (Table~" + BS + "ref{tab:oper}).", ".")

# the repo URL must be breakable everywhere: cmtt gives no breaks at hyphens
# and the source's three \allowbreak spots still overflowed the column into
# the neighbor (user-reported collision in the Acknowledgment)
out = out.replace(
    "https://github.com/\\allowbreak{}touhidsiddiqueeraj-bit/\\allowbreak{}"
    "Multi-Horizon-\\allowbreak{}Hazard-Models-for-Battery-"
    "\\allowbreak{}Failure-Prediction",
    "github.com/\\allowbreak{}touhidsiddiqueeraj-bit/\\allowbreak{}"
    "Multi-\\allowbreak{}Horizon-\\allowbreak{}Hazard-\\allowbreak{}Models-"
    "\\allowbreak{}for-\\allowbreak{}Battery-\\allowbreak{}Failure-"
    "\\allowbreak{}Prediction")
out = out.replace("\\includegraphics[width=0.9\\textwidth]{fig_reliability_v2.png}",
                  "\\includegraphics[width=0.78\\textwidth]{fig_reliability_v2.png}")
out = out.replace("\\includegraphics[width=0.95\\textwidth]{fig_collapse_map.png}",
                  "\\includegraphics[width=0.88\\textwidth]{fig_collapse_map.png}")
# all floats are placed by p.14; the IEEE-era flush \clearpage would strand
# the acknowledgment + references alone on p.16 (16pp > venue's 15pp cap)
out = out.replace("\\clearpage\n\\section*{Acknowledgment}",
                  "\\section*{Acknowledgment}")
out = out.replace("\\includegraphics[width=0.5\\textwidth]{fig_netbenefit.png}",
                  "\\includegraphics[width=\\columnwidth]{fig_netbenefit.png}")

os.makedirs(os.path.join(ROOT, "figs"), exist_ok=True)
open(os.path.join(ROOT, "main.tex"), "w").write(out)
print("wrote paper_ijphm/main.tex (%d chars)" % len(out))
