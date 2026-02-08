#!/usr/bin/env python3
"""
Use the computer's camera (e.g. front-facing) as a light sensor.
Reads frames, computes average brightness, and prints or streams the value.
Flash: uses the screen as a flashing light (point camera at screen); the camera
LED is not software-controllable.
"""

import argparse
import csv
import sys
import time
from pathlib import Path
from typing import List, Optional, Tuple

import cv2
import numpy as np

_ROOT = Path(__file__).resolve().parent.parent
_DATA = _ROOT / "data"
_DEFAULT_CSV = _DATA / "light_sensor_timeseries.csv"


def _run_flash_and_record_on_main_thread(
    cap: cv2.VideoCapture,
    csv_path: Path,
    flash_hz: float,
    duration_sec: float,
    interval_sec: float,
    do_spectrogram: bool,
) -> List[Tuple[float, float]]:
    """
    Run fullscreen flash and camera recording on the main thread (required on macOS).
    Returns list of (timestamp, brightness) rows.
    """
    try:
        import tkinter as tk
    except ImportError:
        print("Warning: tkinter not available; skipping screen flash.", file=sys.stderr)
        return []

    cap.read()  # warm-up
    start = time.perf_counter()
    rows: List[Tuple[float, float]] = []
    flash_period = 1.0 / flash_hz
    next_flash = start
    next_sample = start
    flash_is_white = False

    root = tk.Tk()
    root.attributes("-fullscreen", True)
    root.overrideredirect(True)
    root.configure(bg="black")
    root.lift()

    def tick() -> None:
        nonlocal next_flash, next_sample, flash_is_white
        now = time.perf_counter()
        if now - start >= duration_sec:
            root.quit()
            return
        # Toggle flash
        if now >= next_flash:
            flash_is_white = not flash_is_white
            root.configure(bg="white" if flash_is_white else "black")
            next_flash = now + flash_period / 2
        # Sample camera
        if now >= next_sample:
            b = get_brightness(cap)
            if b is not None:
                rows.append((now, b))
                print(f"  {now - start:6.1f}s  brightness={b:6.1f}")
            next_sample = now + interval_sec
        root.after(20, tick)

    root.after(100, tick)
    root.mainloop()
    try:
        root.destroy()
    except Exception:
        pass
    return rows


def get_brightness(cap: cv2.VideoCapture) -> Optional[float]:
    """Capture one frame and return average brightness (0–255)."""
    ok, frame = cap.read()
    if not ok or frame is None:
        return None
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return float(gray.mean())


def plot_time_series(csv_path: Path, output_path: Optional[Path] = None) -> None:
    """Load CSV of timestamp,brightness and plot time series."""
    import matplotlib.pyplot as plt

    timestamps = []
    brightness = []
    with open(csv_path, newline="") as f:
        for row in csv.DictReader(f):
            timestamps.append(float(row["timestamp"]))
            brightness.append(float(row["brightness"]))

    if not timestamps:
        print("No data to plot.", file=sys.stderr)
        return

    t0 = timestamps[0]
    elapsed = [t - t0 for t in timestamps]

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(elapsed, brightness, color="#2563eb", linewidth=1.2, alpha=0.9)
    ax.fill_between(elapsed, brightness, alpha=0.2, color="#2563eb")
    ax.set_xlabel("Time (seconds)", fontsize=11)
    ax.set_ylabel("Brightness (0–255)", fontsize=11)
    ax.set_title("Light sensor time series", fontsize=12)
    ax.grid(True, alpha=0.3)
    ax.set_ylim(0, 255)
    ax.tick_params(axis="both", labelsize=10)
    # Ensure tick labels show numeric values
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f"{x:.1f}"))
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, p: f"{int(y)}"))
    fig.tight_layout()

    if output_path:
        fig.savefig(output_path, dpi=150)
        print("Saved plot to", output_path)
    plt.show()


