"""
Train XGBoost, LightGBM, Random Forest on NASA data (H=20)
and export to trees.bin binary + model_manifest.h for ESP32.
"""
import os, sys, math, struct, json
import numpy as np
import pandas as pd

def as_f32(x):
    """Cast to float32 to match XGBoost's internal precision."""
    return struct.unpack("f", struct.pack("f", float(x)))[0]

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from composite_label import make_composite_fail_in_H

# ── Config ────────────────────────────────────────────────────────────────
HERE = os.path.dirname(__file__)
PROJECT = os.path.join(HERE, "..")
DATA_DIR = os.path.join(PROJECT, "data")
OUT_DIR = os.path.join(PROJECT, "esp32_firmware", "main")
os.makedirs(OUT_DIR, exist_ok=True)

NASA_CSV = os.path.join(DATA_DIR, "nasa_clean_filtered.csv")
H = 20
FEATURES = ["cycle", "avg_voltage", "min_voltage", "avg_current", "avg_temp", "duration", "SOH"]

# ── Model hyperparameters (paper) ─────────────────────────────────────────
from xgboost import XGBClassifier
from lightgbm import LGBMClassifier
from sklearn.ensemble import RandomForestClassifier

def clean_df(df):
    cols_available = [c for c in FEATURES if c in df.columns]
    df = df.replace([np.inf, -np.inf], np.nan)
    df = df.dropna(subset=["cycle", "SOH", "cell", "RUL"]).copy()
    df = df[(df["SOH"] > 0) & (df["SOH"] < 1.2)].copy()
    df = df[df["RUL"] >= 0].copy()
    df = df.sort_values(["cell", "cycle"]).copy()
    df[cols_available] = df[cols_available].fillna(0)
    return df

MODELS = {
    "xgboost": XGBClassifier(
        max_depth=4, learning_rate=0.05, n_estimators=300,
        subsample=0.8, colsample_bytree=0.8, min_child_weight=5,
        objective="binary:logistic", eval_metric="logloss",
        random_state=42, verbosity=0
    ),
    "lightgbm": LGBMClassifier(
        max_depth=4, learning_rate=0.05, n_estimators=300,
        subsample=0.8, colsample_bytree=0.8, min_child_samples=20,
        random_state=42, verbose=-1
    ),
    "random_forest": RandomForestClassifier(
        n_estimators=300, max_depth=6,
        random_state=42, n_jobs=-1
    ),
}

# ── Tree node (14 bytes, packed) ──────────────────────────────────────────
# Matches C struct (with __attribute__((packed))):
#   int16_t feature_idx;   // -1 = leaf
#   float   threshold;
#   int16_t left_child;    // flat index, -1 = none
#   int16_t right_child;   // flat index, -1 = none
#   float   leaf_value;    # output if leaf
PACK_FMT = "<hfh h f"  # 2+4+2+2+4 = 14 bytes (packed, no alignment padding)
NODE_BYTES = 14

# ── Tree Extractors ───────────────────────────────────────────────────────

def extract_xgboost_trees(model):
    """Extract tree structures from trained XGBoost model."""
    booster = model.get_booster()
    df_all = booster.trees_to_dataframe()
    n_trees = df_all["Tree"].nunique()

    # base_score from config (stored as string like "[0.5]")
    config = json.loads(booster.save_config())
    raw = config["learner"]["learner_model_param"]["base_score"]
    base_score_prob = float(raw.strip("[]"))
    init_score = math.log(base_score_prob / (1.0 - base_score_prob))

    trees = []
    for t in range(n_trees):
        df_t = df_all[df_all["Tree"] == t].copy()
        # Map string IDs like "0-0", "0-3" to flat indices 0, 1, 2...
        id_to_idx = {row["ID"]: i for i, (_, row) in enumerate(df_t.iterrows())}

        flat = []
        for _, row in df_t.iterrows():
            if row["Feature"] == "Leaf":
                flat.append({
                    "feature_idx": -1,
                    "threshold": 0.0,
                    "left_child": -1,
                    "right_child": -1,
                    "leaf_value": float(row["Gain"]),
                })
            else:
                feat_str = row["Feature"]
                # Handle "f0", "f1" or "ff0", "ff1"
                feat_idx = int(feat_str.lstrip("f"))
                # XGBoost: Yes = condition true (feature <= split), No = false
                # Our convention: left_child is taken when condition <= threshold
                flat.append({
                    "feature_idx": feat_idx,
                    "threshold": float(row["Split"]),
                    "left_child": id_to_idx[row["Yes"]],
                    "right_child": id_to_idx[row["No"]],
                    "leaf_value": 0.0,
                })
        trees.append(flat)
    return trees, init_score, n_trees


