# Agent notes

## texflow MCP (local LaTeX compiler)

- Server code: `/home/touhid/Documents/texflowmcp/texflow-mcp-main/texflow/`, workspace: `/home/touhid/Documents/texflowmcp/workspace/` (document.tex / document.pdf live there)
- `document(action='ingest')` markdown-mangles existing `.tex` files (lost equation labels, broken `\usepackage` placement). For verbatim fidelity do NOT ingest: rebuild as raw blocks (`RawLatex`), emitted verbatim between `\begin{document}` and `\EOD`.
- `\usepackage` only works in the preamble: put them in a style YAML (`texflow/data/styles/*.yaml`, e.g. `battery-access.yaml`) applied via `layout(style=...)`. Raw blocks land after `\begin{document}`; `\usepackage` there = "Can be used only in preamble" error.
- Serializer's `\maketitle` is skipped when metadata title/author are empty → front matter (`\title`, `\author`, `\abstract`, `\maketitle`) must live inside the first raw block.
- `ieeeaccess.cls` redefines `\textbf#1{{\bf #1}}` — `\textbf{$p$-value}` (math inside) fails with "Extra }, or forgotten $". Keep math out of `\textbf`.
- `edit(action='replace_raw', lines=...)` takes a 1-based `[start, end]` range, not a single int.
- `document.tex` regenerates on every compile — edits to the .tex file are overwritten; edit the model instead.
- Local compile needs `ieeeaccess.cls` on `TEXINPUTS`: `TEXINPUTS=<texflow>/data/ieee/:<figs dir>:` (+ `TEXFONTS`, `FONTMAP`).
- **Two-column float sizing**: `ieeeaccess.cls` output is 2-column; `\textwidth` = full page (~516pt), `\columnwidth` ≈ 252pt. Never size single-column floats with `\textwidth` (every float clips). Wide floats must be `table*`/`figure*` (span both columns) with `\textwidth` sizing. Verify with `render(check)` — the LOG defects (overfull pt) are trustworthy; its polaris vision pass is not (hallucinates; use pixel scans / `pdftotext` instead).
- `replace_raw` lints by counting `\begin/\end` pairs — `figure*`/`table*` fail lint ("Extra \end{figure}") and the edit is silently REJECTED. Always pass `lint=false` when writing starred envs. `texflow_queue` reports such rejections as "Success" — verify by grepping regenerated `document.tex`.
- Styles (`data/styles/*.yaml`) are read at server start; editing the YAML mid-session has no effect (`layout(style=...)` re-apply doesn't reload). For body-legal fixes (register sets, `\def`s) put them in the first raw block instead — e.g. `\emergencystretch=6em` and `\makeatletter\def\UrlBreaks{\do\/\do\-}\makeatother` (hyperref `\url` won't wrap long URLs otherwise).
- `ieeeaccess.cls` sets `\flushbottom` (line 790) globally — a bibliography shorter than a full column gets its inter-item glue stretched to fill the frame ("spread references" in the left column). Put `\raggedbottom` on the line before `\clearpage` + `\begin{thebibliography}` (raw block 3). `replace_raw` can silently duplicate lines on re-edit (the model line numbers shift after your own prior edit) — after a bibliography edit, READ the block back and check for a doubled `\begin{thebibliography}` before compiling.
- Paper now 21 pages; check script: `pdftoppm -r 150 -png` + PIL max-ink-x scan (clean pages max at 0.936 of width, floats past 0.94 = overflow).

## IEEE Access paper (this repo)

- Deliverable: `paper_ieee_access/main_access.tex` + `main_access.pdf` (21 pages, all figures embedded). Figures: `paper_ieee_access/figs/`.
- Regenerate SHAP figures with `src/plot_shap.py` (single-panel) and copy to `paper_ieee_access/figs/` — the committed PNGs were silently 2-panel stacked (with-SOH + without-SOH in one file), causing plot duplication across FIGURE 6-11 and horizontally compacted beeswarms.
- Section order in raw block 3: Conclusion → `\clearpage` (flushes pending floats onto dedicated plate pages) → Acknowledgment → `\raggedbottom \clearpage` → references. No trailing `\clearpage` after `\end{thebibliography}` (creates a blank final page). ltxgrid (loaded at ieeeaccess.cls:50) balances/bizarrely splits short LAST pages — with this structure refs land tight in one column.
- Authors kept as anonymous placeholders ("ANONYMOUS", "Affiliation 1", etc.), no funding acknowledgment.
