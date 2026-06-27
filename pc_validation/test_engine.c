/**
 * PC Validation — verify C tree engine matches Python reference.
 *
 * Compile: gcc -O2 -o test_engine test_engine.c ../esp32_firmware/components/tree_engine/tree_engine.c -lm
 * Run:     ./test_engine <trees.bin> <reference.csv>
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>
#include "../esp32_firmware/components/tree_engine/tree_engine.h"

#define MAX_LINE 4096
#define MAX_ROWS 2000
#define MAX_COLS 32
#define N_FEATURES 7
#define PRED_TOLERANCE 1e-5f

static float features[MAX_ROWS * N_FEATURES];
static int   labels[MAX_ROWS];
static double ref_probs[MAX_ROWS][N_MODELS];
static int    n_rows = 0;

static const char *MODEL_KEYS[N_MODELS] = {"p_xgboost", "p_lightgbm", "p_random_forest"};
static const char *FEAT_KEYS[N_FEATURES] = {"f_cycle", "f_avg_voltage", "f_min_voltage",
                                             "f_avg_current", "f_avg_temp", "f_duration", "f_SOH"};

int main(int argc, char **argv) {
    if (argc < 3) {
        fprintf(stderr, "Usage: %s <trees.bin> <reference.csv>\n", argv[0]);
        return 1;
    }

    /* ── Load trees.bin ────────────────────────────────────────────── */
    FILE *fp = fopen(argv[1], "rb");
    if (!fp) { perror(argv[1]); return 1; }
    fseek(fp, 0, SEEK_END);
    long bin_len = ftell(fp);
    fseek(fp, 0, SEEK_SET);
    uint8_t *binary = (uint8_t *)malloc(bin_len);
    fread(binary, 1, bin_len, fp);
    fclose(fp);
    printf("Loaded trees.bin: %ld bytes\n", bin_len);

    if (tree_engine_init(binary, bin_len) != 0) {
        fprintf(stderr, "tree_engine_init failed\n");
        free(binary);
        return 1;
    }

    /* ── Load reference.csv ────────────────────────────────────────── */
    fp = fopen(argv[2], "r");
    if (!fp) { perror(argv[2]); return 1; }

    char line[MAX_LINE];
    if (!fgets(line, sizeof(line), fp)) { fclose(fp); return 1; }

    /* Parse header */
    char *header[MAX_COLS];
    int n_cols = 0;
    char *tok = strtok(line, ",\n\r");
    while (tok && n_cols < MAX_COLS) {
        header[n_cols++] = tok;
        tok = strtok(NULL, ",\n\r");
    }

    /* Map columns */
    int col_label = -1;
    int col_feat[N_FEATURES], col_ref[N_MODELS];
    for (int f = 0; f < N_FEATURES; f++) col_feat[f] = -1;
    for (int m = 0; m < N_MODELS; m++) col_ref[m] = -1;

    for (int i = 0; i < n_cols; i++) {
        if (strcmp(header[i], "idx") == 0) continue;
        else if (strcmp(header[i], "label") == 0) col_label = i;
        for (int f = 0; f < N_FEATURES; f++)
            if (strcmp(header[i], FEAT_KEYS[f]) == 0) col_feat[f] = i;
        for (int m = 0; m < N_MODELS; m++)
            if (strcmp(header[i], MODEL_KEYS[m]) == 0) col_ref[m] = i;
    }

    if (col_label < 0) { fprintf(stderr, "Missing 'label' column\n"); return 1; }
    for (int f = 0; f < N_FEATURES; f++)
        if (col_feat[f] < 0) { fprintf(stderr, "Missing feature column %s\n", FEAT_KEYS[f]); return 1; }
    for (int m = 0; m < N_MODELS; m++)
        if (col_ref[m] < 0) { fprintf(stderr, "Missing reference column %s\n", MODEL_KEYS[m]); return 1; }

    n_rows = 0;
    while (fgets(line, sizeof(line), fp) && n_rows < MAX_ROWS) {
        float vals[MAX_COLS];
        tok = strtok(line, ",\n\r");
        int c = 0;
        while (tok && c < MAX_COLS) {
            vals[c++] = (float)atof(tok);
            tok = strtok(NULL, ",\n\r");
        }
        labels[n_rows] = (int)vals[col_label];
        for (int f = 0; f < N_FEATURES; f++)
            features[n_rows * N_FEATURES + f] = vals[col_feat[f]];
        for (int m = 0; m < N_MODELS; m++)
            ref_probs[n_rows][m] = (double)vals[col_ref[m]];
        n_rows++;
    }
    fclose(fp);
    printf("Loaded reference.csv: %d rows\n", n_rows);

    /* ── Run predictions and compare ───────────────────────────────── */
    int pass = 1;
    double max_err[N_MODELS] = {0, 0, 0};
    int err_count[N_MODELS] = {0, 0, 0};

    const char *model_names[N_MODELS] = {"XGBoost", "LightGBM", "RandomForest"};

    for (int m = 0; m < N_MODELS; m++) {
        tree_engine_select((model_id_t)m);
        printf("\n--- %s ---\n", model_names[m]);

        for (int i = 0; i < n_rows; i++) {
            float c_prob = tree_engine_predict(&features[i * N_FEATURES]);
            float r_prob = (float)ref_probs[i][m];
            float err = fabsf(c_prob - r_prob);

            if (err > max_err[m]) max_err[m] = err;
            if (err > PRED_TOLERANCE) err_count[m]++;
        }

        printf("  Max error:  %.2e\n", max_err[m]);
        printf("  Errors >%g: %d/%d\n", PRED_TOLERANCE, err_count[m], n_rows);

        if (err_count[m] > 0) {
            pass = 0;
            /* Print first 3 errors */
            int shown = 0;
            for (int i = 0; i < n_rows && shown < 3; i++) {
                float c_prob = tree_engine_predict(&features[i * N_FEATURES]);
                float r_prob = (float)ref_probs[i][m];
                if (fabsf(c_prob - r_prob) > PRED_TOLERANCE) {
                    printf("  Row %d: C=%.8f  Python=%.8f  diff=%.2e\n",
                           i, c_prob, r_prob, fabsf(c_prob - r_prob));
                    shown++;
                }
            }
        }
    }

    /* ── Benchmark (--benchmark flag) ────────────────────────────────── */
    if (argc >= 4 && strcmp(argv[3], "--benchmark") == 0) {
        int bench_iter = 100000;
        float bench_feats[N_FEATURES] = {0};
        printf("\n=== BENCHMARK (%d iterations per model) ===\n", bench_iter);

        for (int m = 0; m < N_MODELS; m++) {
            tree_engine_select((model_id_t)m);
            clock_t start = clock();
            for (int i = 0; i < bench_iter; i++) {
                bench_feats[0] = (float)(i % 300);
                bench_feats[1] = 3.7f;
                bench_feats[2] = 3.5f;
                bench_feats[3] = -0.5f;
                bench_feats[4] = 25.0f;
                bench_feats[5] = 3600.0f;
                bench_feats[6] = 0.95f;
                tree_engine_predict(bench_feats);
            }
            clock_t end = clock();
            double total_s = (double)(end - start) / CLOCKS_PER_SEC;
            double per_prediction_us = (total_s / bench_iter) * 1e6;
            printf("  %-12s : %.3f s total, %.3f us per prediction, %.0f pred/s\n",
                   model_names[m], total_s, per_prediction_us, bench_iter / total_s);
        }
    }

    printf("\n=== %s ===\n", pass ? "ALL PASS" : "SOME FAILURES");
    free(binary);
    return pass ? 0 : 1;
}
