# Submission package — Journal of Energy Storage (Elsevier)

Manuscript: **Multi-Horizon Failure-Risk Models for Battery Failure Prediction:
How Much Cross-Chemistry Transfer Is a State-of-Health Shortcut?**

## Files

| File | Purpose |
|---|---|
| `main_jest.tex` | Manuscript source (generated — do not hand-edit) |
| `main_jest.pdf` | Compiled manuscript for upload |
| `figs/` (14 PNGs) | All `\includegraphics`'d figures, copied from `paper_ieee_access/figs/` |
| `highlights.txt` | 3–5 Highlights bullets, each ≤ 85 chars (Elsevier mandatory file) |
| `cover_letter.txt` | Cover-letter draft (placeholders in ALL CAPS) |
| `scripts/make_jest.py` | Generator: IEEE Access tex → elsarticle (re-run after any paper edit) |

Regenerate with: `python3 scripts/make_jest.py`, then compile in `paper_jest/`
with the repo LaTeX toolchain (`pdflatex -progname=pdflatex`, twice).

## Template provenance

- Class: `elsarticle` v3.5 (CTAN, LPPL 1.3), local TeX Live copy —
  no download required. Options: `[preprint,12pt]`, numerical citations.
- `elsarticle-num.bst` available locally but **not used**: references are kept
  as a manual `thebibliography` (25 entries) carried over from the IEEE
  version. Elsevier's Your Paper Your Way permits any reference format at
  initial submission; reformat to `elsarticle-num` at revision stage.

## Journal limits vs this manuscript (Guide for Authors, ISSN 2352-152X)

> "Ideally, a research article should have a maximum of **6,000 words**
> and **8–10 figures and/or tables**."

| Measure | This manuscript | Guidance |
|---|---|---|
| Words (PDF text incl. tables/refs) | ~13,700 | max 6,000 |
| Figures | 14 | 8–10 floats total |
| Tables | 20 | (shared budget with figures) |

**This manuscript exceeds the guidance roughly twofold on all three counts.**
"Ideally" is not a hard cap, but a desk editor may ask for condensation.
Condensation plan (not yet executed): move SHAP figs 7–12 to supplementary
(6 floats), merge Tables 4+5 and 13+15, cut §III-O to a paragraph → ≈8 figs,
≈14 tables, ≈10,000 words. Say the word and it gets done as a separate pass.

## Known build notes

- `pdflatex` error count: **0**; undefined refs/cites: **0**.
- Overflow scan (`scripts/check_overflow.py`, threshold calibrated for
  two-column IEEE): one marginal flag at jest p-11 (0.9404) — the Platt-scaling
  display equation, fully rendered with clear margin, benign.
- Anonymous author placeholders retained (replace before submission).
