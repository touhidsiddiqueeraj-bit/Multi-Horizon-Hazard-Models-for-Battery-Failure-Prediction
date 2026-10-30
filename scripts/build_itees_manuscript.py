#!/usr/bin/env python3
"""Build main_itees.tex (Wiley ITEES submission format) from main_tr.tex.

ITEES (Wiley Forward Series) requirements implemented:
- abstract <= 300 words (266 words, kept verbatim)
- numbered square-bracket references in citation order (any style accepted)
- no page limit -> single-column 11pt A4 for clean review
- title page: full author names, full institutional address, emails
- mandatory declarations (funding, conflicts of interest, data availability)
- figures embedded via \\graphicspath (already in manuscript PDF)
- section numbering kept as I, II, ... / II-A so "Section III-C" refs stay right
"""
import re

SRC = "/home/z/my-project/download/paper_tr/main_tr.tex"
DST = "/home/z/my-project/download/itees_package/main_itees.tex"

src = open(SRC).read()

# ---------- extract pieces ----------
abstract = re.search(r"\\begin\{abstract\}\n(.*?)\\end\{abstract\}", src, re.S).group(1).strip()
keywords = re.search(r"\\begin\{IEEEkeywords\}\n(.*?)\\end\{IEEEkeywords\}", src, re.S).group(1).strip().rstrip(".")

body_start = src.index("\\section{Introduction}")
refs_marker = src.index("% ======================================================================\n% References.")
body = src[body_start:refs_marker].rstrip()
refs_part = src[refs_marker:].rstrip()  # includes \end{thebibliography}
# Wiley ITEES manuscripts do not carry IEEE author-biography blocks: cut them.
bio_marker = refs_part.index("% Author biographies")
refs_part = refs_part[:refs_part.rindex("% ======================================================================", 0, bio_marker)].rstrip() + "\n\\end{document}\n"

# ---------- body adjustments ----------
body = body.replace("LITHIUM-ION batteries underpin", "Lithium-ion batteries underpin")
# shrink the 9-column comparison table for single-column width (16.6 cm text)
body = body.replace(
    ">p{2.3cm}>{\\raggedright\\arraybackslash}p{1.35cm}*{7}{>{\\centering\\arraybackslash}p{1.55cm}}",
    ">p{2.1cm}>{\\raggedright\\arraybackslash}p{1.25cm}*{7}{>{\\centering\\arraybackslash}p{1.42cm}}",
)
first_tabcolsep = body.index("\\setlength{\\tabcolsep}{4pt}")
body = body[:first_tabcolsep] + "\\setlength{\\tabcolsep}{3pt}" + body[first_tabcolsep + len("\\setlength{\\tabcolsep}{4pt}"):]

# wide 6-column CI baselines table: shrink font + column separation
body = body.replace(
    "\\footnotesize\n\\setlength{\\tabcolsep}{4pt}\n\\begin{tabular}{lcccccc}",
    "\\scriptsize\n\\setlength{\\tabcolsep}{2.5pt}\n\\begin{tabular}{lcccccc}",
)

for token in ("IEEE", "markboth", "IEEEkeywords", "\\thanks", "\\appendix", "Acknowledg"):
    if token in body:
        print(f"WARNING: token {token!r} still present in body")

preamble = r"""% ======================================================================
% ITEES submission manuscript (International Transactions on Electrical
% Energy Systems -- Wiley Forward Series, eISSN 2050-7038).
% Converted from the IEEE TR version (paper_tr/main_tr.tex).
% Journal rules applied: abstract <=300 words; numbered square-bracket
% references in citation order (any style accepted); no page limit;
% mandatory funding / conflict-of-interest / data-availability statements;
% figures embedded in the manuscript PDF.
% Compile: tectonic main_itees.tex
% ======================================================================
\documentclass[11pt,a4paper]{article}
\usepackage[margin=2.2cm]{geometry}
\usepackage{amsmath}
\usepackage{amssymb}
\usepackage{array}
\usepackage{booktabs}
\usepackage{graphicx}
\usepackage{fontspec}
% Times text (as in the IEEE version); math stays Computer Modern.
\setmainfont{texgyretermes}[Extension=.otf, UprightFont=*-regular,
  BoldFont=*-bold, ItalicFont=*-italic, BoldItalicFont=*-bolditalic]
\usepackage[hidelinks]{hyperref}
\graphicspath{{./figs/}}
\emergencystretch=2em
\makeatletter\def\UrlBreaks{\do\/\do\-\do\.}\makeatother
% Keep Roman section / lettered subsection numbering so cross-references
% such as "Section III-C" remain correct.
\renewcommand{\thesection}{\Roman{section}}
\renewcommand{\thesubsection}{\thesection-\Alph{subsection}}
\renewcommand{\thesubsubsection}{\thesection-\Alph{subsection}.\arabic{subsubsection}}
\linespread{1.06}
\setlength{\parskip}{2pt}
\begin{document}

\begin{center}
  {\LARGE\bfseries Multi-Horizon Failure-Risk Models for Battery Failure
   Prediction: How Much Cross-Chemistry Transfer Is a State-of-Health
   Shortcut?\par}
  \vspace{1.6em}
  {\normalsize Hussain Touhid Siddiquee\textsuperscript{\,*},
   Syeda Salsabil Islam,
   Jasimul Islam Chowdhury, and
   Farzana Hoque Eshica\par}
  \vspace{0.9em}
  {\small Department of Electrical and Electronic Engineering, Leading University,\par
   Ragib Nagar, Kamal Bazar, South Surma, Sylhet 3110, Bangladesh\par}
  \vspace{0.7em}
  {\small $^{*}$Corresponding author: Hussain Touhid Siddiquee\\
   \mbox{touhidsiddiqueeraj@gmail.com}; \mbox{salsabil.ariyaa@gmail.com};\\
   \mbox{chowdhuryjasimul@gmail.com}; \mbox{ishicafhaque@gmail.com}\par}
\end{center}

\vspace{1.4em}

\begin{quote}\small
\textbf{Abstract.} @@ABSTRACT@@
\end{quote}

\medskip
\noindent\textbf{Keywords:} @@KEYWORDS@@

\bigskip
\noindent
""".replace("@@ABSTRACT@@", abstract).replace("@@KEYWORDS@@", keywords)

declarations = r"""
\section*{Declarations}
\subsection*{Funding}
This research received no specific grant from any funding agency in the public, commercial, or not-for-profit sectors.

\subsection*{Conflicts of interest}
The authors declare no conflicts of interest relevant to this work.

\subsection*{Data availability}
All datasets analyzed in this study are publicly available from the repositories cited in the reference list, including the battery data archive and the original dataset publications. Additional tables supporting the monotonicity and recalibration analyses are provided in the Supplementary Material.

"""

out = preamble + body + "\n" + declarations + refs_part

# the source tail already ends with \end{thebibliography}; ensure \end{document}
if "\\end{document}" not in out:
    out += "\n\\end{document}\n"

open(DST, "w").write(out)
words = len(re.sub(r"\\[a-zA-Z]+|[{}$\\%]", " ", abstract).split())
print(f"OK wrote {DST}")
print(f"abstract words: {words} (limit 300)")
print(f"body length: {len(body)} chars; refs part: {len(refs_part)} chars")
