#!/usr/bin/env python3
"""
SpO2-like sensor using the computer's camera (reflectance PPG).

How pulse oximetry works (see https://en.wikipedia.org/wiki/Pulse_oximetry):
  - Medical devices use RED (660 nm) and INFRARED (940 nm) and the
    ratio of pulsatile absorption (AC/DC) to estimate SpO2 (Beer-Lambert).
  - This script: RED channel = red proxy; second signal = GREEN (default)
    or an IR proxy (mean intensity or chosen channel) if your camera sees NIR.
  - Pulse rate (BPM) from PPG peak detection.

Usage:
  python pulse_ox_camera.py              # camera 0, red vs green
  python pulse_ox_camera.py --camera 1   # choose camera index
  python pulse_ox_camera.py --mode red-ir --ir-proxy mean   # red vs NIR proxy (cameras that see IR)

NOT FOR MEDICAL USE. Not validated or calibrated. For testing/education only.
"""
import argparse
import csv
import sys
import time
from pathlib import Path
from typing import List, Optional, Tuple

import cv2

_ROOT = Path(__file__).resolve().parent.parent
_DATA = _ROOT / "data"
import matplotlib.pyplot as plt
import numpy as np
from scipy import signal as scipy_signal

# Prefer AVFoundation on macOS so built-in and external (e.g. phone) cameras work
_CAP = cv2.CAP_AVFOUNDATION if sys.platform == "darwin" else cv2.CAP_ANY


def get_roi_rgb(frame: np.ndarray, roi_frac: float = 0.3) -> Tuple[float, float, float]:
    """Extract mean R, G, B from center ROI (BGR order in OpenCV)."""
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


def bandpass(sig: np.ndarray, low_hz: float, high_hz: float, fs: float) -> np.ndarray:
    """Butterworth bandpass filter."""
    nyq = fs / 2
    low = max(0.01, low_hz / nyq)
    high = min(0.99, high_hz / nyq)
    if low >= high:
        return sig
    b, a = scipy_signal.butter(2, [low, high], btype="band")
    return scipy_signal.filtfilt(b, a, sig)


def compute_bpm_from_peaks(times: np.ndarray, sig: np.ndarray, fs: float) -> Optional[float]:
    """Estimate BPM from peak intervals in bandpass-filtered signal (0.7–3 Hz)."""
    if len(sig) < 3 * fs:  # need at least ~3 s
        return None
    filtered = bandpass(sig.astype(float), 0.7, 3.0, fs)
    peaks, _ = scipy_signal.find_peaks(filtered, distance=int(0.35 * fs), prominence=0.3)
    if len(peaks) < 2:
        return None
    intervals = np.diff(times[peaks])
    median_interval = np.median(intervals)
    if median_interval <= 0:
        return None
    return 60.0 / median_interval


def compute_ratio_of_ratios(
    red_sig: np.ndarray, second_sig: np.ndarray, fs: float
) -> Optional[float]:
    """
    Ratio-of-ratios (AC/DC)_red / (AC/DC)_second for SpO2-like estimate.
    second_sig can be green (red-green mode) or IR proxy (red-ir mode).
    """
    if len(red_sig) < 2 or len(second_sig) < 2:
        return None
    dc_r = np.mean(red_sig)
    dc_2 = np.mean(second_sig)
    if dc_r < 1 or dc_2 < 1:
        return None
    filtered_r = bandpass(red_sig.astype(float), 0.7, 3.0, fs)
    filtered_2 = bandpass(second_sig.astype(float), 0.7, 3.0, fs)
    ac_r = np.std(filtered_r)
    ac_2 = np.std(filtered_2)
    if ac_2 < 1e-6:
        return None
    rr = (ac_r / dc_r) / (ac_2 / dc_2)
    return float(rr)


def rr_to_spo2_approx(rr: float) -> float:
    """
    Map ratio-of-ratios to an approximate SpO2-like value (NOT calibrated).
    Empirical relationship varies by device; this is a placeholder for demo.
    """
    # Placeholder: clamp to a plausible range (real calibration is per-device)
    spo2 = 110 - 35 * rr
    return float(np.clip(spo2, 70, 100))


