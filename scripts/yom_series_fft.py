#!/usr/bin/env python3
"""
Parse YOM Arduino serial dump into two time series (1720 nm and 940 nm),
save CSV, run FFT, and plot to check for periodicity around ~1 Hz (e.g. pulse).
Then take max of 0.85–1.1 Hz bandpass (1720 nm) for reflectance at 1722 nm and write test_data.json.
"""
import json
import math
import re
import sys
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
RAW_PATH = DATA_DIR / "raw" / "yom_arduino_series_raw.txt"
CSV_PATH = DATA_DIR / "timeseries" / "yom_series_1720_940.csv"
FFT_PNG = DATA_DIR / "figures" / "yom_series_fft.png"
BANDPASS_PNG = DATA_DIR / "figures" / "yom_series_band_0.85_1.1hz.png"
YOM_TEST_DATA_PATH = DATA_DIR / "processed" / "yom_test_data.json"
F_LO, F_HI = 0.85, 1.1  # Hz band for IFFT (1720 nm -> reflectance at 1722 nm)
I0 = 1023


def parse_time(s: str) -> float:
    """HH:MM:SS.mmm -> seconds since midnight (relative to first timestamp)."""
    m = re.match(r"(\d+):(\d+):(\d+)\.(\d+)", s.strip())
    if not m:
        return np.nan
    h, mm, ss, ms = (int(m.group(i)) for i in range(1, 5))
    return h * 3600 + mm * 60 + ss + ms / 1000.0


def channel_from_line(right: str) -> str | None:
    """Return '1720' if (0,0,0,255,0), '940' if (0,0,255,0,0), else None."""
    right = right.strip().rstrip(")")
    if "0, 0, 0, 255" in right or "0,0,0,255" in right:
        return "1720"
    if "0, 0, 255, 0" in right or "0,0,255,0" in right:
        return "940"
    return None


def parse_raw(path: Path):
    """Parse raw Arduino dump. Yield (t_sec, channel, value) for each reading."""
    with open(path) as f:
        lines = f.readlines()
    t_sec_base = None
    pending_channel = None
    pending_t = None
    for line in lines:
        if " -> " not in line:
            continue
        left, right = line.split(" -> ", 1)
        t_sec = parse_time(left)
        if np.isnan(t_sec):
            continue
        if t_sec_base is None:
            t_sec_base = t_sec
        t_sec = t_sec - t_sec_base
        ch = channel_from_line(right)
        if ch is not None:
            pending_channel = ch
            pending_t = t_sec
            continue
        try:
            value = int(right.strip())
        except ValueError:
            continue
        if pending_channel is not None and pending_t is not None:
            yield (pending_t, pending_channel, value)
        pending_channel = None
        pending_t = None


