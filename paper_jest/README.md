# Submission package — Journal of Energy Storage (Elsevier)

Manuscript: **Multi-Horizon Failure-Risk Models for Battery Failure Prediction:
How Much Cross-Chemistry Transfer Is a State-of-Health Shortcut?**

## Files

| File | Purpose |
|---|---|
| `main_condensed.tex` / `.pdf` | **Submission manuscript** (condensed, generated — do not hand-edit) |
| `supplement.tex` / `.pdf` | Supplementary Material: 15 tables + 11 figures omitted for length |
| `main_jest.tex` / `.pdf` | Full-length port (record only, NOT for submission) |
| `figs/` (14 PNGs) | All figures |
| `highlights.txt` | 3–5 Highlights bullets, each ≤ 85 chars (Elsevier mandatory file) |
| `cover_letter.txt` | Cover-letter draft (placeholders in ALL CAPS) |
| `scripts/make_jest.py` | Generator: `--condensed` builds manuscript + supplement |

Regenerate with: `python3 scripts/make_paper_v2.py && python3 scripts/make_jest.py --condensed`,
then compile in `paper_jest/` with the repo LaTeX toolchain
(`pdflatex -progname=pdflatex`, twice per document).

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

| Measure | Condensed manuscript | Guidance |
|---|---|---|
| Words (PDF text incl. tables/refs) | ~7,700 | ideally ≤ 6,000 |
| Figures + tables | 3 + 7 = **10** | 8–10 floats total |
| Abstract | single paragraph, ~150 words | 150–250 words |
| Keywords | 6, `\sep`-separated | ~6 |
| Highlights | 5 bullets, ≤85 chars | 3–5 bullets |

**Word-count status: 7,700 vs 6,000 guidance (~28% over).** Floats, abstract,
keywords, and highlights comply. The manuscript was cut from ~13,700 words
(full port) by moving 15 tables + 11 figures to the 15-page supplement; the
remaining prose is methods and kept-table explanations with little redundancy
left. The cover letter discloses the overage and offers further condensation
on editorial direction. Deeper cuts from here remove kept content (GRU/hazard
methods, operational analysis) rather than redundancy.

## Known build notes

- `pdflatex` error count: **0**; undefined refs/cites: **0**.
- Overflow scan (`scripts/check_overflow.py`, threshold calibrated for
  two-column IEEE): one marginal flag at jest p-11 (0.9404) — the Platt-scaling
  display equation, fully rendered with clear margin, benign.
- Anonymous author placeholders retained (replace before submission).
