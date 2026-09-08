/*  ═══════════════════════════════════════════════════════════════════════════
 *  Battery Health Predictor — ESP32-S3
 *  Single-sketch firmware with embedded XGBoost / LightGBM / Random Forest.
 *
 *  Features:
 *   - 3 tree models embedded in PROGMEM, switchable at runtime
 *   - 4 sensors: ADC voltage divider, INA219 current, DS18B20 temp, DS3231 RTC
 *   - Auto-calibration: detects charge/discharge via current sign
 *   - Web dashboard via ESPAsyncWebServer
 *   - mDNS: http://battery-predictor.local
 *   - Captive portal for WiFi setup on first boot
 *   - LittleFS for persistent config, calibration data, cycle log
 *  ═══════════════════════════════════════════════════════════════════════════ */

// ═══════════════════════════════════════════════════════════════════════════
//  Includes
// ═══════════════════════════════════════════════════════════════════════════
#include <Arduino.h>
#include <math.h>
#include <WiFi.h>
#include <ESPmDNS.h>
#include <DNSServer.h>
#include <LittleFS.h>
#include <ESPAsyncWebServer.h>
#include <ArduinoJson.h>
#include <Wire.h>
#include <Adafruit_INA219.h>
#include <OneWire.h>
#include <DallasTemperature.h>
#include <RTClib.h>

// Generated model binary (372 KB in PROGMEM)
#include "models_data.h"

// ═══════════════════════════════════════════════════════════════════════════
//  Pin Assignments
// ═══════════════════════════════════════════════════════════════════════════
#define PIN_ADC_VBAT      1       // ADC1_GPIO1 — voltage divider input
#define PIN_ONE_WIRE      10      // DS18B20 data pin
#define PIN_I2C_SDA       8       // I2C bus (INA219 + DS3231)
#define PIN_I2C_SCL       9
#define ADC_ATTEN         ADC_11db  // 0–3.3V input range
#define VOLTAGE_DIVIDER_RATIO  2.0f   // 10k+10k → 2:1 divider (matches ESP-IDF firmware + BOM)
#define VOLTAGE_REF           3.3f   // ESP32-S3 ADC reference

// ═══════════════════════════════════════════════════════════════════════════
//  Constants
// ═══════════════════════════════════════════════════════════════════════════
#define N_FEATURES         7
#define H                  20
#define CALIBRATION_CYCLES 10
#define SAMPLE_INTERVAL_MS 100      // 10 Hz sampling
#define DASHBOARD_INTERVAL_MS 1000  // 1 Hz dashboard push
#define PRED_TOLERANCE     1e-5f
#define CHARGE_THRESHOLD_A 0.05f    // I > +0.05A = charging
#define DISCHARGE_THRESHOLD_A -0.05f  // I < -0.05A = discharging
#define WEB_PORT           80
#define DNS_PORT           53
#define MAX_HISTORY_POINTS 200
#define CYCLE_LOG_PATH     "/cycle_log.csv"
#define WIFI_PATH          "/wifi.json"

static const char *FEATURE_NAMES[N_FEATURES] = {
  "cycle", "avg_voltage", "min_voltage", "avg_current",
  "avg_temp", "duration", "SOH"
};

static const char *MODEL_NAMES[3] = {
  "xgboost", "lightgbm", "random_forest"
};

// ═══════════════════════════════════════════════════════════════════════════
//  State Machine
// ═══════════════════════════════════════════════════════════════════════════
enum State {
  STATE_INIT = 0,
  STATE_CALIBRATE_CHARGE,
  STATE_CALIBRATE_DISCHARGE,
  STATE_MONITOR,
  STATE_ERROR
};

static const char *STATE_NAMES[5] = {
  "INIT", "CALIBRATE_CHARGE", "CALIBRATE_DISCHARGE", "MONITOR", "ERROR"
};

// ═══════════════════════════════════════════════════════════════════════════
//  Global State
// ═══════════════════════════════════════════════════════════════════════════
State g_state = STATE_INIT;
int   g_active_model = 0;      // 0=XGBoost, 1=LightGBM, 2=RF
int   g_cal_cycle_count = 0;   // cycles during calibration
int   g_cycle = 0;             // total discharge cycles observed
float g_prediction = 0.0f;     // latest prediction
uint32_t g_infer_us = 0;       // last inference latency (microseconds)
float g_soh = 1.0f;
float g_soh_baseline = 0.0f;   // average capacity of first 10 cycles

// Live sensor readings (updated at 10 Hz)
float g_voltage = 0.0f;
float g_current = 0.0f;
float g_temperature = 25.0f;

// Cycle accumulator (reset each discharge cycle)
struct CycleAccum {
  float v_sum;
  float v_min;
  float i_sum;
  float t_sum;
  float coulomb_sum;  // Ah
  unsigned long sample_count;
  unsigned long start_ms;
  unsigned long duration_ms;
  bool in_progress;
} g_cycle_acc = {0};

// Prediction history for chart
struct { float pred; unsigned long cycle; } g_history[MAX_HISTORY_POINTS];
int g_history_count = 0;

