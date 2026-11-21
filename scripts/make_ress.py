#!/usr/bin/env python3
"""Build the Reliability Engineering & System Safety (Elsevier) submission package.

Reads paper_ieee_access/main_access.tex (the generated IEEE Access paper)
and emits paper_ress/main_ress.tex on the elsarticle preprint class with the
real author front matter, an abstract trimmed to the RESS 200-word cap,
7 keywords (RESS allows 1-7), arabic section numbering with the body's
literal Roman references remapped (RESS style is 1.1, 1.1.1), and the
mandatory RESS declaration sections (CRediT, competing interest, funding,
data availability) ahead of the references.

RESS has no page limit; the journal cap is 13,000 words, checked here.

Also writes highlights.txt (3-5 bullets, <=85 chars), cover_letter.txt,
declaration_of_interests.txt, README.md, and copies the figures used.
"""
import os
import re
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "paper_ieee_access", "main_access.tex")
OUTDIR = os.path.join(ROOT, "paper_ress")
FIGSRC = os.path.join(ROOT, "paper_ieee_access", "figs")
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

# RESS abstract cap is 200 words; this replaces the 356-word ACCESS abstract.
# Kept tight (~180 words) so the four-author front matter + Keywords all fit
# on the title page.
ABSTRACT = (
    "Predicting whether a lithium-ion cell will fail within a short operating "
    "window differs from estimating its remaining useful life, and it is the "
    "question that matters most for real-time dispatch. This study treats "
    "multi-horizon failure-risk classification as a validity question --- how "
    "much apparent cross-chemistry transfer is real --- comparing four model "
    "families, a true discrete-time hazard model, and trivial health-state "
    "baselines across six laboratories and four chemistries under "
    "cell-disjoint splits and leakage-clean, cross-fitted calibration. The "
    "central result is a controlled State-of-Health (SOH) ablation: transfer "
    "with SOH included (pooled AUC up to 1.00) collapses without it (at most "
    "0.75), and an unfitted distance-to-threshold rule on SOH reproduces most "
    "of the with-SOH signal (0.912 AUC on 141 Severson cells). Because SOH "
    "enters the failure label, with-SOH numbers are diagnostic-proximity "
    "upper bounds: voltage-sag relabeling alone cuts with-SOH transfer by "
    "0.17. Same-chemistry controls and a 60-cell replication on NMC, NCA and "
    "LFP confirm that the collapse is dataset shift as much as chemistry: "
    "with-SOH transfer spans 0.77--1.00 and falls to 0.36--0.91 without SOH. "
    "Source-fitted calibration fails to transfer; the ensembles deploy on a "
    "\\$12 microcontroller in under a millisecond."
)

KEYWORDS = ("Battery failure prediction \\sep "
            "multi-horizon failure-risk classification \\sep "
            "state-of-health shortcut \\sep cross-chemistry transfer \\sep "
            "probability calibration \\sep discrete-time hazard model \\sep "
            "embedded machine learning")