def extract_lightgbm_trees(model):
    """Extract trees from trained LightGBM model via model_to_string()."""
    model_str = model.booster_.model_to_string()
    lines = model_str.strip().split("\n")

    trees_raw = []
    cur = None
    for line in lines:
        if line.startswith("Tree="):
            if cur:
                trees_raw.append(cur)
            cur = {"index": int(line.split("=")[1])}
        elif cur is not None and "=" in line and not line.startswith(" "):
            key, val = line.split("=", 1)
            cur[key] = val
    if cur:
        trees_raw.append(cur)

    # LightGBM bakes the init_score into the first tree's leaf values.
    # Prediction = sigmoid(sum of all leaf values), no separate bias.
    init_score = 0.0

    trees = []
    for t in trees_raw:
        leaf_values = [float(x) for x in t["leaf_value"].split()]
        split_features = [int(x) for x in t["split_feature"].split()]
        thresholds = [float(x) for x in t["threshold"].split()]
        left_child = [int(x) for x in t["left_child"].split()]
        right_child = [int(x) for x in t["right_child"].split()]
        n_internal = len(split_features)
        n_leaves = len(leaf_values)

        flat = []
        # Internal nodes — store negative children as offset to leaf in flat array
        # LightGBM leaf child convention: leaf_idx = -(child + 1)
        for i in range(n_internal):
            def resolve_child(child_val):
                if child_val < 0:
                    # Leaf: resolve to flat index = n_internal + leaf_idx
                    return n_internal + (-(child_val + 1))
                return child_val
            flat.append({
                "feature_idx": split_features[i],
                "threshold": thresholds[i],
                "left_child": resolve_child(left_child[i]),
                "right_child": resolve_child(right_child[i]),
                "leaf_value": 0.0,
            })
        # Leaf nodes (referenced from internal nodes by resolved flat indices)
        for i in range(n_leaves):
            flat.append({
                "feature_idx": -1,
                "threshold": 0.0,
                "left_child": -1,
                "right_child": -1,
                "leaf_value": leaf_values[i],
            })
        trees.append(flat)
    return trees, init_score, len(trees)


def extract_rf_trees(model):
    """Extract trees from trained RandomForest model."""
    trees = []
    for estimator in model.estimators_:
        t = estimator.tree_
        flat = []
        for i in range(t.node_count):
            if t.feature[i] == -2:  # sklearn leaf marker
                flat.append({
                    "feature_idx": -1,
                    "threshold": 0.0,
                    "left_child": -1,
                    "right_child": -1,
                    "leaf_value": float(t.value[i, 0, 1]),
                })
            else:
                flat.append({
                    "feature_idx": int(t.feature[i]),
                    "threshold": float(t.threshold[i]),
                    "left_child": int(t.children_left[i]),
                    "right_child": int(t.children_right[i]),
                    "leaf_value": 0.0,
                })
        trees.append(flat)
    # RF: init_score = 0 (no additive bias), prediction = avg of leaf probs
    return trees, 0.0, len(trees)


# ── Binary Serialization ──────────────────────────────────────────────────

