#!/usr/bin/env python3
"""Convert the IEEE TR manuscript package (paper_tr/) to ITEES submission format
(International Transactions on Electrical Energy Systems, Wiley open access).

- Single-column Wiley/Hindawi-style layout (article class + TeX Gyre Termes).
- Front matter: title, authors, affiliation, correspondence, abstract, keywords.
- IEEE Roman-numeral section references -> Arabic ("Section III-C" -> "Section 3.3").
- table* -> table, Fig.~ -> Figure~, \columnwidth -> 0.78\textwidth.
- Abstract trimmed to <= 250 words (Hindawi convention); all numbers unchanged.
- Declarations added (Funding / Conflict of interest / Data availability /
  Author contributions) before the references.
- IEEE biographies removed.
Also repairs the corrupted hyperref line in paper_tr/supplement_tr.tex.
"""
import re
import pathlib
import shutil

ROOT = pathlib.Path("/home/z/my-project/download")
SRC = ROOT / "paper_tr"
DST = ROOT / "paper_itees"

# ---------------------------------------------------------------- fix TR supplement
sup_tr = SRC / "supplement_tr.tex"
sup_text = sup_tr.read_text()
if "\\usepackageidelinks]{hyperref}" in sup_text:
    sup_text = sup_text.replace(
        "\\usepackageidelinks]{hyperref}", "\\usepackage[hidelinks]{hyperref}"
    )
    sup_tr.write_text(sup_text)
    print("FIXED: paper_tr/supplement_tr.tex corrupted hyperref line")

# ---------------------------------------------------------------- helpers
ROMAN = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6}
SUBORD = {c: i + 1 for i, c in enumerate("ABCDEFGHIJKLM")}


def conv_sections(text):
    """Section~II-A -> Section~2.1 ; Sections~III-C--III-E -> Sections~3.3--3.5"""
    def one(m):
        sec = ROMAN[m.group(1)]
        sub = SUBORD.get(m.group(2)) if m.group(2) else None
        return f"Section~{sec}" + (f".{sub}" if sub else "")
    def two(m):
        a = f"{ROMAN[m.group(1)]}" + (f".{SUBORD[m.group(2)]}" if m.group(2) else "")
        b = f"{ROMAN[m.group(3)]}" + (f".{SUBORD[m.group(4)]}" if m.group(4) else "")
        return f"Sections~{a}--{b}"
    text = re.sub(r"Sections~([IVX]+)-([A-Z])--([IVX]+)-([A-Z])", two, text)
    text = re.sub(r"Sections~([IVX]+)--([IVX]+)", two, text)
    text = re.sub(r"Section~([IVX]+)(-([A-Z]))?", one, text)
    return text


def body_transforms(text):
    text = text.replace("\\begin{table*}", "\\begin{table}").replace(
        "\\end{table*}", "\\end{table}")
    text = text.replace("\\begin{figure*}", "\\begin{figure}").replace(
        "\\end{figure*}", "\\end{figure}")
    text = text.replace("Fig.~\\ref", "Figure~\\ref")
    text = text.replace("width=\\columnwidth", "width=0.78\\textwidth")
    text = conv_sections(text)
    return text


def strip_months_in_refs(text):
    """', vol. 45, no. 1, pp. 521-530, Jan. 2012' -> '..., 2012' (bibliography only)."""
    start = text.index("\\begin{thebibliography}")
    head, bib = text[:start], text[start:]
    bib = re.sub(
        r",\s*(?:Jan\.|Feb\.|Mar\.|Apr\.|May|Jun\.|Jul\.|Aug\.|Sep\.|Oct\.|Nov\.|Dec\.)(\s+\d{4})",
        r",\1", bib)
    bib = bib.replace("art. no.~", "Article ID ").replace("art. no. ", "Article ID ")
    return head + bib


# ---------------------------------------------------------------- preamble
PREAMBLE = r"""% International Transactions on Electrical Energy Systems (Wiley, open access)
% submission manuscript. Converted 2026-10-30 from the validated IEEE TR
% version (paper_tr/main_tr.tex). All tables and quantitative claims are
% unchanged; the abstract was trimmed to <=250 words and the IEEE-specific
% front matter, biographies, and Roman-numeral section references were
% replaced with the Wiley/Hindawi single-column conventions. ITEES imposes
% no page limit; this manuscript compiles to a single-column A4 article.
% Compile: tectonic main_itees.tex
\documentclass[11pt,a4paper]{article}
\usepackage{amsmath}
\usepackage{amssymb}
\usepackage{array}
\usepackage{booktabs}
\usepackage{graphicx}
\usepackage{fontspec}
% Times-like text face (TeX Gyre Termes), matching the Wiley journal look.
\setmainfont{texgyretermes}[Extension=.otf, UprightFont=*-regular,
  BoldFont=*-bold, ItalicFont=*-italic, BoldItalicFont=*-bolditalic]
\usepackage[a4paper,margin=2.5cm]{geometry}
\usepackage{titlesec}
\usepackage{caption}
\usepackage[hidelinks]{hyperref}
\graphicspath{{./figs/}}
\emergencystretch=2em
\makeatletter\def\UrlBreaks{\do\/\do\-\do\.}\makeatother

% Hindawi/Wiley numbered headings ("1. Introduction", "2.1. Datasets").
\titleformat{\section}{\large\bfseries}{\thesection.}{0.55em}{}
\titleformat{\subsection}{\normalsize\bfseries}{\thesubsection.}{0.55em}{}
\titlespacing*{\section}{0pt}{18pt plus 3pt minus 2pt}{7pt}
\titlespacing*{\subsection}{0pt}{13pt plus 2pt minus 2pt}{5pt}
\captionsetup{font=small,labelfont=bf,skip=7pt}
"""