HIGHLIGHTS = (
    "Cross-dataset battery failure-risk transfer is mostly a health-state shortcut\n"
    "Removing SOH collapses transfer; a threshold rule matches tuned ensembles\n"
    "Dataset shift matters at least as much as chemistry shift for transfer\n"
    "Source-fitted calibration fails under shift; thresholds rarely transfer\n"
    "Tree ensembles deploy on a $12 microcontroller in under a millisecond\n"
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

    # Arabic section numbering (RESS style 1.1): remap the literal Roman refs.
    body = remap_section_refs(body, build_section_map(body))
    tok = r"[IVX]+(?:-[A-Z])?(?![a-z])"
    assert not re.search(r"Sections?[~ ]" + tok, body), "roman refs remain"
    assert not re.search(r"and[~ ]" + tok + r"|--" + tok, body), \
        "roman refs remain in conjunction/range tails"

    # Source bug: unescaped % comments out the rest of the prognosis sentence.
    body = re.sub(r"(\d+)% above", r"\1\\% above", body)
    assert not re.search(r"\d% ", body), "unescaped percent left in body"

    # Source placeholder never filled in ACCESS: put the real bootstrap CI in
    # (baselines_transfer.csv, soh_dist / nasa+calce / severson / H=20).
    old_ci = "transfers to Severson at pooled AUC 0.912 [CI] for the ALL-LCO source"
    assert old_ci in body, "expected the 0.912 [CI] placeholder"
    body = body.replace(old_ci,
        "transfers to Severson at pooled AUC 0.912 [0.836, 0.998] for the ALL-LCO source")

    # No supplement exists in this journal version; the monotonicity table is
    # Section 3.8's tab:mono in the same manuscript.
    old_sup = "violate monotonicity on 32--45\\% of rows (see Supplementary Material)"
    assert old_sup in body, "expected the monotonicity supplement pointer"
    body = body.replace(old_sup,
        "violate monotonicity on 32--45\\% of rows (Table~\\ref{tab:mono})")
    assert "Supplementary" not in body, "stale supplement pointers remain"

    # Replace the IEEE Acknowledgment stub (up to \raggedbottom) with the
    # mandatory RESS declaration sections.
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
        "for the replication study (provenance in Section 2.2). The complete "
        "source code, trained models, embedded firmware, and validation "
        f"pipeline are openly available at \\url{{{REPO_URL}}}.\n"
    )
    # Replace the IEEE Acknowledgment stub (through the trailing
    # \raggedbottom) with the mandatory RESS declaration sections. The
    # \clearpage before the declarations flushes pending floats onto plate
    # pages so no figure drifts past the references, and the \clearpage
    # after starts the bibliography on a fresh page (same order the ACCESS
    # paper uses: Conclusion -> \clearpage -> back matter -> \raggedbottom
    # \clearpage -> references).
    decl_tail = "\\clearpage\n" + decl + "\n\\raggedbottom\n\\clearpage\n"
    body = re.sub(r"\\clearpage\s*\\section\*\{Acknowledgment\}.*?"
                  r"\\raggedbottom\s*$",
                  lambda m: decl_tail, body, flags=re.S)
    assert "Acknowledgment" not in body, "IEEE acknowledgment stub survived"

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
    assert len(cited) <= n_entries, "more cited keys than bibitems"
    bib = ("\\begin{thebibliography}{99}\n"
           + "\n".join(b.strip() for b in ordered) + "\n"
           + "\\end{thebibliography}")

    assert len(ABSTRACT.split()) <= 200, f"abstract {len(ABSTRACT.split())} > 200 words"
    assert len(KEYWORDS.split("\\sep")) <= 7, "more than 7 keywords"
    for i, line in enumerate(HIGHLIGHTS.splitlines(), 1):
        assert len(line) <= 85, f"highlight {i} too long ({len(line)} chars)"

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
        "\\journal{Reliability Engineering \\& System Safety}\n"
        "\\begin{document}\n"
        "\\begin{frontmatter}\n"
        f"\\title{{{TITLE}}}\n"
        + "".join(
            (f"\\author[1]{{{name}}}\\corref{{cor1}}\n\\ead{{{mail}}}\n"
             "\\cortext[cor1]{Corresponding author.}\n") if i == 0 else
            f"\\author[1]{{{name}}}\n"
            for i, (name, mail) in enumerate(AUTHORS))
        + f"\\address[1]{{{ADDRESS}}}\n"
        # Keep Keywords on the title page: the 4-author block otherwise
        # pushes the keyword env to page 2 (and the footnote block eats
        # column height).
        "\\vspace{-2\\baselineskip}\n"
        "\\begin{abstract}\n" + ABSTRACT + "\n\\end{abstract}\n"
        "\\begin{keyword}\n" + KEYWORDS + "\n\\end{keyword}\n"
        "\\end{frontmatter}\n\n"
        + body + "\n"
        + bib + "\n"
        "\\end{document}\n"
    )
    os.makedirs(OUTDIR, exist_ok=True)
    with open(os.path.join(OUTDIR, "main_ress.tex"), "w") as fh:
        fh.write(out)

    wc = word_count(ABSTRACT + "\n" + body)
    assert wc <= 13000, f"word count {wc} exceeds the RESS 13000 cap"
    print(f"wrote paper_ress/main_ress.tex ({len(out)} bytes, {wc} words < 13000)")

    os.makedirs(FIGDST, exist_ok=True)
    used_figs = sorted(set(re.findall(r"\\includegraphics\[[^\]]*\]\{(.+?)\}", body)))
    for fig in used_figs:
        for ext in ("", ".png", ".pdf", ".jpg"):
            src = os.path.join(FIGSRC, fig + ext)
            if os.path.exists(src):
                shutil.copy(src, os.path.join(FIGDST, os.path.basename(src)))
                break
        else:
            print(f"WARNING: figure not found: {fig}", file=sys.stderr)
    print(f"copied {len(used_figs)} used figures: {', '.join(used_figs)}")

    with open(os.path.join(OUTDIR, "highlights.txt"), "w") as fh:
        fh.write(HIGHLIGHTS)
    write_cover_letter()
    write_declarations()
    write_readme(wc, used_figs)


