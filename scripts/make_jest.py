#!/usr/bin/env python3
"""Build the Journal of Energy Storage (Elsevier) submission package.

Reads paper_ieee_access/main_access.tex (the generated IEEE Access paper)
and emits paper_jest/main_jest.tex on the elsarticle preprint class:
front matter rebuilt with elsarticle commands, body carried over verbatim
modulo IEEE-only commands, manual thebibliography kept (Your Paper Your
Way permits any reference format at initial submission).

Also writes paper_jest/highlights.txt (3-5 bullets, <=85 chars each,
Elsevier mandatory separate file) and copies only the figures actually
\\includegraphics'd.
"""
import os
import re
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "paper_ieee_access", "main_access.tex")
OUTDIR = os.path.join(ROOT, "paper_jest")
FIGSRC = os.path.join(ROOT, "paper_ieee_access", "figs")
FIGDST = os.path.join(OUTDIR, "figs")


def grab(pattern, text, name):
    m = re.search(pattern, text, re.S)
    if not m:
        print(f"missing {name}", file=sys.stderr)
        sys.exit(1)
    return m.group(1).strip()


def main():
    text = open(SRC).read()

    title = grab(r"\\title\{(.+?)\}\n", text, "title")
    abstract = grab(r"\\begin\{abstract\}\n(.+?)\\end\{abstract\}", text, "abstract")
    keywords = grab(r"\\begin\{keywords\}\n(.+?)\\end\{keywords\}", text, "keywords")
    body = grab(r"\\maketitle\n(.+)\\begin\{thebibliography\}", text, "body")
    bib = grab(r"(\\begin\{thebibliography\}.*\\end\{thebibliography\})", text, "bib")

    # Strip IEEE-Access-only commands from the body.
    body = re.sub(r"\\titlepgskip=-?\d+pt\n?", "", body)
    body = re.sub(r"\\emergencystretch=\d+em\n?", "", body)
    body = re.sub(r"\\makeatletter\\def\\UrlBreaks.*\\makeatother\n?", "", body)
    body = re.sub(r"\\markboth\{.*?\}\n?", "", body)
    # Starred floats are harmless in 1-column preprint, but normalize anyway.
    body = body.replace("\\begin{figure*}", "\\begin{figure}")
    body = body.replace("\\end{figure*}", "\\end{figure}")
    body = body.replace("\\begin{table*}", "\\begin{table}")
    body = body.replace("\\end{table*}", "\\end{table}")
    # Width overrides for the 1-column preprint layout: small-source figures
    # would print with sub-7pt type at their IEEE widths.
    body = body.replace(
        "\\includegraphics[width=0.62\\textwidth]{Fig01_Within_Dataset_AUC.png}",
        "\\includegraphics[width=1.0\\textwidth]{Fig01_Within_Dataset_AUC.png}")
    body = body.replace(
        "\\includegraphics[width=\\columnwidth]{fig_prauc_horizon.png}",
        "\\includegraphics[width=0.65\\textwidth]{fig_prauc_horizon.png}")
    body = body.replace(
        "\\includegraphics[width=0.5\\textwidth]{fig_netbenefit.png}",
        "\\includegraphics[width=0.75\\textwidth]{fig_netbenefit.png}")

    used_figs = sorted(set(re.findall(r"\\includegraphics\[[^\]]*\]\{(.+?)\}", body)))

    # Reorder bibitems into first-citation order (manual thebibliography
    # numbers by list position, so list order must match citation order).
    cited = []
    for m in re.finditer(r"\\cite\{([^}]+)\}", body):
        for key in m.group(1).split(","):
            key = key.strip()
            if key and key not in cited:
                cited.append(key)
    parts = re.findall(r"(\\bibitem\{(.*?)\}.*?)(?=\\bibitem\{|\Z)", bib, re.S)
    by_key = {}
    for b, k in parts:
        b = b.split("\\end{thebibliography}")[0]  # last match swallows the env end
        by_key[k] = b
    missing = [k for k in cited if k not in by_key]
    if missing:
        print(f"WARNING: cited keys without bibitem: {missing}", file=sys.stderr)
    ordered = [by_key[k] for k in cited if k in by_key]
    ordered += [b for b, k in parts if k not in cited]
    n_entries = len(re.findall(r"\\bibitem\{", bib))
    bib = ("\\begin{thebibliography}{99}\n"
           + "\n".join(b.strip() for b in ordered) + "\n"
           + "\\end{thebibliography}")
    assert len(cited) <= n_entries, "more cited keys than bibitems"

    out = (
        "\\documentclass[preprint,12pt]{elsarticle}\n"
        "\\usepackage{amsmath}\n"
        "\\usepackage{booktabs}\n"
        "\\usepackage{graphicx}\n"
        "\\usepackage[colorlinks=true]{hyperref}\n"
        # The ported body cites sections by IEEE Roman numbers (II-A, III-C…).
        "\\renewcommand{\\thesection}{\\Roman{section}}\n"
        "\\renewcommand{\\thesubsection}{\\thesection-\\Alph{subsection}}\n"
        "\\graphicspath{{./figs/}}\n"
        "\\begin{document}\n"
        "\\begin{frontmatter}\n"
        f"\\title{{{title}}}\n"
        "\\author{Anonymous}\n"
        "\\address{Affiliation 1, City, Country (e-mail: author1@example.com)}\n"
        "\\begin{abstract}\n" + abstract + "\n\\end{abstract}\n"
        "\\begin{keyword}\n" + keywords + "\n\\end{keyword}\n"
        "\\end{frontmatter}\n\n"
        + body + "\n"
        + bib + "\n"
        "\\end{document}\n"
    )
    os.makedirs(OUTDIR, exist_ok=True)
    with open(os.path.join(OUTDIR, "main_jest.tex"), "w") as fh:
        fh.write(out)

    os.makedirs(FIGDST, exist_ok=True)
    for fig in used_figs:
        for ext in ("", ".png", ".pdf", ".jpg"):
            src = os.path.join(FIGSRC, fig + ext)
            if os.path.exists(src):
                shutil.copy(src, os.path.join(FIGDST, os.path.basename(src)))
                break
        else:
            print(f"WARNING: figure not found: {fig}", file=sys.stderr)

    highlights = (
        "Cross-dataset battery failure-risk transfer is mostly a health-state shortcut\n"
        "Removing SOH collapses transfer; a threshold rule matches tuned ensembles\n"
        "Dataset shift matters at least as much as chemistry shift for transfer\n"
        "Source-fitted calibration fails under shift; thresholds rarely transfer\n"
        "Tree ensembles deploy on a $12 microcontroller in under a millisecond\n"
    )
    for i, line in enumerate(highlights.splitlines(), 1):
        assert len(line) <= 85, f"highlight {i} too long ({len(line)} chars)"
    with open(os.path.join(OUTDIR, "highlights.txt"), "w") as fh:
        fh.write(highlights)

    print(f"wrote paper_jest/main_jest.tex ({len(out)} bytes)")
    print(f"copied {len(used_figs)} used figures: {', '.join(used_figs)}")


if __name__ == "__main__":
    main()
