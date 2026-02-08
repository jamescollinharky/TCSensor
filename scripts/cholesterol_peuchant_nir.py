#!/usr/bin/env python3
"""
Peuchant 1987 NIR reflectance methodology for serum cholesterol (synthetic data).

Peuchant et al. (Anal. Chem. 1987, 59, 1816–1819) used near-infrared reflectance
at 7 wavelengths (1445, 1680, 1722, 1734, 1940, 2190, 2208 nm) with a multilinear
regression: C_mmol/L = a0 + sum(a_i * log(1/R_i)). This script uses SYNTHETIC
reflectance values (no real NIR hardware) to demonstrate the calculation.
LDL is estimated from total cholesterol using the Friedewald equation (synthetic HDL, TG).

NOT FOR MEDICAL USE. Synthetic data only; no real serum or NIR measurement.

Pure fat NIR reference: see fat_nir_reference.json (van Veen/OMLC data 429-1098 nm).
Peuchant wavelengths (1445-2208 nm) are beyond that range; no public reflectance table
for pure fat at those exact wavelengths was found.
"""
import json
from pathlib import Path
from typing import List

import numpy as np

# Peuchant 1987: 7 wavelengths (nm) from Table II: 2208, 2190, 1940, 1734, 1722, 1445, 1680.
# Paper formula: C_mmol/L = a0 + sum(a_i * log(1/R_i)). Original a0=48.709 and a_i from Table I
# are for the Technicon InfraAlyzer 450 (instrument-specific). For synthetic R in [0.2, 0.85] we use
# scaled factors (same signs as paper) so TC ≈ 3–12 mmol/L.
PEUCHANT_WAVELENGTHS_NM = (2208, 2190, 1940, 1734, 1722, 1445, 1680)
PEUCHANT_BIAS = 5.0
# Scaled factors (paper: 1722 +, 1734/1680 −)
PEUCHANT_FACTORS = {
    2208: -2.20,
    2190: 1.95,
    1940: -0.02,
    1734: -7.90,
    1722: 14.20,
    1445: 0.26,
    1680: -6.64,
}


def reflectance_to_log_inv_r(r: float) -> float:
    """Convert reflectance R (0-1) to log(1/R). Avoid log(0)."""
    r = max(1e-6, min(1.0 - 1e-6, float(r)))
    return np.log(1.0 / r)


def peuchant_total_cholesterol_mmol_l(reflectance: dict) -> float:
    """
    Compute serum total cholesterol (mmol/L) from NIR reflectance at 7 wavelengths.
    reflectance: dict mapping wavelength (nm) to R in [0, 1].
    """
    c = PEUCHANT_BIAS
    for wl, factor in PEUCHANT_FACTORS.items():
        r = reflectance.get(wl, 0.5)
        c += factor * reflectance_to_log_inv_r(r)
    return float(c)


def friedewald_ldl_mmol_l(tc_mmol: float, hdl_mmol: float, tg_mmol: float) -> float:
    """LDL (mmol/L) ≈ TC - HDL - TG/2.2 (Friedewald, valid when TG < 4.5 mmol/L)."""
    return max(0.0, tc_mmol - hdl_mmol - tg_mmol / 2.2)


def mmol_l_to_mg_dl(x: float) -> float:
    """Cholesterol: 1 mmol/L ≈ 38.67 mg/dL."""
    return x * 38.67


def mu_a_to_reflectance(mu_a: float, path_cm: float = 0.2) -> float:
    """Convert absorption coefficient (1/cm) to reflectance proxy: R = exp(-mu_a * path)."""
    r = np.exp(-float(mu_a) * path_cm)
    return float(np.clip(r, 0.05, 0.98))


def load_fat_nir_reflectance(fat_json_path: Path) -> dict:
    """
    Load fat_nir_reference.json and return reflectance at Peuchant wavelengths.
    If the file has mu_a_per_cm_peuchant_estimate (literature-based lipid at 1445-2208 nm),
    use those so pure fat gives high TC. Otherwise interpolate from 500-1098 nm data
    (constant extrapolation beyond 1098 nm underestimates TC for pure fat).
    """
    with open(fat_json_path) as f:
        data = json.load(f)
    if "mu_a_per_cm_peuchant_estimate" in data and "peuchant_wavelengths_nm" in data:
        wl_peuchant = data["peuchant_wavelengths_nm"]
        mu_a_peuchant = data["mu_a_per_cm_peuchant_estimate"]
        return {
            int(wl): mu_a_to_reflectance(mu)
            for wl, mu in zip(wl_peuchant, mu_a_peuchant)
            if wl in PEUCHANT_WAVELENGTHS_NM
        }
    wl_nm = np.array(data["wavelength_nm"], dtype=float)
    mu_a = np.array(data["mu_a_per_cm"], dtype=float)
    r_proxy = np.array([mu_a_to_reflectance(m) for m in mu_a])
    target_wl = np.array(PEUCHANT_WAVELENGTHS_NM, dtype=float)
    r_at_peuchant = np.interp(target_wl, wl_nm, r_proxy)
    return {int(wl): float(np.clip(r, 0.05, 0.98)) for wl, r in zip(PEUCHANT_WAVELENGTHS_NM, r_at_peuchant)}


