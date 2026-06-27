#include "tree_engine.h"
#include <math.h>
#include <stdlib.h>
#include <string.h>

/* ── Binary format constants ─────────────────────────────────────────── */
#define MAGIC_TREE  0x54524545  /* "EERT" as little-endian uint32 */
#define BIN_VERSION 1

/* ── State ────────────────────────────────────────────────────────────── */
static const uint8_t   *g_binary = NULL;
static size_t           g_binary_len = 0;
static const uint32_t  *g_offsets = NULL;   /* array of N_MODELS offsets */
static uint32_t         g_n_models = 0;
static model_data_t     g_models[N_MODELS];
static model_id_t       g_active = MODEL_XGBOOST;

static const char *MODEL_NAMES[N_MODELS] = {
    "XGBoost", "LightGBM", "RandomForest"
};

/* ── Internal: read uint32 from binary ────────────────────────────────── */
static inline uint32_t rd32(const uint8_t *p) {
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) |
           ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}
static inline uint16_t rd16(const uint8_t *p) {
    return (uint16_t)p[0] | ((uint16_t)p[1] << 8);
}
static inline float rdfloat(const uint8_t *p) {
    float v;
    memcpy(&v, p, sizeof(v));
    return v;
}

/* ── Init: parse binary and build tree index ─────────────────────────── */
int tree_engine_init(const uint8_t *binary, size_t binary_len) {
    if (!binary || binary_len < 12) return -1;

    g_binary = binary;
    g_binary_len = binary_len;

    uint32_t magic = rd32(binary + 0);
    uint32_t ver   = rd32(binary + 4);
    if (magic != MAGIC_TREE || ver != BIN_VERSION) return -2;

    g_n_models = rd32(binary + 8);
    if (g_n_models != N_MODELS) return -3;

    g_offsets = (const uint32_t *)(binary + 12);

    for (uint32_t m = 0; m < g_n_models; m++) {
        uint32_t offset = g_offsets[m];
        if (offset + sizeof(model_header_t) > binary_len) return -4;

        const model_header_t *hdr = (const model_header_t *)(binary + offset);
        model_data_t *md = &g_models[m];
        md->header = hdr;

        /* Allocate tree index arrays */
        md->trees = (const treenode_t **)malloc(hdr->n_trees * sizeof(treenode_t *));
        md->tree_sizes = (uint32_t *)malloc(hdr->n_trees * sizeof(uint32_t));
        if (!md->trees || !md->tree_sizes) return -5;

        /* Skip past header */
        const uint8_t *p = binary + offset + sizeof(model_header_t);

        for (uint32_t t = 0; t < hdr->n_trees; t++) {
            uint32_t n_nodes = rd32(p);
            p += 4;
            md->tree_sizes[t] = n_nodes;
            md->trees[t] = (const treenode_t *)p;
            p += n_nodes * sizeof(treenode_t);
        }
    }
    return 0;
}

/* ── Select active model ─────────────────────────────────────────────── */
void tree_engine_select(model_id_t model) {
    if (model >= MODEL_XGBOOST && model <= MODEL_RANDOM_FOREST)
        g_active = model;
}

model_id_t tree_engine_active_model(void) {
    return g_active;
}

const char *tree_engine_model_name(void) {
    return MODEL_NAMES[g_active];
}

unsigned int tree_engine_n_trees(void) {
    return g_models[g_active].header->n_trees;
}

/* ── Predict ──────────────────────────────────────────────────────────── */
float tree_engine_predict(const float features[N_FEATURES]) {
    const model_data_t *md = &g_models[g_active];
    const model_header_t *hdr = md->header;
    uint32_t n_trees = hdr->n_trees;
    int use_lt = (hdr->comparison_type == COMPARISON_LT);

    double total = 0.0;

    for (uint32_t t = 0; t < n_trees; t++) {
        const treenode_t *nodes = md->trees[t];
        uint32_t n_nodes = md->tree_sizes[t];
        int32_t node = 0;

        while (node < (int32_t)n_nodes && nodes[node].feature_idx >= 0) {
            /* XGBoost uses strict < with float32 (matches library internals).
             * LightGBM and sklearn RF use <= with float64. Using the wrong
             * precision can produce ~5e-4 prediction drift — see ARCHITECTURE.md
             * Key Design Decision #4. The double cast below mirrors the Python
             * walker in pc_validation/generate_reference.py. */
            int cond;
            if (use_lt) {
                float fv = features[nodes[node].feature_idx];
                float thr = nodes[node].threshold;
                cond = fv < thr;
            } else {
                double fv = (double)features[nodes[node].feature_idx];
                double thr = (double)nodes[node].threshold;
                cond = fv <= thr;
            }
            node = cond ? nodes[node].left_child : nodes[node].right_child;
        }

        if (node >= 0 && node < (int32_t)n_nodes) {
            total += (double)nodes[node].leaf_value;
        }
    }
    double raw_score;

    switch (hdr->model_type) {
        case MODEL_RANDOM_FOREST: {
            float p = (float)(total / (double)n_trees);
            if (p < 0.0f) p = 0.0f;
            if (p > 1.0f) p = 1.0f;
            return p;
        }
        case MODEL_XGBOOST:
            raw_score = total + (double)hdr->init_score;
            break;
        case MODEL_LIGHTGBM:
            raw_score = total;
            break;
        default:
            return 0.5f;
    }

    /* Sigmoid for XGBoost and LightGBM */
    if (raw_score < -45.0) return 0.0f;
    if (raw_score > 45.0)  return 1.0f;
    return (float)(1.0 / (1.0 + exp(-raw_score)));
}
