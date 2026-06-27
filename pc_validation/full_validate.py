"""
Full validation: compare extracted trees against the ORIGINAL trained models
on ALL data rows, not just 50.

This validates the full pipeline:
  trained model → tree extraction → binary serialization → tree walker

If this passes with 0 errors, the binary is correct and any C vs Python
match simply confirms the C engine reads the binary faithfully.
"""
import os, sys, math, struct, json, subprocess, tempfile
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from composite_label import make_composite_fail_in_H

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from export_esp32_models import (
    MODELS, FEATURES, H, DATA_DIR, NASA_CSV, clean_df,
    extract_xgboost_trees, extract_lightgbm_trees, extract_rf_trees,
    serialize_trees,
)
MODEL_TYPES = {"xgboost": 0, "lightgbm": 1, "random_forest": 2}

HERE = os.path.dirname(__file__)
PROJECT = os.path.join(HERE, "..")
BIN_PATH = os.path.join(PROJECT, "esp32_firmware", "main", "trees.bin")
PRED_TOLERANCE = 1e-5
N_FEATURES = 7


def as_f32(x):
    return struct.unpack("f", struct.pack("f", float(x)))[0]


def manual_predict(trees, init_score, features, is_rf, use_f32, use_strict_lt):
    """Python tree walker — mirrors generate_reference.py and C engine."""
    total = 0.0 if is_rf else float(init_score)
    for tree_nodes in trees:
        node_idx = 0
        while tree_nodes[node_idx]["feature_idx"] >= 0:
            n = tree_nodes[node_idx]
            fv = float(features[n["feature_idx"]])
            tv = n["threshold"]
            if use_f32:
                fv = as_f32(fv)
                tv = as_f32(tv)
            if fv < tv if use_strict_lt else fv <= tv:
                node_idx = n["left_child"]
            else:
                node_idx = n["right_child"]
        total += tree_nodes[node_idx]["leaf_value"]
    return total / len(trees) if is_rf else 1.0 / (1.0 + math.exp(-total))


def parse_models(bin_path):
    """Parse trees.bin — same logic as generate_reference.py."""
    with open(bin_path, "rb") as f:
        data = f.read()

    magic, _, n_models, _ = struct.unpack_from("<I III", data, 0)
    assert magic == 0x54524545, f"Bad magic: 0x{magic:08X}"

    offsets = struct.unpack_from(f"<{n_models}I", data, 12)
    NODE_FMT = "<hfhhf"
    NODE_SIZE = struct.calcsize(NODE_FMT)

    models = []
    for mi in range(n_models):
        pos = offsets[mi]
        hdr_fmt = "<HIfB3x"
        model_type, n_trees, init_score, comparison_type = struct.unpack_from(hdr_fmt, data, pos)
        pos += struct.calcsize(hdr_fmt)

        all_trees = []
        for _ in range(n_trees):
            n_nodes = struct.unpack_from("<I", data, pos)[0]
            pos += 4
            nodes = []
            for _ in range(n_nodes):
                f_idx, thr, lc, rc, lv = struct.unpack_from(NODE_FMT, data, pos)
                nodes.append({
                    "feature_idx": f_idx, "threshold": thr,
                    "left_child": lc, "right_child": rc, "leaf_value": lv,
                })
                pos += NODE_SIZE
            all_trees.append(nodes)

        models.append({
            "type": model_type, "n_trees": n_trees,
            "init_score": init_score, "comparison_type": comparison_type,
            "trees": all_trees,
        })
    return models


