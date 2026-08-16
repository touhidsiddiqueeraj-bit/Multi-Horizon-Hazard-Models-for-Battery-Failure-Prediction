/*
 * bench.ino — minimal ESP32-S3 inference benchmark for the 3 deployed tree models,
 * across three storage locations: flash (PROGMEM), PSRAM, and internal SRAM.
 *
 * Ports the correct tree-engine logic from esp32_firmware/components/tree_engine/tree_engine.c
 * (the Arduino sketch's tree_engine_predict has a bug: it returns an undefined `sig`
 * and skips the sigmoid / RF-averaging output transform).
 *
 * Output (115200 baud), one line per (location, model):
 *   RESULT <FLASH|SRAM|PSRAM> <name> trees=<n> nodes=<n> mean=<x.xx>us min=<x.xx>us max=<x.xx>us
 *
 * pred = prediction on the NASA row-0 feature vector, cross-checked against
 * pc_validation/reference.csv (xgboost=0.006154, lightgbm=5.07e-05, rf=0.079953).
 */
#include <Arduino.h>
#include <math.h>
#include "esp_cpu.h"
#include "esp_heap_caps.h"
#include "models_data.h"
#include "reference_rows.h"

typedef struct __attribute__((packed)) {
  int16_t feature_idx;   // -1 = leaf
  float   threshold;
  int16_t left_child;
  int16_t right_child;
  float   leaf_value;
} treenode_t;

typedef struct __attribute__((packed)) {
  uint16_t model_type;
  uint32_t n_trees;
  float    init_score;
  uint8_t  comparison_type;
  uint8_t  _pad[3];
} model_header_t;

static const uint8_t *g_bin = NULL;
static size_t g_bin_len = 0;
static uint32_t g_offsets[3];
static uint32_t g_nmodels = 0;
static const model_header_t *g_hdr[3];
static const treenode_t *g_trees[3][300];
static uint32_t g_tree_sizes[3][300];
static int g_sel = 0;

static const char *MODEL_NAMES[3] = { "XGBoost", "LightGBM", "RandomForest" };

