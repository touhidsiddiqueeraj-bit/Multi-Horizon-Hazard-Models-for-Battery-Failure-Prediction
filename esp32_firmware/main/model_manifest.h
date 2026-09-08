#ifndef MODEL_MANIFEST_H
#define MODEL_MANIFEST_H

#define MANIFEST_N_MODELS 3

typedef enum {
    MANIFEST_MODEL_XGBOOST,
    MANIFEST_MODEL_LIGHTGBM,
    MANIFEST_MODEL_RANDOM_FOREST
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
    { MANIFEST_MODEL_XGBOOST, "xgboost", -0.48806207f, 300, MANIFEST_COMPARISON_LT },
    { MANIFEST_MODEL_LIGHTGBM, "lightgbm", 0.00000000f, 300, MANIFEST_COMPARISON_LE },
    { MANIFEST_MODEL_RANDOM_FOREST, "random_forest", 0.00000000f, 300, MANIFEST_COMPARISON_LE },
};

#endif /* MODEL_MANIFEST_H */
