#!/usr/bin/env python3
"""Build the Journal of Power Sources (Elsevier) submission package.

Reads paper_jest/main_condensed.tex (the condensed manuscript, itself
generated from paper_ieee_access/main_access.tex) and emits
paper_jps/main_jps.tex on the elsarticle preprint class with the real
author front matter, arabic section numbering with the body's literal
Roman references remapped (JPS style is 1.1), and the mandatory Elsevier
declaration sections (CRediT, competing interest, funding, data
availability) ahead of the references.

JPS caps a Research Paper at 8,000 words and 8 main-manuscript figures,
checked here: the condensed body carries 3 figures (11 further figures
plus 15 tables go to the supplement, which JPS permits).

Also writes highlights.txt (3-5 bullets, <=85 chars, plain text),
cover_letter.txt, declaration_of_interests.txt, README.md, and copies
the figures used plus the graphical abstract.
"""
import os
import re
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "paper_jest", "main_condensed.tex")
SUPPL_SRC = os.path.join(ROOT, "paper_jest", "supplement.tex")
FIGSRC = os.path.join(ROOT, "paper_jest", "figs")
GA_SRC = os.path.join(ROOT, "paper", "Graphical_Abstract.png")
OUTDIR = os.path.join(ROOT, "paper_jps")
FIGDST = os.path.join(OUTDIR, "figs")

AUTHORS = [
    ("Hussain Touhid Siddiquee", "touhidsiddiqueeraj@gmail.com"),
    ("Jasimul Islam Chowdhury", "chowdhuryjasimul@gmail.com"),
    ("Syeda Salsabil Islam Ariya", "salsabil.ariyaa@gmail.com"),
    ("Farzana Hoque Eshica", "ishicafhaque@gmail.com"),
]
ADDRESS = "Leading University, Sylhet 3100, Bangladesh"
EMAIL = AUTHORS[0][1]
REPO_URL = ("https://github.com/touhidsiddiqueeraj-bit/"
            "Multi-Horizon-Hazard-Models-for-Battery-Failure-Prediction")

TITLE = ("Multi-Horizon Failure-Risk Models for Battery Failure Prediction: "
         "How Much Cross-Chemistry Transfer Is a State-of-Health Shortcut?")

# Condensed abstract (161 words) already under the JPS 200-word cap.
ABSTRACT = (
    "Predicting whether a lithium-ion cell will fail inside a short operating window "
    "matters more for real-time dispatch than remaining-useful-life regression. This study "
    "widens a multi-horizon failure-risk classification framework into a validity-focused "
    "evaluation covering tree ensembles, a GRU classifier, a discrete-time hazard model, "
    "and 60 new Battery Archive cells from two further laboratories, in an evaluation spanning "
    "six laboratories in total. Within-dataset discrimination "
    "is reliable (fold-mean AUC 0.90--0.96 across the tree ensembles). The central result is a controlled State-of-Health "
    "(SOH) ablation: apparent cross-dataset transfer with SOH (pooled AUC up to 1.00) collapses "
    "without it, and an unfitted SOH distance rule matches the tuned ensembles. Because SOH "
    "enters the failure label and the label window includes the current cycle, with-SOH numbers "
    "are diagnostic-proximity upper bounds: prognosis-only evaluation gives 0.838 on Severson. "
    "Same-chemistry controls show dataset shift matters at least as much as chemistry. "
    "Source-fitted calibration does not transfer, and the ensembles deploy on a \\$12 "
    "microcontroller in under a millisecond per SRAM-resident model."
)

KEYWORDS = ("battery failure prediction \\sep state-of-health shortcut "
            "\\sep cross-dataset transfer \\sep probability calibration "
            "\\sep discrete-time hazard model \\sep embedded machine learning")

HIGHLIGHTS = (
    "Cross-dataset battery failure-risk transfer is mostly a health-state shortcut\n"
    "Removing SOH collapses transfer; a threshold rule matches tuned ensembles\n"
    "Dataset shift matters at least as much as chemistry shift for transfer\n"
    "Source-fitted calibration fails under shift; thresholds rarely transfer\n"
    "Tree ensembles run on a low-cost microcontroller in under a millisecond\n"
)

