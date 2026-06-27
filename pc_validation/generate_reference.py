"""
Generate reference predictions from trees.bin — the exact binary the C engine uses.
This validates C vs Python on identical model weights.

Usage: python generate_reference.py [trees.bin path]
"""
import sys, os, math, struct
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from composite_label import make_composite_fail_in_H

HERE = os.path.dirname(__file__)
DATA_DIR = os.path.join(HERE, "..", "data")
H = 20
FEATURES = ["cycle", "avg_voltage", "min_voltage", "avg_current", "avg_temp", "duration", "SOH"]

def as_f32(x):
    return struct.unpack("f", struct.pack("f", float(x)))[0]

NODE_FMT = "<hfhhf"     # treenode_t: int16, float, int16, int16, float = 14 bytes (packed, no alignment)
NODE_SIZE = struct.calcsize(NODE_FMT)

def read_treenode(data, offset):
    f_idx, thr, lc, rc, lv = struct.unpack_from(NODE_FMT, data, offset)
    return {"feature_idx": f_idx, "threshold": thr,
            "left_child": lc, "right_child": rc, "leaf_value": lv}

def parse_models(bin_path):
    """Parse trees.bin into model dicts.
    
    Binary layout (bug-compatible with C engine at binary+12):
      [compact header]: magic(4) + ver(4) + n_models(4) = 12 bytes
      [offset table]: starts at byte 12, n_models * uint32 (overlaps with reserved field)
      For each model:
        [model_header_t]: model_type(2) + n_trees(4) + init_score(4) + comp_type(1) + pad(3) = 14 bytes
        For each tree:
          [n_nodes]: uint32 (4 bytes)
          [nodes]: n_nodes * 14 bytes (treenode_t each)
      [checksum]: uint32 (4 bytes)
    """
    with open(bin_path, "rb") as f:
        data = f.read()

    magic, _, n_models, _ = struct.unpack_from("<I III", data, 0)
    assert magic == 0x54524545, f"Bad magic: 0x{magic:08X}"

    offset_table_pos = 12  # Matches C engine: binary + 12 (bug-compat with writer)
    offsets = struct.unpack_from(f"<{n_models}I", data, offset_table_pos)

    models = []
    for mi in range(n_models):
        pos = offsets[mi]
        if pos >= len(data):
            print(f"  WARNING: model {mi} offset {pos} exceeds file size {len(data)}")
            break
        hdr_fmt = "<HIfB3x"
        model_type, n_trees, init_score, comparison_type = struct.unpack_from(hdr_fmt, data, pos)
        pos += struct.calcsize(hdr_fmt)

        all_trees = []
        for _ in range(n_trees):
            n_nodes = struct.unpack_from("<I", data, pos)[0]
            pos += 4
            nodes = []
            for _ in range(n_nodes):
                nodes.append(read_treenode(data, pos))
                pos += NODE_SIZE
            all_trees.append(nodes)

        models.append({
            "type": model_type,
            "n_trees": n_trees,
            "init_score": init_score,
            "comparison_type": comparison_type,
            "trees": all_trees,
        })

    return models

if __name__ == "__main__":
    default_bin = os.path.join(HERE, "..", "esp32_firmware", "main", "trees.bin")
    bin_path = sys.argv[1] if len(sys.argv) > 1 else default_bin
    if not os.path.exists(bin_path):
        alt = os.path.join(HERE, "..", "esp32_firmware", "main", "trees.bin")
        if os.path.exists(alt):
            bin_path = alt
        else:
            print(f"ERROR: trees.bin not found. Run 'python scripts/export_esp32_models.py' first.")
            sys.exit(1)

    print(f"Loading {bin_path}...")
    models = parse_models(bin_path)
    model_names = ["xgboost", "lightgbm", "random_forest"]

    print(f"Loaded {len(models)} models:")
    for i, m in enumerate(models):
        total_nodes = sum(len(t) for t in m["trees"])
        print(f"  {model_names[i]}: {m['n_trees']} trees, {total_nodes} nodes, "
              f"init_score={m['init_score']:.4f}, comp_type={'<' if m['comparison_type'] else '<='}")

    # Load and prepare data
    df = pd.read_csv(os.path.join(DATA_DIR, "nasa_clean_filtered.csv"))
    df = df.replace([np.inf, -np.inf], np.nan)
    df = df.dropna(subset=["cycle", "SOH", "cell", "RUL"])
    df = df[(df["SOH"] > 0) & (df["SOH"] < 1.2)]
    df = df[df["RUL"] >= 0]
    df = df.sort_values(["cell", "cycle"])
    cols_avail = [c for c in FEATURES if c in df.columns]
    df[cols_avail] = df[cols_avail].fillna(0)

    y = make_composite_fail_in_H(df, H)
    X = df[cols_avail].values

    n_test = min(200, len(X))
    records = []

    for i in range(n_test):
        record = {"idx": i, "label": int(y[i])}
        for f, fn in enumerate(FEATURES):
            record[f"f_{fn}"] = X[i, f]

        for midx, name in enumerate(model_names):
            m = models[midx]
            use_lt = (m["comparison_type"] == 1)
            use_f32 = use_lt  # XGBoost uses both f32 + strict <; others use f64 + <=
            is_rf = (midx == 2)
            init_score = m["init_score"]
            trees = m["trees"]

            total = 0.0 if is_rf else float(init_score)
            for tree_nodes in trees:
                node_idx = 0
                while tree_nodes[node_idx]["feature_idx"] >= 0:
                    n = tree_nodes[node_idx]
                    fv = float(X[i, n["feature_idx"]])
                    tv = n["threshold"]
                    if use_f32:
                        fv = as_f32(fv)
                        tv = as_f32(tv)
                    if fv < tv if use_lt else fv <= tv:
                        node_idx = n["left_child"]
                    else:
                        node_idx = n["right_child"]
                total += tree_nodes[node_idx]["leaf_value"]

            prob = total / len(trees) if is_rf else 1.0 / (1.0 + math.exp(-total))
            record[f"p_{name}"] = prob
        records.append(record)

    ref_df = pd.DataFrame(records)
    ref_df.to_csv(os.path.join(HERE, "reference.csv"), index=False)
    print(f"\nSaved {len(ref_df)} rows to reference.csv")

    for name in model_names:
        auc = roc_auc_score(ref_df["label"], ref_df[f"p_{name}"])
        print(f"  {name} AUC on {n_test} rows: {auc:.6f}")

    print("\nFirst 5 rows:")
    print(ref_df[["idx", "label", "p_xgboost", "p_lightgbm", "p_random_forest"]].head().to_string())
