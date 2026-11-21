# RESS submission package

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
| `figs/` | Figures referenced by the manuscript (14 files) |

## Compliance with the RESS Guide for Authors

| Requirement | RESS rule | This package |
| --- | --- | --- |
| Length | max 13,000 words (no page limit) | ~6703 words (abstract + body incl. captions; references excluded) |
| Abstract | <= 200 words | 186 words |
| Keywords | 1-7 | 7 |
| Highlights | 3-5 bullets, <= 85 chars | 5 bullets, max 77 chars |
| Section numbering | 1.1, 1.1.1 (arabic) | arabic; literal Roman refs remapped |
| References | numbered [n] in citation order | `thebibliography` reordered into first-citation order |
| CRediT author statement | mandatory | in manuscript (before declarations) |
| Declaration of competing interest | mandatory | in manuscript + separate file |
| Funding statement | mandatory | in manuscript |
| Data availability | mandatory (Option C) | in manuscript; all datasets public; code repo linked |
| Corresponding author | e-mail on title page | `touhidsiddiqueeraj@gmail.com` |
| Double-column / line numbers | double-column only for LaTeX | single-column `preprint` class (permitted) |

## Build

```
python3 scripts/make_ress.py        # regenerate main_ress.tex + package files
cd paper_ress && pdflatex main_ress.tex && pdflatex main_ress.tex
```

`elsarticle.cls` ships with TeX Live (no extra TEXINPUTS needed).
The manuscript is regenerated from `paper_ieee_access/main_access.tex`;
edit that source (via the v2 pipeline), not `main_ress.tex`.