ROMAN = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6, "VII": 7}


def grab(pattern, text, name):
    m = re.search(pattern, text, re.S)
    if not m:
        print(f"missing {name}", file=sys.stderr)
        sys.exit(1)
    return m.group(1).strip()


def build_section_map(body):
    """Parse \\section/\\subsection order -> {(roman, letter): '3.6'}."""
    sec, nsub, smap = 0, 0, {}
    for m in re.finditer(r"\\(section|subsection)\{", body):
        if m.group(1) == "section":
            sec += 1
            nsub = 0
        else:
            nsub += 1
            letter = chr(ord("A") + nsub - 1)
            smap[(list(ROMAN)[sec - 1], letter)] = f"{sec}.{nsub}"
    return smap


def remap_section_refs(body, smap):
    tok = r"[IVX]+(?:-[A-Z])?(?![a-z])"

    def one(t):
        sec, _, letter = t.partition("-")
        if letter:
            v = smap.get((sec, letter))
            return str(v) if v is not None else None
        return str(ROMAN[sec]) if sec in ROMAN else None

    def sub(m):
        v = one(m.group(3))
        if v is None:
            print(f"WARNING: unmapped section ref {m.group(0)}", file=sys.stderr)
            return m.group(0)
        sep = "~" if m.group(2) == "~" else " "
        tail = re.sub(
            r"([~ ]and[~ ]|--)(%s)" % tok,
            lambda rm: rm.group(1) + (one(rm.group(2)) or rm.group(2)),
            m.group(4))
        return m.group(1) + sep + v + tail

    # "Section~III-F", "Section II-B" (plain space, e.g. in captions),
    # bare "Section~IV", and conjunction/range tails "and~III-G", "--III-E".
    return re.sub(
        r"(Sections?)([~ ])(%s)((?:[~ ]and[~ ]%s|--%s)*)" % (tok, tok, tok),
        sub, body)


def word_count(tex):
    seg = re.sub(r"\\begin\{(figure|table)\*?\}.*?\\end\{(figure|table)\*?\}",
                 " ", tex, flags=re.S)
    seg = re.sub(r"\\begin\{thebibliography\}.*?\\end\{thebibliography\}",
                 " ", seg, flags=re.S)
    seg = re.sub(r"\\[a-zA-Z]+\*?(\[[^\]]*\])?(\{[^{}]*\})?", " ", seg)
    seg = re.sub(r"[{}$&%\\]", " ", seg)
    return len(seg.split())


