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

    if "--condensed" in sys.argv:
        build_condensed(title, abstract, keywords, body, bib, used_figs)

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


CONDENSED_ABSTRACT = (
    "Predicting whether a lithium-ion cell will fail inside a short operating window "
    "matters more for real-time dispatch than remaining-useful-life regression. This study "
    "widens a multi-horizon failure-risk classification framework into a validity-focused "
    "evaluation covering tree ensembles, a GRU classifier, a discrete-time hazard model, "
    "and 60 new Battery Archive cells across six laboratories. Within-dataset discrimination "
    "is reliable (fold-mean AUC 0.90--0.96). The central result is a controlled State-of-Health "
    "(SOH) ablation: apparent cross-dataset transfer with SOH (pooled AUC up to 1.00) collapses "
    "without it, and an unfitted SOH distance rule matches the tuned ensembles. Because SOH "
    "enters the failure label and the label window includes the current cycle, with-SOH numbers "
    "are diagnostic-proximity upper bounds: prognosis-only evaluation gives 0.838 on Severson. "
    "Same-chemistry controls show dataset shift matters at least as much as chemistry. "
    "Source-fitted calibration does not transfer, and the ensembles deploy on a \\$12 "
    "microcontroller in under a millisecond per SRAM-resident model."
)

CONDENSED_KEYWORDS = (
    "battery failure prediction \\sep state-of-health shortcut "
    "\\sep cross-dataset transfer \\sep probability calibration "
    "\\sep discrete-time hazard model \\sep embedded machine learning"
)

# subsection-title substring -> (action, summary). Action KEEP retains the chunk
# (optionally minus listed floats); REPLACE swaps the body for the summary.
CONDENSED = {
    "calibration under cross-fitting": ("REPLACE",
        "Calibration is fitted leakage-clean on cross-fitted out-of-fold scores. Raw scores rank "
        "best within dataset; isotonic's tied step outputs destroy precision--recall (NASA PR-AUC "
        "0.77 raw versus 0.64 isotonic) while temperature scaling is most balanced on NASA and Platt "
        "on CALCE calibration error. The full comparison is in the Supplementary Material."),
    "minimal baselines": ("KEEP-MINUS", ["tab:baselines"]),
    "factorial feature ablation": ("REPLACE",
        "A full $2^3-1$ factorial ablation over \\{SOH, cycle index, sensors\\} (see Supplementary "
        "Material) shows SOH-only is the strongest single group on both LFP targets, cycle-only is "
        "competitive solely on Oxford, and no combination without SOH reaches 0.76 on either target: "
        "the sensor features carry no cross-dataset signal."),
    "same-chemistry": ("KEEP-MINUS", ["tab:samechem"]),
    "hazard model versus": ("KEEP-MINUS", ["tab:hazard", "tab:mono"]),
    "failure of calibration transfer": ("REPLACE",
        "Source-fitted calibrators fail on shifted targets; refitting on five labeled target cells "
        "repairs calibration error (0.82 to 0.04) but not ranking, and continued training recovers "
        "source-dependently (see Supplementary Material for both recalibration arms)."),
    "statistical evidence": ("KEEP-MINUS", ["tab:sohtests"]),
    "shap:": ("REPLACE",
        "TreeSHAP attributions (see Supplementary Material) show SOH dominating with-SOH transfer "
        "while every remaining feature collapses to near-zero spread without it: the shortcut is "
        "visible inside the models."),
    "replication on new chemistries": ("REPLACE",
        "The transfer claim replicates on 60 Battery Archive NMC/NCA/LFP cells admitted under a "
        "pre-registered cleaning rule: with-SOH transfer spans 0.77--1.00 pooled AUC and drops to "
        "0.36--0.91 outside the single-condition HNEI group, where full no-SOH transfer stays near "
        "0.99 (audit figure and full table in the Supplementary Material)."),
    "operating-condition shift": ("REPLACE",
        "Holding out entire operating conditions at fixed chemistry and laboratory costs the "
        "sensor-only model while the SOH distance rule stays undisturbed (see Supplementary "
        "Material): no competing shortcut hides in temperature or C-rate."),
    "cross-dataset transfer": ("KEEP-MINUS", ["tab:gru"]),
    "operational cost analysis": ("KEEP-MINUS", ["fig:netbenefit"]),
    "embedded deployment validation": ("KEEP-MINUS", ["fig:pyc", "tab:deploy"]),
}

# In kept chunks, reworded references to moved floats.
REWORD = [
    ("(Table~\\ref{tab:gru})",
     "(see Supplementary Material)"),
    ("Table~\\ref{tab:baselines} places the tuned ensembles next to trivial baselines.",
     "A baseline comparison (see Supplementary Material) places the tuned ensembles next to trivial baselines."),
    ("Table~\\ref{tab:samechem} shows it does not.",
     "The same-chemistry controls (see Supplementary Material) show it does not."),
    ("Table~\\ref{tab:hazard} compares the survival-product model",
     "A survival-product comparison (see Supplementary Material) sets the discrete-time hazard model"),
    ("(raw scores; Table~\\ref{tab:mono}), rising to",
     "(raw scores; see Supplementary Material), rising to"),
    ("Table~\\ref{tab:sohtests} states the central comparison",
     "The central comparison (full numbers in the Supplementary Material)"),
    ("The decision-curve view (Fig.~\\ref{fig:netbenefit}) agrees:",
     "The decision-curve view (see Supplementary Material) agrees:"),
    ("Table~\\ref{tab:deploy} lists sizes,",
     "The deployment table (see Supplementary Material) lists sizes,"),
    ("Fig.~\\ref{fig:pyc} plots every one of the 1~028 on-device predictions",
     "An agreement scatter over all 1~028 on-device predictions (see Supplementary Material) plots every one of them"),
]