def main():
    print("=" * 70)
    print("FULL VALIDATION: Extracted trees vs Original trained model")
    print("=" * 70)

    # ── 1. Load data ───────────────────────────────────────────────────
    print("\n[1/5] Loading data...")
    if not os.path.exists(NASA_CSV):
        print(f"ERROR: {NASA_CSV} not found")
        sys.exit(1)

    df = clean_df(pd.read_csv(NASA_CSV))
    y = make_composite_fail_in_H(df, H)
    cols_available = [c for c in FEATURES if c in df.columns]
    X = df[cols_available].values
    n_total = len(X)
    print(f"  {n_total} rows, {df['cell'].nunique()} cells")

    # ── 2. Train models ────────────────────────────────────────────────
    print("\n[2/5] Training models...")
    trained = {}
    model_names_ordered = ["xgboost", "lightgbm", "random_forest"]
    for name in model_names_ordered:
        print(f"  Training {name}... ", end="", flush=True)
        m = MODELS[name]
        if hasattr(m, 'fit'):
            m.fit(X, y)
        trained[name] = m
        print(f"done")

    # ── 3. Get model.predict_proba() for ALL rows ──────────────────────
    print("\n[3/5] Getting model predictions (all rows)...")
    model_probas = {}
    for name in model_names_ordered:
        m = trained[name]
        p = m.predict_proba(X)[:, 1]
        model_probas[name] = p
        print(f"  {name}: {len(p)} predictions")

    # ── 4. Load trees.bin and run tree walker ──────────────────────────
    print("\n[4/5] Loading trees.bin and running tree walker...")
    if not os.path.exists(BIN_PATH):
        print(f"ERROR: {BIN_PATH} not found. Run export_esp32_models.py first.")
        sys.exit(1)

    models = parse_models(BIN_PATH)
    for i, m in enumerate(models):
        total_nodes = sum(len(t) for t in m["trees"])
        print(f"  {model_names_ordered[i]}: {m['n_trees']} trees, {total_nodes} nodes, "
              f"init_score={m['init_score']:.4f}, comp={'<' if m['comparison_type'] else '<='}")

    # ── 5. Compare ─────────────────────────────────────────────────────
    print("\n[5/5] Comparing tree walker vs original model...")
    all_pass = True
    comparison_rows = []

    for midx, name in enumerate(model_names_ordered):
        m = models[midx]
        use_strict_lt = (m["comparison_type"] == 1)
        use_f32 = use_strict_lt  # XGBoost uses f32 + strict <
        is_rf = (name == "random_forest")
        init_score = m["init_score"]
        trees = m["trees"]
        model_p = model_probas[name]

        max_err = 0.0
        max_err_row = -1
        err_count = 0
        errors_by_bin = {}

        for i in range(n_total):
            p_manual = manual_predict(trees, init_score, X[i], is_rf, use_f32, use_strict_lt)
            p_model = float(model_p[i])
            err = abs(p_manual - p_model)

            if err > max_err:
                max_err = err
                max_err_row = i
            if err > PRED_TOLERANCE:
                err_count += 1
                # Bucket errors by magnitude for debugging
                bucket = int(math.log10(err)) if err > 0 else -16
                errors_by_bin[bucket] = errors_by_bin.get(bucket, 0) + 1

            comparison_rows.append({
                "idx": i, "model": name,
                "manual": p_manual, "model_p": p_model, "err": err,
            })

        status = "PASS" if err_count == 0 else "FAIL"
        print(f"\n  --- {name} ---")
        print(f"    Errors > {PRED_TOLERANCE}: {err_count} / {n_total}")
        print(f"    Max error:         {max_err:.6e} (row {max_err_row})")
        print(f"    AUC (walker):      {roc_auc_score(y, [manual_predict(trees, init_score, X[i], is_rf, use_f32, use_strict_lt) for i in range(n_total)]):.6f}")
        print(f"    AUC (model):       {roc_auc_score(y, model_p):.6f}")
        print(f"    Status:            {status}")

        if err_count > 0 and errors_by_bin:
            print(f"    Error magnitude distribution (log10):")
            for bucket in sorted(errors_by_bin, reverse=True):
                print(f"      1e{bucket} — {errors_by_bin[bucket]} rows")

            # Print first 5 errors
            shown = 0
            for i in range(n_total):
                if shown >= 5:
                    break
                p_manual = manual_predict(trees, init_score, X[i], is_rf, use_f32, use_strict_lt)
                p_model = float(model_p[i])
                err = abs(p_manual - p_model)
                if err > PRED_TOLERANCE:
                    feats_str = "  ".join(f"{FEATURES[j]}: {X[i,j]:.4f}" for j in range(N_FEATURES))
                    print(f"    Row {i}: manual={p_manual:.8f}  model={p_model:.8f}  err={err:.2e}")
                    print(f"      features: {feats_str}")
                    shown += 1

        if err_count > 0:
            all_pass = False

    print("\n" + "=" * 70)
    print(f"OVERALL: {'ALL PASS' if all_pass else 'SOME FAILURES — see above'}")
    print("=" * 70)

    # ── 6. Optional: Run C engine comparison ──────────────────────────
    print("\n\n[Optional] Cross-checking C engine against model.predict_proba()...")
    c_bin = os.path.join(HERE, "test_engine")
    if os.path.exists(c_bin):
        # Dump features + model predictions to a temp CSV for C
        rows_out = []
        for i in range(n_total):
            row = {"idx": i, "label": int(y[i])}
            for f, fn in enumerate(FEATURES):
                row[f"f_{fn}"] = X[i, f]
            for name in model_names_ordered:
                row[f"p_{name}"] = model_probas[name][i]
            rows_out.append(row)

        ref_df = pd.DataFrame(rows_out)
        ref_path = os.path.join(HERE, "model_probas.csv")
        ref_df.to_csv(ref_path, index=False)
        print(f"  Wrote model_probas.csv ({len(ref_df)} rows)")

        # Run C engine and capture output
        try:
            result = subprocess.run(
                [c_bin, BIN_PATH, ref_path],
                capture_output=True, text=True, timeout=30,
            )
            print(f"  C engine stdout:\n{result.stdout}")
            if result.stderr:
                print(f"  C engine stderr:\n{result.stderr}")
        except Exception as e:
            print(f"  Could not run C engine: {e}")
    else:
        print(f"  C engine not found at {c_bin} — compile with Makefile first")
        print(f"  Run: make -C {HERE}")

    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
