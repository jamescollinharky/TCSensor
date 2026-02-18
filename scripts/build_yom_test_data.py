#!/usr/bin/env python3
"""
Build yom test data: one sample with 1722 nm from sensor (1720 band).
Sensor outputs absorption A = -log10(I/I0). We convert A -> R = 10^(-A) for Peuchant.
Other Peuchant wavelengths from median of synthetic data (so TC stays positive).
"""
import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent

# Sensor: values are absorption A = -log10(I/I0). Use max count -> min absorption.
I0 = 1023
MAX_COUNT_940 = 950
MAX_COUNT_1720 = 747


def absorption_from_count(count: float, reference: float = I0) -> float:
    """A = -log10(I/I0)."""
    ratio = max(1e-6, min(1.0, count / reference))
    return -math.log10(ratio)


def reflectance_from_absorption(A: float) -> float:
    """R = 10^(-A)."""
    return 10.0 ** (-A)


# 1720 band: min absorption (max count 747) -> then R for 1722 nm
A_1722_SENSOR = absorption_from_count(MAX_COUNT_1720, I0)
R_1722_FROM_SENSOR = reflectance_from_absorption(A_1722_SENSOR)
# 940 nm not in Peuchant 7 wavelengths; stored for reference only


def main():
    sys.path.insert(0, str(ROOT / "scripts"))
    import cholesterol_peuchant_nir as mod
    tc_formula = mod.peuchant_total_cholesterol_mmol_l
    friedewald = mod.friedewald_ldl_mmol_l
    to_mg_dl = mod.mmol_l_to_mg_dl
    wl_nm = mod.PEUCHANT_WAVELENGTHS_NM

    data_dir = ROOT / "data"
    synthetic_path = data_dir / "reference" / "cholesterol_peuchant_synthetic.json"
    if not synthetic_path.exists():
        print(f"ERROR: {synthetic_path} not found", file=sys.stderr)
        sys.exit(1)

    with open(synthetic_path) as f:
        synthetic = json.load(f)
    # Median reflectance at each wavelength (synthetic data gives positive TC)
    by_wl = {wl: [] for wl in wl_nm}
    for row in synthetic:
        for wl in wl_nm:
            by_wl[wl].append(row["reflectance_nm"][str(wl)])
    median_reflectance = {wl: float(np.median(by_wl[wl])) for wl in wl_nm}

    # YOM sample: 1722 from sensor (1720 band max), others from synthetic median
    reflectance = dict(median_reflectance)
    reflectance[1722] = R_1722_FROM_SENSOR

    tc = tc_formula(reflectance)
    hdl, tg = 1.2, 1.5  # placeholders (not from sensor)
    ldl = friedewald(tc, hdl, tg)

    record = {
        "_comment": "YOM test: 1722 nm from sensor absorption (1720 band); A->R=10^(-A). Other bands = median synthetic.",
        "reflectance_nm": {str(wl): round(reflectance[wl], 4) for wl in wl_nm},
        "absorption_nm": {str(1722): round(A_1722_SENSOR, 4)},  # sensor gives absorption; R = 10^(-A)
        "tc_mmol_l": round(tc, 2),
        "hdl_mmol_l": hdl,
        "tg_mmol_l": tg,
        "ldl_mmol_l": round(ldl, 2),
        "tc_mg_dl": round(to_mg_dl(tc), 1),
        "ldl_mg_dl": round(to_mg_dl(ldl), 1),
        "sensor_bands_used": {
            "1720_nm_max_count": MAX_COUNT_1720,
            "1720_nm_absorption_A": round(A_1722_SENSOR, 4),
            "940_nm_max_count": MAX_COUNT_940,
        },
    }

    out_path = data_dir / "processed" / "yom_test_data.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump([record], f, indent=2)
    print(f"Wrote {out_path}")
    print("1722 nm: sensor absorption A = {:.4f} -> R = 10^(-A) = {:.4f}".format(A_1722_SENSOR, R_1722_FROM_SENSOR))
    print("Reflectance (1722 from sensor A->R, others = median synthetic):")
    for wl in wl_nm:
        src = "sensor (A->R)" if wl == 1722 else "median synthetic"
        print(f"  {wl} nm: R = {reflectance[wl]:.4f}  ({src})")
    print(f"TC = {tc:.2f} mmol/L  ({to_mg_dl(tc):.1f} mg/dL)")
    print(f"LDL (Friedewald, HDL/TG placeholder) = {ldl:.2f} mmol/L  ({to_mg_dl(ldl):.1f} mg/dL)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