def generate_synthetic_reflectance(
    n_samples: int = 20,
    tc_range: tuple = (3.5, 11.0),
    seed: int = 42,
) -> List[dict]:
    """
    Generate synthetic NIR reflectance samples that yield total cholesterol in range.
    Each sample: dict with keys 'reflectance' (wl -> R), 'tc_mmol_l', 'hdl_mmol_l', 'tg_mmol_l', 'ldl_mmol_l'.
    Uses rejection sampling: random R until Peuchant formula gives TC in range.
    """
    rng = np.random.default_rng(seed)
    out = []
    max_attempts = n_samples * 50
    attempt = 0
    while len(out) < n_samples and attempt < max_attempts:
        attempt += 1
        reflectance = {wl: float(rng.uniform(0.20, 0.85)) for wl in PEUCHANT_WAVELENGTHS_NM}
        tc = peuchant_total_cholesterol_mmol_l(reflectance)
        if tc_range[0] <= tc <= tc_range[1]:
            hdl = float(rng.uniform(0.9, 2.2))
            tg = float(rng.uniform(0.8, 3.5))
            ldl = friedewald_ldl_mmol_l(tc, hdl, tg)
            out.append({
                "reflectance": reflectance,
                "tc_mmol_l": round(tc, 2),
                "hdl_mmol_l": round(hdl, 2),
                "tg_mmol_l": round(tg, 2),
                "ldl_mmol_l": round(ldl, 2),
            })
    if len(out) < n_samples:
        # Fallback: scale reflectance to hit target TC (one wavelength as lever)
        base = {wl: 0.5 for wl in PEUCHANT_WAVELENGTHS_NM}
        for _ in range(n_samples - len(out)):
            tc_target = rng.uniform(tc_range[0], tc_range[1])
            # Adjust 1722 nm (largest positive factor) to get near tc_target
            r1722 = 0.3 + 0.5 * (tc_target - 3.5) / 7.5  # rough inverse relation
            base[1722] = np.clip(r1722 + rng.uniform(-0.05, 0.05), 0.2, 0.85)
            reflectance = {wl: float(np.clip(base[wl] + rng.uniform(-0.02, 0.02), 0.2, 0.85)) for wl in PEUCHANT_WAVELENGTHS_NM}
            tc = peuchant_total_cholesterol_mmol_l(reflectance)
            hdl = float(rng.uniform(0.9, 2.2))
            tg = float(rng.uniform(0.8, 3.5))
            ldl = friedewald_ldl_mmol_l(tc, hdl, tg)
            out.append({
                "reflectance": reflectance,
                "tc_mmol_l": round(tc, 2),
                "hdl_mmol_l": round(hdl, 2),
                "tg_mmol_l": round(tg, 2),
                "ldl_mmol_l": round(ldl, 2),
            })
    return out


