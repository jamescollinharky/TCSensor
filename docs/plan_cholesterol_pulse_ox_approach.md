# Plan: Adapting Pulse Oximeter Logic for Cholesterol Measurement

## 1. How a Pulse Oximeter Works (Logic Summary)

### 1.1 Physical basis
- **Beer–Lambert law**: Absorbance \( A = \varepsilon(\lambda) \cdot c \cdot L \): extinction coefficient × concentration × path length.  
  Transmittance \( T = I/I_0 = e^{-A} \), so \( A = \log(1/T) \). For reflectance, a similar idea: \( R \propto \) reflected intensity; \( \log(1/R) \) is used as an absorbance-like term (e.g. Peuchant 1987).
- **Two wavelengths**: Medical pulse oximeters use **red (~660 nm)** and **infrared (~940 nm)** because:
  - Oxyhemoglobin (HbO₂) and deoxyhemoglobin (Hb) have **different extinction coefficients** at these two λ.
  - The **ratio** of absorption at the two wavelengths is related to the **ratio** HbO₂/(HbO₂ + Hb) = SpO₂.

### 1.2 AC/DC decomposition
- The PPG (photoplethysmography) signal has:
  - **DC**: baseline light level (static tissue, venous blood, bone, etc.).
  - **AC**: small **pulsatile** change with each heartbeat (arterial blood volume change).
- Only the **arterial** component carries the oxygen-saturation information; the DC is often treated as constant over a few seconds so that **AC/DC** at each wavelength isolates the pulsatile absorption.

### 1.3 Ratio-of-ratios (RoR)
- Define at each wavelength: \( (AC/DC)_\lambda \).
- **Ratio of ratios**:  
  \[
  R = \frac{(AC/DC)_{\text{red}}}{(AC/DC)_{\text{IR}}}
  \]
- \( R \) depends on SpO₂ because the **relative** change in absorption with pulse is different for red vs IR (Hb vs HbO₂). Path length and scattering largely cancel in the ratio.
- SpO₂ is obtained from \( R \) via an **empirical calibration curve** (from blood gas reference), not from first principles.

---

## 2. What Transfers to Cholesterol vs What Doesn’t

| Pulse oximeter | Cholesterol (Peuchant / NIR) |
|----------------|-------------------------------|
| **Two wavelengths** (red, IR) | **Multiple wavelengths** (e.g. 7 in Peuchant: 1445, 1680, 1722, 1734, 1940, 2190, 2208 nm) |
| **Pulsatile (AC)** carries the signal | **Static (DC)** reflectance; cholesterol is not “pulsing” like SpO₂ |
| **Ratio-of-ratios** → SpO₂ | **Linear combination** \( TC = a_0 + \sum a_i \log(1/R_i) \) (Peuchant) or ratio of log(1/R) at 2 bands |
| **Calibration**: RR vs SaO₂ (blood gas) | **Calibration**: reflectance vs TC from reference method (e.g. enzymatic) |
| **Beer–Lambert / log(1/T)** | Same idea: **log(1/R)** as absorbance-like term |

So:
- **Reuse**: multi-wavelength (or multi-band) reflectance, **log(1/R)** as signal, **calibration** with reference concentrations.
- **Don’t copy literally**: no need for AC/DC ratio-of-ratios for cholesterol *concentration* (no pulsatile cholesterol signal). We use **DC only** (mean reflectance over a short window).

Optional advanced idea: use **PPG only to improve measurement conditions** (e.g. average during stable pulse, or gate by contact quality), not to derive cholesterol from a ratio-of-ratios.

---

## 3. Adaptation Strategy: Multi-band sensor (no camera)

### 3.1 Goal
- Use the **same conceptual pipeline** as pulse oximetry: **multiple bands** → **absorbance-like terms** → **one number** (TC or “cholesterol index”) via a **calibrated** formula.
- Use **Arduino multi-band NIR** (e.g. 1300, 1460, 1650, 1720, 1900 nm) or other sensor bands; we do **not** rely on a camera.

### 3.2 Signal chain

