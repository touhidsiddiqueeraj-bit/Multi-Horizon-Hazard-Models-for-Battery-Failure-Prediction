# Recalibration Results

This directory contains the resumable cross-chemistry recalibration run.

Sampling is by labeled target cell. Severson uses 5, 10, 20, or 40 of 141
cells (3.5%, 7.1%, 14.2%, or 28.4%); Oxford exhaustively uses 1 or 2 of 5
cells (20% or 40%).

- `recalibration_reduced.csv`: 1,047 exported result rows.
- `recalibration_reduced.db`: SQLite checkpoint state for the reduced run.
- `recalibration_full_legacy.csv`: preserved 1,791-row full-grid attempt.
- `run_reduced.log`: experiment log.
- `plot_recalibration_reduced.log`: figure/table generation log.

Regenerate the paper figures and tables with:

```bash
python src/plot_recalibration.py
```

Paper figures are written to `paper_ieee_access/figs/`; paper tables are written
to `tables_journal/`.
