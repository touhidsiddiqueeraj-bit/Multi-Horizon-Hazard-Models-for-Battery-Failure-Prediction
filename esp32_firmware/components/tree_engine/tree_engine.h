/**
 * @file tree_engine.h
 * @brief Tree ensemble inference engine for ESP32
 *
 * Loads XGBoost, LightGBM, and Random Forest models from a single binary
 * packed with @c export_esp32_models.py. Models are loaded into PSRAM and
 * are switchable at runtime via @ref tree_engine_select().
 *
 * Binary format:
 *   - File header: magic(4) + ver(4) + n_models(4) = 12 bytes
 *   - Offset table: n_models × uint32 starting at byte 12
 *   - Per model: model_header_t(14) + trees (each: n_nodes(4) + nodes[])
 *   - Checksum: uint32(4)
 *
 * Node format (treenode_t): feature_idx(int16) + threshold(float32) +
 *   left_child(int16) + right_child(int16) + leaf_value(float32) = 14 bytes
 */
#ifndef TREE_ENGINE_H
#define TREE_ENGINE_H

#include <stdint.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

/** Number of model input features */
#define N_FEATURES 7

/** Number of models in the binary */
#define N_MODELS 3

/** Runtime-selectable model identifiers */
typedef enum {
    MODEL_XGBOOST = 0,
    MODEL_LIGHTGBM = 1,
    MODEL_RANDOM_FOREST = 2,
} model_id_t;

/** Comparison operator used in tree splits */
typedef enum {
    COMPARISON_LE = 0,
    COMPARISON_LT = 1,
} comparison_type_t;

/** Packed tree node (14 bytes, no padding) */
typedef struct __attribute__((packed)) {
    int16_t feature_idx;
    float   threshold;
    int16_t left_child;
    int16_t right_child;
    float   leaf_value;
} treenode_t;

/** Per-model header in the binary */
typedef struct __attribute__((packed)) {
    uint16_t model_type;
    uint32_t n_trees;
    float    init_score;
    uint8_t  comparison_type;
    uint8_t  _pad[3];
} model_header_t;

/** In-memory model state (one per model) */
typedef struct {
    const model_header_t *header;
    const treenode_t    **trees;
    uint32_t             *tree_sizes;
} model_data_t;

/**
 * @brief Load model binary into PSRAM and parse headers/tree indices.
 * @param binary    Pointer to the trees.bin data
 * @param binary_len Length of binary in bytes
 * @return 0 on success, negative on error
 */
int  tree_engine_init(const uint8_t *binary, size_t binary_len);

/**
 * @brief Switch active model for subsequent predictions.
 * @param model One of @ref model_id_t
 */
void tree_engine_select(model_id_t model);

/**
 * @brief Run inference on the currently selected model.
 * @param features Array of N_FEATURES float values
 * @return Predicted failure probability in [0, 1]
 */
float tree_engine_predict(const float features[N_FEATURES]);

/** @return Number of trees in the active model */
unsigned int tree_engine_n_trees(void);

/** @return Currently selected model ID */
model_id_t tree_engine_active_model(void);

/** @return Human-readable name of the active model */
const char *tree_engine_model_name(void);

#ifdef __cplusplus
}
#endif

#endif /* TREE_ENGINE_H */