// ═══════════════════════════════════════════════════════════════════════════
//  Hardware Objects
// ═══════════════════════════════════════════════════════════════════════════
Adafruit_INA219 g_ina219;
OneWire         g_oneWire(PIN_ONE_WIRE);
DallasTemperature g_sensors(&g_oneWire);
RTC_DS3231      g_rtc;

// ═══════════════════════════════════════════════════════════════════════════
//  Network Objects
// ═══════════════════════════════════════════════════════════════════════════
AsyncWebServer  g_server(WEB_PORT);
AsyncWebSocket  g_ws("/ws");
DNSServer       g_dns;

// ═══════════════════════════════════════════════════════════════════════════
//  ╔══════════════════════════════════════════════════════════════════╗
//  ║               T R E E   E N G I N E                             ║
//  ╚══════════════════════════════════════════════════════════════════╝
// ═══════════════════════════════════════════════════════════════════════════

// Packed tree node — 14 bytes, matches export_esp32_models.py
typedef struct __attribute__((packed)) {
  int16_t feature_idx;    // -1 = leaf
  float   threshold;
  int16_t left_child;     // flat index
  int16_t right_child;
  float   leaf_value;
} treenode_t;

// Per-model parsed data
typedef struct {
  int        model_type;     // 0=XGBoost, 1=LightGBM, 2=RF
  int        n_trees;
  float      init_score;
  bool       use_strict_lt;  // XGBoost: f32 + strict <
  uint32_t   tree_offsets[300];  // flat offset to each tree's nodes
  uint32_t   tree_counts[300];   // nodes per tree
  uint32_t   total_nodes;
} model_parsed_t;

static const uint8_t *g_binary = NULL;
static size_t g_binary_len = 0;
static model_parsed_t g_models[3];
static int g_n_models = 0;
static int g_sel_model = 0;  // currently selected model index

// Read treenode_t from binary at given byte offset
static treenode_t read_node(const uint8_t *base, uint32_t offset) {
  treenode_t n;
  memcpy(&n, base + offset, sizeof(treenode_t));
  return n;
}

bool tree_engine_init(const uint8_t *binary, size_t len) {
  g_binary = binary;
  g_binary_len = len;

  // Parse file header
  uint32_t magic, ver, n_models;
  memcpy(&magic, binary, 4);
  memcpy(&ver, binary + 4, 4);
  memcpy(&n_models, binary + 8, 4);
  if (magic != 0x54524545) return false;
  g_n_models = (int)n_models;
  if (g_n_models > 3) g_n_models = 3;

  // Read offset table (starts at byte 12)
  uint32_t offsets[3];
  memcpy(offsets, binary + 12, g_n_models * sizeof(uint32_t));

  for (int mi = 0; mi < g_n_models; mi++) {
    uint32_t pos = offsets[mi];
    if (pos >= len) return false;

    uint16_t model_type;
    uint32_t n_trees;
    float init_score;
    uint8_t comp_type;
    memcpy(&model_type, binary + pos, 2);
    memcpy(&n_trees, binary + pos + 2, 4);
    memcpy(&init_score, binary + pos + 6, 4);
    memcpy(&comp_type, binary + pos + 10, 1);
    pos += 14;  // header size

    g_models[mi].model_type = model_type;
    g_models[mi].n_trees = (int)n_trees;
    g_models[mi].init_score = init_score;
    g_models[mi].use_strict_lt = (comp_type == 1);
    g_models[mi].total_nodes = 0;

    if (n_trees > 300) n_trees = 300;

    for (int ti = 0; ti < (int)n_trees; ti++) {
      uint32_t n_nodes;
      memcpy(&n_nodes, binary + pos, 4);
      pos += 4;
      g_models[mi].tree_offsets[ti] = pos;
      g_models[mi].tree_counts[ti] = n_nodes;
      g_models[mi].total_nodes += n_nodes;
      pos += n_nodes * sizeof(treenode_t);
    }
  }

  g_sel_model = 0;
  return true;
}

bool tree_engine_select(int model_idx) {
  if (model_idx < 0 || model_idx >= g_n_models) return false;
  g_sel_model = model_idx;
  return true;
}