def serialize_trees(trees_list, init_scores, model_types, out_path):
    """Write all models to a single binary file."""
    buf = bytearray()

    # ── Header ──────────────────────────────────────────────────────────
    # We'll write a simple flat format: each model has its trees sequentially
    # The C loader reads each model independently via offsets.
    buf += struct.pack("<I III", 0x54524545, 1, len(trees_list), 0)  # magic, ver, n_models, reserved

    # Placeholder for offset table
    offset_table_pos = len(buf)
    buf += struct.pack(f"<{len(trees_list)}I", *([0] * len(trees_list)))

    for mi, (trees, init_score, mtype) in enumerate(zip(trees_list, init_scores, model_types)):
        offset_table_start = 12  # header size
        offset_pos = offset_table_start + mi * 4
        # Record offset
        struct.pack_into(f"<I", buf, offset_pos, len(buf))

        # Model header: model_type(2), n_trees(4), init_score(4), comparison(1), padding(3)
        # comparison: 0 = <= (LightGBM/RF), 1 = < (XGBoost)
        comparison_type = 1 if mi == 0 else 0  # model index 0 = XGBoost
        n_trees = len(trees)
        buf += struct.pack("<H I f B 3x", mtype, n_trees, init_score, comparison_type)

        # Tree headers + node data
        for tree_nodes in trees:
            n_nodes = len(tree_nodes)
            buf += struct.pack("<I", n_nodes)  # n_nodes(4)
            for node in tree_nodes:
                buf += struct.pack(
                    PACK_FMT,
                    node["feature_idx"],
                    node["threshold"],
                    node["left_child"],
                    node["right_child"],
                    node["leaf_value"],
                )

    # Final: write the total file size at the end (useful for loading)
    buf += struct.pack("<I", len(buf))

    with open(out_path, "wb") as f:
        f.write(buf)
    return buf


