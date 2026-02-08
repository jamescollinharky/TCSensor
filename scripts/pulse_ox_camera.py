#!/usr/bin/env python3
"""
Test pulse oximeter using the computer's camera (reflectance PPG).

How pulse oximetry works (see https://en.wikipedia.org/wiki/Pulse_oximetry):
  - Medical devices use RED (660 nm) and INFRARED (940 nm) LEDs and the
    ratio of pulsatile absorption to estimate SpO2 (Beer-Lambert law).
  - This script uses the camera's RED and GREEN channels as a rough proxy:
    we extract the pulsatile (AC) and baseline (DC) components and use
    a ratio-of-ratios to estimate a non-calibrated "SpO2-like" value.
  - Pulse rate (BPM) is derived from the PPG waveform (peak detection).

NOT FOR MEDICAL USE. Not validated or calibrated. For testing/education only.
"""
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


def get_roi_channels(frame: np.ndarray, roi_frac: float = 0.3) -> Tuple[float, float]:
    """Extract mean R and G from center ROI (BGR order in OpenCV)."""
    h, w = frame.shape[:2]
    x1 = int(w * (0.5 - roi_frac / 2))
    x2 = int(w * (0.5 + roi_frac / 2))
    y1 = int(h * (0.5 - roi_frac / 2))
    y2 = int(h * (0.5 + roi_frac / 2))
    roi = frame[y1:y2, x1:x2]
    if roi.size == 0:
        return 0.0, 0.0
    b, g, r = cv2.split(roi)
    return float(np.mean(r)), float(np.mean(g))


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
    r_sig: np.ndarray, g_sig: np.ndarray, fs: float
) -> Optional[float]:
    """
    Ratio-of-ratios (AC/DC) for red vs green as a rough proxy for SpO2.
    Real pulse oximeters use red vs infrared; we only have RGB.
    """
    if len(r_sig) < 2 or len(g_sig) < 2:
        return None
    dc_r = np.mean(r_sig)
    dc_g = np.mean(g_sig)
    if dc_r < 1 or dc_g < 1:
        return None
    filtered_r = bandpass(r_sig.astype(float), 0.7, 3.0, fs)
    filtered_g = bandpass(g_sig.astype(float), 0.7, 3.0, fs)
    ac_r = np.std(filtered_r)
    ac_g = np.std(filtered_g)
    if ac_g < 1e-6:
        return None
    # RR = (AC/DC)_red / (AC/DC)_green
    rr = (ac_r / dc_r) / (ac_g / dc_g)
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
    camera_index = 0
    duration_sec = 30.0
    target_fps = 30
    if len(sys.argv) > 1:
        try:
            camera_index = int(sys.argv[1])
        except ValueError:
            pass

    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        cap = cv2.VideoCapture(1)
    if not cap.isOpened():
        print("Error: Could not open camera.", file=sys.stderr)
        sys.exit(1)

    cap.set(cv2.CAP_PROP_FPS, target_fps)
    cap.read()

    print("Camera pulse oximeter (reflectance PPG) — real-time time series")
    print("Place your finger over the camera lens; keep still. Use ambient or screen light.")
    print("NOT FOR MEDICAL USE. For testing/education only. Close plot window or Ctrl+C to stop.")
    print("-" * 50)

    times_list: List[float] = []
    r_list: List[float] = []
    g_list: List[float] = []
    ts_elapsed: List[float] = []
    ts_bpm: List[float] = []
    ts_spo2: List[float] = []
    start = time.perf_counter()
    fs_actual = 0.0
    frames_per_reading = int(3.0 * (target_fps or 30))  # one reading every 3 seconds
    frames_since_reading = 0

    fig, (ax_bpm, ax_spo2) = plt.subplots(2, 1, sharex=True, figsize=(8, 5))
    fig.suptitle("Pulse oximeter (real-time, NOT for medical use)")
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
        while (time.perf_counter() - start) < duration_sec:
            ok, frame = cap.read()
            if not ok or frame is None:
                continue
            t = time.perf_counter()
            r, g = get_roi_channels(frame)
            times_list.append(t)
            r_list.append(r)
            g_list.append(g)

            n = len(times_list)
            if n > 2:
                fs_actual = (n - 1) / (times_list[-1] - times_list[0])
            if n >= int(4 * (target_fps or 30)):  # need ~4 s of data for first reading
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
                    g_sig = np.array(g_list)
                    fs = fs_actual if fs_actual > 5 else 30.0
                    bpm = compute_bpm_from_peaks(times, r_sig, fs)
                    rr = compute_ratio_of_ratios(r_sig, g_sig, fs)
                    spo2_approx = rr_to_spo2_approx(rr) if rr is not None else None

                    ts_elapsed.append(elapsed)
                    ts_bpm.append(bpm if bpm is not None else float("nan"))
                    ts_spo2.append(spo2_approx if spo2_approx is not None else float("nan"))

                    line = f"  {elapsed:5.1f}s  BPM: {bpm:.0f}" if bpm else f"  {elapsed:5.1f}s  BPM: --"
                    if spo2_approx is not None:
                        line += f"  SpO2 (uncal): ~{spo2_approx:.0f}%"
                    print(line, flush=True)

                    if plt.fignum_exists(fig.number):
                        line_bpm.set_data(ts_elapsed, ts_bpm)
                        line_spo2.set_data(ts_elapsed, ts_spo2)
                        ax_bpm.relim()
                        ax_bpm.autoscale_view(scalex=True, scaley=False)
                        ax_spo2.relim()
                        ax_spo2.autoscale_view(scalex=True, scaley=False)
                        fig.canvas.draw_idle()
                        fig.canvas.flush_events()
    except KeyboardInterrupt:
        print("\nStopped by user.")

    plt.ioff()

    cap.release()

    # Final summary and save time series
    if len(times_list) < 10:
        print("\nNot enough data. Keep finger still over camera for 5+ seconds.")
        plt.close(fig)
        return

    times = np.array(times_list)
    r_sig = np.array(r_list)
    g_sig = np.array(g_list)
    fs = (len(times) - 1) / (times[-1] - times[0]) if times[-1] > times[0] else 30.0

    bpm = compute_bpm_from_peaks(times, r_sig, fs)
    rr = compute_ratio_of_ratios(r_sig, g_sig, fs)
    spo2_approx = rr_to_spo2_approx(rr) if rr is not None else None

    # Final plot update and save
    if ts_elapsed:
        line_bpm.set_data(ts_elapsed, ts_bpm)
        line_spo2.set_data(ts_elapsed, ts_spo2)
        ax_bpm.relim()
        ax_bpm.autoscale_view(scalex=True, scaley=False)
        ax_spo2.relim()
        ax_spo2.autoscale_view(scalex=True, scaley=False)
        fig.canvas.draw_idle()
        _DATA.mkdir(exist_ok=True)
        out_path = _DATA / "pulse_ox_timeseries.png"
        fig.savefig(out_path, dpi=150)
        print(f"\nSaved time series to {out_path}")
        csv_path = _DATA / "pulse_ox_timeseries.csv"
        with open(csv_path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["elapsed_sec", "bpm", "spo2_uncal"])
            w.writerows(zip(ts_elapsed, ts_bpm, ts_spo2))
        print(f"Saved CSV to {csv_path}")

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
    plt.show(block=True)


if __name__ == "__main__":
    main()