float tree_engine_predict(const float features[7]) {
  model_parsed_t *m = &g_models[g_sel_model];

  // Cast to f32 for XGBoost
  float f32_feat[7];
  if (m->use_strict_lt) {
    for (int i = 0; i < 7; i++) f32_feat[i] = features[i];
  }

  double total = 0.0;

  for (int ti = 0; ti < m->n_trees; ti++) {
    uint32_t offset = m->tree_offsets[ti];
    uint32_t n_nodes = m->tree_counts[ti];
    uint32_t node_off = 0;
    const uint8_t *tree_base = g_binary + offset;

    /* Loop until we hit a leaf (no depth cap). The C engine in
     * esp32_firmware/components/tree_engine/tree_engine.c uses the same
     * loop-until-leaf pattern; a previous version of this code used
     * `for (depth = 0; depth < 20; ...)` which would silently truncate
     * any tree deeper than 20 nodes. Current trees have max_depth ≤ 6 so
     * this is defensive, not behaviour-changing today. */
    while (node_off < n_nodes) {
      treenode_t node = read_node(tree_base, node_off * sizeof(treenode_t));
      if (node.feature_idx < 0) {
        total += (double)node.leaf_value;
        break;
      }
      int fi = node.feature_idx;
      if (fi < 0 || fi >= 7) break;

      if (m->use_strict_lt) {
        // XGBoost: strict < with f32 cast
        float fv = f32_feat[fi];
        float thr = *(float*)&node.threshold;
        node_off = (fv < thr) ? (uint32_t)node.left_child : (uint32_t)node.right_child;
      } else {
        // LightGBM / RF: <= with f64 precision (matches C engine + Python walker)
        double fv = (double)features[fi];
        double thr = (double)node.threshold;
        node_off = (fv <= thr) ? (uint32_t)node.left_child : (uint32_t)node.right_child;
      }
    }
  }

  // Output transform — matches esp32_firmware/components/tree_engine/tree_engine.c.
  switch (m->model_type) {
    case 2: {  // Random Forest: average leaf probabilities, clamp to [0,1]
      float p = (float)(total / (double)m->n_trees);
      if (p < 0.0f) p = 0.0f;
      if (p > 1.0f) p = 1.0f;
      return p;
    }
    case 0: {  // XGBoost: init_score + sigmoid
      double raw = total + (double)m->init_score;
      if (raw < -45.0) return 0.0f;
      if (raw > 45.0)  return 1.0f;
      return (float)(1.0 / (1.0 + exp(-raw)));
    }
    case 1: {  // LightGBM: sigmoid (init_score is 0.0)
      double raw = total;
      if (raw < -45.0) return 0.0f;
      if (raw > 45.0)  return 1.0f;
      return (float)(1.0 / (1.0 + exp(-raw)));
    }
    default:
      return 0.5f;
  }
}

// ═══════════════════════════════════════════════════════════════════════════
//  ╔══════════════════════════════════════════════════════════════════╗
//  ║               S E N S O R   P I P E L I N E                     ║
//  ╚══════════════════════════════════════════════════════════════════╝
// ═══════════════════════════════════════════════════════════════════════════

void init_sensors() {
  // ADC
  analogReadResolution(12);
  pinMode(PIN_ADC_VBAT, INPUT);

  // I2C bus
  Wire.begin(PIN_I2C_SDA, PIN_I2C_SCL);

  // INA219 current sensor
  if (!g_ina219.begin(&Wire)) {
    Serial.println("WARN: INA219 not found");
  } else {
    g_ina219.setCalibration_32V_2A();
  }

  // DS18B20 temperature
  g_sensors.begin();

  // DS3231 RTC
  if (!g_rtc.begin(&Wire)) {
    Serial.println("WARN: DS3231 not found");
  } else if (g_rtc.lostPower()) {
    g_rtc.adjust(DateTime(F(__DATE__), F(__TIME__)));
  }
}

float read_voltage() {
  int raw = analogRead(PIN_ADC_VBAT);
  float v = (float)raw * VOLTAGE_REF / 4095.0f * VOLTAGE_DIVIDER_RATIO;
  return v;
}

float read_current() {
  // INA219 returns current in mA; convert to Amps
  float i = g_ina219.getCurrent_mA() / 1000.0f;
  if (isnan(i) || isinf(i)) return 0.0f;
  return i;
}

float read_temperature() {
  g_sensors.requestTemperatures();
  float t = g_sensors.getTempCByIndex(0);
  if (isnan(t) || t < -20 || t > 100) return 25.0f;
  return t;
}

DateTime read_rtc() {
  if (g_rtc.begin()) return g_rtc.now();
  return DateTime(2026, 1, 1, 0, 0, 0);
}

void sample_sensors() {
  g_voltage = read_voltage();
  g_current = read_current();
  g_temperature = read_temperature();
}

// ═══════════════════════════════════════════════════════════════════════════
//  ╔══════════════════════════════════════════════════════════════════╗
//  ║        C A L I B R A T I O N   S T A T E   M A C H I N E        ║
//  ╚══════════════════════════════════════════════════════════════════╝
// ═══════════════════════════════════════════════════════════════════════════

void reset_cycle_accum() {
  g_cycle_acc.v_sum = 0;
  g_cycle_acc.v_min = 99.0f;
  g_cycle_acc.i_sum = 0;
  g_cycle_acc.t_sum = 0;
  g_cycle_acc.coulomb_sum = 0;
  g_cycle_acc.sample_count = 0;
  g_cycle_acc.start_ms = millis();
  g_cycle_acc.duration_ms = 0;
  g_cycle_acc.in_progress = true;
}

void sample_cycle_accum() {
  if (!g_cycle_acc.in_progress) return;
  g_cycle_acc.v_sum += g_voltage;
  if (g_voltage < g_cycle_acc.v_min) g_cycle_acc.v_min = g_voltage;
  g_cycle_acc.i_sum += g_current;
  g_cycle_acc.t_sum += g_temperature;
  // Coulomb count: I(A) * dt(hours) → Ah
  g_cycle_acc.coulomb_sum += fabsf(g_current) * (SAMPLE_INTERVAL_MS / 3600000.0f);
  g_cycle_acc.sample_count++;
  g_cycle_acc.duration_ms = millis() - g_cycle_acc.start_ms;
}

