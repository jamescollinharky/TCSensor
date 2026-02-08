#!/usr/bin/env python3
"""
Camera-based cholesterol assay demo (inspired by enzymatic method, e.g. Peuchant 1987).

The enzymatic method (cholesterol esterase + cholesterol oxidase + peroxidase + 4-AAP + phenol)
produces a quinoneimine dye whose absorbance is read at ~500 nm. This script uses the
computer camera as a crude colorimeter: it measures the red channel (closest to 500 nm
sensitivity for the pink/red product) over a region of interest where you hold a test strip
or cuvette.

NOT FOR MEDICAL USE. The camera is not a spectrophotometer. Values are uncalibrated and
for demonstration only. Real cholesterol measurement requires lab reagents and calibration.

Reference: Peuchant E et al. (1987), enzymatic cholesterol determination (e.g. Clin Chem Lab Med).
"""
import argparse
import json
import sys
import time
from pathlib import Path
from typing import Optional, Tuple

import cv2

_ROOT = Path(__file__).resolve().parent.parent
_DATA = _ROOT / "data"
import numpy as np


# Wavelength proxy: enzymatic quinoneimine product is read at ~500 nm; camera R channel is a rough proxy
WAVELENGTH_PROXY_NM = 500


def get_roi_mean_rgb(frame: np.ndarray, roi_frac: float = 0.4) -> Tuple[float, float, float]:
    """Mean R, G, B in center ROI (OpenCV BGR)."""
    h, w = frame.shape[:2]
    x1 = int(w * (0.5 - roi_frac / 2))
    x2 = int(w * (0.5 + roi_frac / 2))
    y1 = int(h * (0.5 - roi_frac / 2))
    y2 = int(h * (0.5 + roi_frac / 2))
    roi = frame[y1:y2, x1:x2]
    if roi.size == 0:
        return 0.0, 0.0, 0.0
    b, g, r = cv2.split(roi)
    return float(np.mean(r)), float(np.mean(g)), float(np.mean(b))


def absorbance_proxy(sample_r: float, ref_r: float) -> float:
    """Crude absorbance proxy at ~500 nm: -log10(I_sample / I_ref). Avoid log(0)."""
    if ref_r <= 0:
        ref_r = 1.0
    ratio = (sample_r + 1.0) / (ref_r + 1.0)
    if ratio <= 0:
        return 0.0
    return -np.log10(min(ratio, 1.0))


def main():
    parser = argparse.ArgumentParser(
        description="Camera-based cholesterol assay demo (enzymatic method proxy). NOT for medical use."
    )
    parser.add_argument("camera_index", nargs="?", type=int, default=0)
    parser.add_argument(
        "--reference",
        "-r",
        action="store_true",
        help="Capture reference (blank) and save for later --measure",
    )
    parser.add_argument(
        "--measure",
        "-m",
        action="store_true",
        help="Measure sample; use saved reference if available",
    )
    parser.add_argument(
        "--reference-file",
        default=str(_DATA / "reference" / "cholesterol_reference.json"),
        help="Path to save/load reference RGB (default: data/reference/cholesterol_reference.json)",
    )
    parser.add_argument("--samples", type=int, default=5, help="Number of frames to average (default 5)")
    parser.add_argument("--watch", "-w", action="store_true", help="Live readout (R, absorbance proxy) until Ctrl+C")
    parsed = parser.parse_args()

    cap = cv2.VideoCapture(parsed.camera_index)
    if not cap.isOpened():
        cap = cv2.VideoCapture(1)
    if not cap.isOpened():
        print("Error: Could not open camera.", file=sys.stderr)
        sys.exit(1)

    cap.read()  # warm-up
    ref_path = Path(parsed.reference_file)

    if parsed.reference:
        print("Capture REFERENCE (blank/white). Point camera at blank strip or white card.")
        print("Press Enter when ready, then hold still for 1 s...")
        input()
        r_list, g_list, b_list = [], [], []
        for _ in range(parsed.samples):
            ok, frame = cap.read()
            if ok and frame is not None:
                r, g, b = get_roi_mean_rgb(frame)
                r_list.append(r)
                g_list.append(g)
                b_list.append(b)
            time.sleep(0.1)
        cap.release()
        if not r_list:
            print("No frames captured.", file=sys.stderr)
            sys.exit(1)
        ref_rgb = {
            "R": float(np.mean(r_list)),
            "G": float(np.mean(g_list)),
            "B": float(np.mean(b_list)),
        }
        ref_path.parent.mkdir(parents=True, exist_ok=True)
        with open(ref_path, "w") as f:
            json.dump(ref_rgb, f, indent=2)
        print(f"Reference saved to {ref_path}: R={ref_rgb['R']:.1f} G={ref_rgb['G']:.1f} B={ref_rgb['B']:.1f}")
        return

    # Load reference if available (for --measure or --watch)
    ref_r = None
    if ref_path.exists():
        with open(ref_path) as f:
            ref_rgb = json.load(f)
        ref_r = ref_rgb.get("R", 255.0)
        if parsed.measure or parsed.watch:
            print(f"Using reference from {ref_path} (R={ref_r:.1f})")

    if parsed.watch:
        print("Live readout. Point camera at sample. Ctrl+C to stop.")
        print("-" * 50)
        try:
            while True:
                ok, frame = cap.read()
                if ok and frame is not None:
                    r, g, b = get_roi_mean_rgb(frame)
                    line = f"  R={r:5.1f} G={g:5.1f} B={b:5.1f}"
                    if ref_r is not None:
                        ap = absorbance_proxy(r, ref_r)
                        line += f"  |  A500 proxy={ap:.3f}  chol.index={ap*100:.1f}"
                    print(f"\r{line}   ", end="", flush=True)
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("\nStopped.")
        cap.release()
        return

    if parsed.measure:
        print("Point camera at SAMPLE (test strip or cuvette). Press Enter when ready...")
        input()
    else:
        print("Point camera at strip/cuvette (or blank for reference). One reading.")

    r_list, g_list, b_list = [], [], []
    for _ in range(parsed.samples):
        ok, frame = cap.read()
        if ok and frame is not None:
            r, g, b = get_roi_mean_rgb(frame)
            r_list.append(r)
            g_list.append(g)
            b_list.append(b)
        time.sleep(0.1)
    cap.release()

    if not r_list:
        print("No frames captured.", file=sys.stderr)
        sys.exit(1)

    sample_r = float(np.mean(r_list))
    sample_g = float(np.mean(g_list))
    sample_b = float(np.mean(b_list))

    print("-" * 50)
    print(f"ROI mean (center): R={sample_r:.1f} G={sample_g:.1f} B={sample_b:.1f}")

    if ref_r is not None:
        abs_proxy = absorbance_proxy(sample_r, ref_r)
        cholesterol_index = abs_proxy * 100  # placeholder; calibrate with standards
        print(f"Absorbance proxy (~{WAVELENGTH_PROXY_NM} nm): {abs_proxy:.3f}")
        print(f"Cholesterol index (uncalibrated): {cholesterol_index:.1f} (NOT mg/dL)")
    else:
        print("No reference loaded. Run with --reference then --measure for absorbance proxy.")

    print("-" * 50)
    print("NOT FOR MEDICAL USE. Camera is not a spectrophotometer. Calibration required.")
    print("Method reference: enzymatic cholesterol assay (e.g. Peuchant 1987, Clin Chem Lab Med).")


if __name__ == "__main__":
    main()