def main():
    text = open(SRC).read()

    src_abstract = grab(r"\\begin\{abstract\}\n(.+?)\\end\{abstract\}", text, "abstract")
    # The script abstract must stay in sync with the condensed source.
    assert re.sub(r"\s+", " ", src_abstract) == re.sub(r"\s+", " ", ABSTRACT), \
        "condensed abstract drifted; update ABSTRACT"

    body = grab(r"\\end\{frontmatter\}\n(.+)\\begin\{thebibliography\}", text, "body")
    bib = grab(r"(\\begin\{thebibliography\}.*\\end\{thebibliography\})", text, "bib")

    # Arabic section numbering (JPS style 1.1): remap the literal Roman refs.
    body = remap_section_refs(body, build_section_map(body))
    tok = r"[IVX]+(?:-[A-Z])?(?![a-z])"
    assert not re.search(r"Sections?[~ ]" + tok, body), "roman refs remain"
    assert not re.search(r"and[~ ]" + tok + r"|--" + tok, body), \
        "roman refs remain in conjunction/range tails"

    # Source bug (inherited via the condensed port): unescaped % comments out
    # the rest of the prognosis sentence in the rendered PDF.
    body = re.sub(r"(\d+)% above", r"\1\\% above", body)
    assert not re.search(r"\d% ", body), "unescaped percent left in body"

    # Source placeholder never filled upstream: put the real bootstrap CI in
    # (baselines_transfer.csv, soh_dist / nasa+calce / severson / H=20).
    old_ci = "transfers to Severson at pooled AUC 0.912 [CI] for the ALL-LCO source"
    assert old_ci in body, "expected the 0.912 [CI] placeholder"
    body = body.replace(old_ci,
        "transfers to Severson at pooled AUC 0.912 [0.836, 0.998] for the ALL-LCO source")

    # Replace the anonymous Acknowledgment stub (up to \raggedbottom) with
    # the mandatory Elsevier declaration sections.
    decl = (
        "\\section*{CRediT authorship contribution statement}\n"
        "\\textbf{Hussain Touhid Siddiquee}: Conceptualization, Methodology, "
        "Software, Formal analysis, Investigation, Data curation, "
        "Visualization, Writing --- original draft. "
        "\\textbf{Jasimul Islam Chowdhury}: Validation, Writing --- review "
        "\\& editing. \\textbf{Syeda Salsabil Islam Ariya}: Data curation, "
        "Writing --- review \\& editing. \\textbf{Farzana Hoque Eshica}: "
        "Investigation, Writing --- review \\& editing.\n\n"
        "\\section*{Declaration of competing interest}\n"
        "The authors declare that they have no known competing financial "
        "interests or personal relationships that could have appeared to "
        "influence the work reported in this paper.\n\n"
        "\\section*{Funding}\n"
        "This research did not receive any specific grant from funding "
        "agencies in the public, commercial, or not-for-profit sectors.\n\n"
        "\\section*{Data availability}\n"
        "All datasets analyzed in this study are publicly available: the "
        "NASA/MIT--Stanford Severson, Oxford, CALCE, HNEI, and Sandia (SNL) "
        "battery datasets, and the public Battery Archive compilation used "
        "for the replication study. The complete source code, trained models, "
        "embedded firmware, and validation "
        f"pipeline are openly available at \\url{{{REPO_URL}}}.\n"
    )
    decl_tail = "\\clearpage\n" + decl + "\n\\raggedbottom\n\\clearpage\n"
    body = re.sub(r"\\clearpage\s*\\section\*\{Acknowledgment\}.*?"
                  r"\\raggedbottom\s*$",
                  lambda m: decl_tail, body, flags=re.S)
    assert "Acknowledgment" not in body, "anonymous acknowledgment stub survived"

    n_fig = len(re.findall(r"\\begin\{figure", body))
    n_tab = len(re.findall(r"\\begin\{table", body))
    assert n_fig <= 8, f"{n_fig} figures exceed the JPS 8-figure cap"
    assert len(ABSTRACT.split()) <= 200, "abstract over 200 words"
    assert len(KEYWORDS.split("\\sep")) <= 7, "more than 7 keywords"
    for i, line in enumerate(HIGHLIGHTS.splitlines(), 1):
        assert len(line) <= 85, f"highlight {i} too long ({len(line)} chars)"
        assert "$" not in line and "\\" not in line, f"highlight {i} not plain text"

    out = (
        "\\documentclass[preprint,12pt]{elsarticle}\n"
        "\\usepackage{amsmath}\n"
        "\\usepackage{booktabs}\n"
        "\\usepackage{graphicx}\n"
        "\\usepackage[colorlinks=true]{hyperref}\n"
        # Keep long typewriter words and URLs inside the preprint margins.
        "\\emergencystretch=3em\n"
        "\\makeatletter\\def\\UrlBreaks{\\do\\/\\do\\-\\do\\.\\do\\_}\\makeatother\n"
        "\\graphicspath{{./figs/}}\n"
        "\\journal{Journal of Power Sources}\n"
        "\\begin{document}\n"
        "\\begin{frontmatter}\n"
        f"\\title{{{TITLE}}}\n"
        + "".join(
            (f"\\author[1]{{{name}}}\\corref{{cor1}}\n\\ead{{{mail}}}\n"
             "\\cortext[cor1]{Corresponding author.}\n") if i == 0 else
            f"\\author[1]{{{name}}}\n"
            for i, (name, mail) in enumerate(AUTHORS))
        + f"\\address[1]{{{ADDRESS}}}\n"
        "\\begin{abstract}\n" + ABSTRACT + "\n\\end{abstract}\n"
        "\\begin{keyword}\n" + KEYWORDS + "\n\\end{keyword}\n"
        "\\end{frontmatter}\n\n"
        + body + "\n"
        + bib + "\n"
        "\\end{document}\n"
    )
    os.makedirs(OUTDIR, exist_ok=True)
    with open(os.path.join(OUTDIR, "main_jps.tex"), "w") as fh:
        fh.write(out)

    suppl = open(SUPPL_SRC).read()
    with open(os.path.join(OUTDIR, "supplement.tex"), "w") as fh:
        fh.write(suppl)

    wc = word_count(ABSTRACT + "\n" + body)
    assert wc <= 8000, f"word count {wc} exceeds the JPS 8000 cap"
    n_sfig = len(re.findall(r"\\begin\{figure", suppl))
    n_stab = len(re.findall(r"\\begin\{table", suppl))
    print(f"wrote paper_jps/main_jps.tex ({len(out)} bytes, {wc} words < 8000)")
    print(f"main: {n_fig} figures (cap 8), {n_tab} tables; "
          f"supplement: {n_sfig} figures, {n_stab} tables")

    os.makedirs(FIGDST, exist_ok=True)
    used_figs = sorted(set(
        re.findall(r"\\includegraphics\[[^\]]*\]\{(.+?)\}", body)
        + re.findall(r"\\includegraphics\[[^\]]*\]\{(.+?)\}", suppl)))
    for fig in used_figs:
        for ext in ("", ".png", ".pdf", ".jpg"):
            src = os.path.join(FIGSRC, fig + ext)
            if os.path.exists(src):
                shutil.copy(src, os.path.join(FIGDST, os.path.basename(src)))
                break
        else:
            print(f"WARNING: figure not found: {fig}", file=sys.stderr)
    print(f"copied {len(used_figs)} used figures")
    shutil.copy(GA_SRC, os.path.join(OUTDIR, "graphical_abstract.png"))

    with open(os.path.join(OUTDIR, "highlights.txt"), "w") as fh:
        fh.write(HIGHLIGHTS)
    write_cover_letter(wc, n_fig)
    write_declarations()
    write_readme(wc, n_fig, n_tab, n_sfig, n_stab, len(used_figs))


