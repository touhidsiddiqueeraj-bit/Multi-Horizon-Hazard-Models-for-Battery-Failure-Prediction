# Agent notes

## How to work in this repo

- **Evidence before synthesis.** Read files before stating facts. `read` shows
  hidden directory entries — no need for `ls -la` re-checks. Prefer dedicated
  tools (`read`/`edit`/`write`/`grep`/`glob`); reserve `bash` for real system
  commands (git, python, pdflatex, pdftotext) and short read-only probes.
- **Verify by execution.** After implementing or fixing, run it: regenerate the
  artifact, recompile, rerun the gate. `python3 -c` one-liners for numeric
  cross-checks against `results_v2/*.csv`.
- **TodoWrite discipline.** Multi-step work gets a todo list; mark items
  `completed` as you go, never in batches.
- **Commits.** Commit only when asked. Stage explicit paths (never `git add -A`:
  `results_v2/preds/` is ~7.5 GB untracked and `backups/` is unrelated).
  Never sweep `paper_ijphm/` deletions (removed externally) into commits.
- **Plan vs build.** In plan mode: read-only (inspect, diff, measure, ask).
  In build mode: full execution, then verify.

## texflow MCP (local LaTeX compiler)

- Server code: `/home/touhid/Documents/texflowmcp/texflow-mcp-main/texflow/`, workspace: `/home/touhid/Documents/texflowmcp/workspace/` (document.tex / document.pdf live there)
- `document(action='ingest')` markdown-mangles existing `.tex` files (lost equation labels, broken `\usepackage` placement). For verbatim fidelity do NOT ingest: rebuild as raw blocks (`RawLatex`), emitted verbatim between `\begin{document}` and `\EOD`.
- `\usepackage` only works in the preamble: put them in a style YAML (`texflow/data/styles/*.yaml`, e.g. `battery-access.yaml`) applied via `layout(style=...)`. Raw blocks land after `\begin{document}`; `\usepackage` there = "Can be used only in preamble" error.
- Serializer's `\maketitle` is skipped when metadata title/author are empty → front matter (`\title`, `\author`, `\abstract`, `\maketitle`) must live inside the first raw block.
- `ieeeaccess.cls` redefines `\textbf#1{{\bf #1}}` — `\textbf{$p$-value}` (math inside) fails with "Extra }, or forgotten $". Keep math out of `\textbf` **and out of `\caption`** (class uppercases captions; `$\Delta$` in a caption broke the build — use words).
- `edit(action='replace_raw', lines=...)` takes a 1-based `[start, end]` range, not a single int.
- `document.tex` regenerates on every compile — edits to the .tex file are overwritten; edit the model instead.
- Local compile needs `ieeeaccess.cls` on `TEXINPUTS`: `TEXINPUTS=<texflow>/data/ieee/:<figs dir>:` (+ `TEXFONTS`, `FONTMAP`).
- **Two-column float sizing**: `ieeeaccess.cls` output is 2-column; `\textwidth` = full page (~516pt), `\columnwidth` ≈ 252pt. Never size single-column floats with `\textwidth` (every float clips). Wide floats must be `table*`/`figure*` (span both columns) with `\textwidth` sizing. Verify with `render(check)` — the LOG defects (overfull pt) are trustworthy; its polaris vision pass is not (hallucinates; use pixel scans / `pdftotext` instead).
- `replace_raw` lints by counting `\begin/\end` pairs — `figure*`/`table*` fail lint ("Extra \end{figure}") and the edit is silently REJECTED. Always pass `lint=false` when writing starred envs. `texflow_queue` reports such rejections as "Success" — verify by grepping regenerated `document.tex`.
- Styles (`data/styles/*.yaml`) are read at server start; editing the YAML mid-session has no effect (`layout(style=...)` re-apply doesn't reload). For body-legal fixes (register sets, `\def`s) put them in the first raw block instead — e.g. `\emergencystretch=6em` and `\makeatletter\def\UrlBreaks{\do\/\do\-}\makeatother` (hyperref `\url` won't wrap long URLs otherwise).
- `ieeeaccess.cls` sets `\flushbottom` (line 790) globally — a bibliography shorter than a full column gets its inter-item glue stretched to fill the frame ("spread references" in the left column). Put `\raggedbottom` on the line before `\clearpage` + `\begin{thebibliography}` (raw block 3). `replace_raw` can silently duplicate lines on re-edit (the model line numbers shift after your own prior edit) — after a bibliography edit, READ the block back and check for a doubled `\begin{thebibliography}` before compiling.
- Paper now 23 pages; check script: `pdftoppm -r 150 -png` + PIL max-ink-x scan (clean pages max at 0.936 of width, floats past 0.94 = overflow).

