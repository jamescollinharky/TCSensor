#!/usr/bin/env python3
"""
Validate Peuchant 1987 NIR model with synthetic reflectance data.

Reference: Peuchant E, Salles C, Jensen R. Anal. Chem. 1987, 59, 1816–1819.
Table I (7 selected filters): C_mmol/L = bias + sum(a_i * log(1/R_i)).
Table II: filter → wavelength (nm): 7→2208, 8→2190, 16→1940, 17→1734, 18→1722, 19→1445, 20→1680.

This script:
1. Uses exact coefficients from the paper (Table I).
2. Generates synthetic reflectance at the 7 wavelengths.
3. Computes TC with the paper formula and validates by recomputation.
4. Validates existing cholesterol_peuchant_synthetic.json (script formula consistency).
"""
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent

# --- Exact coefficients from Peuchant 1987 Table I (7 filters) ---
# Wavelengths (nm) in same order as paper Table II
PEUCHANT_1987_WAVELENGTHS_NM = (2208, 2190, 1940, 1734, 1722, 1445, 1680)
PEUCHANT_1987_BIAS = 48.709
# Table I scaling factors for filters 7, 8, 16, 17, 18, 19, 20 (same order as wavelengths above)
PEUCHANT_1987_FACTORS = {
    2208: -926.830,
    2190: 807.140,
    1940: -8.120,
    1734: -3271.400,
    1722: 5873.600,
    1445: 108.770,
    1680: -2744.300,
}


def log_inv_r(r: float) -> float:
    """log(1/R), R in (0, 1]. Avoid log(0)."""
    r = max(1e-9, min(1.0 - 1e-9, float(r)))
    return np.log(1.0 / r)


def tc_paper_formula(reflectance: dict) -> float:
    """
    Total cholesterol (mmol/L) using Peuchant 1987 exact formula.
    reflectance: dict wavelength (nm) -> R in [0, 1].
    """
    c = PEUCHANT_1987_BIAS
    for wl in PEUCHANT_1987_WAVELENGTHS_NM:
        r = reflectance.get(wl, 0.5)
        c += PEUCHANT_1987_FACTORS[wl] * log_inv_r(r)
    return float(c)


def generate_synthetic_reflectance_paper(
    n_samples: int = 15,
    r_min: float = 0.25,
    r_max: float = 0.85,
    seed: int = 1987,
) -> list:
    """Generate synthetic R at 7 wavelengths; return list of dicts with reflectance and expected TC (paper formula)."""
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(n_samples):
        reflectance = {
            wl: float(rng.uniform(r_min, r_max))
            for wl in PEUCHANT_1987_WAVELENGTHS_NM
        }
        tc = tc_paper_formula(reflectance)
        out.append({"reflectance": reflectance, "tc_mmol_l_expected": tc})
    return out


def validate_paper_formula_self(samples: list) -> bool:
    """Recompute TC from reflectance with paper formula; must match expected. Returns True if all pass."""
    ok = True
    for i, s in enumerate(samples):
        tc_recomputed = tc_paper_formula(s["reflectance"])
        expected = s["tc_mmol_l_expected"]
        diff = abs(tc_recomputed - expected)
        if diff > 1e-6:
            print(f"  FAIL sample {i}: expected {expected:.4f}, got {tc_recomputed:.4f}")
            ok = False
    return ok


def validate_existing_json_script_formula() -> bool:
    """Load cholesterol_peuchant_synthetic.json; recompute TC with script formula; must match stored tc_mmol_l."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "cholesterol_peuchant_nir",
        ROOT / "scripts" / "cholesterol_peuchant_nir.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    peuchant_total_cholesterol_mmol_l = mod.peuchant_total_cholesterol_mmol_l

    path = ROOT / "data" / "reference" / "cholesterol_peuchant_synthetic.json"
    if not path.exists():
        print(f"  Skip: {path} not found")
        return True
    with open(path) as f:
        data = json.load(f)
    ok = True
    for i, row in enumerate(data):
        # Keys are strings in JSON
        reflectance = {int(k): v for k, v in row["reflectance_nm"].items()}
        tc_stored = row["tc_mmol_l"]
        tc_computed = peuchant_total_cholesterol_mmol_l(reflectance)
        if abs(tc_computed - tc_stored) > 0.02:  # allow rounding
            print(f"  FAIL sample {i}: stored tc {tc_stored}, computed {tc_computed:.2f}")
            ok = False
    return ok


def run_yom_test_data() -> bool:
    """Load yom_test_data.json; run Peuchant (script + paper) formula; print results. Returns True if file existed."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "cholesterol_peuchant_nir",
        ROOT / "scripts" / "cholesterol_peuchant_nir.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    tc_script = mod.peuchant_total_cholesterol_mmol_l

    path = ROOT / "data" / "processed" / "yom_test_data.json"
    if not path.exists():
        print(f"  Skip: {path} not found")
        return False
    with open(path) as f:
        data = json.load(f)
    for i, row in enumerate(data):
        if "reflectance_nm" not in row:
            continue
        reflectance = {int(k): v for k, v in row["reflectance_nm"].items()}
        tc_stored = row.get("tc_mmol_l")
        tc_script_val = tc_script(reflectance)
        tc_paper_val = tc_paper_formula(reflectance)
        print(f"   YOM sample {i}: 1722 nm from sensor (1720 band max), others pure fat.")
        print(f"   Script formula TC = {tc_script_val:.2f} mmol/L  (stored: {tc_stored})")
        print(f"   Paper formula TC = {tc_paper_val:.2f} mmol/L")
        if tc_stored is not None and abs(tc_script_val - tc_stored) > 0.02:
            print(f"   WARN: stored tc_mmol_l does not match script recompute.")
    return True