1. **Acquire reflectance at several wavelengths**
   - Multi-band cycle: one LED at a time, read sensor; merged CSV: ms, 1300, 1460, 1650, 1720, 1900.
   - This is the **DC** component only (no AC extraction for cholesterol concentration).

2. **Convert to absorbance-like terms**
   - For each band: \( A_i = \log(1/R_i) \), with \( R_i \in (0,1] \) (normalize counts if needed).
   - Same idea as Peuchant: \( \log(1/R) \) at each wavelength.

3. **Combine into one index (two options)**

   **Option A – Peuchant-style linear (recommended)**  
   \[
   \text{TC\_index} = a_0 + \sum a_i A_i
   \]  
   - Coefficients from **regression** on a calibration set: known TC (reference method) vs reflectance/absorbance from sensor bands.
   - Same logic as Peuchant Table I, with available NIR bands.

   **Option B – Ratio (pulse-ox-like)**  
   \[
   \text{Chol\_index} = \frac{A_{\lambda_1}}{A_{\lambda_2}} \quad \text{or similar}
   \]  
   - One ratio of two bands; calibrate with reference TC. Simpler, less flexible than Option A.

4. **Calibration**
   - Collect **reference TC** (enzymatic or lab) for N samples.
   - For each sample, record sensor (counts or reflectance) under **fixed** conditions.
   - Fit regression; store coefficients.

5. **Validation**
   - New samples: predict TC from sensor; compare to reference. Report correlation, bias, limits of agreement if possible.

### 3.3 Where “pulse oximeter logic” appears
- **Multi-band reflectance** → **log(1/R)** → **single number by calibrated formula**: same *structure* as pulse ox.
- **No pulsatile component**: we use **mean** reflectance (DC) over a short window, not AC/DC. (bandpass, AC/DC) only to compute a **contact/quality** or **motion** score and discard bad segments, or to average only over “quiet” intervals—i.e. use PPG as a **gating** tool, not as the source of a cholesterol ratio.

---

## 4. Implementation Plan (Steps)

| Step | Task | Notes |
|------|------|--------|
| 1 | **Sensor bands** | Arduino multi_band_cycle + capture_multi_band_serial.py → CSV: ms, 1300, 1460, 1650, 1720, 1900. |
| 2 | **Reflectance → log(1/R)** | Normalize to [0,1], compute \( A_i = \log(1/R_i) \), avoid log(0). Reuse logic from `cholesterol_peuchant_nir.py` / `validate_peuchant_nir.py`. |
| 3 | **Calibration data format** | Define JSON/CSV: per sample, reference_TC_mmol_L + counts or (A_1300, …). |
| 4 | **Regression (Option A)** | Fit TC = a0 + Σ a_i*A_i. Save coefficients. |
| 5 | **Optional Option B** | Implement ratio Chol_index = A_λ1/A_λ2, fit TC = f(Chol_index). |
| 6 | **Inference script** | Load calibration; from live or recorded (R,G,B[,NIR]) compute A’s and then TC_index (or TC from calibration curve). |
| 7 | **Validation** | Synthetic or lab data: compare predicted TC to reference; report R², RMSE, Bland–Altman if applicable. |

---

## 5. Risks and Limitations

- **Calibration is everything**: Accuracy will depend on reference method and on matching conditions (sample type, geometry). Must be clearly “not for medical use” without proper validation.
- **Sample presentation**: Serum on strip vs cuvette vs finger will change the model; calibration should be per presentation type.

---

## 6. References

- Pulse oximetry: [Wikipedia](https://en.wikipedia.org/wiki/Pulse_oximetry); Beer–Lambert, AC/DC, ratio-of-ratios.
- Project: `scripts/cholesterol_peuchant_nir.py` (log(1/R), 7-wavelength formula); Arduino multi-band cycle + `capture_multi_band_serial.py` for sensor data.
- Peuchant E et al. Anal. Chem. 1987, 59, 1816–1819 (NIR reflectance, 7 filters, TC = a0 + Σ a_i log(1/R_i)).