## IEEE Access paper (this repo)

- Deliverable: `paper_ieee_access/main_access.tex` + `main_access.pdf` (23pp).
  The .tex is GENERATED: edit `paper/paper_v2_template_part1.tex` + `part2.tex`,
  then run `python3 src/make_tables_v2.py && python3 scripts/make_paper_v2.py`
  (assembler fails loudly on unfilled `@@TOKENS@@`; every number comes from
  `results_v2/paper_numbers.json` — 552 keys — plus `results_v2/tex_fragments/`).
- Review-response pipeline (v2): `src/pipeline_core.py` (cell-disjoint splits,
  cross-fitted OOF calibration, feature sets), `src/benchmark_cv.py
  within|transfer|ablation_tests` (trees), `src/gru_cv.py within|transfer`
  (holdout-cell calibration, seeds 42/1/7), `src/baselines.py`,
  `src/feature_ablation.py`, `src/faildef_ablation.py`,
  `src/same_chem_transfer.py`, `src/hazard_model.py` (discrete-time survival),
  `src/operational_metrics.py`, `src/monotonicity_check.py`,
  `src/condition_shift.py` (SNL leave-condition-out),
  `src/prognosis_split.py` (all-rows vs SOH>0.80-at-score AUC from saved
  pooled preds — alignment-validated, no retraining),
  `src/loader_batteryarchive.py` + `src/make_tables_ba.py` (BA audit/tables),
  `src/composite_label.py` (endpoint=combined|soh_only|volt_only). Outputs in
  `results_v2/` (CSV metrics, `preds/` pooled predictions, `tex_fragments/`).
  Legacy `data/benchmark_results.csv` is NOT used by the paper anymore.
- RF with `n_jobs=4` deadlocks under this repo's nested-CV workload (joblib pipe stall) — keep `n_jobs=1` for Random Forest, ≤2 for the boosting libs. `make_composite_fail_in_H` returns labels reindexed to the INPUT frame's row order; any new loader code must keep that contract (callers index `y` by df positions). Frames passed around must be `reset_index(drop=True)`-ed before positional slicing (`build_offset_frame` does this itself).
- LaTeX toolchain (no texflow in this session): `export TEXMFCNF=/usr/share/texmf-dist/web2c: TEXINPUTS=<texflow>/data/ieee//:$P/figs//:/usr/share/texmf-dist/tex//: TEXFONTS=<texflow>/data/ieee//:/usr/share/texmf-dist/fonts//: FONTMAP=<texflow>/data/ieee//:` then `pdflatex -progname=pdflatex` in `paper_ieee_access/`. The `-progname` flag and `TEXMFCNF` are required (AppImage argv[0] breaks kpathsea). xelatex does NOT work (bundled spotcolor.sty uses pdfTeX `\pdfobj`). TeX Live fonts are registered with user fontconfig (`~/.config/fontconfig/fonts.conf` → `/usr/share/texmf-dist/fonts`).
- Formatting gate: `python3 scripts/check_overflow.py paper_ieee_access/main_access.pdf` (pdftoppm + PIL max-ink-x; clean pages max 0.936, fail > 0.94). p-02–p-07 sit at 0.9358 by design (full-width tables); the jest p-11 Platt-equation flag (0.9404, clear margin, nothing clipped) is accepted as benign.
- Key results facts (v2 pipeline): Oxford = 5 cells, 46–78 usable cycles at ~100-cycle raw spacing → labels identical across ALL horizons; Cell5 contributes a single positive row (per-cell means effectively 4-cell). Calibrators are NEVER fit in-sample (cross-fitted OOF). DeLong p-values are cycle-level and pseudoreplication-inflated — cell-level bootstrap is primary; table renders underflow as `<10^{-16}`. SOH enters the failure label → all with-SOH transfer numbers are upper bounds; faildef ablation + prognosis split quantify it. HNEI NMC (single condition, 28% rows scored above threshold) is the no-SOH-transfer exception (≈0.99).
- Regenerate SHAP figures with `src/plot_shap.py` (single-panel) and copy to `paper_ieee_access/figs/` — the old committed PNGs were silently 2-panel stacked (with-SOH + without-SOH in one file), causing plot duplication across FIGURE 6-11 and horizontally compacted beeswarms. Current committed PNGs are single-panel.
- Section order: Conclusion → `\clearpage` (flushes pending floats onto dedicated plate pages) → Acknowledgment → `\raggedbottom \clearpage` → references. No trailing `\clearpage` after `\end{thebibliography}` (creates a blank final page).
- Authors kept as anonymous placeholders ("ANONYMOUS", "Affiliation 1", etc.), no funding acknowledgment.

