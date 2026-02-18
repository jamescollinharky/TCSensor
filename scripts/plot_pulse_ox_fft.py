#!/usr/bin/env python3
"""
FFT on color-band time series (e.g. pulse_ox_color_timeseries.csv: elapsed_sec, R, G, B).

Loads elapsed_sec, R, G, B; runs FFT on each channel; prints dominant frequency (Hz and BPM);
saves spectrum plot for R, G, B.

Usage:
  python scripts/plot_pulse_ox_fft.py
  python scripts/plot_pulse_ox_fft.py data/timeseries/pulse_ox_color_timeseries.csv
  python scripts/plot_pulse_ox_fft.py --t-min 5 --t-max 55  # use middle 50 s for FFT
"""
import argparse
import csv
import sys
from pathlib import Path

import numpy as np


def main():
    parser = argparse.ArgumentParser(description="FFT on pulse ox color bands (R, G, B).")
    parser.add_argument(
        "csv_file",
        nargs="?",
        default=None,
        help="Path to CSV (default: data/timeseries/pulse_ox_color_timeseries.csv)",
    )
    parser.add_argument("--no-show", action="store_true", help="Save PNG only, do not open plot")
    parser.add_argument("--t-min", type=float, default=None, help="Use only elapsed_sec >= this (seconds)")
    parser.add_argument("--t-max", type=float, default=None, help="Use only elapsed_sec < this (seconds)")
    args = parser.parse_args()

    data_dir = Path(__file__).resolve().parent.parent / "data"
    csv_path = Path(args.csv_file) if args.csv_file else data_dir / "timeseries" / "pulse_ox_color_timeseries.csv"

    if not csv_path.exists():
        print(f"File not found: {csv_path}", file=sys.stderr)
        sys.exit(1)

    rows = []
    with open(csv_path, newline="") as f:
        reader = csv.reader(f)
        header = next(reader)
        for row in reader:
            if len(row) < 4:
                continue
            rows.append([float(row[0]), float(row[1]), float(row[2]), float(row[3])])

    if not rows:
        print("No data rows.", file=sys.stderr)
        sys.exit(1)

    data = np.array(rows)
    elapsed = data[:, 0]
    R = data[:, 1]
    G = data[:, 2]
    B = data[:, 3]

    if args.t_min is not None or args.t_max is not None:
        t_min = args.t_min if args.t_min is not None else -np.inf
        t_max = args.t_max if args.t_max is not None else np.inf
        mask = (elapsed >= t_min) & (elapsed < t_max)
        if not np.any(mask):
            print(f"No rows in [{t_min}, {t_max}) s.", file=sys.stderr)
            sys.exit(1)
        elapsed = elapsed[mask]
        R = R[mask]
        G = G[mask]
        B = B[mask]

    n = len(elapsed)
    dt = np.median(np.diff(elapsed)) if n > 1 else 0.2
    if dt <= 0:
        dt = 0.2
    fs = 1.0 / dt

    channels = [("R", R), ("G", G), ("B", B)]
    results = []
    for name, sig in channels:
        sig_centered = sig.astype(float) - np.mean(sig)
        fft_vals = np.fft.rfft(sig_centered)
        freqs = np.fft.rfftfreq(n, dt)
        magnitude = np.abs(fft_vals)
        pos_mask = freqs > 0
        pos_freqs = freqs[pos_mask]
        pos_mag = magnitude[pos_mask]
        if len(pos_mag) > 0:
            idx_max = np.argmax(pos_mag)
            dominant_hz = pos_freqs[idx_max]
            bpm = dominant_hz * 60.0
            results.append((name, pos_freqs, pos_mag, dominant_hz, bpm))
        else:
            results.append((name, np.array([]), np.array([]), None, None))

    print(f"FFT: {csv_path.name}  (N={n}, dt≈{dt:.3f} s, fs≈{fs:.1f} Hz)")
    if args.t_min is not None or args.t_max is not None:
        print(f"  Time window: [{args.t_min or elapsed[0]:.1f}, {args.t_max or elapsed[-1]:.1f}) s")
    print("-" * 50)
    for name, pos_freqs, pos_mag, dom_hz, bpm in results:
        if dom_hz is not None:
            print(f"  {name}: dominant {dom_hz:.4f} Hz  (~{bpm:.0f} BPM)")
        else:
            print(f"  {name}: no peak")

    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(3, 1, sharex=True, figsize=(8, 7))
    colors = ["#dc2626", "#16a34a", "#2563eb"]
    for ax, (name, pos_freqs, pos_mag, dom_hz, bpm), color in zip(axes, results, colors):
        if len(pos_freqs) > 0:
            ax.plot(pos_freqs, pos_mag, color=color, linewidth=1.2)
            if dom_hz is not None:
                ax.axvline(dom_hz, color=color, linestyle="--", alpha=0.7, label=f"peak {dom_hz:.3f} Hz ({bpm:.0f} BPM)")
        ax.set_ylabel(f"{name} magnitude", fontsize=10)
        ax.legend(loc="upper right", fontsize=8)
        ax.grid(True, alpha=0.3)
    axes[-1].set_xlabel("Frequency (Hz)", fontsize=11)
    fig.suptitle(f"FFT: color bands — {csv_path.name}", fontsize=12)
    fig.tight_layout()

    out_path = csv_path.parent / (csv_path.stem + "_fft.png")
    fig.savefig(out_path, dpi=150)
    print(f"Saved {out_path}")
    if not args.no_show:
        plt.show()


if __name__ == "__main__":
    main()
