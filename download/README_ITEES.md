# International Transactions on Electrical Energy Systems — Submission Package

**Manuscript:** *Multi-Horizon Failure-Risk Models for Battery Failure Prediction:
How Much Cross-Chemistry Transfer Is a State-of-Health Shortcut?*

**Corresponding author:** Hussain Touhid Siddiquee (touhidsiddiqueeraj@gmail.com)

**Venue facts (verified 2026-10-30):** Wiley fully open-access journal (ex-Hindawi),
submissions via the Wiley Research Exchange portal; Scopus/Web of Science/DOAJ
indexed; SJR 2025 **Q2 in all three categories** (Energy Engineering & Power
Technology, Modeling & Simulation, Electrical & Electronic Engineering);
CiteScore 7.1; continuous publication; **no page limit**; anonymous peer review.

**Cost:** the listed APC is USD 2,175, but Bangladesh is on Wiley's Research4Life
Group A **full-waiver** list for fully open-access journals, and all four authors
are affiliated in Bangladesh (corresponding author in an eligible country +
≥50% of authors affiliated there — both rules satisfied). A waiver-estimate
e-mail arrives shortly after submission; confirm it shows a 100% waiver before
acceptance and do not pay any invoice without checking.

## Contents

```
paper_itees/
  main_itees.tex           ITEES manuscript (single-column Wiley/Hindawi format;
                           compiles with tectonic / xelatex)
  main_itees.pdf           compiled main paper — 18 pages, no limit applies
  supplement_itees.tex     Supplementary Material (same format, compiles standalone)
  supplement_itees.pdf     compiled supplement — 5 pages, 9 sections of tables
  figs/                    the four figures (PNG, source files for production)
Cover_Letter_ITEES.docx           cover letter (leads with the validity focus and
                                  the continuity with the framework paper published
                                  in this journal)
Suggested_Reviewers_ITEES.docx    seven suggested reviewers with rationale
Submission_Checklist_ITEES.docx   pre-upload checklist, portal steps, waiver notes
AUTHORS.md                        author list, ORCIDs, profiles
README_ITEES.md                   this file
```

## What changed from the IEEE TR version (paper_tr/)

1. **Layout:** IEEE two-column IEEEtran → single-column 11 pt A4 article in the
   Wiley/Hindawi submission style (Times-like TeX Gyre Termes, numbered headings
   "1. Introduction" / "2.1. Datasets", journal-style front matter with authors,
   affiliation, and a correspondence line).
2. **Abstract:** trimmed from 267 to exactly **250 words** (the Hindawi-era
   abstract convention). No number was changed; only connective wording was
   tightened.
3. **Section references:** all IEEE Roman-numeral cross-references converted
   ("Section III-C" → "Section 3.3"); table/figure floats converted from
   two-column `table*` spans to single-column floats sized for the 16 cm text
   frame (the capability matrix and the minimal-baselines table were re-fitted;
   the latter's value + [CI] cells now wrap onto two lines).
4. **Figure citations:** "Fig." → "Figure".
5. **Declarations added** after the Conclusion (Wiley/Hindawi OA structure):
   Funding (none), Conflict of Interest (none), Data Availability (all eight
   datasets public), Author Contributions (CRediT-style default — see TODO 1).
6. **IEEE-specific material removed:** "Manuscript received XXX" footnote,
   running heads, and the four author biographies (not used in this journal).
7. **References:** months stripped per journal style ("Jan. 2012" → "2012"),
   "art. no." → "Article ID"; all 39 entries otherwise identical to the
   verified IEEE TR bibliography, still ordered by first citation.
8. **Supplement:** same conversion applied, plus a repair — the TR copy of
   `supplement_tr.tex` had a corrupted `\usepackage[hidelinks]{hyperref}` line
   (fixed in both packages).
9. Quantitative content (every table, every in-text number) is **unchanged**
   from the four-round-verified IEEE TR manuscript.

## Still to complete before submission (see the checklist doc)

1. **Author Contributions statement** — currently a standard CRediT default
   (conceptualization/software/writing to the first author; data
   curation/validation to co-authors). Adjust to the actual division of work.
2. **Reviewer e-mails** — copy from each researcher's official page when
   entering the seven names in the portal.
3. **Companion-study reference [18]** — cited as "manuscript under review";
   update with the venue if accepted before submission.

## Rebuilding

```
cd paper_itees
tectonic main_itees.tex
tectonic supplement_itees.tex
```

Generator scripts (workspace `scripts/` directory): `convert_to_itees.py`
(paper_tr/ → paper_itees/, includes the table-fitting fixes),
`gen_itees_docs.js` (the three .docx files), `layout_qa_itees.py` (page QA).

The previous IEEE Transactions on Reliability package (paper_tr/,
IEEE_TR_Submission_Package.zip, and its three documents) is retained unchanged
as the fallback target.
