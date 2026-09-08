import numpy as np
import pandas as pd

VOLTAGE_SAG_FRAC = 0.94
SOH_THRESHOLD = 0.80
EARLY_CYCLES = 10

ENDPOINTS = ("combined", "soh_only", "volt_only")


def composite_fail_cycle(df: pd.DataFrame, endpoint: str = "combined") -> pd.Series:
    """Per-row first-failure cycle for the row's cell (inf if the cell never fails).

    endpoint:
      - "combined": SOH <= 0.80 OR voltage sag (original protocol)
      - "soh_only": SOH <= 0.80 only
      - "volt_only": voltage sag only
    """
    if endpoint not in ENDPOINTS:
        raise ValueError(f"endpoint must be one of {ENDPOINTS}, got {endpoint!r}")
    df = df.sort_values(["cell", "cycle"])
    fail = pd.Series(np.inf, index=df.index)
    voltage_col = "min_voltage" if "min_voltage" in df.columns else (
        "avg_voltage" if "avg_voltage" in df.columns else None)

    for _, g in df.groupby("cell", sort=False):
        g = g.sort_values("cycle")
        candidates = []
        if endpoint in ("combined", "soh_only"):
            soh_fail = g[g["SOH"] <= SOH_THRESHOLD]
            if len(soh_fail) > 0:
                candidates.append(int(soh_fail["cycle"].iloc[0]))
        if endpoint in ("combined", "volt_only") and voltage_col is not None:
            early = g.head(EARLY_CYCLES)
            if len(early) > 0 and early[voltage_col].notna().any():
                v_threshold = early[voltage_col].mean() * VOLTAGE_SAG_FRAC
                v_fail = g[g[voltage_col] < v_threshold]
                if len(v_fail) > 0:
                    candidates.append(int(v_fail["cycle"].iloc[0]))
        if candidates:
            fail.loc[g.index] = min(candidates)
    return fail


def make_composite_fail_in_H(df: pd.DataFrame, H: int,
                             endpoint: str = "combined") -> np.ndarray:
    """Label 1 if the cell's first failure cycle T_f satisfies T_f < t + H.

    Matches the original protocol (mask = cycle + H > fail_cycle) so the
    "combined" endpoint reproduces the historical labels exactly.
    """
    fail = composite_fail_cycle(df, endpoint=endpoint)
    cycles = df.sort_values(["cell", "cycle"])["cycle"].astype(float)
    y_sorted = (cycles + H > fail).astype(int)
    # Reindex to the input frame's row order (callers index by df positions).
    return y_sorted.reindex(df.index).to_numpy()
