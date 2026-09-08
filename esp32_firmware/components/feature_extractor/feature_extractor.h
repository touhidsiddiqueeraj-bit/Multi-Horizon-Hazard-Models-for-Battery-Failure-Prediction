/**
 * @file feature_extractor.h
 * @brief Convert cycle_data_t into the 7 model features
 *
 * Maps the sensor cycle data directly to the feature vector expected
 * by the tree models. No preprocessing — all 7 features are used as-is.
 *
 * Feature order (must match Python training):
 *   cycle, avg_voltage, min_voltage, avg_current, avg_temp, duration, SOH
 */
#ifndef FEATURE_EXTRACTOR_H
#define FEATURE_EXTRACTOR_H

#include "../sensors/sensors.h"

#ifdef __cplusplus
extern "C" {
#endif

/**
 * @brief The 7 model features, in training order.
 *
 * These map directly to the feature columns used during model training:
 *   [0] cycle       — discharge cycle number
 *   [1] avg_voltage — mean voltage during discharge
 *   [2] min_voltage — minimum voltage during discharge
 *   [3] avg_current — mean current during discharge
 *   [4] avg_temp    — mean temperature during discharge
 *   [5] duration    — discharge duration in seconds
 *   [6] SOH         — State of Health (fraction of nominal capacity)
 */
typedef struct {
    float cycle;
    float avg_voltage;
    float min_voltage;
    float avg_current;
    float avg_temp;
    float duration;
    float SOH;
} model_features_t;

/**
 * @brief Extract model features from a completed discharge cycle.
 * @param cycle  Pointer to cycle_data_t from sensors_end_cycle()
 * @return model_features_t filled with the 7 features
 */
model_features_t extract_features(const cycle_data_t *cycle);

#ifdef __cplusplus
}
#endif

#endif /* FEATURE_EXTRACTOR_H */