def run_fat_test(out_dir: Path) -> None:
    """Run Peuchant formula on fat NIR reference data (mu_a -> R, interp to 7 wavelengths)."""
    data_dir = out_dir / "data"
    fat_path = data_dir / "reference" / "fat_nir_reference.json"
    if not fat_path.exists():
        print(f"Fat reference not found: {fat_path}", file=__import__("sys").stderr)
        return
    reflectance = load_fat_nir_reflectance(fat_path)
    tc = peuchant_total_cholesterol_mmol_l(reflectance)
    # HDL and TG are NOT from fat data; Peuchant/reflectance only give TC. We assume values for Friedewald LDL.
    hdl, tg = 1.2, 1.5  # assumed (mmol/L), not measured
    ldl = friedewald_ldl_mmol_l(tc, hdl, tg)
    with open(fat_path) as f:
        _d = json.load(f)
    using_extended = "mu_a_per_cm_peuchant_estimate" in _d
    print("Peuchant 1987 NIR on fat reference data (fat_nir_reference.json). NOT FOR MEDICAL USE.")
    if using_extended:
        print("Using extended lipid mu_a at Peuchant wavelengths (literature-based; 1722/1734 nm strong CH2 -> low R -> high TC).")
    else:
        print("Fat data: van Veen/OMLC mu_a 500-1098 nm -> R = exp(-mu_a*0.2); extrapolated to 1445-2208 nm.")
    print("-" * 60)
    print("Reflectance R at Peuchant wavelengths (from fat):")
    for wl in PEUCHANT_WAVELENGTHS_NM:
        print(f"  {wl} nm: R = {reflectance[wl]:.4f}")
    print("-" * 60)
    print("From fat reflectance (Peuchant formula):")
    print(f"  TC (total cholesterol): {tc:.2f} mmol/L  ({mmol_l_to_mg_dl(tc):.1f} mg/dL)")
    print()
    print("HDL and TG are not from fat data; assumed for Friedewald LDL only:")
    print(f"  HDL (assumed): {hdl:.1f} mmol/L  ({mmol_l_to_mg_dl(hdl):.0f} mg/dL)")
    print(f"  TG  (assumed): {tg:.1f} mmol/L")
    print(f"  LDL (Friedewald): {ldl:.2f} mmol/L  ({mmol_l_to_mg_dl(ldl):.1f} mg/dL)")
    print()
    if using_extended:
        print("Note: Extended mu_a at 1445-2208 nm are literature-based estimates for lipid (Bashkatov adipose, Peuchant cholesterol bands). HDL/TG fixed; illustrative only.")
    else:
        print("Note: Fat spectrum ends at 1098 nm; R at 1445-2208 nm is extrapolated (constant), which underestimates TC for pure fat. HDL/TG fixed; illustrative only.")


def main():
    out_dir = Path(__file__).resolve().parent.parent
    data_dir = out_dir / "data"
    data_dir.mkdir(exist_ok=True)
    synthetic_path = data_dir / "cholesterol_peuchant_synthetic.json"

    import sys
    if "--fat-test" in sys.argv:
        run_fat_test(out_dir)
        return

    # Generate synthetic samples
    samples = generate_synthetic_reflectance(n_samples=24, tc_range=(3.5, 11.0))
    # Export for inspection
    export = []
    for s in samples:
        export.append({
            "reflectance_nm": {str(k): round(v, 4) for k, v in s["reflectance"].items()},
            "tc_mmol_l": s["tc_mmol_l"],
            "hdl_mmol_l": s["hdl_mmol_l"],
            "tg_mmol_l": s["tg_mmol_l"],
            "ldl_mmol_l": s["ldl_mmol_l"],
            "tc_mg_dl": round(mmol_l_to_mg_dl(s["tc_mmol_l"]), 1),
            "ldl_mg_dl": round(mmol_l_to_mg_dl(s["ldl_mmol_l"]), 1),
        })
    with open(synthetic_path, "w") as f:
        json.dump(export, f, indent=2)
    print(f"Wrote {len(samples)} synthetic samples to {synthetic_path}")
    print()

    # Summary table
    print("Peuchant 1987 NIR methodology (synthetic data). NOT FOR MEDICAL USE.")
    print("Wavelengths (nm):", ", ".join(str(w) for w in PEUCHANT_WAVELENGTHS_NM))
    print("Formula: TC_mmol/L = bias + sum(a_i * log(1/R_i)); LDL = TC - HDL - TG/2.2 (Friedewald)")
    print("-" * 72)
    print(f"{'TC (mmol/L)':>12} {'TC (mg/dL)':>12} {'LDL (mmol/L)':>14} {'LDL (mg/dL)':>12} {'HDL':>8} {'TG':>8}")
    print("-" * 72)
    for s in samples[:12]:
        tc = s["tc_mmol_l"]
        ldl = s["ldl_mmol_l"]
        print(f"{tc:>12.2f} {mmol_l_to_mg_dl(tc):>12.1f} {ldl:>14.2f} {mmol_l_to_mg_dl(ldl):>12.1f} {s['hdl_mmol_l']:>8.2f} {s['tg_mmol_l']:>8.2f}")
    if len(samples) > 12:
        print(f"  ... and {len(samples) - 12} more in {synthetic_path}")
    print("-" * 72)
    tc_mean = np.mean([s["tc_mmol_l"] for s in samples])
    ldl_mean = np.mean([s["ldl_mmol_l"] for s in samples])
    print(f"Mean TC: {tc_mean:.2f} mmol/L ({mmol_l_to_mg_dl(tc_mean):.1f} mg/dL)")
    print(f"Mean LDL (Friedewald): {ldl_mean:.2f} mmol/L ({mmol_l_to_mg_dl(ldl_mean):.1f} mg/dL)")
    print()
    print("Reference: Peuchant E et al. Anal. Chem. 1987, 59, 1816–1819 (NIR reflectance).")
    print("LDL: Friedewald equation; synthetic HDL/TG for demonstration only.")


if __name__ == "__main__":
    main()