TITLE = ("Multi-Horizon Failure-Risk Models for Battery Failure Prediction: "
         "How Much Cross-Chemistry Transfer Is a State-of-Health Shortcut?")

# Abstract trimmed to <=250 words (Hindawi abstract convention). Numbers unchanged.
ABSTRACT = r"""Predicting whether a lithium-ion cell will fail within a short operating window --- rather than estimating its remaining useful life --- is the question that matters for real-time dispatch in electric vehicles and grid storage. This study widens a recently proposed multi-horizon failure-risk framework, first shown on one model and dataset, into a validity-focused evaluation covering four model families, a discrete-time hazard model, trivial health-state baselines, and eight public aging datasets spanning four chemistries (LCO, LFP, NCA, and NMC) from six laboratories, under cell-disjoint splits and a leakage-clean, cross-fitted calibration protocol. Within-dataset discrimination is reliable: fold-mean area under the curve (AUC) is 0.90--0.96 across the tree ensembles. The central result is a controlled state-of-health (SOH) ablation: apparent cross-dataset transfer with SOH included (pooled AUC up to 1.00) collapses without SOH (at best 0.58 at $H{=}20$), and much of the with-SOH signal is reproducible by a distance-to-threshold rule on SOH alone (0.912 AUC on the 141-cell MIT--Stanford set). Because SOH also enters the failure definition, all with-SOH numbers are diagnostic-proximity upper bounds rather than pure prognosis: relabeling failures by voltage sag alone, a criterion SOH does not define, cuts with-SOH transfer by 0.17. Same-chemistry cross-laboratory controls confirm dataset shift drives the collapse at least as much as chemistry, and the findings replicate on 60 pre-registered NMC, NCA, and LFP cells from two other laboratories. Isotonic calibration largely fails to transfer, and the tree ensembles deploy on a \$12 ESP32-S3 in under a millisecond per inference on SRAM-resident models."""

KEYWORDS = ("battery failure prediction; prognostics and health management; "
            "multi-horizon failure-risk classification; state-of-health shortcut; "
            "cross-chemistry transfer; dataset shift; probability calibration; "
            "discrete-time hazard model; embedded machine learning")

FRONT = r"""\begin{document}

\begin{center}
{\LARGE\bfseries """ + TITLE + r"""\par}
\vspace{16pt}
{\large Hussain Touhid Siddiquee\textsuperscript{1}, Syeda Salsabil Islam\textsuperscript{1}, Jasimul Islam Chowdhury\textsuperscript{1}, and Farzana Hoque Eshica\textsuperscript{1}\par}
\vspace{9pt}
\textsuperscript{1}Department of Electrical and Electronic Engineering, Leading University, Sylhet, Bangladesh\par
\vspace{7pt}
{\itshape Correspondence: Hussain Touhid Siddiquee, touhidsiddiqueeraj@gmail.com\par}
\end{center}
\vspace{14pt}

\noindent\textbf{Abstract}\\[2pt]
""" + ABSTRACT + r"""

\medskip
\noindent\textbf{Keywords:} """ + KEYWORDS + r"""

\vspace{4pt}
"""

DECLARATIONS = r"""
% ======================================================================
% Declarations (Wiley/Hindawi open-access article structure).
% ======================================================================
\section*{Funding}
This research received no specific grant from any funding agency in the public, commercial, or not-for-profit sectors.

\section*{Conflict of Interest}
The authors declare that they have no known competing financial interests or personal relationships that could have appeared to influence the work reported in this paper.

\section*{Data Availability}
All datasets analyzed in this study are publicly available from the repositories cited in Section~2.2 (the NASA Ames prognostics data repository, the CALCE Battery Data Center, the Oxford degradation dataset, the MIT--Stanford dataset, and the Battery Archive cycle-test export). No new data were created. All reported values were produced by a version-locked analysis pipeline, and the Supplementary Material documents the complete tabular results.

\section*{Author Contributions}
Conceptualization, methodology, software, formal analysis, and writing --- original draft: Hussain Touhid Siddiquee. Data curation, validation, and visualization: Syeda Salsabil Islam, Jasimul Islam Chowdhury, and Farzana Hoque Eshica. Writing --- review and editing: all authors. All authors have read and agreed to the final version of the manuscript.

"""