def main():
    parser = argparse.ArgumentParser(
        description="SpO2-like sensor: camera choice, red vs green or red vs IR proxy. NOT for medical use."
    )
    parser.add_argument(
        "--camera", "-c",
        type=int,
        default=0,
        metavar="INDEX",
        help="Camera device index (0=default, 1=often external/phone). Use list_cameras.py to see indices.",
    )
    parser.add_argument(
        "--mode",
        choices=("red-green", "red-ir"),
        default="red-green",
        help="red-green: red vs green channel (any RGB camera). red-ir: red vs IR proxy (if camera sees NIR).",
    )
    parser.add_argument(
        "--ir-proxy",
        choices=("mean", "g", "b"),
        default="mean",
        help="For --mode red-ir: second signal = mean(R,G,B), or green, or blue (default: mean).",
    )
    parser.add_argument(
        "--duration", "-d",
        type=float,
        default=60.0,
        metavar="SEC",
        help="Recording duration in seconds (default 60). 0 = run until you kill the program (Ctrl+C).",
    )
    parser.add_argument(
        "--report-interval",
        type=float,
        default=5.0,
        metavar="SEC",
        help="Report BPM and SpO2 every N seconds (default 5).",
    )
    parser.add_argument(
        "--no-plot",
        action="store_true",
        help="No plot window; only print to terminal (avoids matplotlib issues on some systems).",
    )
    args = parser.parse_args()

    camera_index = args.camera
    duration_sec = args.duration
    run_until_kill = duration_sec <= 0
    target_fps = 30

    cap = cv2.VideoCapture(camera_index, _CAP)
    if not cap.isOpened():
        # Fallback to next camera
        cap = cv2.VideoCapture(1, _CAP)
        if not cap.isOpened():
            print("Error: Could not open camera. Try: python scripts/list_cameras.py", file=sys.stderr)
            sys.exit(1)
        camera_index = 1

    cap.set(cv2.CAP_PROP_FPS, target_fps)
    cap.read()

    mode_label = "red vs green" if args.mode == "red-green" else f"red vs IR proxy ({args.ir_proxy})"
    print("SpO2-like sensor (reflectance PPG) — real-time")
    print(f"  Camera: {camera_index}  Mode: {mode_label}  Report every: {args.report_interval:.1f} s")
    if run_until_kill:
        print("  Duration: until you stop (Ctrl+C)")
    else:
        print(f"  Duration: {duration_sec:.0f} s")
    print("  Color bands (R,G,B): saved every 0.2 s to data/timeseries/pulse_ox_color_timeseries.csv")
    print("Place your finger over the camera lens; keep still. Use ambient or screen light.")
    print("NOT FOR MEDICAL USE. For testing/education only. Use --no-plot if it stops early; close plot or Ctrl+C to stop.")
    print("-" * 50)

    times_list: List[float] = []
    r_list: List[float] = []
    g_list: List[float] = []
    b_list: List[float] = []
    ts_elapsed: List[float] = []
    ts_bpm: List[float] = []
    ts_spo2: List[float] = []
    color_stream_rows: List[Tuple[float, float, float, float]] = []  # (elapsed_sec, R, G, B)
    last_color_log_time = 0.0
    color_log_interval = 0.2  # seconds
    start = time.perf_counter()
    fs_actual = 0.0
    report_interval_sec = args.report_interval
    frames_per_reading = max(1, int(report_interval_sec * (target_fps or 30)))
    frames_since_reading = 0
    no_plot = args.no_plot

    def second_signal() -> np.ndarray:
        if args.mode == "red-green":
            return np.array(g_list)
        if args.ir_proxy == "mean":
            return (np.array(r_list) + np.array(g_list) + np.array(b_list)) / 3.0
        if args.ir_proxy == "g":
            return np.array(g_list)
        return np.array(b_list)

    fig, ax_bpm, ax_spo2, line_bpm, line_spo2 = None, None, None, None, None
    if not no_plot:
        fig, (ax_bpm, ax_spo2) = plt.subplots(2, 1, sharex=True, figsize=(8, 5))
        fig.suptitle("SpO2-like sensor (NOT for medical use)")
        ax_bpm.set_ylabel("BPM")
        ax_bpm.set_ylim(40, 120)
        ax_bpm.grid(True, alpha=0.3)
        ax_spo2.set_ylabel("SpO2 (uncal) %")
        ax_spo2.set_xlabel("Time (s)")
        ax_spo2.set_ylim(70, 102)
        ax_spo2.grid(True, alpha=0.3)
        line_bpm, = ax_bpm.plot([], [], color="#2563eb", linewidth=1.5)
        line_spo2, = ax_spo2.plot([], [], color="#dc2626", linewidth=1.5)
        plt.ion()
        plt.show(block=False)

    try:
        while run_until_kill or (time.perf_counter() - start) < duration_sec:
            ok, frame = cap.read()
            if not ok or frame is None:
                continue
            t = time.perf_counter()
            r, g, b = get_roi_rgb(frame)
            times_list.append(t)
            r_list.append(r)
            g_list.append(g)
            b_list.append(b)

            # Log color bands every 0.2 s
            elapsed = t - start
            if elapsed - last_color_log_time >= color_log_interval:
                color_stream_rows.append((round(elapsed, 3), round(r, 2), round(g, 2), round(b, 2)))
                last_color_log_time = elapsed

            n = len(times_list)
            if n > 2:
                fs_actual = (n - 1) / (times_list[-1] - times_list[0])
            if n >= int(4 * (target_fps or 30)):
                take_reading = False
                if len(ts_elapsed) == 0:
                    take_reading = True
                    frames_since_reading = 0
                else:
                    frames_since_reading += 1
                    if frames_since_reading >= frames_per_reading:
                        frames_since_reading = 0
                        take_reading = True
                if take_reading:
                    elapsed = t - start
                    times = np.array(times_list)
                    r_sig = np.array(r_list)
                    sec_sig = second_signal()
                    fs = fs_actual if fs_actual > 5 else 30.0
                    bpm = compute_bpm_from_peaks(times, r_sig, fs)
                    rr = compute_ratio_of_ratios(r_sig, sec_sig, fs)
                    spo2_approx = rr_to_spo2_approx(rr) if rr is not None else None

                    ts_elapsed.append(elapsed)
                    ts_bpm.append(bpm if bpm is not None else float("nan"))
                    ts_spo2.append(spo2_approx if spo2_approx is not None else float("nan"))

                    line = f"  {elapsed:5.1f}s  BPM: {bpm:.0f}" if bpm else f"  {elapsed:5.1f}s  BPM: --"
                    if spo2_approx is not None:
                        line += f"  SpO2 (uncal): ~{spo2_approx:.0f}%"
                    print(line, flush=True)

                    if not no_plot and fig is not None:
                        try:
                            if plt.fignum_exists(fig.number):
                                line_bpm.set_data(ts_elapsed, ts_bpm)
                                line_spo2.set_data(ts_elapsed, ts_spo2)
                                ax_bpm.relim()
                                ax_bpm.autoscale_view(scalex=True, scaley=False)
                                ax_spo2.relim()
                                ax_spo2.autoscale_view(scalex=True, scaley=False)
                                fig.canvas.draw_idle()
                                fig.canvas.flush_events()
                        except Exception:
                            pass  # Skip plot update; keep recording
    except KeyboardInterrupt:
        print("\nStopped by user.")

    if not no_plot:
        plt.ioff()

    cap.release()

    if len(times_list) < 10:
        print("\nNot enough data. Keep finger still over camera for 5+ seconds.")
        if fig is not None:
            plt.close(fig)
        return

    times = np.array(times_list)
    r_sig = np.array(r_list)
    sec_sig = second_signal()
    fs = (len(times) - 1) / (times[-1] - times[0]) if times[-1] > times[0] else 30.0

    bpm = compute_bpm_from_peaks(times, r_sig, fs)
    rr = compute_ratio_of_ratios(r_sig, sec_sig, fs)
    spo2_approx = rr_to_spo2_approx(rr) if rr is not None else None

    (_DATA / "timeseries").mkdir(parents=True, exist_ok=True)
    (_DATA / "figures").mkdir(parents=True, exist_ok=True)
    if ts_elapsed:
        csv_path = _DATA / "timeseries" / "pulse_ox_timeseries.csv"
        with open(csv_path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["elapsed_sec", "bpm", "spo2_uncal"])
            w.writerows(zip(ts_elapsed, ts_bpm, ts_spo2))
        print(f"Saved CSV to {csv_path}")
    if color_stream_rows:
        color_path = _DATA / "timeseries" / "pulse_ox_color_timeseries.csv"
        with open(color_path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["elapsed_sec", "R", "G", "B"])
            w.writerows(color_stream_rows)
        print(f"Saved color bands (every 0.2 s) to {color_path}")
        if fig is not None:
            try:
                if plt.fignum_exists(fig.number):
                    line_bpm.set_data(ts_elapsed, ts_bpm)
                    line_spo2.set_data(ts_elapsed, ts_spo2)
                    ax_bpm.relim()
                    ax_bpm.autoscale_view(scalex=True, scaley=False)
                    ax_spo2.relim()
                    ax_spo2.autoscale_view(scalex=True, scaley=False)
                    fig.canvas.draw_idle()
                    out_path = _DATA / "figures" / "pulse_ox_timeseries.png"
                    fig.savefig(out_path, dpi=150)
                    print(f"Saved time series to {out_path}")
            except Exception:
                pass

    print("\n" + "-" * 50)
    print("Result (NOT for medical use):")
    if bpm is not None:
        print(f"  Pulse: ~{bpm:.0f} BPM")
    else:
        print("  Pulse: could not detect (hold finger still, good lighting)")
    if spo2_approx is not None:
        print(f"  SpO2 (uncalibrated proxy): ~{spo2_approx:.0f}%")
    else:
        print("  SpO2: could not estimate")
    print("  Reference: https://en.wikipedia.org/wiki/Pulse_oximetry")
    if fig is not None:
        try:
            if plt.fignum_exists(fig.number):
                plt.show(block=True)
        except Exception:
            pass


if __name__ == "__main__":
    main()
