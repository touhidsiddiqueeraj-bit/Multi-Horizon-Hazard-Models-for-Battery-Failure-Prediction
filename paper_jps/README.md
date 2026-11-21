# JPS submission package

Target journal: **Journal of Power Sources** (Elsevier, ISSN 0378-7753),
Elsevier "Your Paper Your Way" (flexible format at first submission).

## Files

| File | Purpose |
| --- | --- |
| `main_jps.tex` / `main_jps.pdf` | Manuscript (elsarticle preprint, 12pt, single column) |
| `supplement.tex` / `supplement.pdf` | Supplementary Material (15 tables + 11 figures) |
| `figs/` | Figures referenced by manuscript + supplement (14 files) |
| `graphical_abstract.png` | Graphical abstract, 2820x1820 px (minimum 1328x531) |
| `highlights.txt` | Highlights file (3-5 bullets, <=85 chars each) |
| `cover_letter.txt` | Editor cover letter |
| `declaration_of_interests.txt` | Competing-interest declaration (also in manuscript) |

## Compliance with the JPS Guide for Authors

| Requirement | JPS rule | This package |
| --- | --- | --- |
| Length (Research Paper) | max 8,000 words (excl. abstract/figs/tables/refs) | ~5507 words |
| Main-manuscript figures | max 8 (extras as supplement) | 3 (supplement holds 11 more) |
| Main-manuscript tables | no stated cap | 7 |
| Abstract | <= 200 words | 161 words |
| Keywords | 1-7 | 6 |
| Highlights | 3-5 bullets, <= 85 chars | 5 bullets, max 77 chars |
| Graphical abstract | encouraged, min 1328x531 px | 2820x1820 px PNG |
| Section numbering | 1.1, 1.1.1 (arabic) | arabic; literal Roman refs remapped |
| References | numbered [n] in citation order | `thebibliography` in first-citation order |
| CRediT author statement | mandatory | in manuscript (before declarations) |
| Declaration of competing interest | mandatory | in manuscript + separate file |
| Funding statement | mandatory | in manuscript |
| Data availability | mandatory | in manuscript; all datasets public; code repo linked |
| Corresponding author | e-mail on title page | `touhidsiddiqueeraj@gmail.com` |

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
