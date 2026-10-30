# IEEE Transactions on Reliability — Submission Package

**Manuscript:** *Multi-Horizon Failure-Risk Models for Battery Failure Prediction:
How Much Cross-Chemistry Transfer Is a State-of-Health Shortcut?*

**Corresponding author:** Hussain Touhid Siddiquee (touhidsiddiqueeraj@gmail.com)

## Contents

```
paper_tr/
  main_tr.tex           IEEE TR manuscript (compiles with tectonic/pdflatex+fontspec)
  main_tr.pdf           compiled main paper (11 pages, IEEE TR limit is ~15)
  supplement_tr.tex     Supplementary Material (compiles standalone)
  supplement_tr.pdf     compiled supplement (3 pages)
  IEEEtran.cls          class file used for compilation
  figs/                 figures (all regenerated from validated results)
Cover_Letter_IEEE_TR.docx       cover letter, incl. conference-extension declaration
Suggested_Reviewers_IEEE_TR.docx seven suggested reviewers with rationale
Submission_Checklist_IEEE_TR.docx pre-upload checklist and QA record
AUTHORS.md             author list, ORCIDs, profiles
README.md              this file
```

## What "add authors" changed

1. **Corrected author names** in the `\author` block (the draft carried garbled names):
   - `Ariya Jasimul Islam` → **Jasimul Islam Chowdhury**
   - `Chowdhury Farzana Hoque Eshica` → **Farzana Hoque Eshica**
2. **Final author order:** Hussain Touhid Siddiquee (corresponding author),
   Syeda Salsabil Islam, Jasimul Islam Chowdhury, Farzana Hoque Eshica.
3. **Affiliation completed** (was `[TODO: DEPARTMENT] [TODO: UNIVERSITY]`):
   Department of Electrical and Electronic Engineering, Leading University,
   Sylhet, Bangladesh.
4. **Corresponding-author e-mail added** to the first-page `\thanks` footnote:
   touhidsiddiqueeraj@gmail.com. (Co-author e-mails can be added to the same
   footnote if all four should be listed; the submission form requests them
   regardless.)
5. **IEEE biographies added** for all four authors (standard
   `IEEEbiographynophoto` blocks after the references).
6. `AUTHORS.md` records ORCIDs and profiles for the submission forms.

## Four-round review record

- **Round 1 — Figures:** 4 figures, all present and referenced, none missing or
  unused; every page visually QA'd (no overflow/overlap/cut-off). Figures were
  regenerated truthfully from the validated results JSON. *Original figures that
  cannot be regenerated without raw data — SHAP beeswarms (Fig06a–f), the
  Python-vs-C agreement scatter (`fig_py_c_agreement.png`), the Battery-Archive
  capacity-trace audit (`fig_ba_quality.png`), the decision-curve figure
  (`fig_netbenefit.png`), and the calibration figure — were lost with the
  environment. The SHAP result is retained as a text-only paragraph; copy those
  files from your local repo and re-add their figure environments if you want
  them back.*
- **Round 2 — Numbers:** 379 automated checks of every table row and in-text
  claim in `main_tr.tex` and `supplement_tr.tex` against
  `results_v2/paper_numbers.json` — **all pass**. Three errors were caught and
  fixed during re-verification: Oxford SOH-delta range corrected to +0.26–0.64;
  factorial-ablation cycle-only value corrected to 0.71 on Severson; a column
  mis-ordering in the supplement's factorial table.
- **Round 3 — References:** 25 cite keys ↔ 25 bibitems, no undefined citations,
  no orphan bibitems, no duplicates. On 2026-10-30 **all 25 entries were
  verified against publisher records** (Wiley, Nature, Scientific Reports,
  IEEE, MDPI, Crossref, arXiv, PMLR, JMLR listings). Fixes applied:
  - `shikdar2026learning` → published as "Learning When Not to Use a Battery:
    Multihorizon Failure Intelligence," *Int. Trans. Elect. Energy Syst.*,
    2026, doi:10.1155/etep/6000810.
  - `sahoo2022transfer` → *Scientific Reports*, vol. 12, art. 13173, 2022
    (full author list added).
  - `lu2023deep` → *Nature Communications*, vol. 14, art. 2760, 2023 (Lu,
    Xiong, Tian, Wang, Sun).
  - `huang2020experimental` → *IEEE Access*, vol. 8, pp. 127343–127352, 2020
    (Huang, Zhao, Zhu, Chen, Vanden Broucke).
  - `grzesik2024combining` → *Electronics*, vol. 13, no. 3, art. 640, 2024
    (first author initial corrected to P.).
  - `gupta2023online` → the previous JMLR attribution could not be verified
    (not in JMLR v24–v26 listings); replaced with the verifiable "Online Platt
    scaling with calibeating," ICML 2023, pp. 12182–12204, matching the
    citation context (online recalibration).
  - The Introduction's claim about Platt vs. isotonic on imbalanced data was
    corrected to match Huang et al.'s actual finding (isotonic best overall,
    unstable under severe imbalance).
  - `shikdar2026robustness` is cited as a companion study under review —
    confirm its final venue before submission.
- **Round 4 — Consistency/readability:** section cross-references verified
  against the compiled heading letters (II-A…II-I, III-A…III-M, IV, V);
  biography blocks fixed; placeholder audit clean (the only "XXX" left is the
  standard "Manuscript received XXX" that the editor fills in); layout visually
  verified on all 14 pages, and re-verified after the 2026-10-30 author-block
  and bibliography edits with a clean recompile.

## Still to complete before submission

1. **Conference citation in the cover letter** — the placeholder
   `【complete citation — …】` in `Cover_Letter_IEEE_TR.docx` must be replaced
   with the full citation of the prior WIECON-ECE conference version, and the
   enumerated new-material list verified against the camera-ready conference
   paper.
2. **Companion-study reference [14]** — cited as "manuscript under review";
   update with the venue if accepted.
3. **Co-author e-mails** — optionally add to the `\thanks` footnote (only the
   corresponding author's is listed in the manuscript).
4. **Restore the lost figures** (see Round 1 note) if desired.
5. **Reviewer e-mails** — copy from each researcher's official page when
   entering them in ScholarOne.

## Recovery note (important)

The working environment was recycled between sessions and the working copy of
the repository (`paper-repo/`) was lost. The package was rebuilt from recovered,
verified material:

- `main_tr.tex` lines 1–250 (preamble, title, abstract, Introduction,
  Methodology, Results III-A/III-B incl. Tables I–II and the first rows of
  Table III) — **recovered verbatim** from the session cache, with only the
  author block changed and a `Fig. 2` reference added in III-A.
- The remainder (Results III-C onward, Analysis, Conclusion, References,
  Biographies) — **reconstructed** from (a) the validated IEEE Access version
  text (recovered), (b) all table values re-generated from
  `results_v2/paper_numbers.json` (recovered complete, 552 keys), and
  (c) the prior session's verification scripts (recovered).
- `supplement_tr.tex` — **regenerated programmatically** from
  `paper_numbers.json` (no hand-transcribed numbers).
- The bibliography was rebuilt after the loss and then **re-verified online**
  on 2026-10-30 (see Round 3 above).

## Rebuilding

```
cd paper_tr
tectonic main_tr.tex
tectonic supplement_tr.tex
```

Generator scripts (in the workspace `scripts/` directory): `gen_figs.py`,
`gen_supplement.py`, `assemble_main.py`, `verify_round2_numbers.py`,
`gen_submission_docs.js` (the three .docx files).