def write_manifest(out_dir, model_names, init_scores, model_counts):
    """Write model_manifest.h with metadata for C code.

    Types are prefixed with MANIFEST_ to avoid colliding with the same-named
    types in tree_engine.h (which main.c also includes). The manifest is a
    compile-time sanity check; the runtime source of truth for inference is
    the model_header_t struct parsed from trees.bin."""
    lines = [
        "#ifndef MODEL_MANIFEST_H",
        "#define MODEL_MANIFEST_H",
        "",
        "#define MANIFEST_N_MODELS 3",
        "",
        "typedef enum {",
    ]
    for i, name in enumerate(model_names):
        lines.append(f"    MANIFEST_MODEL_{name.upper()}{'' if i == len(model_names)-1 else ','}")
    lines += [
        "} manifest_model_id_t;",
        "",
        "typedef enum {",
        "    MANIFEST_COMPARISON_LE = 0,  /* <= (LightGBM, RF) */",
        "    MANIFEST_COMPARISON_LT = 1,  /* <  (XGBoost strict) */",
        "} manifest_comparison_type_t;",
        "",
        "typedef struct {",
        "    manifest_model_id_t id;",
        "    const char *name;",
        "    float init_score;",
        "    unsigned int n_trees;",
        "    manifest_comparison_type_t comparison;",
        "} model_meta_t;",
        "",
        "static const model_meta_t MODEL_META[MANIFEST_N_MODELS] = {",
    ]
    comparisons = ["MANIFEST_COMPARISON_LT", "MANIFEST_COMPARISON_LE", "MANIFEST_COMPARISON_LE"]
    for i, (name, init, count) in enumerate(zip(model_names, init_scores, model_counts)):
        lines.append(f'    {{ MANIFEST_MODEL_{name.upper()}, "{name}", {init:.8f}f, {count}, {comparisons[i]} }},')
    lines += [
        "};",
        "",
        "#endif /* MODEL_MANIFEST_H */",
    ]
    path = os.path.join(out_dir, "model_manifest.h")
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"  Written: {path}")
    print("=" * 60)
    print("ESP32 Model Export — NASA H=20")
    print("=" * 60)

    # Load and prepare data
    if not os.path.exists(NASA_CSV):
        print(f"ERROR: {NASA_CSV} not found. Run benchmark_cv.py first.")
        sys.exit(1)

    df = clean_df(pd.read_csv(NASA_CSV))
    y = make_composite_fail_in_H(df, H)
    cols_available = [c for c in FEATURES if c in df.columns]
    X = df[cols_available].values
    pos_rate = y.mean()
    print(f"\nData: {len(df)} rows, {df['cell'].nunique()} cells")
    print(f"Labels: {y.sum()} positive / {len(y)-y.sum()} negative ({pos_rate*100:.1f}% positive)")

    all_trees = []
    all_init_scores = []
    model_names = []
    extractors = {
        "xgboost": extract_xgboost_trees,
        "lightgbm": extract_lightgbm_trees,
        "random_forest": extract_rf_trees,
    }
    model_types = {"xgboost": 0, "lightgbm": 1, "random_forest": 2}

    for name in ["xgboost", "lightgbm", "random_forest"]:
        print(f"\n--- Training {name} ---")
        model = MODELS[name]
        model.fit(X, y)

        if name == "xgboost":
            trees, init_score, n = extract_xgboost_trees(model)
        elif name == "lightgbm":
            trees, init_score, n = extract_lightgbm_trees(model)
        else:
            trees, init_score, n = extract_rf_trees(model)

        all_trees.append(trees)
        all_init_scores.append(init_score)
        model_names.append(name)

        total_nodes = sum(len(t) for t in trees)
        print(f"  Trees: {n},  Total nodes: {total_nodes},  Init score: {init_score:.6f}")

        # Verify: predict first 5 samples and compare with model output
        print(f"  Verifying predictions... ", end="")
        mismatches = 0
        for i in range(min(50, len(X))):
            # Manual predict
            features = X[i]
            # XGBoost uses float32 internally; LightGBM/RF use float64
            use_f32 = (name == "xgboost")
            use_strict_lt = (name == "xgboost")

            def compare(fv, thr):
                if use_f32:
                    fv = as_f32(fv)
                    thr = as_f32(thr)
                if use_strict_lt:
                    return fv < thr
                return fv <= thr

            if name == "random_forest":
                total = 0.0
                for tree_nodes in trees:
                    node = 0
                    while tree_nodes[node]["feature_idx"] >= 0:
                        n = tree_nodes[node]
                        fv = features[n["feature_idx"]]
                        cond = compare(fv, n["threshold"])
                        node = n["left_child"] if cond else n["right_child"]
                    total += tree_nodes[node]["leaf_value"]
                p_manual = total / len(trees)
            else:
                # XGBoost/LightGBM: sigmoid(init_score + sum leaf values)
                total = init_score
                for tree_nodes in trees:
                    node = 0
                    while tree_nodes[node]["feature_idx"] >= 0:
                        n = tree_nodes[node]
                        fv = features[n["feature_idx"]]
                        cond = compare(fv, n["threshold"])
                        node = n["left_child"] if cond else n["right_child"]
                    total += tree_nodes[node]["leaf_value"]
                p_manual = 1.0 / (1.0 + math.exp(-total))

            p_model = model.predict_proba(features.reshape(1, -1))[0, 1]
            if abs(p_manual - p_model) > 1e-5:
                mismatches += 1

        if mismatches == 0:
            print("ALL MATCH")
        else:
            print(f"{mismatches} MISMATCHES — aborting")
            sys.exit(1)

    # Write binary
    out_bin = os.path.join(OUT_DIR, "trees.bin")
    buf = serialize_trees(
        all_trees,
        all_init_scores,
        [model_types[n] for n in model_names],
        out_bin,
    )
    print(f"\n  Written: {out_bin} ({len(buf)} bytes, {len(buf)/1024:.1f} KB)")

    # Write header
    model_counts = [len(t) for t in all_trees]
    write_manifest(OUT_DIR, model_names, all_init_scores, model_counts)

    # Print memory estimate
    total_nodes_all = sum(sum(len(t) for t in trees) for trees in all_trees)
    print(f"\n  Total tree nodes across all models: {total_nodes_all}")
    print(f"  Estimated PSRAM usage: {total_nodes_all * NODE_BYTES / 1024:.1f} KB")
    print(f"\nDone. Ready for ESP32 firmware build.")
    print("=" * 60)


if __name__ == "__main__":
    main()
