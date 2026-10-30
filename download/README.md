# IEEE Transactions on Reliability — Submission Package

**Manuscript:** *Multi-Horizon Failure-Risk Models for Battery Failure Prediction:
How Much Cross-Chemistry Transfer Is a State-of-Health Shortcut?*

## Contents

```
paper_tr/
  main_tr.tex          IEEE TR manuscript (compiles with tectonic/pdflatex+fontspec)
  main_tr.pdf          compiled main paper (11 pages, IEEE TR limit is ~15)
  supplement_tr.tex    Supplementary Material (compiles standalone)
  supplement_tr.pdf    compiled supplement (3 pages)
  IEEEtran.cls         class file used for compilation
  figs/                figures (all regenerated from validated results)
AUTHORS.md             author list, ORCIDs, profiles, pending items
```

## What "add authors" changed (this session's request)

1. **Corrected author names** in the `\author` block (the draft carried garbled names):
   - `Ariya Jasimul Islam` → **Jasimul Islam Chowdhury**
   - `Chowdhury Farzana Hoque Eshica` → **Farzana Hoque Eshica**
2. **Final author order:** Hussain Touhid Siddiquee (corresponding author),
   Syeda Salsabil Islam, Jasimul Islam Chowdhury, Farzana Hoque Eshica.
3. **Affiliation completed** (was `[TODO: DEPARTMENT] [TODO: UNIVERSITY]`):
   Department of Electrical and Electronic Engineering, Leading University,
   Sylhet, Bangladesh.
4. **IEEE biographies added** for all four authors (standard
   `IEEEbiographynophoto` blocks after the references; names supplied by the
   class, bio text starting with degree/research statement per IEEE style).
5. `AUTHORS.md` records ORCIDs and profiles for the submission forms.

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

## Four-round review status (re-run on the rebuilt package)

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
  no orphan bibitems, no duplicates (checked in tex and compile logs).
  **6 bibitems are flagged `% * VERIFY` in the source** (shikdar2026learning,
  sahoo2022transfer, lu2023deep, huang2020experimental, shikdar2026robustness,
  grzesik2024combining): their entries were reconstructed from citation context
  after the loss and their venue/page details must be checked against your
  local `paper_ieee_access/main_access.tex` before submission.
- **Round 4 — Consistency/readability:** section cross-references verified
  against the compiled heading letters (II-A…II-I, III-A…III-M, IV, V);
  biography blocks fixed (name was duplicated by the class heading); placeholder
  audit clean except the two intended items below; layout visually verified on
  all 14 pages (main + supplement).

## Still to complete before submission

1. **Author e-mails** — the `\thanks{...}` block has
   `[TODO: corresponding author e-mail]`; IEEE TR expects all authors' e-mails.
2. **"Manuscript received XXX"** — dates are filled by the editor; confirm the
   format required at submission.
3. **Verify the 6 flagged references** against your local repository.
4. **Restore the lost figures** (see Round 1 note) if desired.
5. The **cover letter, suggested reviewers, and submission checklist** prepared
   in the earlier session were lost with the environment — ask and they will be
   regenerated (the conference-extension declaration should reference your
   `paper_wiecon/` version of this work).

## Rebuilding

```
cd paper_tr
tectonic main_tr.tex
tectonic supplement_tr.tex
```

Generator scripts (in the workspace `scripts/` directory): `gen_figs.py`,
`gen_supplement.py`, `assemble_main.py`, `verify_round2_numbers.py`.