void end_cycle() {
  if (!g_cycle_acc.in_progress || g_cycle_acc.sample_count == 0) return;
  g_cycle_acc.in_progress = false;
  g_cycle++;

  float avg_v = g_cycle_acc.v_sum / g_cycle_acc.sample_count;
  float min_v = g_cycle_acc.v_min;
  float avg_i = g_cycle_acc.i_sum / g_cycle_acc.sample_count;
  float avg_t = g_cycle_acc.t_sum / g_cycle_acc.sample_count;
  float dur_s = g_cycle_acc.duration_ms / 1000.0f;

  // SOH tracking
  if (g_cycle <= CALIBRATION_CYCLES) {
    // During calibration: accumulate capacity baseline
    g_soh_baseline += g_cycle_acc.coulomb_sum;
    g_cal_cycle_count = g_cycle;
  }

  if (g_soh_baseline > 0 && g_cycle > 0) {
    g_soh = g_cycle_acc.coulomb_sum / (g_soh_baseline / (float)CALIBRATION_CYCLES);
    if (g_soh > 1.2f) g_soh = 1.2f;
    if (g_soh < 0.0f) g_soh = 0.0f;
  }

  // Build features and run prediction
  float features[N_FEATURES] = {
    (float)g_cycle, avg_v, min_v, avg_i, avg_t, dur_s, g_soh
  };

  tree_engine_select(g_active_model);
  uint32_t t0 = micros();
  g_prediction = tree_engine_predict(features);
  g_infer_us = micros() - t0;

  // Save to history
  if (g_history_count < MAX_HISTORY_POINTS) {
    g_history[g_history_count].pred = g_prediction;
    g_history[g_history_count].cycle = g_cycle;
    g_history_count++;
  } else {
    // Shift
    memmove(g_history, g_history + 1, (MAX_HISTORY_POINTS - 1) * sizeof(g_history[0]));
    g_history[MAX_HISTORY_POINTS - 1].pred = g_prediction;
    g_history[MAX_HISTORY_POINTS - 1].cycle = g_cycle;
  }

  // Log to LittleFS
  DateTime now = read_rtc();
  char buf[256];
  snprintf(buf, sizeof(buf), "%d,%04d-%02d-%02d %02d:%02d:%02d,%.4f,%.4f,%.4f,%.2f,%.1f,%.4f,%.6f,%s,%d\n",
    g_cycle, now.year(), now.month(), now.day(), now.hour(), now.minute(), now.second(),
    avg_v, min_v, avg_i, avg_t, dur_s, g_soh,
    (double)g_prediction, MODEL_NAMES[g_active_model], 0);

  File logf = LittleFS.open(CYCLE_LOG_PATH, FILE_APPEND);
  if (logf) { logf.print(buf); logf.close(); }

  // State transition
  if (g_state == STATE_CALIBRATE_DISCHARGE && g_cycle >= CALIBRATION_CYCLES) {
    g_soh_baseline /= (float)CALIBRATION_CYCLES;
    g_state = STATE_MONITOR;
    Serial.println("→ MONITOR (calibration complete)");
  }
}

void handle_state_machine() {
  switch (g_state) {
    case STATE_INIT: {
      if (g_cycle_acc.in_progress) {
        // If already discharging, skip charge calibration
        if (g_current < DISCHARGE_THRESHOLD_A) {
          g_state = STATE_CALIBRATE_DISCHARGE;
        } else {
          g_state = STATE_CALIBRATE_CHARGE;
        }
      } else {
        g_state = STATE_CALIBRATE_CHARGE;
      }
      Serial.printf("→ %s\n", STATE_NAMES[g_state]);
      break;
    }

    case STATE_CALIBRATE_CHARGE: {
      // Detect charge → discharge transition
      if (g_current < DISCHARGE_THRESHOLD_A && g_cycle_acc.in_progress) {
        end_cycle();
      }
      if (g_current < DISCHARGE_THRESHOLD_A && !g_cycle_acc.in_progress) {
        g_state = STATE_CALIBRATE_DISCHARGE;
        reset_cycle_accum();
        Serial.println("→ CALIBRATE_DISCHARGE");
      }
      if (!g_cycle_acc.in_progress && g_current > CHARGE_THRESHOLD_A) {
        // Charging detected — idle until discharge starts
      }
      break;
    }

    case STATE_CALIBRATE_DISCHARGE: {
      if (g_current > CHARGE_THRESHOLD_A && g_cycle_acc.in_progress) {
        // Transitioned to charging — end this discharge cycle
        end_cycle();
      }
      if (g_current < DISCHARGE_THRESHOLD_A && !g_cycle_acc.in_progress) {
        // Start of new discharge cycle
        reset_cycle_accum();
      }
      break;
    }

    case STATE_MONITOR: {
      if (g_current > CHARGE_THRESHOLD_A && g_cycle_acc.in_progress) {
        end_cycle();
      }
      if (g_current < DISCHARGE_THRESHOLD_A && !g_cycle_acc.in_progress) {
        reset_cycle_accum();
      }
      break;
    }

    case STATE_ERROR:
      break;
  }
}

// ═══════════════════════════════════════════════════════════════════════════
//  ╔══════════════════════════════════════════════════════════════════╗
//  ║        W I F I   &   C A P T I V E   P O R T A L               ║
//  ╚══════════════════════════════════════════════════════════════════╝
// ═══════════════════════════════════════════════════════════════════════════