def main():
    import argparse
    p = argparse.ArgumentParser(description="Parse Arduino serial dump, FFT, optional yom_test_data.json")
    p.add_argument("input", nargs="?", default=None, help="Raw serial dump (default: data/raw/yom_arduino_series_raw.txt)")
    args = p.parse_args()
    raw_path = Path(args.input) if args.input else RAW_PATH
    if not raw_path.exists():
        print(f"Missing {raw_path}")
        return 1
    # Optional output names when using a named input file
    stem = raw_path.stem if raw_path != RAW_PATH else "yom_series"
    csv_path = DATA_DIR / "timeseries" / f"{stem}_1720_940.csv"
    fft_png = DATA_DIR / "figures" / f"{stem}_fft.png"
    bandpass_png = DATA_DIR / "figures" / f"{stem}_band_0.85_1.1hz.png"
    for d in ("timeseries", "figures", "processed"):
        (DATA_DIR / d).mkdir(parents=True, exist_ok=True)
    rows = list(parse_raw(raw_path))
    t_1720 = []
    y_1720 = []
    t_940 = []
    y_940 = []
    for t, ch, val in rows:
        if ch == "1720":
            t_1720.append(t)
            y_1720.append(val)
        elif ch == "940":
            t_940.append(t)
            y_940.append(val)
    t_1720 = np.array(t_1720)
    y_1720 = np.array(y_1720, dtype=float)
    t_940 = np.array(t_940)
    y_940 = np.array(y_940, dtype=float)

    # Save CSV: two blocks (1720 then 940) with timestamp_sec and count
    with open(csv_path, "w") as f:
        f.write("series,timestamp_sec,count\n")
        for i in range(len(t_1720)):
            f.write(f"1720nm,{t_1720[i]:.3f},{y_1720[i]:.0f}\n")
        for i in range(len(t_940)):
            f.write(f"940nm,{t_940[i]:.3f},{y_940[i]:.0f}\n")
    print(f"Wrote {csv_path}")
    print(f"  1720 nm: {len(t_1720)} points, t in [{t_1720.min():.1f}, {t_1720.max():.1f}] s")
    print(f"  940 nm:  {len(t_940)} points, t in [{t_940.min():.1f}, {t_940.max():.1f}] s")

    # FFT for each series (use uniform time step via interpolation if needed)
    def fft_series(t: np.ndarray, y: np.ndarray, label: str):
        dt = np.diff(t)
        fs_approx = 1.0 / np.median(dt) if len(dt) > 0 else 4.0
        n = len(y)
        # Detrend
        y_detrend = y - np.mean(y)
        Y = np.fft.rfft(y_detrend)
        freqs = np.fft.rfftfreq(n, d=1.0 / fs_approx)
        power = np.abs(Y) ** 2
        return freqs, power, fs_approx, label

    # Estimate fs from median dt
    dt_1720 = np.diff(t_1720)
    fs_1720 = 1.0 / np.median(dt_1720) if len(dt_1720) > 0 else 4.0
    dt_940 = np.diff(t_940)
    fs_940 = 1.0 / np.median(dt_940) if len(dt_940) > 0 else 4.0

    freqs_1720 = np.fft.rfftfreq(len(y_1720), d=1.0 / fs_1720)
    power_1720 = np.abs(np.fft.rfft(y_1720 - np.mean(y_1720))) ** 2
    freqs_940 = np.fft.rfftfreq(len(y_940), d=1.0 / fs_940)
    power_940 = np.abs(np.fft.rfft(y_940 - np.mean(y_940))) ** 2

    # Plot: time series + FFT (focus 0.3–2.5 Hz for ~1 Hz / pulse)
    fig, axes = plt.subplots(2, 2, figsize=(10, 8))
    axes[0, 0].plot(t_1720, y_1720, "b.-", markersize=2, label="1720 nm")
    axes[0, 0].set_xlabel("Time (s)")
    axes[0, 0].set_ylabel("Count")
    axes[0, 0].set_title("1720 nm time series")
    axes[0, 0].legend()

    axes[0, 1].plot(t_940, y_940, "r.-", markersize=2, label="940 nm")
    axes[0, 1].set_xlabel("Time (s)")
    axes[0, 1].set_ylabel("Count")
    axes[0, 1].set_title("940 nm time series")
    axes[0, 1].legend()

    # FFT 0–5 Hz; show bin spacing and band used for IFFT
    df_1720 = fs_1720 / len(y_1720) if len(y_1720) else 0
    df_940 = fs_940 / len(y_940) if len(y_940) else 0
    ax_fft_1720 = axes[1, 0]
    ax_fft_1720.axvspan(F_LO, F_HI, color="blue", alpha=0.2, label=f"IFFT band {F_LO}–{F_HI} Hz")
    ax_fft_1720.plot(freqs_1720, power_1720, "b-", label="1720 nm")
    ax_fft_1720.axvline(1.0, color="gray", linestyle="--", alpha=0.8, label="1 Hz")
    ax_fft_1720.set_xlim(0, 5)
    ax_fft_1720.set_xlabel("Frequency (Hz)")
    ax_fft_1720.set_ylabel("Power")
    ax_fft_1720.set_title("FFT 1720 nm (fs≈{:.1f} Hz, Δf≈{:.3f} Hz)".format(fs_1720, df_1720))
    ax_fft_1720.legend()

    ax_fft_940 = axes[1, 1]
    ax_fft_940.axvspan(F_LO, F_HI, color="red", alpha=0.2, label=f"IFFT band {F_LO}–{F_HI} Hz")
    ax_fft_940.plot(freqs_940, power_940, "r-", label="940 nm")
    ax_fft_940.axvline(1.0, color="gray", linestyle="--", alpha=0.8, label="1 Hz")
    ax_fft_940.set_xlim(0, 5)
    ax_fft_940.set_xlabel("Frequency (Hz)")
    ax_fft_940.set_ylabel("Power")
    ax_fft_940.set_title("FFT 940 nm (fs≈{:.1f} Hz, Δf≈{:.3f} Hz)".format(fs_940, df_940))
    ax_fft_940.legend()

    plt.suptitle(f"{stem}: periodicity around 1 Hz?", fontsize=12)
    plt.tight_layout()
    plt.savefig(fft_png, dpi=150)
    plt.close()
    print(f"Wrote {fft_png}")

    # Peak near 1 Hz (0.5–2 Hz)
    band = (freqs_1720 >= 0.5) & (freqs_1720 <= 2.0)
    if np.any(band):
        idx_1720 = np.argmax(power_1720[band])
        f_peak_1720 = freqs_1720[band][idx_1720]
        print(f"  1720 nm: peak in 0.5–2 Hz at {f_peak_1720:.3f} Hz ({f_peak_1720 * 60:.1f} bpm)")
    band = (freqs_940 >= 0.5) & (freqs_940 <= 2.0)
    if np.any(band):
        idx_940 = np.argmax(power_940[band])
        f_peak_940 = freqs_940[band][idx_940]
        print(f"  940 nm:  peak in 0.5–2 Hz at {f_peak_940:.3f} Hz ({f_peak_940 * 60:.1f} bpm)")

    # Inverse FFT: keep only F_LO <= f < F_HI Hz, reconstruct time series
    mean_1720 = np.mean(y_1720)
    mean_940 = np.mean(y_940)
    Y_1720 = np.fft.rfft(y_1720 - mean_1720)
    Y_940 = np.fft.rfft(y_940 - mean_940)
    band_center = (F_LO + F_HI) / 2.0
    mask_1720 = (freqs_1720 >= F_LO) & (freqs_1720 < F_HI)
    mask_940 = (freqs_940 >= F_LO) & (freqs_940 < F_HI)
    if not np.any(mask_1720) and len(freqs_1720) > 0:
        idx = np.argmin(np.abs(freqs_1720 - band_center))
        mask_1720 = np.zeros_like(mask_1720, dtype=bool)
        mask_1720[idx] = True
    if not np.any(mask_940) and len(freqs_940) > 0:
        idx = np.argmin(np.abs(freqs_940 - band_center))
        mask_940 = np.zeros_like(mask_940, dtype=bool)
        mask_940[idx] = True
    bins_1720 = freqs_1720[mask_1720]
    bins_940 = freqs_940[mask_940]
    if len(bins_1720):
        print(f"  1720 nm IFFT band {F_LO}–{F_HI} Hz: bins at {bins_1720.tolist()}")
    else:
        print(f"  1720 nm IFFT band {F_LO}–{F_HI} Hz: no bins (Δf={df_1720:.3f} Hz)")
    if len(bins_940):
        print(f"  940 nm IFFT band {F_LO}–{F_HI} Hz: bins at {bins_940.tolist()}")
    else:
        print(f"  940 nm IFFT band {F_LO}–{F_HI} Hz: no bins (Δf={df_940:.3f} Hz)")
    Y_1720_band = np.zeros_like(Y_1720)
    Y_1720_band[mask_1720] = Y_1720[mask_1720]
    Y_940_band = np.zeros_like(Y_940)
    Y_940_band[mask_940] = Y_940[mask_940]
    y_1720_band = np.fft.irfft(Y_1720_band, n=len(y_1720)).real + mean_1720
    y_940_band = np.fft.irfft(Y_940_band, n=len(y_940)).real + mean_940

    # Plot bandpass-reconstructed (F_LO–F_HI Hz) time series; show actual bins used
    ch2_label = "1650 nm" if "1650" in stem else "940 nm"
    bin_str_1720 = ", ".join(f"{f:.3f}" for f in bins_1720) if len(bins_1720) else "none"
    bin_str_940 = ", ".join(f"{f:.3f}" for f in bins_940) if len(bins_940) else "none"
    fig2, axes2 = plt.subplots(2, 1, figsize=(10, 6), sharex=False)
    axes2[0].plot(t_1720, y_1720, "b.-", markersize=2, alpha=0.4, label="1720 nm raw")
    axes2[0].plot(t_1720, y_1720_band, "b-", linewidth=1.5, label=f"1720 nm {F_LO}–{F_HI} Hz IFFT")
    axes2[0].set_xlabel("Time (s)")
    axes2[0].set_ylabel("Count")
    axes2[0].set_title(f"1720 nm: IFFT band {F_LO}–{F_HI} Hz (bins at {bin_str_1720} Hz)")
    axes2[0].legend()
    axes2[0].grid(True, alpha=0.3)
    axes2[1].plot(t_940, y_940, "r.-", markersize=2, alpha=0.4, label=f"{ch2_label} raw")
    axes2[1].plot(t_940, y_940_band, "r-", linewidth=1.5, label=f"{ch2_label} {F_LO}–{F_HI} Hz IFFT")
    axes2[1].set_xlabel("Time (s)")
    axes2[1].set_ylabel("Count")
    axes2[1].set_title(f"{ch2_label}: IFFT band {F_LO}–{F_HI} Hz (bins at {bin_str_940} Hz)")
    axes2[1].legend()
    axes2[1].grid(True, alpha=0.3)
    plt.suptitle(f"Bandpass {F_LO}–{F_HI} Hz (FFT bins used: 1720→[{bin_str_1720}], {ch2_label}→[{bin_str_940}])", fontsize=11)
    plt.tight_layout()
    plt.savefig(bandpass_png, dpi=150)
    plt.close()
    print(f"Wrote {bandpass_png} (inverse FFT {F_LO}–{F_HI} Hz)")

    # Max and min of bandpass-reconstructed (0.85–1.1 Hz) 1720 nm series -> Peuchant regression
    max_count_1720 = float(np.max(y_1720_band))
    min_count_1720 = float(np.min(y_1720_band))
    max_count_940 = float(np.max(y_940_band))

    sys.path.insert(0, str(ROOT / "scripts"))
    import cholesterol_peuchant_nir as mod
    wl_nm = mod.PEUCHANT_WAVELENGTHS_NM
    tc_formula = mod.peuchant_total_cholesterol_mmol_l
    friedewald = mod.friedewald_ldl_mmol_l
    to_mg_dl = mod.mmol_l_to_mg_dl
    synthetic_path = DATA_DIR / "reference" / "cholesterol_peuchant_synthetic.json"
    with open(synthetic_path) as f:
        synthetic = json.load(f)
    by_wl = {wl: [] for wl in wl_nm}
    for row in synthetic:
        for wl in wl_nm:
            by_wl[wl].append(row["reflectance_nm"][str(wl)])
    median_reflectance = {wl: float(np.median(by_wl[wl])) for wl in wl_nm}
    hdl, tg = 1.2, 1.5

    # Regression from MAX of IFFT series (current output)
    A_1722_max = -math.log10(max(1e-6, min(1.0, max_count_1720 / I0)))
    R_1722_max = 10.0 ** (-A_1722_max)
    reflectance = dict(median_reflectance)
    reflectance[1722] = R_1722_max
    tc = tc_formula(reflectance)
    ldl = friedewald(tc, hdl, tg)
    print(f"  TC from MAX of IFFT: {tc:.2f} mmol/L  ({to_mg_dl(tc):.1f} mg/dL)")
    print(f"  LDL from MAX:        {ldl:.2f} mmol/L  ({to_mg_dl(ldl):.1f} mg/dL)")

    # Regression from MIN of IFFT series (for comparison)
    A_1722_min = -math.log10(max(1e-6, min(1.0, min_count_1720 / I0)))
    R_1722_min = 10.0 ** (-A_1722_min)
    reflectance_min = dict(median_reflectance)
    reflectance_min[1722] = R_1722_min
    tc_min = tc_formula(reflectance_min)
    ldl_min = friedewald(tc_min, hdl, tg)
    print(f"  TC from MIN of IFFT: {tc_min:.2f} mmol/L  ({to_mg_dl(tc_min):.1f} mg/dL)")
    print(f"  LDL from MIN:        {ldl_min:.2f} mmol/L  ({to_mg_dl(ldl_min):.1f} mg/dL)")

    A_1722 = A_1722_max
    R_1722 = R_1722_max

    record = {
        "_comment": "1722 nm from MAX of 0.85–1.1 Hz IFFT bandpass (1720 nm); A=-log10(count/I0), R=10^(-A). Other bands = median synthetic.",
        "reflectance_nm": {str(wl): round(reflectance[wl], 4) for wl in wl_nm},
        "absorption_nm": {"1722": round(A_1722, 4)},
        "tc_mmol_l": round(tc, 2),
        "hdl_mmol_l": hdl,
        "tg_mmol_l": tg,
        "ldl_mmol_l": round(ldl, 2),
        "tc_mg_dl": round(to_mg_dl(tc), 1),
        "ldl_mg_dl": round(to_mg_dl(ldl), 1),
        "sensor_bands_used": {
            "1720_nm_max_count_0.85_1.1hz": round(max_count_1720, 2),
            "1720_nm_min_count_0.85_1.1hz": round(min_count_1720, 2),
            "1720_nm_absorption_A": round(A_1722, 4),
            "940_nm_max_count_0.85_1.1hz": round(max_count_940, 2),
        },
        "from_min_of_IFFT": {
            "tc_mmol_l": round(tc_min, 2),
            "tc_mg_dl": round(to_mg_dl(tc_min), 1),
            "ldl_mmol_l": round(ldl_min, 2),
            "ldl_mg_dl": round(to_mg_dl(ldl_min), 1),
        },
    }
    out_path = YOM_TEST_DATA_PATH if raw_path == RAW_PATH else DATA_DIR / "processed" / f"{stem}_test_data.json"
    with open(out_path, "w") as f:
        json.dump([record], f, indent=2)
    print(f"Wrote {out_path} (max IFFT bandpass -> reflectance, TC={tc:.2f} mmol/L, LDL={ldl:.2f} mmol/L)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