def plot_spectrogram(csv_path: Path, output_path: Optional[Path] = None) -> None:
    """Load brightness time series from CSV and plot spectrogram (time vs frequency)."""
    import matplotlib.pyplot as plt
    from scipy import signal as scipy_signal

    timestamps = []
    brightness = []
    with open(csv_path, newline="") as f:
        for row in csv.DictReader(f):
            timestamps.append(float(row["timestamp"]))
            brightness.append(float(row["brightness"]))

    if len(timestamps) < 2:
        print("Not enough samples for spectrogram.", file=sys.stderr)
        return

    t = np.array(timestamps)
    y = np.array(brightness)
    t0 = t[0]
    elapsed = t - t0
    duration = elapsed[-1] - elapsed[0]
    if duration <= 0:
        duration = 1.0

    # Resample to uniform grid for spectrogram (linear interpolation)
    n_uniform = len(elapsed)
    t_uniform = np.linspace(elapsed[0], elapsed[-1], n_uniform)
    y_uniform = np.interp(t_uniform, elapsed, y)
    fs = (n_uniform - 1) / duration  # samples per second

    nperseg = min(256, n_uniform // 4)
    if nperseg < 32:
        nperseg = min(32, n_uniform)
    nperseg = max(4, nperseg)
    noverlap = min(nperseg // 2, nperseg - 1)
    f, t_spec, Sxx = scipy_signal.spectrogram(
        y_uniform, fs=fs, nperseg=nperseg, noverlap=noverlap, detrend="constant"
    )
    # Log scale for visibility (avoid log(0))
    Sxx_db = 10 * np.log10(Sxx + 1e-12)

    # pcolormesh expects edges; scipy returns segment centers
    dt = (t_spec[-1] - t_spec[0]) / max(1, len(t_spec) - 1) if len(t_spec) > 1 else duration
    t_edges = np.concatenate(([max(0, t_spec[0] - dt / 2)], t_spec + dt / 2))
    t_edges[-1] = min(duration, t_edges[-1])
    df = (f[1] - f[0]) if len(f) > 1 else (fs / 2 - f[0]) if f[0] < fs / 2 else 0.5
    f_edges = np.concatenate(([max(0, f[0] - df / 2)], f + df / 2))
    f_edges[-1] = min(fs / 2, f_edges[-1])

    fig, ax = plt.subplots(figsize=(10, 4))
    im = ax.pcolormesh(
        t_edges, f_edges, Sxx_db, shading="flat", cmap="viridis", rasterized=True
    )
    ax.set_xlim(0, duration)
    ax.set_ylim(0, min(fs / 2, f[-1] * 1.01))
    ax.set_xlabel("Time (seconds)")
    ax.set_ylabel("Frequency (Hz)")
    ax.set_title("Brightness spectrogram")
    fig.colorbar(im, ax=ax, label="Power (dB)")
    # Use data range for color scale so spectrogram is always visible
    vmin, vmax = np.nanpercentile(Sxx_db, [2, 98])
    if vmax > vmin:
        im.set_clim(vmin, vmax)
    fig.tight_layout()

    if output_path:
        fig.savefig(output_path, dpi=150)
        print("Saved spectrogram to", output_path)
    plt.show()


def get_dominant_frequencies(
    csv_path: Path,
    top_n: int = 10,
) -> List[Tuple[float, float]]:
    """
    Load brightness time series from CSV and return dominant frequencies (Hz) with power (dB).
    Returns list of (frequency_Hz, power_dB) sorted by power descending, up to top_n.
    """
    from scipy import signal as scipy_signal

    timestamps = []
    brightness = []
    with open(csv_path, newline="") as f:
        for row in csv.DictReader(f):
            timestamps.append(float(row["timestamp"]))
            brightness.append(float(row["brightness"]))

    if len(timestamps) < 2:
        return []

    t = np.array(timestamps)
    y = np.array(brightness)
    t0 = t[0]
    elapsed = t - t0
    duration = elapsed[-1] - elapsed[0]
    if duration <= 0:
        duration = 1.0

    n_uniform = len(elapsed)
    t_uniform = np.linspace(elapsed[0], elapsed[-1], n_uniform)
    y_uniform = np.interp(t_uniform, elapsed, y)
    fs = (n_uniform - 1) / duration

    nperseg = min(256, n_uniform // 4)
    if nperseg < 32:
        nperseg = min(32, n_uniform)
    nperseg = max(4, nperseg)
    noverlap = min(nperseg // 2, nperseg - 1)
    f, _, Sxx = scipy_signal.spectrogram(
        y_uniform, fs=fs, nperseg=nperseg, noverlap=noverlap, detrend="constant"
    )
    # Average power over time (mean spectrum)
    power_mean = np.mean(Sxx, axis=1)
    power_db = 10 * np.log10(power_mean + 1e-12)

    # Find peaks (exclude DC at index 0 for "frequencies of variation")
    peaks, props = scipy_signal.find_peaks(
        power_db, height=power_db.max() - 20, distance=1
    )
    if len(peaks) == 0:
        # No clear peaks: return top by power (skip 0 Hz)
        idx = np.argsort(power_db[1:])[::-1][:top_n]
        return [(float(f[i + 1]), float(power_db[i + 1])) for i in idx]

    # Sort peaks by power
    peak_powers = power_db[peaks]
    order = np.argsort(peak_powers)[::-1][:top_n]
    return [(float(f[peaks[i]]), float(peak_powers[i])) for i in order]


def run_record(
    cap: cv2.VideoCapture,
    csv_path: Path,
    interval_sec: float = 1.0,
    duration_sec: Optional[float] = None,
    flash_hz: Optional[float] = None,
    do_spectrogram: bool = False,
) -> None:
    """Record brightness at intervals; optionally flash screen and/or produce spectrogram."""
    if flash_hz is not None and flash_hz > 0:
        # Flash must run on main thread (macOS requires NSWindow on main thread)
        if duration_sec is None:
            duration_sec = 10.0
        if interval_sec > 1 / 30:
            interval_sec = 1 / 30
        print(f"Point camera at screen. Flashing at {flash_hz} Hz for {duration_sec:.1f}s.")
        print("-" * 50)
        rows = _run_flash_and_record_on_main_thread(
            cap, csv_path, flash_hz, duration_sec, interval_sec, do_spectrogram
        )
    else:
        cap.read()  # warm-up
        start = time.perf_counter()
        rows = []
        print(f"Recording (interval={interval_sec}s). Stop with Ctrl+C or wait for duration.")
        if duration_sec is not None:
            print(f"Duration: {duration_sec}s")
        print("(Camera LED cannot be controlled; for a flashing light use --flash and point camera at screen.)")
        print("-" * 50)
        try:
            next_ts = start
            while True:
                now = time.perf_counter()
                if duration_sec is not None and (now - start) >= duration_sec:
                    break
                if now >= next_ts:
                    b = get_brightness(cap)
                    if b is not None:
                        rows.append((now, b))
                        print(f"  {now - start:6.1f}s  brightness={b:6.1f}")
                    next_ts = now + interval_sec
                time.sleep(0.02)
        except KeyboardInterrupt:
            print("\nStopped by user.")

    if not rows:
        print("No samples recorded.", file=sys.stderr)
        return

    with open(csv_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["timestamp", "brightness"])
        w.writerows(rows)
    print(f"Saved {len(rows)} samples to {csv_path}")

    plot_path = csv_path.with_suffix(".png")
    plot_time_series(csv_path, output_path=plot_path)

    if do_spectrogram:
        spec_path = csv_path.with_name(csv_path.stem + "_spectrogram.png")
        plot_spectrogram(csv_path, output_path=spec_path)
        freqs = get_dominant_frequencies(csv_path, top_n=10)
        if freqs:
            print("Dominant frequencies (Hz) detected in brightness:")
            for hz, db in freqs:
                print(f"  {hz:.2f} Hz  (power {db:.1f} dB)")
            freq_path = csv_path.with_name(csv_path.stem + "_frequencies.csv")
            with open(freq_path, "w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["frequency_Hz", "power_dB"])
                w.writerows(freqs)
            print(f"Saved to {freq_path}")


def main():
    parser = argparse.ArgumentParser(description="Use camera as light sensor.")
    parser.add_argument("camera_index", nargs="?", type=int, default=0, help="Camera device index (default: 0)")
    parser.add_argument("--record", "-r", action="store_true", help="Record time series to CSV and plot")
    parser.add_argument("--watch", "-w", action="store_true", help="Live brightness bar")
    parser.add_argument("--plot", "-p", nargs="?", const="default", metavar="CSV", help="Plot time series from CSV")
    parser.add_argument("--spectrogram", "-s", nargs="?", const="default", metavar="CSV", help="Plot spectrogram from CSV (default: light_sensor_timeseries.csv)")
    parser.add_argument("--frequencies", nargs="?", const="default", metavar="CSV", help="Print dominant frequencies (Hz) from CSV; optional path (default: light_sensor_timeseries.csv)")
    parser.add_argument("--flash", "-f", type=float, default=None, metavar="HZ", help="Flash screen at HZ during record (point camera at screen)")
    parser.add_argument("--duration", "-d", type=float, default=None, metavar="SEC", help="Recording duration in seconds (with --record)")
    parser.add_argument("--interval", "-i", type=float, default=1.0, metavar="SEC", help="Sampling interval in seconds (with --record)")
    parsed = parser.parse_args()

    # --plot without camera
    if parsed.plot is not None:
        csv_path = _DEFAULT_CSV if parsed.plot == "default" else Path(parsed.plot)
        if not csv_path.exists():
            print(f"File not found: {csv_path}", file=sys.stderr)
            sys.exit(1)
        plot_time_series(csv_path)
        return

    # --spectrogram without camera
    if parsed.spectrogram is not None:
        csv_path = _DEFAULT_CSV if parsed.spectrogram == "default" else Path(parsed.spectrogram)
        if not csv_path.exists():
            print(f"File not found: {csv_path}", file=sys.stderr)
            sys.exit(1)
        plot_spectrogram(csv_path)
        return

    # --frequencies: print dominant frequencies from CSV (no camera, no plot)
    if parsed.frequencies is not None:
        csv_path = _DEFAULT_CSV if parsed.frequencies == "default" else Path(parsed.frequencies)
        if not csv_path.exists():
            print(f"File not found: {csv_path}", file=sys.stderr)
            sys.exit(1)
        freqs = get_dominant_frequencies(csv_path, top_n=10)
        if not freqs:
            print("Not enough data or no dominant frequencies found.")
        else:
            print("Dominant frequencies (Hz) in brightness signal:")
            for hz, db in freqs:
                print(f"  {hz:.2f} Hz  (power {db:.1f} dB)")
        return

    camera_index = parsed.camera_index
    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened() and camera_index == 0:
        cap = cv2.VideoCapture(1)
    if not cap.isOpened():
        print("Error: Could not open camera.", file=sys.stderr)
        print("On macOS: grant Camera access to Terminal (or this app) in System Settings → Privacy & Security.", file=sys.stderr)
        sys.exit(1)

    try:
        cap.read()

        if parsed.record:
            _DATA.mkdir(exist_ok=True)
            out_csv = _DEFAULT_CSV
            run_record(
                cap,
                out_csv,
                interval_sec=parsed.interval,
                duration_sec=parsed.duration,
                flash_hz=parsed.flash,
                do_spectrogram=True,
            )
            return

        if parsed.watch:
            print("Light sensor (Ctrl+C to stop). Camera index:", camera_index)
            print("-" * 50)
            while True:
                brightness = get_brightness(cap)
                if brightness is None:
                    continue
                pct = round(100 * brightness / 255, 1)
                bar_len = 30
                filled = int(bar_len * brightness / 255)
                bar = "█" * filled + "░" * (bar_len - filled)
                print(f"\r  {bar}  {brightness:5.1f}  ({pct:5.1f}%)", end="", flush=True)
        else:
            # single reading
            brightness = get_brightness(cap)
            if brightness is None:
                print("Error: Could not read frame.", file=sys.stderr)
                sys.exit(1)
            pct = round(100 * brightness / 255, 1)
            print(f"Brightness: {brightness:.1f} (0–255) | {pct}% (0–100)")
    finally:
        cap.release()


if __name__ == "__main__":
    main()