static bool g_wifi_connected = false;

String read_file(const char *path) {
  File f = LittleFS.open(path, FILE_READ);
  if (!f) return "";
  String s = f.readString();
  f.close();
  return s;
}

bool write_file(const char *path, const String &data) {
  File f = LittleFS.open(path, FILE_WRITE);
  if (!f) return false;
  size_t n = f.print(data);
  f.close();
  return n > 0;
}

bool init_wifi() {
  String cfg = read_file("/wifi.json");
  if (cfg.length() == 0) return false;

  JsonDocument doc;
  DeserializationError err = deserializeJson(doc, cfg);
  if (err) return false;

  const char *ssid = doc["ssid"] | "";
  const char *pass = doc["pass"] | "";
  if (strlen(ssid) == 0) return false;

  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, pass);
  Serial.printf("Connecting to %s", ssid);

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 40) {
    delay(500);
    Serial.print(".");
    attempts++;
  }
  Serial.println();

  if (WiFi.status() == WL_CONNECTED) {
    Serial.printf("WiFi connected: %s\n", WiFi.localIP().toString().c_str());
    g_wifi_connected = true;
    return true;
  }

  Serial.println("WiFi failed — starting AP mode");
  return false;
}

const char SETUP_HTML[] PROGMEM = R"rawliteral(<!DOCTYPE html>
<html><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>Battery Predictor — Setup</title>
<style>body{font-family:-apple-system,BlinkMacSystemFont,sans-serif;
max-width:500px;margin:40px auto;padding:0 16px;background:#0d1117;color:#c9d1d9}
h1{color:#58a6ff}label{display:block;margin-top:16px;font-size:14px}
input{width:100%;padding:10px;margin-top:4px;background:#161b22;
border:1px solid #30363d;border-radius:6px;color:#c9d1d9;font-size:16px}
button{margin-top:24px;padding:12px 24px;background:#238636;color:#fff;
border:none;border-radius:6px;font-size:16px;cursor:pointer;width:100%}
button:hover{background:#2ea043}.error{color:#f85149;margin-top:8px}
.success{color:#3fb950;margin-top:8px}
</style></head><body>
<h1>🔋 Battery Predictor</h1>
<p>Enter your WiFi credentials to connect.</p>
<form id=wf><label>SSID</label><input id=ssid required autofocus>
<label>Password</label><input id=pass type=password>
<button type=submit>Connect</button></form>
<div id=msg></div>
<script>
document.getElementById('wf').onsubmit=async function(e){
e.preventDefault();const r=await fetch('/setup',{method:'POST',
headers:{'Content-Type':'application/json'},
body:JSON.stringify({ssid:document.getElementById('ssid').value,
pass:document.getElementById('pass').value})});
const d=await r.json();
document.getElementById('msg').innerHTML=
d.ok?'<div class=success>Connected! Redirecting...</div>':
'<div class=error>'+d.error+'</div>';
if(d.ok)setTimeout(()=>window.location.href='/',3000);
};
</script></body></html>
)rawliteral";

void start_captive_portal() {
  WiFi.mode(WIFI_AP);
  WiFi.softAP("Battery-Predictor-Setup");
  Serial.printf("AP started: Battery-Predictor-Setup (IP: %s)\n",
    WiFi.softAPIP().toString().c_str());
  g_dns.start(DNS_PORT, "*", WiFi.softAPIP());
}

void handle_setup_post(AsyncWebServerRequest *req) {
  String body = req->hasParam("body", true) ? req->getParam("body", true)->value() : "";
  JsonDocument doc;
  DeserializationError err = deserializeJson(doc, body);
  if (err) {
    AsyncResponseStream *res = req->beginResponseStream("application/json");
    res->print("{\"ok\":false,\"error\":\"Bad JSON\"}");
    req->send(res);
    return;
  }
  const char *ssid = doc["ssid"] | "";
  const char *pass = doc["pass"] | "";

  JsonDocument out;
  out["ssid"] = ssid;
  out["pass"] = pass;
  String outStr;
  serializeJson(out, outStr);
  write_file("/wifi.json", outStr);

  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, pass);
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 30) {
    delay(500);
    attempts++;
  }

  AsyncResponseStream *res = req->beginResponseStream("application/json");
  if (WiFi.status() == WL_CONNECTED) {
    g_wifi_connected = true;
    g_dns.stop();
    res->print("{\"ok\":true}");
  } else {
    WiFi.mode(WIFI_AP);
    WiFi.softAP("Battery-Predictor-Setup");
    g_dns.start(DNS_PORT, "*", WiFi.softAPIP());
    res->print("{\"ok\":false,\"error\":\"Connection failed — check credentials\"}");
  }
  req->send(res);
}

void handle_dns() {
  g_dns.processNextRequest();
}

// ═══════════════════════════════════════════════════════════════════════════
//  ╔══════════════════════════════════════════════════════════════════╗
//  ║          W E B   S E R V E R   &   D A S H B O A R D           ║
//  ╚══════════════════════════════════════════════════════════════════╝
// ═══════════════════════════════════════════════════════════════════════════

// ── Embed dashboard HTML in PROGMEM ─────────────────────────────────────
const char DASHBOARD_HTML[] PROGMEM = R"rawliteral(
<!DOCTYPE html>
<html><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>Battery Health Predictor</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js"></script>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
background:#0d1117;color:#c9d1d9;padding:20px;max-width:1200px;margin:0 auto}
h1{color:#58a6ff;font-size:24px;margin-bottom:4px;display:flex;align-items:center;gap:8px}
.subtitle{color:#8b949e;font-size:14px;margin-bottom:24px}
.card{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:16px;margin-bottom:16px}
.card h2{font-size:16px;color:#8b949e;margin-bottom:12px;text-transform:uppercase;letter-spacing:0.5px}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}
@media(max-width:768px){.grid{grid-template-columns:1fr}}
.sensor-group{display:flex;flex-wrap:wrap;gap:12px}
.sensor{flex:1;min-width:100px;background:#0d1117;border-radius:6px;padding:12px;text-align:center}
.sensor .label{font-size:12px;color:#8b949e}
.sensor .value{font-size:24px;font-weight:700;color:#f0f6fc;margin-top:4px}
.sensor .unit{font-size:14px;color:#8b949e}
.sensor.voltage .value{color:#58a6ff}
.sensor.current .value{color:#d2a8ff}
.sensor.temp .value{color:#79c0ff}
.sensor.soh .value{color:#3fb950}
.sensor.cycle .value{color:#e3b341}
.prediction{font-size:36px;font-weight:700;text-align:center;padding:20px}
.prediction .prob{color:#58a6ff}
.prediction .label{font-size:14px;color:#8b949e;font-weight:400}
.state{display:inline-flex;align-items:center;gap:6px;
padding:4px 12px;border-radius:12px;font-size:14px;font-weight:600}
.state.init{background:#1f2028;color:#8b949e}
.state.calibrate_charge{background:#1f3820;color:#3fb950}
.state.calibrate_discharge{background:#3d2e00;color:#d29922}
.state.monitor{background:#0d419d;color:#58a6ff}
.state.error{background:#490202;color:#f85149}
.model-select select{background:#0d1117;color:#c9d1d9;border:1px solid #30363d;
border-radius:6px;padding:6px 12px;font-size:14px;margin-left:8px}
button{background:#238636;color:#fff;border:none;border-radius:6px;
padding:8px 16px;font-size:14px;cursor:pointer;transition:.2s}
button:hover{background:#2ea043}
button.danger{background:#da3633}
button.danger:hover{background:#f85149}
.controls{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-top:12px}
.chart-container{position:relative;height:250px;width:100%}
#log{border:1px solid #30363d;border-radius:6px;background:#0d1117;
font-family:'SF Mono','Fira Code',monospace;font-size:11px;color:#8b949e;
padding:16px;max-height:300px;overflow:auto;white-space:pre;line-height:1.5}
.dot{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:6px}
.dot.green{background:#3fb950}
.dot.yellow{background:#d29922}
.dot.red{background:#f85149}
</style></head><body>
<h1>🔋 Battery Health Predictor</h1>
<div class=subtitle>battery-predictor.local  ·  <span id=ip></span></div>

<div class="grid">
<div>
<div class=card>
<h2>Status</h2>
<div style=display:flex;gap:16px;align-items:center;flex-wrap:wrap>
<span id=stateEl class="state init">INIT</span>
<span id=modelDisplay style=font-size:14px>Model: <strong id=modelName>xgboost</strong></span>
<span style=font-size:14px>Cycle: <strong id=cycleCount>0</strong></span>
</div>
<div class=controls>
<label style=font-size:14px>Switch model:
<select id=modelSelect style=background:#0d1117;color:#c9d1d9;border:1px solid #30363d;border-radius:6px;padding:4px 8px>
<option value=0>XGBoost</option>
<option value=1>LightGBM</option>
<option value=2>Random Forest</option>
</select></label>
<button id=recalBtn class=danger style=margin-left:auto>Re-calibrate</button>
</div>
</div>

<div class=card>
<h2>Live Sensors</h2>
<div class=sensor-group>
<div class="sensor voltage"><div class=label>Voltage</div>
<div class=value id=vVal>--</div><div class=unit>V</div></div>
<div class="sensor current"><div class=label>Current</div>
<div class=value id=iVal>--</div><div class=unit>A</div></div>
<div class="sensor temp"><div class=label>Temperature</div>
<div class=value id=tVal>--</div><div class=unit>°C</div></div>
<div class="sensor soh"><div class=label>SOH</div>
<div class=value id=sohVal>--</div><div class=unit>%</div></div>
</div>
</div>

<div class=card>
<h2>Latest Prediction</h2>
<div class=prediction>
<div class=prob id=predVal>-</div>
<div class=label>failure probability within next 20 cycles</div>
</div>
</div>
</div>

<div>
<div class=card>
<h2>Prediction History</h2>
<div class=chart-container><canvas id=predChart></canvas></div>
</div>

<div class=card>
<h2>Actions</h2>
<button id=downloadBtn>📥 Download Cycle Log</button>
</div>
</div>
</div>

<div class=card>
<h2>Cycle Log</h2>
<div id=log>Waiting for data...</div>
</div>

<script>
const ws=new WebSocket('ws://'+location.host+'/ws');
const ctx=document.getElementById('predChart').getContext('2d');
let chart=new Chart(ctx,{type:'line',data:{labels:[],datasets:[{
label:'Prediction',data:[],borderColor:'#58a6ff',
backgroundColor:'rgba(88,166,255,0.08)',fill:true,
tension:0.3,pointRadius:2,pointHitRadius:8}]},
options:{responsive:true,maintainAspectRatio:false,
plugins:{legend:{display:false}},
scales:{x:{display:true,grid:{color:'#21262d'},
ticks:{color:'#8b949e',maxTicksLimit:10}},
y:{beginAtZero:true,max:1,grid:{color:'#21262d'},
ticks:{color:'#8b949e',format:{style:'percent'}}}}}});

document.getElementById('modelSelect').onchange=async function(){
await fetch('/api/model',{method:'POST',
headers:{'Content-Type':'application/json'},
body:JSON.stringify({model:parseInt(this.value)})});
};

document.getElementById('recalBtn').onclick=async function(){
if(confirm('Restart calibration?')){
await fetch('/api/recalibrate',{method:'POST'});}
};

document.getElementById('downloadBtn').onclick=function(){
window.location.href='/api/download';
};

ws.onmessage=function(e){
const d=JSON.parse(e.data);
document.getElementById('vVal').textContent=d.v.toFixed(3);
document.getElementById('iVal').textContent=d.i.toFixed(3);
document.getElementById('tVal').textContent=d.t.toFixed(1);
document.getElementById('sohVal').textContent=(d.soh*100).toFixed(1);
document.getElementById('cycleCount').textContent=d.cycle;
document.getElementById('predVal').textContent=(d.pred*100).toFixed(1)+'%';
document.getElementById('modelName').textContent=d.model;

const st=d.state.toLowerCase();
document.getElementById('stateEl').className='state '+st;
document.getElementById('stateEl').textContent=d.state.replace(/_/g,' ');

document.getElementById('modelSelect').value=d.active_model;

if(d.history&&d.history.length){
chart.data.labels=d.history.map((_,i)=>'#'+(i+1));
chart.data.datasets[0].data=d.history;
chart.update();
}
if(d.log){
document.getElementById('log').textContent=d.log;
}
};

fetch('/api/status').then(r=>r.json()).then(d=>{
document.getElementById('ip').textContent=d.ip;
if(d.history) {
chart.data.labels=d.history.map((_,i)=>'#'+(i+1));
chart.data.datasets[0].data=d.history;
chart.update();
}
});
</script></body></html>
)rawliteral";

// ── WebSocket event handler ──────────────────────────────────────────────
void on_ws_event(AsyncWebSocket *server, AsyncWebSocketClient *client,
                 AwsEventType type, void *arg, uint8_t *data, size_t len) {
  (void)server; (void)data; (void)len;
  if (type == WS_EVT_CONNECT) {
    client->printf("{\"connected\":true}");
  }
}

// ── Build status JSON ────────────────────────────────────────────────────
String build_status_json() {
  JsonDocument doc;
  doc["v"] = g_voltage;
  doc["i"] = g_current;
  doc["t"] = g_temperature;
  doc["soh"] = g_soh;
  doc["cycle"] = g_cycle;
  doc["pred"] = g_prediction;
  doc["infer_us"] = g_infer_us;
  doc["state"] = STATE_NAMES[g_state];
  doc["model"] = MODEL_NAMES[g_active_model];
  doc["active_model"] = g_active_model;
  doc["cal_cycle"] = g_cal_cycle_count;
  doc["ip"] = g_wifi_connected ? WiFi.localIP().toString() : WiFi.softAPIP().toString();

  // Prediction history
  JsonArray hist = doc["history"].to<JsonArray>();
  int start = g_history_count > 100 ? g_history_count - 100 : 0;
  for (int i = start; i < g_history_count; i++) {
    hist.add(g_history[i].pred);
  }

  // Last 20 lines of cycle log
  String logData = read_file(CYCLE_LOG_PATH);
  if (logData.length() > 0) {
    int idx = logData.lastIndexOf('\n', logData.length() - 2);
    for (int i = 0; i < 20 && idx > 0; i++) {
      idx = logData.lastIndexOf('\n', idx - 1);
    }
    if (idx > 0) logData = logData.substring(idx + 1);
    doc["log"] = logData;
  }

  String out;
  serializeJson(doc, out);
  return out;
}

// ── Register HTTP handlers ───────────────────────────────────────────────
void init_web_server() {
  g_ws.onEvent(on_ws_event);
  g_server.addHandler(&g_ws);

  g_server.on("/", HTTP_GET, [](AsyncWebServerRequest *req) {
    if (g_wifi_connected) {
      req->send(200, "text/html", DASHBOARD_HTML);
    } else {
      req->send(200, "text/html", SETUP_HTML);
    }
  });

  g_server.on("/setup", HTTP_POST, handle_setup_post);

  g_server.on("/api/status", HTTP_GET, [](AsyncWebServerRequest *req) {
    String json = build_status_json();
    AsyncResponseStream *res = req->beginResponseStream("application/json");
    res->print(json);
    req->send(res);
  });

  g_server.on("/api/model", HTTP_POST, [](AsyncWebServerRequest *req) {
    String body = req->hasParam("body", true) ? req->getParam("body", true)->value() : "";
    JsonDocument doc;
    DeserializationError err = deserializeJson(doc, body);
    if (err) { req->send(400, "application/json", "{\"error\":\"Bad JSON\"}"); return; }

    int model = doc["model"] | -1;
    if (model < 0 || model > 2) { req->send(400, "application/json", "{\"error\":\"Invalid model\"}"); return; }

    g_active_model = model;
    AsyncResponseStream *res = req->beginResponseStream("application/json");
    res->printf("{\"ok\":true,\"model\":%d,\"name\":\"%s\"}", model, MODEL_NAMES[model]);
    req->send(res);
  });

  g_server.on("/api/recalibrate", HTTP_POST, [](AsyncWebServerRequest *req) {
    g_state = STATE_CALIBRATE_CHARGE;
    g_cal_cycle_count = 0;
    g_cycle = 0;
    g_soh_baseline = 0;
    g_soh = 1.0f;
    g_history_count = 0;
    g_cycle_acc.in_progress = false;
    LittleFS.remove(CYCLE_LOG_PATH);
    req->send(200, "application/json", "{\"ok\":true}");
  });

  g_server.on("/api/download", HTTP_GET, [](AsyncWebServerRequest *req) {
    if (LittleFS.exists(CYCLE_LOG_PATH)) {
      req->send(LittleFS, CYCLE_LOG_PATH, "text/csv", true);
    } else {
      req->send(404, "text/plain", "No data yet");
    }
  });

  g_server.onNotFound([](AsyncWebServerRequest *req) {
    // Captive portal: redirect to ESP's IP
    String ip = g_wifi_connected ? WiFi.localIP().toString() : WiFi.softAPIP().toString();
    req->redirect("http://" + ip);
  });

  g_server.begin();
}

// ═══════════════════════════════════════════════════════════════════════════
//  LITTLEFS
// ═══════════════════════════════════════════════════════════════════════════

void init_littlefs() {
  if (!LittleFS.begin(true)) {
    Serial.println("ERROR: LittleFS mount failed — formatting...");
    LittleFS.format();
    if (!LittleFS.begin()) {
      Serial.println("FATAL: LittleFS");
      g_state = STATE_ERROR;
    }
  } else {
    Serial.println("LittleFS mounted");
    // Initialize cycle log with header if new
    if (!LittleFS.exists(CYCLE_LOG_PATH)) {
      File f = LittleFS.open(CYCLE_LOG_PATH, FILE_WRITE);
      if (f) {
        f.println("cycle,datetime,avg_voltage,min_voltage,avg_current,avg_temp,duration,soh,prediction,model,label");
        f.close();
      }
    }
  }
}

// ═══════════════════════════════════════════════════════════════════════════
//  ╔══════════════════════════════════════════════════════════════════╗
//  ║               S E T U P   &   L O O P                           ║
//  ╚══════════════════════════════════════════════════════════════════╝
// ═══════════════════════════════════════════════════════════════════════════

void setup() {
  Serial.begin(115200);
  delay(100);
  Serial.println("\n\n=== Battery Health Predictor ===");

  // Initialize storage
  init_littlefs();

  // Initialize tree engine with PROGMEM model data
  if (!tree_engine_init(trees_bin, trees_bin_len)) {
    Serial.println("FATAL: tree_engine_init failed");
    g_state = STATE_ERROR;
    return;
  }
  Serial.printf("Tree engine loaded: %d models\n", g_n_models);
  for (int i = 0; i < g_n_models; i++) {
    Serial.printf("  Model %d: %d trees, %d nodes, type=%d\n",
      i, g_models[i].n_trees, g_models[i].total_nodes, g_models[i].model_type);
  }

  // Initialize sensors
  init_sensors();

  // WiFi
  if (!init_wifi()) {
    start_captive_portal();
  }

  // mDNS
  if (g_wifi_connected) {
    if (MDNS.begin("battery-predictor")) {
      MDNS.addService("http", "tcp", WEB_PORT);
      Serial.println("mDNS: http://battery-predictor.local");
    }
  }

  // Web server
  init_web_server();
  Serial.println("Web server started");

  // Initial sensor reading
  sample_sensors();
  Serial.println("Ready.");
}

void loop() {
  // Network housekeeping
  handle_dns();
  g_ws.cleanupClients();

  // Sample sensors at 10 Hz
  static unsigned long last_sample = 0;
  unsigned long now = millis();
  if (now - last_sample >= SAMPLE_INTERVAL_MS) {
    last_sample = now;
    sample_sensors();

    // Accumulate cycle data if in active discharge
    if (g_cycle_acc.in_progress && g_current < DISCHARGE_THRESHOLD_A) {
      sample_cycle_accum();
    }

    // Run state machine
    handle_state_machine();
  }

  // Push dashboard data at 1 Hz
  static unsigned long last_dash = 0;
  if (now - last_dash >= DASHBOARD_INTERVAL_MS) {
    last_dash = now;
    String json = build_status_json();
    g_ws.textAll(json);
  }

  // Small delay to prevent watchdog issues
  delay(5);
}