static inline uint32_t rd32(const uint8_t *p) {
  return (uint32_t)p[0] | ((uint32_t)p[1] << 8) | ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

bool tree_init(const uint8_t *binary, size_t len) {
  if (!binary || len < 12) return false;
  if (rd32(binary + 0) != 0x54524545) return false;   // "EERT"
  if (rd32(binary + 4) != 1) return false;            // version
  g_bin = binary;
  g_bin_len = len;
  g_nmodels = rd32(binary + 8);
  if (g_nmodels < 1 || g_nmodels > 3) return false;
  for (uint32_t m = 0; m < g_nmodels; m++) g_offsets[m] = rd32(binary + 12 + m * 4);

  for (uint32_t m = 0; m < g_nmodels; m++) {
    uint32_t pos = g_offsets[m];
    if (pos + sizeof(model_header_t) > len) return false;
    const model_header_t *hdr = (const model_header_t *)(binary + pos);
    g_hdr[m] = hdr;
    uint32_t n_trees = hdr->n_trees;
    if (n_trees > 300) return false;
    const uint8_t *p = binary + pos + sizeof(model_header_t);
    for (uint32_t t = 0; t < n_trees; t++) {
      uint32_t nn = rd32(p); p += 4;
      g_tree_sizes[m][t] = nn;
      g_trees[m][t] = (const treenode_t *)p;
      p += nn * sizeof(treenode_t);
    }
  }
  g_sel = 0;
  return true;
}

__attribute__((noinline))
float tree_predict(const float features[7]) {
  const model_header_t *hdr = g_hdr[g_sel];
  uint32_t n_trees = hdr->n_trees;
  int use_lt = (hdr->comparison_type == 1);   // COMPARISON_LT

  double total = 0.0;
  for (uint32_t t = 0; t < n_trees; t++) {
    const treenode_t *nodes = g_trees[g_sel][t];
    uint32_t n_nodes = g_tree_sizes[g_sel][t];
    int32_t node = 0;
    while (node < (int32_t)n_nodes && nodes[node].feature_idx >= 0) {
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
    if (node >= 0 && node < (int32_t)n_nodes) total += (double)nodes[node].leaf_value;
  }

  double raw;
  switch (hdr->model_type) {
    case 2: {  // Random Forest
      float p = (float)(total / (double)n_trees);
      if (p < 0.0f) p = 0.0f;
      if (p > 1.0f) p = 1.0f;
      return p;
    }
    case 0: raw = total + (double)hdr->init_score; break;  // XGBoost
    case 1: raw = total; break;                            // LightGBM
    default: return 0.5f;
  }
  if (raw < -45.0) return 0.0f;
  if (raw > 45.0)  return 1.0f;
  return (float)(1.0 / (1.0 + exp(-raw)));
}

// NASA row-0 features (must match pc_validation/reference.csv row 0)
static float FEATS[7] = {
  2.0f, 3.52982866886934f, 2.612467347907089f,
  -1.8187019641679727f, 32.572328114029f, 3690.234f, 1.0f
};

void time_one_model(const char *where, const char *name) {
  const int N = 2000;
  const int NMINMAX = 1000;
  float mhz = (float)getCpuFrequencyMhz();

  for (int i = 0; i < 20; i++) { volatile float q = tree_predict(FEATS); (void)q; }

  volatile float sink = 0.0f;
  uint32_t c0 = esp_cpu_get_cycle_count();
  for (int i = 0; i < N; i++) { sink += tree_predict(FEATS); }
  uint32_t c1 = esp_cpu_get_cycle_count();
  (void)sink;
  float mean_us = (float)(c1 - c0) / (mhz * (float)N);

  uint32_t tmin = 0xFFFFFFFF, tmax = 0;
  volatile float sink2 = 0.0f;
  for (int i = 0; i < NMINMAX; i++) {
    uint32_t a = esp_cpu_get_cycle_count();
    sink2 += tree_predict(FEATS);
    uint32_t b = esp_cpu_get_cycle_count();
    uint32_t d = b - a;
    if (d < tmin) tmin = d;
    if (d > tmax) tmax = d;
  }
  (void)sink2;

  uint32_t nodes = 0;
  for (uint32_t t = 0; t < g_hdr[g_sel]->n_trees; t++) nodes += g_tree_sizes[g_sel][t];

  Serial.printf("RESULT %s %s trees=%u nodes=%u mean=%.3fus min=%.3fus max=%.3fus\n",
                where, name, g_hdr[g_sel]->n_trees, nodes,
                mean_us, (float)tmin / mhz, (float)tmax / mhz);
}

void bench_one(const char *where, const uint8_t *bin, size_t len) {
  if (!tree_init(bin, len)) {
    Serial.printf("[%s] tree_init FAILED\n", where);
    return;
  }
  for (int m = 0; m < (int)g_nmodels; m++) {
    g_sel = m;
    time_one_model(where, MODEL_NAMES[m]);
  }
}

// Run the C engine over all 1,028 NASA rows on-device and compare each model's
// output to the library predictions embedded in reference_rows.h.
void validate_rows() {
  if (!tree_init(trees_bin, trees_bin_len)) { Serial.println("validate: init FAIL"); return; }
  for (int m = 0; m < 3; m++) {
    g_sel = m;
    double maxerr = 0.0;
    int worst = -1;
    for (int i = 0; i < REF_N; i++) {
      float p = tree_predict(REF_ROWS[i]);
      double e = fabs((double)p - (double)REF_ROWS[i][7 + m]);
      if (e > maxerr) { maxerr = e; worst = i; }
    }
    Serial.printf("VALIDATE %s rows=%d maxerr=%.3e at row %d\n",
                  MODEL_NAMES[m], REF_N, maxerr, worst);
  }
}

// Load one model at a time into internal SRAM (each single model fits where the
// full 372 kB binary does not) and time inference there.
void bench_single_sram() {
  if (!tree_init(trees_bin, trees_bin_len)) return;
  uint32_t st[3], en[3];
  for (int m = 0; m < 3; m++) st[m] = g_offsets[m];
  en[0] = g_offsets[1]; en[1] = g_offsets[2]; en[2] = (uint32_t)trees_bin_len;

  for (int m = 0; m < 3; m++) {
    uint32_t sec = en[m] - st[m];
    uint32_t total = 16 + sec;   // 12-byte header + 4-byte offset table + model section
    uint8_t *buf = (uint8_t *)heap_caps_malloc(total, MALLOC_CAP_8BIT | MALLOC_CAP_INTERNAL);
    if (!buf) {
      Serial.printf("SRAM-1 malloc fail %s (%u B)\n", MODEL_NAMES[m], total);
      continue;
    }
    uint32_t magic = 0x54524545, ver = 1, n = 1, off = 16;
    memcpy(buf, &magic, 4); memcpy(buf + 4, &ver, 4); memcpy(buf + 8, &n, 4);
    memcpy(buf + 12, &off, 4);
    memcpy(buf + 16, trees_bin + st[m], sec);
    if (tree_init(buf, total)) {
      g_sel = 0;
      time_one_model("SRAM-1M", MODEL_NAMES[m]);
    }
    heap_caps_free(buf);
  }
}

void setup() {
  Serial.begin(115200);
  delay(300);
  run_bench();
}

void loop() {
  delay(8000);
  run_bench();
}

// Dump per-row C predictions for all models over serial so we can build a
// Python-vs-C agreement figure from real on-device numbers.
void dump_predictions() {
  if (!tree_init(trees_bin, trees_bin_len)) return;
  for (int m = 0; m < 3; m++) {
    g_sel = m;
    Serial.printf("CPRED_BEGIN %s\n", MODEL_NAMES[m]);
    for (int i = 0; i < REF_N; i++) {
      float p = tree_predict(REF_ROWS[i]);
      Serial.printf("CPRED %d %d %.9f\n", m, i, p);
    }
    Serial.printf("CPRED_END %s\n", MODEL_NAMES[m]);
  }
  Serial.println("CPRED_DONE");
}

void run_bench() {
  Serial.println("=== ESP32-S3 battery-model inference benchmark ===");
  Serial.printf("CPU freq: %lu MHz\n", (unsigned long)getCpuFrequencyMhz());

  // 0) dump per-row on-device C predictions
  Serial.println("--- dump per-row C predictions ---");
  dump_predictions();

  // 1) on-device validation over all 1,028 rows (vs embedded library predictions)
  Serial.println("--- validation (1028 rows, flash-resident) ---");
  validate_rows();

  // 2) flash (PROGMEM)
  Serial.println("--- FLASH (PROGMEM) ---");
  bench_one("FLASH", trees_bin, trees_bin_len);

  // 3) internal SRAM (full binary — expected to fail: 372 kB > free internal RAM)
  Serial.println("--- SRAM (internal, MALLOC_CAP_INTERNAL) ---");
  {
    uint8_t *sram = (uint8_t *)heap_caps_malloc(trees_bin_len, MALLOC_CAP_8BIT | MALLOC_CAP_INTERNAL);
    if (sram) {
      memcpy(sram, trees_bin, trees_bin_len);
      bench_one("SRAM", sram, trees_bin_len);
      heap_caps_free(sram);
    } else {
      Serial.printf("SRAM malloc failed for %u bytes (model exceeds internal SRAM)\n", (unsigned)trees_bin_len);
    }
  }

  // 4) PSRAM (explicit)
  Serial.println("--- PSRAM (8 MB octal, MALLOC_CAP_SPIRAM) ---");
  {
    uint8_t *psram = (uint8_t *)heap_caps_malloc(trees_bin_len, MALLOC_CAP_SPIRAM);
    if (psram) {
      memcpy(psram, trees_bin, trees_bin_len);
      bench_one("PSRAM", psram, trees_bin_len);
      heap_caps_free(psram);
    } else {
      Serial.println("PSRAM malloc failed");
    }
  }

  // 5) single model in internal SRAM (each individual model fits)
  Serial.println("--- SRAM single-model (internal) ---");
  bench_single_sram();

  Serial.println("=== DONE ===");
}