def write_cover_letter():
    letter = f"""Dear Editors of Reliability Engineering & System Safety,

Please find enclosed our manuscript "{TITLE}" for consideration as a
regular research paper in Reliability Engineering & System Safety.

The paper asks a reliability question that battery prognostics has mostly
side-stepped: how much of the reported cross-chemistry failure-transfer
performance is a genuine prediction capability, and how much is a
State-of-Health (SOH) shortcut shared between source and target. Across four
model families, a true discrete-time hazard model, six laboratories, and four
chemistries, we show with controlled ablations, a failure-definition
ablation, a prognosis-only split, same-chemistry cross-laboratory controls,
and a pre-registered 60-cell replication that:

  - with-SOH cross-dataset transfer (pooled AUC up to 1.00) collapses without
    SOH (at best 0.58), and an unfitted SOH distance rule reproduces the tuned
    ensembles;
  - because SOH enters the failure label, all with-SOH numbers are
    diagnostic-proximity upper bounds, quantified by the ablations;
  - dataset shift matters at least as much as chemistry shift, and
    source-fitted calibrators do not transfer under it.

The work aligns directly with the journal's scope on the reliability,
safety, and prognostics of engineering systems, and carries practical
guidance for battery-management-system designers: validated evaluation
protocols, calibration-robust deployment, and an embedded (ESP32-S3)
feasibility study.

This manuscript is original, has not been published previously, and is not
under consideration by any other journal. All datasets are public, and the
complete code, models, firmware, and validation pipeline are openly
available at {REPO_URL}.
The authors declare no competing interests and received no external funding
for this work.

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


def write_readme(wc, used_figs):
    md = f"""# RESS submission package

Target journal: **Reliability Engineering & System Safety** (Elsevier,
ISSN 0951-8320), single-anonymized review, Elsevier "Your Paper Your Way"
(flexible format at first submission).

## Files

| File | Purpose |
| --- | --- |
| `main_ress.tex` / `main_ress.pdf` | Manuscript (elsarticle preprint, 12pt, single column) |
| `highlights.txt` | Mandatory separate highlights file (3-5 bullets, <=85 chars each) |
| `cover_letter.txt` | Editor cover letter |
| `declaration_of_interests.txt` | Competing-interest declaration (also in manuscript) |
| `figs/` | Figures referenced by the manuscript ({len(used_figs)} files) |

## Compliance with the RESS Guide for Authors

| Requirement | RESS rule | This package |
| --- | --- | --- |
| Length | max 13,000 words (no page limit) | ~{wc} words (abstract + body incl. captions; references excluded) |
| Abstract | <= 200 words | {len(ABSTRACT.split())} words |
| Keywords | 1-7 | 7 |
| Highlights | 3-5 bullets, <= 85 chars | 5 bullets, max {max(len(l) for l in HIGHLIGHTS.splitlines())} chars |
| Section numbering | 1.1, 1.1.1 (arabic) | arabic; literal Roman refs remapped |
| References | numbered [n] in citation order | `thebibliography` reordered into first-citation order |
| CRediT author statement | mandatory | in manuscript (before declarations) |
| Declaration of competing interest | mandatory | in manuscript + separate file |
| Funding statement | mandatory | in manuscript |
| Data availability | mandatory (Option C) | in manuscript; all datasets public; code repo linked |
| Corresponding author | e-mail on title page | `{EMAIL}` |
| Double-column / line numbers | double-column only for LaTeX | single-column `preprint` class (permitted) |

## Build

```
python3 scripts/make_ress.py        # regenerate main_ress.tex + package files
cd paper_ress && pdflatex main_ress.tex && pdflatex main_ress.tex
```

`elsarticle.cls` ships with TeX Live (no extra TEXINPUTS needed).
The manuscript is regenerated from `paper_ieee_access/main_access.tex`;
edit that source (via the v2 pipeline), not `main_ress.tex`.
"""
    with open(os.path.join(OUTDIR, "README.md"), "w") as fh:
        fh.write(md)


if __name__ == "__main__":
    main()
