#include "feature_extractor.h"

model_features_t extract_features(const cycle_data_t *cycle) {
    model_features_t f;
    f.cycle        = (float)cycle->cycle_num;
    f.avg_voltage  = cycle->voltage_avg;
    f.min_voltage  = cycle->voltage_min;
    f.avg_current  = cycle->current_avg;
    f.avg_temp     = cycle->temp_avg;
    f.duration     = cycle->duration_sec;
    f.SOH          = cycle->soh;
    return f;
}
