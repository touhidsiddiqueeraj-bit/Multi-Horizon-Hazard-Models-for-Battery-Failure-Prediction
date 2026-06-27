/**
 * @file model_manifest.h
 * @brief Compile-time metadata for the three deployed tree models.
 *
 * Used by main.c for sanity-check assertions against the runtime values
 * read from trees.bin. The runtime source of truth for inference is the
 * model_header_t struct parsed from the binary by tree_engine.c; this
 * manifest catches stale-binary-vs-firmware mismatches at boot.
 *
 * Names are lowercase to match the JSON output of the Arduino firmware's
 * web dashboard ("xgboost", "lightgbm", "random_forest"). The ESP-IDF
 * tree_engine.c uses mixed-case names for UART logs ("XGBoost", etc.) —
 * the two naming conventions are intentional and reflect the different
 * output channels.
 */
#ifndef MODEL_MANIFEST_H
#define MODEL_MANIFEST_H

#define MANIFEST_N_MODELS 3

typedef enum {
    MANIFEST_MODEL_XGBOOST = 0,
    MANIFEST_MODEL_LIGHTGBM = 1,
    MANIFEST_MODEL_RANDOM_FOREST = 2,
} manifest_model_id_t;

typedef enum {
    MANIFEST_COMPARISON_LE = 0,  /* <= (LightGBM, RF) */
    MANIFEST_COMPARISON_LT = 1,  /* <  (XGBoost strict) */
} manifest_comparison_type_t;

typedef struct {
    manifest_model_id_t id;
    const char *name;
    float init_score;
    unsigned int n_trees;
    manifest_comparison_type_t comparison;
} model_meta_t;

static const model_meta_t MODEL_META[MANIFEST_N_MODELS] = {
    { MANIFEST_MODEL_XGBOOST,      "xgboost",        -0.48806207f, 300, MANIFEST_COMPARISON_LT },
    { MANIFEST_MODEL_LIGHTGBM,     "lightgbm",        0.00000000f, 300, MANIFEST_COMPARISON_LE },
    { MANIFEST_MODEL_RANDOM_FOREST,"random_forest",   0.00000000f, 300, MANIFEST_COMPARISON_LE },
};

#endif /* MODEL_MANIFEST_H */