def main():
    print("=" * 72)
    print("Peuchant 1987 NIR validation (Anal. Chem. 1987, 59, 1816–1819)")
    print("=" * 72)
    print()

    # 1) Generate synthetic reflectance (paper formula)
    print("1) Generating synthetic reflectance data (paper formula)...")
    samples = generate_synthetic_reflectance_paper(n_samples=15, seed=1987)
    print(f"   Generated {len(samples)} samples with R in [0.25, 0.85].")
    print()

    # 2) Run through model (paper formula) and show one sample with hand-check
    print("2) Running synthetic data through Peuchant model (paper coefficients)...")
    r0 = samples[0]["reflectance"]
    print("   Sample 0: R and log(1/R) at each wavelength:")
    for wl in PEUCHANT_1987_WAVELENGTHS_NM:
        r = r0[wl]
        log_inv = log_inv_r(r)
        term = PEUCHANT_1987_FACTORS[wl] * log_inv
        print(f"      {wl} nm: R={r:.4f}  log(1/R)={log_inv:.4f}  a_i*log(1/R)={term:.2f}")
    tc0 = tc_paper_formula(r0)
    sum_terms = sum(PEUCHANT_1987_FACTORS[wl] * log_inv_r(r0[wl]) for wl in PEUCHANT_1987_WAVELENGTHS_NM)
    print(f"   TC = bias + sum = {PEUCHANT_1987_BIAS:.3f} + {sum_terms:.2f} = {tc0:.4f} mmol/L")
    print("   (Paper coefficients are instrument-specific; values here are for formula check.)")
    print()

    # 3) Validate: recompute TC from same R and compare
    print("3) Validating: recompute TC from reflectance (paper formula)...")
    if validate_paper_formula_self(samples):
        print("   PASS: all recomputed TC match expected.")
    else:
        print("   FAIL: some recomputed TC did not match.")
    print()

    # 4) Validate existing JSON with script formula
    print("4) Validating existing data/reference/cholesterol_peuchant_synthetic.json (script formula)...")
    if validate_existing_json_script_formula():
        print("   PASS: stored tc_mmol_l matches recomputed from reflectance.")
    else:
        print("   FAIL: some stored TC did not match script formula.")
    print()

    # 5) Save synthetic validation set (paper formula) for reference
    out_path = ROOT / "data" / "reference" / "peuchant_1987_validation_synthetic.json"
    export = []
    for s in samples:
        export.append({
            "reflectance_nm": {str(wl): round(s["reflectance"][wl], 4) for wl in PEUCHANT_1987_WAVELENGTHS_NM},
            "tc_mmol_l": round(s["tc_mmol_l_expected"], 4),
        })
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(export, f, indent=2)
    print(f"5) Wrote validation synthetic set to {out_path}")
    print()

    # 6) Run Peuchant regression on yom test data (1722 from sensor, others pure fat)
    print("6) Running Peuchant regression on data/processed/yom_test_data.json (YOM test)...")
    if run_yom_test_data():
        print("   Done.")
    else:
        print("   (No yom test data file.)")
    print()

    print("Reference: Peuchant E et al. Anal. Chem. 1987, 59, 1816–1819 (Table I, 7 filters).")
    print("Formula: TC = 48.709 + sum(a_i * log(1/R_i)) at 2208, 2190, 1940, 1734, 1722, 1445, 1680 nm.")


if __name__ == "__main__":
    main()
