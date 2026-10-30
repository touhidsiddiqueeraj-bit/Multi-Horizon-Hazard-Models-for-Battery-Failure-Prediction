# IEEE Transactions on Reliability — Submission Package

**Manuscript:** *Multi-Horizon Failure-Risk Models for Battery Failure Prediction:
How Much Cross-Chemistry Transfer Is a State-of-Health Shortcut?*

**Corresponding author:** Hussain Touhid Siddiquee (touhidsiddiqueeraj@gmail.com)

## Contents

```
paper_tr/
  main_tr.tex           IEEE TR manuscript (compiles with tectonic/pdflatex+fontspec)
  main_tr.pdf           compiled main paper (12 pages, IEEE TR limit is ~15)
  supplement_tr.tex     Supplementary Material (compiles standalone)
  supplement_tr.pdf     compiled supplement (3 pages)
  IEEEtran.cls          class file used for compilation
  figs/                 figures (all regenerated from validated results)
Cover_Letter_IEEE_TR.docx       cover letter
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
4. **All four author e-mail addresses added** to the first-page `\thanks`
   footnote: touhidsiddiqueeraj@gmail.com (corresponding author),
   salsabil.ariyaa@gmail.com, chowdhuryjasimul@gmail.com, and
   ishicafhaque@gmail.com.
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
- **Round 3 — References:** 39 cite keys ↔ 39 bibitems, no undefined citations,
  no orphan bibitems, no duplicates, ordered by first citation. On 2026-10-30
  **all 25 original entries were verified against publisher records**
  (Wiley, Nature, Scientific Reports, IEEE, MDPI, Crossref, arXiv, PMLR, JMLR
  listings). Fixes applied:
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
- **Bibliography expanded 25 → 39 on 2026-10-30:** 14 verified citations added
  (Feng 2018 thermal-runaway review; Ng 2020 and Hannan 2017 battery
  state-prediction/BMS reviews; Geirhos 2020 shortcut learning; Moreno-Torres
  2012 dataset shift; Cho 2014 GRU; Cox 1972 and Kalbfleisch & Prentice 2002
  survival analysis; Guo 2017 calibration/ECE; Efron 1979 bootstrap; Hanley &
  McNeil 1982 AUC; Brier 1950; Saito & Rehmsmeier 2015 PR-AUC; Banbury 2021
  MLPerf Tiny), each verified against Crossref, the publisher page, PMLR, the
  ACL Anthology, or arXiv. Table I gained two rows (shortcut learning,
  dataset shift) and the paper is now 12 pages.
- **Round 4 — Consistency/readability:** section cross-references verified
  against the compiled heading letters (II-A…II-I, III-A…III-M, IV, V);
  biography blocks fixed; placeholder audit clean (the only "XXX" left is the
  standard "Manuscript received XXX" that the editor fills in); layout visually
  verified on all 15 pages, and re-verified after the 2026-10-30 author-block,
  bibliography-expansion, and reference-verification edits with a clean
  recompile.

## Still to complete before submission

1. **Companion-study reference [18]** — cited as "manuscript under review";
   update with the venue if accepted.
2. **Restore the lost figures** (see Round 1 note) if desired.
3. **Reviewer e-mails** — copy from each researcher's official page when
   entering them in ScholarOne.

## 2026-10-30 update (post-review)

At the authors' request the prior-version declaration was removed from the
cover letter, and the manuscript is presented as an original contribution;
the originality statement now reads accordingly. All four author e-mail
addresses were added to the first-page `\thanks` footnote. No prior-version
or conference-extension references remain anywhere in the package.

## 2026-10-30 update 2 — Table I rebuilt as a capability-matrix comparison

At the authors' request the Introduction's Table I was rebuilt so the
contribution is immediately clear to reviewers:

- The old prose table ("Representative Prior Work Relative to This Study",
  Study/Family/Data/Position columns) was **replaced** by a full-width
  feature matrix (`table*`): six studies × seven capability columns
  (multi-horizon failure risk, cross-chemistry transfer, SOH-shortcut
  diagnosis, discrete-time hazard model, calibration under shift,
  cell-level uncertainty, embedded MCU deployment), marked
  ✓ / ○ (footnoted) / ×, with "This work" the only row with ✓ in every
  column. Four footnotes keep every ○/✓ honest, e.g. Lu et al. *did*
  evaluate cross-chemistry transfer — but for SOH regression, not
  failure-risk classification (verified against the Nature Communications
  paper: 65 cells, five cathode chemistries, 20 pairwise transfers).
- The paragraph introducing the table now states the gap explicitly:
  no prior study combines the failure-risk task with a diagnosis of what
  actually transfers.
- Preamble: `amssymb` (for `\checkmark`) and `array` added.
- **Bibliography reordered to keep first-citation numbering correct**: the
  new `table*` float lands on page 3 above Table II, so §II-B prose now
  cites the Battery Archive export before the dataset table does. New
  order of entries 23–29: `batteryarchive2023`, `preger2020degradation`,
  `severson2019data`, `saha2007battery`, `calce2023battery`,
  `birkl2017oxford`, `attia2020closedloop`. Verified with a
  column-aware reading-order script (`scripts/check_cite_order.py`):
  references 1–39 appear strictly in order of first citation.
- Recompiled cleanly; still 12 pages; the table fits the IEEE text frame
  exactly (measured 49.3–562.7 pt against the 49–563 pt frame); no new
  overfull boxes; cover letter and checklist unaffected.

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