def write_cover_letter(wc, n_fig):
    letter = f"""Dear Editor,

Please find enclosed our manuscript "{TITLE}" for consideration as a
Research Paper in the Journal of Power Sources.

Instead of remaining-useful-life regression, we study multi-horizon
failure-risk classification --- whether a cell fails within the next H
cycles --- and subject it to a validity analysis across eight datasets
(NASA, CALCE, Oxford, Severson, and 60 new Battery Archive NMC/NCA/LFP
cells from two further laboratories), four model families, leakage-clean
calibration, and an ESP32-S3 deployment. The central finding is a
cautionary negative result: apparent cross-dataset transfer is largely a
State-of-Health shortcut, reproducible by an unfitted threshold rule,
while sensor features carry no cross-dataset signal. Same-chemistry
cross-laboratory controls show dataset shift matters at least as much as
chemistry shift, and source-fitted calibration does not survive shift.
The work speaks to the journal's diagnostics, degradation-and-aging, and
system-integration coverage: failure-risk validity, calibration under
shift, and microcontroller deployment for battery management.

This manuscript is original, has not been published previously, and is
not under consideration by any other journal. All datasets are public,
and the complete code, models, firmware, and validation pipeline are
openly available at {REPO_URL}.
The authors declare no competing interests and received no external
funding for this work.

Compliance note: the manuscript is ~{wc} words of main prose (Research
Paper limit 8,000, excluding abstract/figures/tables/references) with
{n_fig} figures (limit 8; further figures and tables are provided as
Supplementary Material), a {len(ABSTRACT.split())}-word abstract (limit
200), {len(KEYWORDS.split(chr(92) + 'sep'))} keywords, and Highlights and
a graphical abstract are included.

Sincerely,

{AUTHORS[0][0]} (corresponding author), on behalf of all authors
{ADDRESS}
E-mail: {EMAIL}
"""
    with open(os.path.join(OUTDIR, "cover_letter.txt"), "w") as fh:
        fh.write(letter)