# ---------------------------------------------------------------- main conversion
main = (SRC / "main_tr.tex").read_text()

# Body = from \section{Introduction} onward.
body_start = main.index("\\section{Introduction}")
body = main[body_start:]

# Drop IEEE biographies: keep everything up to the biography comment block.
bio_idx = body.index("% ======================================================================\n% Author biographies")
body = body[:bio_idx].rstrip() + "\n"
body = body.replace("\\end{document}", "")

# Insert declarations before the references comment block / thebibliography.
bib_idx = body.index("\\begin{thebibliography}")
# find the comment block right before the bibliography (provenance note)
ref_note = body.rfind("% ======================================================================", 0, bib_idx)
body = body[:ref_note] + DECLARATIONS + body[ref_note:]

body = body_transforms(body)
body = strip_months_in_refs(body)


def fit_wide_tables(text):
    """The IEEE two-column table* floats were sized for an ~18.2cm span; the
    A4 single-column frame is 16cm. Fit the two over-wide tables."""
    # Table 1 (lit comparison): narrow the label columns, keep capability
    # columns wide enough for bold unhyphenated headers ("Calibration"),
    # tighten colsep. Frame = 16 cm.
    text = text.replace(
        "\\setlength{\\tabcolsep}{4pt}\n"
        "\\begin{tabular}{>{\\raggedright\\arraybackslash}p{2.3cm}>{\\raggedright\\arraybackslash}p{1.35cm}*{7}{>{\\centering\\arraybackslash}p{1.55cm}}}",
        "\\setlength{\\tabcolsep}{2pt}\n"
        "\\begin{tabular}{>{\\raggedright\\arraybackslash}p{2.0cm}>{\\raggedright\\arraybackslash}p{1.2cm}*{7}{>{\\centering\\arraybackslash}p{1.63cm}}}",
    )
    # Minimal-baselines table: value + [CI] cells wrap onto two lines in p-cols;
    # colsep tightened 4pt -> 3pt to fit the 16 cm frame.
    text = text.replace(
        "\\footnotesize\n"
        "\\setlength{\\tabcolsep}{4pt}\n"
        "\\begin{tabular}{lcccccc}\n"
        "\\toprule\n"
        " & \\multicolumn{3}{c}{\\textbf{Oxford}} & \\multicolumn{3}{c}{\\textbf{Severson}}\\\\",
        "\\footnotesize\n"
        "\\setlength{\\tabcolsep}{3pt}\n"
        "\\begin{tabular}{>{\\raggedright\\arraybackslash}p{2.0cm}*{6}{>{\\raggedright\\arraybackslash}p{2.05cm}}}\n"
        "\\toprule\n"
        " & \\multicolumn{3}{c}{\\textbf{Oxford}} & \\multicolumn{3}{c}{\\textbf{Severson}}\\\\",
    )
    return text


body = fit_wide_tables(body)

main_out = PREAMBLE + FRONT + body + "\\end{document}\n"

DST.mkdir(exist_ok=True)
(DST / "figs").mkdir(exist_ok=True)
for f in (SRC / "figs").glob("*.png"):
    shutil.copy2(f, DST / "figs" / f.name)
(DST / "main_itees.tex").write_text(main_out)

# abstract word count
abs_plain = re.sub(r"\\[a-zA-Z]+|[{}$\\]", " ", ABSTRACT)
print(f"main_itees.tex written; abstract = {len(abs_plain.split())} words")

# ---------------------------------------------------------------- supplement
sup = (SRC / "supplement_tr.tex").read_text()
s_body_start = sup.index("This supplement provides")
s_body = sup[s_body_start:]

SUP_FRONT = r"""\begin{document}

\begin{center}
{\LARGE\bfseries Supplementary Material\par}
\vspace{10pt}
{\large\bfseries for ``""" + TITLE + r"""''\par}
\vspace{12pt}
{\normalsize Hussain Touhid Siddiquee\textsuperscript{1}, Syeda Salsabil Islam\textsuperscript{1}, Jasimul Islam Chowdhury\textsuperscript{1}, and Farzana Hoque Eshica\textsuperscript{1}\par}
\vspace{7pt}
\textsuperscript{1}Department of Electrical and Electronic Engineering, Leading University, Sylhet, Bangladesh\par
\end{center}
\vspace{12pt}
"""

s_body = body_transforms(s_body)
sup_out = PREAMBLE.replace("main_itees.tex", "supplement_itees.tex") + SUP_FRONT + s_body
(DST / "supplement_itees.tex").write_text(sup_out)
print("supplement_itees.tex written")

# diagnostics: any leftover IEEE markers or Roman refs?
for name, txt in [("main", main_out), ("supp", sup_out)]:
    leftovers = re.findall(r"Section~[IVX]+|Fig\.~|IEEE[a-z]+|table\*|figure\*", txt)
    print(f"{name}: leftovers = {leftovers if leftovers else 'none'}")
