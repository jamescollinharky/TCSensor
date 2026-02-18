# Sensor recommendations for Peuchant 1987 NIR wavelengths

**Reference:** Peuchant E et al. *Anal. Chem.* 1987, 59, 1816–1819.

The paper uses **reflectance** at **7 wavelengths**: **1445, 1680, 1722, 1734, 1940, 2190, 2208 nm** (10 nm bandwidth filters), with formula **TC = a₀ + Σ aᵢ log(1/Rᵢ)**. The original instrument was a Technicon InfraAlyzer 450 (1445–2345 nm, 19 filters).

To replicate that approach you need a sensor that can measure **reflectance (or absorbance)** in the **NIR range ~1445–2210 nm**. Silicon photodiodes/cameras stop around 1000 nm; **InGaAs** (indium gallium arsenide) detectors are used for 900–1700 nm; **extended InGaAs** or similar for 1700–2500 nm.

---

## Requirements (from the paper)

| Item | Spec |
|------|------|
| Wavelength range | At least **1445–2208 nm** (ideally 1445–2345 nm) |
| Bandwidth | ~10 nm per channel (narrow band) |
| Mode | **Reflectance** (ratio reflected / incident); log(1/R) used in the formula |
| Sample | Liquid (serum) in a cell; reflectance from the sample |

---

## Recommended sensors / systems (from public info)

### 1. **NIRvascan™ handheld NIR** (Allied Scientific Pro)