def write_declarations():
    txt = (
        "Declaration of interests\n"
        "\n"
        "The authors declare that they have no known competing financial\n"
        "interests or personal relationships that could have appeared to\n"
        "influence the work reported in this paper.\n"
        "\n"
        "Funding: This research did not receive any specific grant from funding\n"
        "agencies in the public, commercial, or not-for-profit sectors.\n"
        "\n"
        "Authors: " + "; ".join(name for name, _ in AUTHORS) + "\n"
        "Corresponding author: " + AUTHORS[0][0] + ", " + ADDRESS + "\n"
    )
    with open(os.path.join(OUTDIR, "declaration_of_interests.txt"), "w") as fh:
        fh.write(txt)


def write_readme(wc, n_fig, n_tab, n_sfig, n_stab, n_figfiles):
    md = f"""# JPS submission package

Target journal: **Journal of Power Sources** (Elsevier, ISSN 0378-7753),
Elsevier "Your Paper Your Way" (flexible format at first submission).

## Files

| File | Purpose |
| --- | --- |
| `main_jps.tex` / `main_jps.pdf` | Manuscript (elsarticle preprint, 12pt, single column) |
| `supplement.tex` / `supplement.pdf` | Supplementary Material ({n_stab} tables + {n_sfig} figures) |
| `figs/` | Figures referenced by manuscript + supplement ({n_figfiles} files) |
| `graphical_abstract.png` | Graphical abstract, 2820x1820 px (minimum 1328x531) |
| `highlights.txt` | Highlights file (3-5 bullets, <=85 chars each) |
| `cover_letter.txt` | Editor cover letter |
| `declaration_of_interests.txt` | Competing-interest declaration (also in manuscript) |

## Compliance with the JPS Guide for Authors

| Requirement | JPS rule | This package |
| --- | --- | --- |
| Length (Research Paper) | max 8,000 words (excl. abstract/figs/tables/refs) | ~{wc} words |
| Main-manuscript figures | max 8 (extras as supplement) | {n_fig} (supplement holds {n_sfig} more) |
| Main-manuscript tables | no stated cap | {n_tab} |
| Abstract | <= 200 words | {len(ABSTRACT.split())} words |
| Keywords | 1-7 | {len(KEYWORDS.split(chr(92) + 'sep'))} |
| Highlights | 3-5 bullets, <= 85 chars | 5 bullets, max {max(len(l) for l in HIGHLIGHTS.splitlines())} chars |
| Graphical abstract | encouraged, min 1328x531 px | 2820x1820 px PNG |
| Section numbering | 1.1, 1.1.1 (arabic) | arabic; literal Roman refs remapped |
| References | numbered [n] in citation order | `thebibliography` in first-citation order |
| CRediT author statement | mandatory | in manuscript (before declarations) |
| Declaration of competing interest | mandatory | in manuscript + separate file |
| Funding statement | mandatory | in manuscript |
| Data availability | mandatory | in manuscript; all datasets public; code repo linked |
| Corresponding author | e-mail on title page | `{EMAIL}` |

## Build

```
python3 scripts/make_jps.py        # regenerate main_jps.tex + package files
cd paper_jps && pdflatex main_jps.tex && pdflatex main_jps.tex
```

`elsarticle.cls` ships with TeX Live (no extra TEXINPUTS needed).
The manuscript is derived from `paper_jest/main_condensed.tex` (which is
generated from `paper_ieee_access/main_access.tex`); the generator also
repairs two inherited source defects (unescaped `%` truncating the
prognosis sentence; unfilled `0.912 [CI]` placeholder) and asserts the
8-figure cap. Edit the upstream sources, not `main_jps.tex`.
"""
    with open(os.path.join(OUTDIR, "README.md"), "w") as fh:
        fh.write(md)


if __name__ == "__main__":
    main()
