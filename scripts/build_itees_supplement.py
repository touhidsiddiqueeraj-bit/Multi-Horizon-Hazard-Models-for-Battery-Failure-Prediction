#!/usr/bin/env python3
"""Build supplement_ITEES.tex (Wiley ITEES style) from paper_tr/supplement_tr.tex.

- Drops the IEEEtran preamble for the same single-column article style as
  main_itees.tex.
- Wiley supplement conventions: sections numbered S1..., tables S1...,
  equations S1...
- Reframes the recalibration section title: the under-review companion study
  was removed from the bibliography, and the arms are this study's own
  experiment (matching the main paper).
"""
import re

SRC = "/home/z/my-project/download/paper_tr/supplement_tr.tex"
DST = "/home/z/my-project/download/itees_package/supplement_ITEES.tex"

src = open(SRC).read()

# body: from the first prose line after \maketitle to before \end{document}
body_start = src.index("This supplement provides the detailed tables")
body = src[body_start:src.index("\\end{document}")].rstrip()

# framing fix: the arms are this study's own experiment
body = body.replace(
    "\\section{Small-Sample Recalibration (Companion-Study Arms)}",
    "\\section{Small-Sample Recalibration (Arms A and B)}",
)
assert "Companion" not in body and "companion" not in body, "companion framing left behind"

# keep the title block first on page 1: allow here-placement for floats
body = body.replace("\\begin{table*}[!t]", "\\begin{table*}[!htbp]")
body = body.replace("\\begin{table}[!t]", "\\begin{table}[!htbp]")

preamble = r"""% ======================================================================
% ITEES supplementary material (International Transactions on Electrical
% Energy Systems -- Wiley Forward Series). Companion to main_itees.tex;
% every number is generated from the validated results (results_v2/
% paper_numbers.json), identical to the IEEE TR supplement.
% Wiley supplement conventions: sections S1..., tables S1..., equations S1...
% Compile: tectonic supplement_ITEES.tex
% ======================================================================
\documentclass[11pt,a4paper]{article}
\usepackage[margin=2.2cm]{geometry}
\usepackage{amsmath}
\usepackage{amssymb}
\usepackage{array}
\usepackage{booktabs}
\usepackage{graphicx}
\usepackage{fontspec}
\setmainfont{texgyretermes}[Extension=.otf, UprightFont=*-regular,
  BoldFont=*-bold, ItalicFont=*-italic, BoldItalicFont=*-bolditalic]
\usepackage[hidelinks]{hyperref}
\graphicspath{{./figs/}}
\emergencystretch=2em
\makeatletter\def\UrlBreaks{\do\/\do\-\do\.}\makeatother
\renewcommand{\thesection}{S\arabic{section}}
\renewcommand{\thetable}{S\arabic{table}}
\renewcommand{\theequation}{S\arabic{equation}}
\linespread{1.06}
\setlength{\parskip}{2pt}
\begin{document}

\begin{center}
  {\LARGE\bfseries Supplementary Material for\\[4pt]
   ``Multi-Horizon Failure-Risk Models for Battery Failure Prediction:
   How Much Cross-Chemistry Transfer Is a State-of-Health Shortcut?''\par}
  \vspace{1.2em}
  {\normalsize Hussain Touhid Siddiquee,
   Syeda Salsabil Islam,
   Jasimul Islam Chowdhury, and
   Farzana Hoque Eshica\par}
  \vspace{0.7em}
  {\small Department of Electrical and Electronic Engineering, Leading University,\par
   Ragib Nagar, Kamal Bazar, South Surma, Sylhet 3110, Bangladesh\par}
\end{center}

\vspace{1.2em}

\noindent
"""

out = preamble + body + "\n\\end{document}\n"
open(DST, "w").write(out)
print(f"OK wrote {DST} ({len(body)} body chars)")
