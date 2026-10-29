# Submission package — IEEE Transactions on Reliability

Manuscript: **Multi-Horizon Failure-Risk Models for Battery Failure
Prediction: How Much Cross-Chemistry Transfer Is a State-of-Health
Shortcut?** (see `main_tr.tex` for the exact title).

## What is in this folder

| File | Purpose |
|---|---|
| `main_tr.tex` / `main_tr.pdf` | **Submission manuscript** — IEEEtran journal class, 11 pages (TR limit: 15), 12 tables + 5 figures embedded |
| `supplement_tr.tex` / `supplement_tr.pdf` | Supplementary Material — 6 pp, 9 tables + 14 figures moved out of the main paper for length |
| `figs/` (20 PNGs) | All figures used by both documents |
| `IEEEtran.cls` | Bundled class file (same as `paper_wiecon/`) |
| `cover_letter.txt` | Cover letter draft (placeholders in [TODO] / ALL-CAPS) |
| `suggested_reviewers.txt` | Candidate reviewer list + COI guidance |
| `README.md` | This file — submission checklist |

All numerical values are identical to `paper_ieee_access/main_access.tex`
(both derive from `results_v2/`); only formatting and length differ.

## Compile

```bash
cd paper_tr
tectonic main_tr.tex          # or: pdflatex main_tr.tex (x2) with texlive
tectonic supplement_tr.tex
# Optional formatting gate from the repo root:
python3 scripts/check_overflow.py paper_tr/main_tr.pdf        # CLEAN at 11 pp
python3 scripts/check_overflow.py paper_tr/supplement_tr.pdf  # CLEAN at 6 pp
```

Font note: `fontspec` loads TeX Gyre Termes (Times clone) by filename
because tectonic's bundle does not expose it by font name. Under
pdflatex the same sources fall back to the class's native Times setup
(`ptm`) — remove the three `fontspec` lines if compiling with pdflatex.

## Why IEEE TR fits this paper

- The Transactions' scope explicitly lists **Prognostics and Health
  Management** (submission category **B2**) and **Degradation and
  Maintenance** (**B5**) — the paper's reliability/validity framing
  (cell-level bootstrap evidence, pseudoreplication critique of DeLong,
  monotone cumulative risk, decision-curve operating points) is core
  TR material, unlike the battery-science venues that rejected it.
- **Costs: USD 0.** The traditional (subscription) route has no page
  charges within the **15-page limit**; the OA option (~$2,495) is
  entirely optional. Voluntary page charges may be requested after
  acceptance and are exactly that — voluntary.
- The journal welcomes extensions of conference papers with significant
  new technical content (see cover letter for the WIECON-ECE 2026 delta).

## Submission checklist (ieee.atyponrex.com/journal/tr-ieee)

Before submitting, complete every `[TODO: ...]`:

- [ ] **Author block** in `main_tr.tex` (line ~25): department, university,
      city/postcode, and emails for all four authors; confirm author order.
- [ ] **Corresponding author** name, email, and **ORCID** (required by the
      submission system; register at orcid.org if needed).
- [ ] **Cover letter**: corresponding-author block at the end; suggested
      reviewers (fill or copy from `suggested_reviewers.txt`).
- [ ] **WIECON-ECE 2026 status**: if the conference version has been
      accepted before you submit, add one sentence citing it in the
      cover letter (the delta is already described there).
- [ ] **Category selection**: choose **B2** (PHM) as primary; B5 as
      secondary if the form allows two.
- [ ] Upload: `main_tr.pdf` (main document), `supplement_tr.pdf`
      (supplementary file), cover letter (pasted + PDF), and the LaTeX
      source ZIP if the system requests sources at submission.
- [ ] IEEE copyright form: filled only AFTER acceptance.
- [ ] Optional: author bios + photos are added at final stage, not needed
      for initial submission.
- [ ] Re-run the overflow gate after any edit; keep the main paper
      at 15 pages or fewer (currently 11 — substantial headroom for
      reviewer-requested additions).

## What moved to the Supplement (vs. the 23-pp IEEE Access version)

Main paper keeps: within-dataset results, both transfer tables + collapse
map, minimal baselines, failure-definition ablation, same-chemistry
controls, new-chemistry replication, operational cost, deployment,
calibration comparison, and one SHAP panel pair.
Supplement holds: diagnosis-vs-prognosis split, factorial feature
ablation, GRU/hazard transfer, monotonicity violations, full SOH-ablation
statistics, both recalibration arms, leave-condition-out, PR-AUC,
reliability diagrams, multi-horizon figure, BA audit figure, C-vs-Python
agreement, remaining SHAP panels, and recalibration curves.
