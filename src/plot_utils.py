"""Shared utilities for plot scripts."""

import pandas as pd


def build_cross_chem_pivot(raw_df: pd.DataFrame, suffix: str, model_order: list) -> pd.DataFrame:
    """Trees: H=20 AUC_raw.  GRU: mean(H=10-50) AUC_raw.

    Returns columns like ``nasa→oxford``, ``nasa→severson``, etc.
    where the test-target name comes from the ``dataset`` column.
    """
    rows = []
    for ev_name in raw_df["eval"].unique():
        if not ev_name.endswith(suffix):
            continue
        ev_df = raw_df[raw_df["eval"] == ev_name]
        for ds_name in ["oxford", "severson"]:
            ds_df = ev_df[ev_df["dataset"] == ds_name]
            if len(ds_df) == 0:
                continue
            for mod in model_order:
                mod_df = ds_df[ds_df["model"] == mod]
                if len(mod_df) == 0:
                    continue
                val = mod_df[mod_df["H"] == 20]["AUC_raw"].mean() if mod != "gru" else mod_df["AUC_raw"].mean()
                train_label = ev_name.replace("train_", "").replace(suffix, "")
                rows.append({"train_set": f"{train_label}→{ds_name}", "model": mod, "AUC": val})
    p = pd.DataFrame(rows).pivot(index="model", columns="train_set", values="AUC").reindex(index=model_order)
    # Restrict to expected combinations
    expected = [f"{t}→{d}" for t in ["nasa", "calce", "nasa+calce"] for d in ["oxford", "severson"]]
    return p[[c for c in expected if c in p.columns]]
