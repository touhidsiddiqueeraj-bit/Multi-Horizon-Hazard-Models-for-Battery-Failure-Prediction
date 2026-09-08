# Multi-Horizon Hazard Framework

## Problem Setup

Given a lithium-ion battery cell cycled from time $t = 1, 2, \dots, T$, the goal at each cycle $t$ is to predict:

> **Will this cell fail within the next $H$ cycles?**

This reformulates battery health prognosis as **binary classification** instead of traditional RUL regression.

---

## Failure Definition

A cell is considered **failed** when **either** criterion triggers:

| Criterion | Threshold | Physical Meaning |
|-----------|-----------|------------------|
| SOH | $\text{SOH}(t) \leq 0.80$ | Capacity degraded to 80% of initial |
| Voltage sag | $V_{\text{avg}}(t) < 0.94 \cdot V_{\text{baseline}}$ | Impedance growth (early-cycles baseline) |

Let $t_f$ be the first cycle where either condition holds:

$$t_f = \min\left(\; \min\{t : \text{SOH}(t) \leq 0.80\},\; \min\{t : V_{\text{avg}}(t) < 0.94 \cdot V_{\text{baseline}}\} \;\right)$$

---

## Composite Binary Label

For a given horizon $H$, the label $y^{(H)}(t)$ is:

$$y^{(H)}(t) = \begin{cases}
1 & \text{if } t_f \leq t + H \\
0 & \text{otherwise}
\end{cases}$$

Equivalently: $y^{(H)}(t) = \mathbb{1}\big(t_f \in [t,\; t+H)\big)$.

Once $y^{(H)}(t) = 1$ for a cell, it stays 1 for all subsequent cycles (absorbing state).

---

## Multi-Horizon

The classification problem is solved **independently** for each horizon:

$$H \in \{10, 20, 30, 50\}$$

- **$H=10$**: short-term warning (~2% of life)
- **$H=50$**: longer-term risk (~10% of life)

Shorter horizons predict more imminent failures; longer horizons capture more failure events per cell (easier AUC, less precise timing).

---

## Model

Each horizon trains a classifier $f_H(x_t)$ that outputs a failure probability:

$$p_{\text{fail}}^{(H)}(t) = f_H\left(\text{cycle}_t,\; V_{\text{avg}}(t),\; V_{\text{min}}(t),\; I_{\text{avg}}(t),\; T_{\text{avg}}(t),\; \text{duration}(t),\; \text{SOH}(t)\right)$$

Four model classes are tested: **XGBoost**, **LightGBM**, **Random Forest**, and **GRU** (1-layer, 8 hidden units, sliding window $W=10$).

---

## Why Not RUL?

| Aspect | RUL regression | Multi-horizon hazard |
|--------|---------------|---------------------|
| Output | Continuous time-to-failure | Discrete probability per cycle |
| Uncertainty | Implicit/noisy | Well-calibrated via Platt scaling |
| Transfer | Degradation model doesn't shift | Can test whether features transfer |
| Evaluation | MAE/RMSE (scale-dependent) | AUC + Brier (threshold-free) |

The hazard framing reveals that **SOH is a chemistry-specific lookup table**, not a transferable degradation feature — a finding RUL regression would mask.