def extract_floats(chunk, labels, store):
    """Remove float envs containing any of labels from chunk; append to store."""
    def repl(m):
        env = m.group(0)
        for lab in labels:
            if f"\\label{{{lab}}}" in env:
                store.append(env)
                return ""
        return env
    return re.sub(r"\\begin\{(figure|table)\*?\}.*?\\end\{(figure|table)\*?\}",
                  repl, chunk, flags=re.S)


def build_condensed(title, abstract, keywords, body, bib, used_figs):
    parts = re.split(r"(\\subsection\{[^}]*\})", body)
    head, chunks = parts[0], parts[1:]
    suppl_floats = []
    out_chunks = [head]
    for i in range(0, len(chunks), 2):
        heading, chunk = chunks[i], chunks[i + 1] if i + 1 < len(chunks) else ""
        key = heading.strip().lower()
        action = None
        for k, v in CONDENSED.items():
            if k in key:
                action = v
                break
        if action is None:
            out_chunks += [heading, chunk]
        elif action[0] == "REPLACE":
            out_chunks += [heading, "\n" + action[1] + "\n"]
            chunk_nc = chunk
            for lab in ["tab:cal", "fig:cal", "fig:prauc", "tab:gru",
                        "tab:baselines", "tab:abl", "tab:samechem",
                        "tab:hazard", "tab:mono", "tab:rec_a", "tab:rec_b",
                        "tab:sohtests", "fig:shap_xgb", "fig:shap_lgbm",
                        "fig:shap_rf", "fig:shap_noxgb", "fig:shap_nolgbm",
                        "fig:shap_norf", "tab:crosschemnew", "fig:baquality",
                        "tab:condshift", "fig:netbenefit", "fig:pyc"]:
                chunk_nc = extract_floats(chunk_nc, [lab], suppl_floats)
            # Any float left behind in a replaced chunk also moves; remaining
            # prose is dropped by design (replaced by the summary above).
            leftover = re.sub(
                r"\\begin\{(figure|table)\*?\}.*?\\end\{(figure|table)\*?\}",
                lambda m: (suppl_floats.append(m.group(0)), "")[1],
                chunk_nc, flags=re.S)
        else:  # KEEP-MINUS
            chunk = extract_floats(chunk, action[1], suppl_floats)
            for old, new in REWORD:
                chunk = chunk.replace(old, new)
            out_chunks += [heading, chunk]
    main_body = "".join(out_chunks)
    # Contributions bullet points at the mono table, which moves (tokens
    # are already filled at this stage, so match the rendered text).
    main_body = main_body.replace(
        "(Table~\\ref{tab:mono});",
        "(see Supplementary Material);")

    preamble = (
        "\\documentclass[preprint,12pt]{elsarticle}\n"
        "\\usepackage{amsmath}\n"
        "\\usepackage{booktabs}\n"
        "\\usepackage{graphicx}\n"
        "\\usepackage[colorlinks=true]{hyperref}\n"
        "\\renewcommand{\\thesection}{\\Roman{section}}\n"
        "\\renewcommand{\\thesubsection}{\\thesection-\\Alph{subsection}}\n"
        "\\graphicspath{{./figs/}}\n"
        "\\begin{document}\n"
        "\\begin{frontmatter}\n"
        f"\\title{{{title}}}\n"
        "\\author{Anonymous}\n"
        "\\address{Affiliation 1, City, Country (e-mail: author1@example.com)}\n"
        "\\begin{abstract}\n" + CONDENSED_ABSTRACT + "\n\\end{abstract}\n"
        "\\begin{keyword}\n" + CONDENSED_KEYWORDS + "\n\\end{keyword}\n"
        "\\end{frontmatter}\n\n"
    )
    with open(os.path.join(OUTDIR, "main_condensed.tex"), "w") as fh:
        fh.write(preamble + main_body + "\n" + bib + "\n\\end{document}\n")

    suppl = (
        "\\documentclass[preprint,12pt]{elsarticle}\n"
        "\\usepackage{amsmath}\n"
        "\\usepackage{booktabs}\n"
        "\\usepackage{graphicx}\n"
        "\\usepackage[colorlinks=true]{hyperref}\n"
        "\\graphicspath{{./figs/}}\n"
        "\\begin{document}\n"
        "\\begin{frontmatter}\n"
        f"\\title{{Supplementary Material for: {title}}}\n"
        "\\author{Anonymous}\n"
        "\\end{frontmatter}\n\n"
        "This supplement collects the tables and figures omitted from the main text "
        "for length. All numbers are produced by the same pipeline as the main text.\n\n"
        + "\n\n".join(suppl_floats) + "\n"
        + bib + "\n\\end{document}\n"
    )
    # Moved floats must not point back at main-text labels.
    suppl = suppl.replace(
        "Table~\\ref{tab:crosswith}",
        "the main-text transfer table")
    with open(os.path.join(OUTDIR, "supplement.tex"), "w") as fh:
        fh.write(suppl)
    print(f"condensed main + supplement ({len(suppl_floats)} moved floats)")


if __name__ == "__main__":
    main()