- **URL:** [NIRvascan handheld NIR spectrometer](https://www.alliedscientificpro.com/en/nirvascan)
- **Range:** Multiple models; **R12**: 1350–2150 nm; **R14**: 1600–2400 nm; **R16**: 900–2400 nm.
- **Fit for Peuchant:** **R16** (900–2400 nm) covers all 7 wavelengths; **R14** covers 1680–2208 nm (misses 1445 nm); **R12** covers 1445–2150 nm (misses 2190, 2208).
- **Resolution:** ~10–12 nm; wavelength accuracy ±1 nm.
- **Price:** ~\$2,995 (R14/R16 tier).
- **Notes:** Handheld, portable; good match to the 7-wavelength range if you use R16 or combine with a unit that includes 1445 nm.

### 2. **Ocean Insight NIRQuest (e.g. 512)**

- **URL:** [Ocean Insight NIRQuest](https://www.oceaninsight.com/products/spectrometers/) (search “NIRQuest”).
- **Range:** 512-element InGaAs array; variants include **900–1700 nm**, **900–2200 nm**, **900–2500 nm**.
- **Fit for Peuchant:** Choose the **900–2200 nm** or **900–2500 nm** version to cover 1445–2208 nm in one instrument.
- **Notes:** Benchtop/fiber-coupled; thermoelectrically cooled; research-grade. You’d need a reflectance accessory (e.g. integrating sphere or fiber probe) and a NIR light source.

### 3. **ZEISS AURA® handheld NIR**

- **URL:** [ZEISS AURA handheld NIR](https://zeiss.com/spectroscopy/products/spectrometer-systems/aura.html)
- **Range:** 950–1650 nm (from search results).
- **Fit for Peuchant:** **Does not cover** 1680–2208 nm; only 1445 nm and 1650 nm fall in range. **Not sufficient** for the full 7-wavelength method.

### 4. **Sarspec ProNIR**

- **URL:** [Sarspec ProNIR](https://www.sarspec.com/products/spectrometers/pronir)
- **Range:** 1000–2500 nm (256 or 512 pixel InGaAs, TE cooled).
- **Fit for Peuchant:** Full 1445–2208 nm in one unit.
- **Notes:** Benchtop / OEM style; need reflectance setup and illumination.

### 5. **InnoSpectra NIR (e.g. NIR-S-G1, NIR-M-F1)**

- **URL:** [InnoSpectra NIR](https://www.inno-spectra.com/) (e.g. reflective NIR-S-G1, 900–1700 nm).
- **Range:** 900–1700 nm typical for standard InGaAs; extended range models may go to 2500 nm.
- **Fit for Peuchant:** 900–1700 nm covers **1445, 1680, 1722, 1734, 1940**; you’d need an **extended-range** model or a second unit for **2190, 2208 nm**.

### 6. **NIRLIGHT (NIRLAB)**

- **URL:** [NIRLIGHT handheld NIR](https://www.nirlab.com/nirlight/)
- **Notes:** Handheld, Bluetooth/USB; exact wavelength range should be confirmed (many handhelds are 900–1700 nm). Check specs for 1700–2200 nm coverage before assuming full Peuchant coverage.

---

## Cheap ways to get NIR (and their limits)

### Why “cheap” and “full Peuchant” don’t match

- **Silicon** (photodiodes, cameras, AS7263): sensitive only up to ~**1000–1100 nm**. Very cheap, but **cannot** see 1445–2208 nm.
- **Standard InGaAs**: sensitive to ~**1700 nm**. Moderately priced; covers **1445, 1680, 1722, 1734**, and partly **1940 nm**.
- **Extended InGaAs** (or InGaAsSb, etc.): needed for **2190, 2208 nm**. More expensive (hundreds to thousands per detector or in a spectrometer).

So a **cheap** setup can only cover **part** of the Peuchant range; **full** 7-wavelength needs extended InGaAs or a commercial unit.

---

### Option A: Silicon NIR (cheapest, wrong range for Peuchant)

- **Parts:** IR photodiode (e.g. BPW34, SFH 203, ~\$0.10–2), or **AS7263** 6-channel NIR spectral sensor (~\$28, SparkFun/Core Electronics).
- **Range:** ~600–870 nm (AS7263) or ~900–1000 nm (silicon photodiode). **Does not reach 1445 nm.**
- **Use:** Good for visible/short-NIR (e.g. pulse oximetry proxy, color); **not** for the Peuchant formula.

---

### Option B: Single InGaAs photodiode + DIY spectrometer (~\$200–500)

- **Idea:** One InGaAs photodiode (~\$20–60), a **diffraction grating** (e.g. 600 lines/mm for 800–1600 nm), an **optical slit** (e.g. fiber or slit), and a **scanning stage** (e.g. stepper + linear stage) so the detector moves across the dispersed spectrum.
- **Range:** Typically **800–1600 nm** (or 800–1700 nm with a 1.7 µm cutoff InGaAs). That gives you **1445, 1680, 1722, 1734** nm and part of **1940 nm**; **2190 and 2208 nm** are out of range for standard InGaAs.
- **References:** DIY NIR spectrometer designs (e.g. [caoyuan.scripts.mit.edu/ir_spec](https://caoyuan.scripts.mit.edu/ir_spec.html)), open NIR spectroscope PCBs on EasyEDA.
- **Result:** “Partial Peuchant” (4–5 of 7 wavelengths) with calibration; full formula still needs 2190/2208 nm.

---

### Option C: InGaAs photodiode module (one band, ~\$60–100)

- **Parts:** Ready-made **InGaAs PIN photodiode module** (800–1700 nm), e.g. ~\$59 (BeamQ) or similar from Digi‑Key/Mouser. You get **one** wide-band NIR channel.
- **To get multiple wavelengths:** Add **narrow bandpass filters** (e.g. 1445, 1680, 1722 nm) in front of the detector and swap them (filter wheel or manual). NIR bandpass filters at 1400–1700 nm exist but are not very cheap; 2000–2200 nm filters need extended-range optics.
- **Result:** Possible to build a few discrete channels in 1445–1700 nm for a few hundred dollars; 2190/2208 nm still need extended InGaAs + suitable filters.

---

### Option D: Raspberry Pi / Arduino + “NIR” boards

- **AS7263, AS7262, AS7341:** These are **silicon** multi-channel spectral sensors (visible and/or 600–870 nm or 350–1000 nm). **None** reach 1445 nm.
- **Result:** No cheap Pi/Arduino board covers the Peuchant NIR range; they are for visible/short-NIR only.

---

### Summary: cheap vs full Peuchant

| Approach | Est. cost | Wavelength range | Peuchant 7 λ? |
|----------|-----------|-------------------|----------------|
| Silicon photodiode / AS7263 | \$1–30 | &lt; 1000 nm | No |
| Single InGaAs + DIY grating | \$200–500 | 800–1600 nm | Partial (4–5 λ) |
| InGaAs module + filters | \$100–400 | 1445–1700 nm (discrete) | Partial |
| Extended InGaAs spectrometer | \$2000+ | 1445–2208 nm | Yes |

**Bottom line:** There is no **very** cheap way to read the **full** Peuchant IR spectrum (1445–2208 nm). The cheapest path that touches the method is a **DIY InGaAs spectrometer** (~\$200–500) for **800–1600 nm**, giving 4–5 of the 7 wavelengths; the last two (2190, 2208 nm) require extended InGaAs hardware or a commercial NIR spectrometer.

---

## Cheap commercial devices that use IR (can they be used?)

Many consumer and prosumer products use IR or NIR sensors. Most are **not** suitable for the Peuchant 1445–2208 nm range; a few are in the right ballpark but not “cheap” or not sold as standalone sensors.

### Not suitable for Peuchant (wrong wavelength range)

| Device | Typical IR/NIR | Why it doesn’t help |
|--------|----------------|----------------------|
| **Pulse oximeters** (\$10–\$30) | Red ~660 nm + IR ~**940 nm** | Silicon-friendly only; 940 nm is below 1000 nm. **Does not reach 1445 nm.** Teardown gives LEDs + photodiode you could reuse for SpO₂-style projects only. |
| **Fitness / SpO₂ wearables** | Same 660 + 940 nm | Same as above. |
| **Phone / webcam cameras** | Visible + sometimes weak NIR to ~1000 nm | IR cut filter on most; at best only to ~1000 nm. |
| **AS7263 / AS7262 / AS7341** (spectral sensor breakouts, ~\$25–\$35) | 610–870 nm (AS7263) or 350–1000 nm (AS7341) | Silicon; **max ~1000 nm**. Not 1445–2208 nm. |
| **“NIR” moisture / food pens** (some under \$100) | Often 900–1000 nm or single band | Check specs; many are short NIR only. |

### Possibly useful (right range, but not “cheap” or not standalone)

| Device | Range | Notes |
|--------|--------|--------|
| **trinamiX NIR module** (BASF/trinamiX) | **1000–3000 nm** | Miniaturized NIR spectrometer for integration into **smartphones** (e.g. Snapdragon reference design). Covers full Peuchant range. **Not sold as a consumer dongle**; OEM only (phone makers). May appear in future phones; no retail price yet. |
| **NIRvascan Smart G1 / F1** (Allied Scientific Pro) | 900–1700 nm | Reflectance (G1) or fiber (F1); **~\$2,200–\$3,200**. “Cheap” relative to lab kit; covers 1445–1734 nm (and partly 1940), not 2190/2208 nm. |
| **VIAVI MicroNIR 1700** (e.g. 1700EC) | 950–1650 nm | Compact, USB; used in food/ag. **Price on request** (often in the low thousands). Partial Peuchant only. |
| **AliExpress / generic “NIR analyzer”** | Varies (often 900–1700 nm) | Some list 900–1700 nm or “NIR for food/ag”. **Verify actual wavelength range and detector type**; quality and support vary. Possible budget option for 1445–1700 nm only. |

### Summary

- **Cheap commercial IR devices** (pulse oximeters, phone cameras, spectral breakouts) use **≤ ~1000 nm** and **cannot** read the Peuchant spectrum (1445–2208 nm). They are useful for SpO₂, color, or short-NIR proxies only.
- **Commercial devices that do cover part or all of Peuchant** are either **OEM modules** (trinamiX in future phones) or **portable/handheld NIR spectrometers** in the **\$2k–\$3k+** range (e.g. NIRvascan, MicroNIR, or extended-range units from Ocean/Sarspec).
- **Budget “NIR” devices** on marketplaces (e.g. AliExpress) may cover 900–1700 nm; check datasheets and reviews before assuming they reach 1445 nm or beyond.

---

## Summary table

| Product type | Approx. range | Covers 1445–2208 nm? | Typical use |
|-------------|----------------|----------------------|-------------|
| **NIRvascan R16** | 900–2400 nm | Yes | Handheld, field |
| **Ocean NIRQuest 512 (extended)** | 900–2200 / 2500 nm | Yes | Benchtop, research |
| **Sarspec ProNIR** | 1000–2500 nm | Yes | Benchtop / OEM |
| **ZEISS AURA** | 950–1650 nm | No (only 1445, 1650) | Handheld |
| **InnoSpectra 900–1700** | 900–1700 nm | Partial (missing 2190, 2208) | Benchtop / OEM |

---

## Practical recommendation

- **Best single-unit match for the full Peuchant 7 wavelengths (1445–2208 nm):**  
  A **handheld or benchtop NIR spectrometer with extended InGaAs (or equivalent) covering at least 1445–2210 nm**, e.g.:
  - **NIRvascan R16** (900–2400 nm) if you want handheld and one purchase.
  - **Ocean Insight NIRQuest** or **Sarspec ProNIR** in a 900–2200 nm or 1000–2500 nm configuration if you want benchtop/fiber and highest flexibility.

- **Reflectance setup:** The paper used an **integrating sphere** and a **liquid cell**. You’ll need:
  - A **NIR-compatible reflectance accessory** (integrating sphere, or reflectance probe).
  - A **NIR light source** (e.g. tungsten halogen, as in the original).
  - **Liquid cell** and sample handling similar to the paper (e.g. 100 µL serum, controlled temperature).

- **Not suitable for the full Peuchant method:**  
  Silicon-based or visible–NIR sensors that stop around 1000 nm (e.g. AS7341, typical webcams, phone sensors) **cannot** read 1445–2208 nm. They are only useful for visible or short‑NIR proxies, not for implementing the exact 7-wavelength Peuchant formula.

---

*Links and prices are from public search results; verify specs and availability on the manufacturers’ sites before purchasing.*