## JES submission package (`paper_jest/`)

- `scripts/make_jest.py` ports `main_access.tex` → elsarticle preprint
  (`main_jest.tex`, full record build, 40pp). `--condensed` additionally writes
  `main_condensed.tex` (submission manuscript: 7 tables + 3 figs) +
  `supplement.tex` (15 tables + 11 figs). Mechanism: ALL `\subsection`
  headings are kept (stable auto-numbering — hardcoded `Section~III-X` strings
  keep working); moved sections are replaced by summary paragraphs; moved
  floats go to the supplement; `REWORD` map rewrites `\ref`s to moved floats
  (a stale REWORD entry silently stops matching after template trims — after
  any template edit, re-run the dangling-ref check below).
- `main_condensed.tex` + `supplement.tex` + `highlights.txt` (5×≤85 chars) +
  `cover_letter.txt` (placeholders in ALL CAPS) + `paper_jest/README.md`
  (word/float compliance table). Condensed abstract is ~150 words, 6 `\sep`
  keywords. JES guidance is ideally ≤6,000 words / 8–10 floats; condensed is
  ~7,700 words at exactly 10 floats — disclosed in the cover letter.
- `make_jest.py` also: Roman `\thesection` (body cites II-A/III-C literally),
  bibitem reorder into first-citation order, jest width overrides for small
  figures, supplement-only split of baselines/ablation into per-target tables
  (regenerated from CSVs — never by parsing LaTeX; a regex-span attempt once
  interleaved content and was reverted).
- After ANY template/script change, run the dangling-ref check on both docs:
  collect `\ref`/`\eqref` vs `\label` per file (zero tolerance), recompile
  twice, rerun the overflow gate. Current state: 0 errors, 0 undefined refs
  on all three PDFs.

## LaTeX table hygiene (lessons, all bitten before)

- Every `tabular` spec must match data-field counts — audit with a script that
  compares spec columns against `&`-counts per row (excluding `\multicolumn`
  headers). Past bugs: condshift 5-vs-6, deploy 7-vs-6, prognosis 7-vs-6.
- No unescaped `_` in generated fragments (a `base_soh_only` feature-set value
  once broke compilation) and no `$`-opening suffixes (a `$^*$` footnote marker
  opened an unbalanced math group — use `\textsuperscript{*}`).
- `df.mode` is a pandas METHOD, not the `mode` column — a `condshift` filter
  silently matched zero rows for a full round. Always use `df["mode"]`.
- Beware greedy `\\caption\{(.*)\}` / `\\begin\{tabular\}...\\end\{tabular\}`
  spans across floats; match envs positionally (nearest preceding
  `\begin`, depth-counted `\end`).
- `pdflatex` with `-interaction=nonstopmode` recovers and hides damage —
  `grep -c "^! " *.log` must be **0**; the log line numbers point at
  `\end{tabular}` while the cause is usually earlier (unbalanced `$`,
  math-in-`\textbf`, spec mismatch). Bisect with minimal docs under the real
  class (`ieeeaccess` needs `\EOD` even in minimal tests).

## Judges workflow

- Two subagent types are routinely dispatched: a **numbers judge** (every
  printed number vs `results_v2/*.csv` + `paper_numbers.json`, plus JEST↔ACCESS
  port fidelity) and a **formatting judge** (elsarticle compliance, float
  inventory exactly-once across main+supplement, type-size math from
  figsize/dpi/width-spec, caption audits). Both read-only; fixes happen after.
- Known recurring verdicts already actioned (do not re-litigate without new
  evidence): baselines/ablation column order is target-major; faildef-within
  values are means over reruns; NASA→CALCE retains no-SOH transfer (0.87→0.85);
  Oxford Cell5 single-positive-row handling; 372 kB is approximate.
