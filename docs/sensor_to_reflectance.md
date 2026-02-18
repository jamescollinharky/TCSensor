# Translation: Sensor Values → reflectance_nm

Peuchant regression expects **reflectance** R ∈ (0, 1] at each wavelength. The sensor gives **ADC counts** (or absorption). Below is the translation.

---

## 1. Sensor output: ADC counts (bits)

- Example: 940 nm band → counts like 947, 886, 940, …  
- Example: 1720 nm band → counts like 703, 725, 747, …

Count = raw ADC reading (e.g. 10-bit → 0–1023). Count is proportional to **intensity** I (light reaching the detector).

---

## 2. Counts → Absorption (optional intermediate)

**Absorption** (base-10):

```
A = -log₁₀(I / I₀) = -log₁₀(count / I₀)
```

- **I₀** = reference (e.g. 1023 for 10-bit full scale, or a “no sample” baseline count).
- Clip `count / I₀` to (0, 1] to avoid log(0).

Example: count = 747, I₀ = 1023  
→ A = -log₁₀(747/1023) ≈ **0.1366**

---

## 3. Absorption → Reflectance

**Reflectance** R and absorption A are related by:

```
R = 10^(-A)
```

So:

- If you have **count** and I₀:  
  **R = count / I₀**  
  (same as R = 10^(-A) when A = -log₁₀(count/I₀).)

- If you have **absorption** A from the sensor or from step 2:  
  **R = 10^(-A)**

Example: A = 0.1366 → R = 10^(-0.1366) ≈ **0.7302**

---

## 4. Mapping sensor bands to Peuchant wavelengths

Peuchant uses 7 wavelengths (nm): **2208, 2190, 1940, 1734, 1722, 1445, 1680**.

| Sensor band (nm) | Use for Peuchant (nm) | Notes |
|------------------|------------------------|--------|
| 940              | —                      | Not in Peuchant set; store for reference only. |
| 1720             | **1722**               | Use 1720-band R (or A→R) as reflectance at 1722 nm. |

For wavelengths you do **not** measure (e.g. 1445, 1680, 1734, 1940, 2190, 2208), use another source (e.g. median of synthetic data, or a reference spectrum).

---

## 5. Full pipeline (sensor → reflectance_nm)

```
For each measured band:

  count_raw = <ADC reading>           # e.g. 747
  I0        = 1023                     # or your reference count
  A         = -log10(count_raw / I0)   # absorption
  R         = 10^(-A)                  # reflectance (equiv: R = count_raw / I0)

  Assign R to the corresponding Peuchant wavelength (e.g. 1720 band → 1722 nm).

For unmeasured Peuchant wavelengths:

  Use median/mean from calibration set, or reference spectrum (e.g. synthetic).
```

**reflectance_nm** for Peuchant is then:

```json
{
  "2208": <R or placeholder>,
  "2190": <R or placeholder>,
  "1940": <R or placeholder>,
  "1734": <R or placeholder>,
  "1722": <R from 1720 nm sensor>,
  "1445": <R or placeholder>,
  "1680": <R or placeholder>
}
```

with each value in (0, 1].

---

## 6. One-line summary

| You have      | To get R for Peuchant      |
|---------------|----------------------------|
| Count, I₀     | R = count / I₀             |
| Absorption A  | R = 10^(-A)                |

Then pass the 7-wavelength **reflectance_nm** dict into the Peuchant regression.
