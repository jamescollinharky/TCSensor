#!/usr/bin/env python3
"""
Plot time series from color_reader.py --stream CSV output.
Usage: python plot_color_stream.py [data/color_stream.csv]
       python plot_color_stream.py --no-show data/color_stream.csv  # save only, no window
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Plot time series from color_reader --stream CSV.")
    parser.add_argument("csv_file", nargs="?", help="Path to CSV (default: data/color_stream.csv)")
    parser.add_argument("--no-show", action="store_true", help="Save PNG only, do not open plot window")
    parser.add_argument("--t-min", type=float, default=None, metavar="SEC", help="Use only time (seconds) >= this value")
    parser.add_argument("--t-max", type=float, default=None, metavar="SEC", help="Use only time (seconds) < this value")
    parser.add_argument("--gain", type=float, default=1.0, metavar="G", help="Multiply values by this factor (default 1.0)")
    parser.add_argument("--fft", action="store_true", help="FFT first value column (e.g. NIR_proxy_broad), print dominant frequency, save spectrum plot")
    parser.add_argument("--fft-t-min", type=float, default=None, metavar="SEC", help="Use only time >= this for FFT (e.g. 10)")
    parser.add_argument("--fft-t-max", type=float, default=None, metavar="SEC", help="Use only time < this for FFT (e.g. 30)")
    parsed = parser.parse_args()

    data_dir = Path(__file__).resolve().parent.parent / "data"
    default_csv = data_dir / "color_stream.csv"
    csv_path = Path(parsed.csv_file) if parsed.csv_file else default_csv

    if not csv_path.exists():
        print(f"File not found: {csv_path}", file=sys.stderr)
        sys.exit(1)

    # Load CSV (skip duplicate header rows if --header-every was used)
    import matplotlib.pyplot as plt
    import numpy as np

    rows = []
    with open(csv_path, newline="") as f:
        reader = csv.reader(f)
        header = next(reader)
        for row in reader:
            if len(row) != len(header) or row[0].strip().lower() == "timestamp":
                continue  # skip malformed or repeated header lines
            rows.append([float(x) for x in row])

    if not rows:
        print("No data rows to plot.", file=sys.stderr)
        sys.exit(1)

    data_full = np.array(rows)
    t = data_full[:, 0]
    t0 = t[0]
    elapsed_full = t - t0
    data = data_full
    elapsed = elapsed_full

    if parsed.t_min is not None or parsed.t_max is not None:
        t_min = parsed.t_min if parsed.t_min is not None else -np.inf
        t_max = parsed.t_max if parsed.t_max is not None else np.inf
        mask = (elapsed >= t_min) & (elapsed < t_max)
        if not np.any(mask):
            print(f"No rows with {t_min} <= time < {t_max}.", file=sys.stderr)
            sys.exit(1)
        data = data[mask]
        elapsed = elapsed[mask]

    value_cols = [c for c in header[1:] if c]
    if not value_cols:
        print("No value columns found.", file=sys.stderr)
        sys.exit(1)

    gain = parsed.gain
    values = data[:, 1:] * gain

    # FFT on first value column (e.g. NIR_proxy_broad); optional window via --fft-t-min/--fft-t-max
    if parsed.fft:
        if parsed.fft_t_min is not None or parsed.fft_t_max is not None:
            fft_t_min = parsed.fft_t_min if parsed.fft_t_min is not None else -np.inf
            fft_t_max = parsed.fft_t_max if parsed.fft_t_max is not None else np.inf
            fft_mask = (elapsed_full >= fft_t_min) & (elapsed_full < fft_t_max)
            if not np.any(fft_mask):
                print(f"No rows with {fft_t_min} <= time < {fft_t_max} for FFT.", file=sys.stderr)
                sys.exit(1)
            fft_elapsed = elapsed_full[fft_mask]
            fft_signal = data_full[fft_mask, 1].astype(float)
            print(f"FFT window: {fft_t_min}–{fft_t_max} s ({len(fft_signal)} points)")
        else:
            fft_elapsed = elapsed
            fft_signal = data[:, 1].astype(float)
        signal = fft_signal  # for n, dt below
        n = len(signal)
        fft_elapsed_use = fft_elapsed
        dt = np.median(np.diff(fft_elapsed_use)) if len(fft_elapsed_use) > 1 else 0.03
        if dt <= 0:
            dt = 0.03
        fs = 1.0 / dt
        # detrend: remove mean so DC doesn't dominate
        signal_centered = signal - np.mean(signal)
        fft_vals = np.fft.rfft(signal_centered)
        freqs = np.fft.rfftfreq(n, dt)
        magnitude = np.abs(fft_vals)
        # skip DC (index 0)
        pos_mask = freqs > 0
        pos_freqs = freqs[pos_mask]
        pos_mag = magnitude[pos_mask]
        if len(pos_mag) > 0:
            idx_max = np.argmax(pos_mag)
            dominant_freq = pos_freqs[idx_max]
            print(f"Sampling: dt={dt:.4f} s  fs={fs:.1f} Hz  N={n}")
            print(f"Dominant frequency: {dominant_freq:.4f} Hz")
            # top 5 peaks (simple: sort by magnitude)
            top_idx = np.argsort(pos_mag)[-5:][::-1]
            print("Top frequencies (Hz)  magnitude")
            for i in top_idx:
                print(f"  {pos_freqs[i]:.4f}  {pos_mag[i]:.1f}")
        out_fft = csv_path.parent / (csv_path.stem + "_fft.png")
        fig_fft, ax_fft = plt.subplots(figsize=(8, 4))
        ax_fft.plot(freqs[freqs > 0], magnitude[freqs > 0], color="#2563eb", linewidth=1)
        ax_fft.set_xlabel("Frequency (Hz)", fontsize=11)
        ax_fft.set_ylabel("Magnitude", fontsize=11)
        title = f"FFT: {value_cols[0]} ({csv_path.name})"
        if parsed.fft_t_min is not None or parsed.fft_t_max is not None:
            title += f"  [{parsed.fft_t_min or 0}–{parsed.fft_t_max or '∞'} s]"
        ax_fft.set_title(title, fontsize=12)
        ax_fft.grid(True, alpha=0.3)
        fig_fft.tight_layout()
        fig_fft.savefig(out_fft, dpi=150)
        print("Saved", out_fft)
        if not parsed.no_show:
            plt.figure(fig_fft.number)
            plt.show()

    ncols = len(value_cols)
    if ncols == 1:
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.plot(elapsed, values[:, 0], color="#2563eb", linewidth=1.2, alpha=0.9)
        ylabel = value_cols[0] if gain == 1.0 else f"{value_cols[0]} (×{gain})"
        ax.set_ylabel(ylabel, fontsize=11)
        ax.set_ylim(40, None)
    else:
        fig, ax = plt.subplots(figsize=(10, 5))
        colors = plt.cm.tab10(np.linspace(0, 1, min(ncols, 10)))
        if ncols > 10:
            colors = plt.cm.tab20(np.linspace(0, 1, ncols))
        for i, name in enumerate(value_cols):
            ax.plot(elapsed, values[:, i], label=name, color=colors[i % len(colors)], linewidth=1, alpha=0.9)
        ax.legend(loc="upper right", fontsize=8, ncol=2 if ncols > 5 else 1)
        ylabel = "Value" if gain == 1.0 else f"Value (×{gain})"
        ax.set_ylabel(ylabel, fontsize=11)
        ax.set_ylim(40, None)
    ax.set_xlabel("Time (seconds)", fontsize=11)
    ax.set_title(f"Color stream: {csv_path.name}", fontsize=12)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()

    out_path = csv_path.with_suffix(".png")
    fig.savefig(out_path, dpi=150)
    print("Saved", out_path)
    if not parsed.no_show:
        plt.show()


if __name__ == "__main__":
    main()
