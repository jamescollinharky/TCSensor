#!/usr/bin/env python3
"""
Read R, G, B and brightness from the camera in real time. Point the camera at
a light source (e.g. the iPhone screen running flashlight_phone.html) to see
the colors change when the screen flashes.

For the iPhone rear camera: use the phone as webcam (e.g. Iriun/Camo), select
the rear/back camera in the app, then use camera index 1 (or run with --rear).

Usage:
  python color_reader.py              # use default camera (0)
  python color_reader.py 1             # use camera index 1 (e.g. phone as webcam)
  python color_reader.py 1 --watch    # live readout until Ctrl+C
  python color_reader.py --rear --stream   # stream CSV from phone rear camera
  python color_reader.py --nir --watch     # broad NIR proxy (attach IR pass filter to camera, e.g. Hoya R72)
"""
import argparse
import sys
import time

try:
    import cv2
    import numpy as np
except ImportError:
    print("Install: pip install opencv-python numpy", file=sys.stderr)
    sys.exit(1)

# On macOS, use AVFoundation so external cameras (e.g. phone) work
_CAP = cv2.CAP_AVFOUNDATION if sys.platform == "darwin" else cv2.CAP_ANY


# Granular wavelength bands (nm). Each band is a weighted sum of R,G,B approximating
# that part of the visible spectrum (camera has only 3 channels, so these are proxies).
BANDS = [
    ("400-450nm", 0.1, 0.2, 0.9),   # violet
    ("450-495nm", 0.05, 0.2, 0.95),  # blue
    ("495-520nm", 0.05, 0.5, 0.85),  # blue-green
    ("520-565nm", 0.1, 0.95, 0.2),   # green
    ("565-590nm", 0.6, 0.85, 0.1),   # yellow
    ("590-625nm", 0.85, 0.5, 0.05),  # orange
    ("625-700nm", 0.95, 0.15, 0.05), # red
]


def rgb_to_bands(r, g, b):
    """Convert R,G,B to granular wavelength-band proxies (0-255 scale). Returns list of (name, value)."""
    r, g, b = float(r), float(g), float(b)
    out = []
    for name, wr, wg, wb in BANDS:
        wsum = wr + wg + wb
        val = (wr * r + wg * g + wb * b) / wsum if wsum > 0 else 0.0
        out.append((name, val))
    return out


def get_roi_rgb(frame, roi_frac=0.4):
    """Mean R, G, B in center ROI (OpenCV BGR). Returns (r, g, b), brightness."""
    h, w = frame.shape[:2]
    x1 = int(w * (0.5 - roi_frac / 2))
    x2 = int(w * (0.5 + roi_frac / 2))
    y1 = int(h * (0.5 - roi_frac / 2))
    y2 = int(h * (0.5 + roi_frac / 2))
    roi = frame[y1:y2, x1:x2]
    if roi.size == 0:
        return 0.0, 0.0, 0.0, 0.0
    b, g, r = cv2.split(roi)
    r_mean = float(np.mean(r))
    g_mean = float(np.mean(g))
    b_mean = float(np.mean(b))
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    bright = float(np.mean(gray))
    return r_mean, g_mean, b_mean, bright


def draw_overlay(frame, r, g, b, bright, bands=None):
    """Draw R, G, B, brightness and optional bands on frame (for --show)."""
    h, w = frame.shape[:2]
    font = cv2.FONT_HERSHEY_SIMPLEX
    scale = min(h, w) / 800
    thick = max(1, int(2 * scale))
    y0 = int(40 * scale)
    line_h = int(28 * scale)
    for i, (label, val) in enumerate([("R", r), ("G", g), ("B", b), ("bright", bright)]):
        cv2.putText(frame, f"{label}={val:.0f}", (20, y0 + i * line_h), font, scale * 0.9, (0, 255, 0), thick)
    if bands:
        for i, (name, val) in enumerate(bands):
            cv2.putText(frame, f"{name}={val:.0f}", (20, y0 + (4 + i) * line_h), font, scale * 0.75, (0, 255, 0), thick)
    # Center ROI rectangle
    roi_frac = 0.4
    x1 = int(w * (0.5 - roi_frac / 2))
    x2 = int(w * (0.5 + roi_frac / 2))
    y1 = int(h * (0.5 - roi_frac / 2))
    y2 = int(h * (0.5 + roi_frac / 2))
    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), max(1, thick))
    return frame


def main():
    parser = argparse.ArgumentParser(
        description="Read R, G, B and brightness from camera. Use --rear for iPhone rear camera (as webcam)."
    )
    parser.add_argument(
        "camera_index",
        nargs="?",
        type=int,
        default=None,
        help="Camera device index (0=default, 1=phone as webcam). Ignored if --rear.",
    )
    parser.add_argument(
        "--rear",
        "-r",
        action="store_true",
        help="Use camera index 1 (phone as webcam). Select rear camera in Iriun/Camo.",
    )
    parser.add_argument("--watch", "-w", action="store_true", help="Live readout until Ctrl+C")
    parser.add_argument(
        "--stream",
        "-s",
        action="store_true",
        help="Stream CSV lines: timestamp,R,G,B,brightness (one per frame, Ctrl+C to stop)",
    )
    parser.add_argument(
        "--show",
        action="store_true",
        help="Show live video window with R,G,B overlay (with --watch or --stream)",
    )
    parser.add_argument(
        "--nir",
        "-n",
        action="store_true",
        help="Broad NIR proxy: report mean intensity from center ROI. Attach an IR pass filter (e.g. Hoya R72, 720 nm) to the camera so the sensor sees mostly NIR.",
    )
    parser.add_argument(
        "--header-every",
        type=int,
        default=0,
        metavar="N",
        help="In --stream: repeat CSV header every N data rows (0=once at start, 1=above every row). Default 0.",
    )
    parsed = parser.parse_args()

    cam_index = 1 if parsed.rear else (parsed.camera_index if parsed.camera_index is not None else 0)
    stream_mode = parsed.stream
    watch_mode = parsed.watch
    show_window = parsed.show
    nir_mode = parsed.nir
    header_every = max(0, parsed.header_every)

    cap = cv2.VideoCapture(cam_index, _CAP)
    if not cap.isOpened() and cam_index != 0:
        cap = cv2.VideoCapture(cam_index, cv2.CAP_ANY)
    if not cap.isOpened():
        print("Error: Could not open camera.", file=sys.stderr)
        print("Try: python list_cameras.py  to see available indices.", file=sys.stderr)
        if parsed.rear:
            print("For --rear: use phone as webcam (Iriun/Camo) and select rear camera on the phone.", file=sys.stderr)
        sys.exit(1)

    cap.read()  # warm-up

    band_names = [b[0] for b in BANDS]

    if stream_mode:
        if nir_mode:
            stream_header = "timestamp,NIR_proxy_broad"
        else:
            stream_header = "timestamp,R,G,B,brightness," + ",".join(band_names)
        print(stream_header, flush=True)
        try:
            t0 = time.perf_counter()
            row_count = 0
            while True:
                ok, frame = cap.read()
                if ok and frame is not None:
                    if header_every > 0 and row_count > 0 and row_count % header_every == 0:
                        print(stream_header, flush=True)
                    r, g, b, bright = get_roi_rgb(frame)
                    t = time.perf_counter() - t0
                    if nir_mode:
                        print(f"{t:.4f},{bright:.2f}", flush=True)
                    else:
                        bands = rgb_to_bands(r, g, b)
                        band_vals = ",".join(f"{v:.2f}" for _, v in bands)
                        print(f"{t:.4f},{r:.2f},{g:.2f},{b:.2f},{bright:.2f},{band_vals}", flush=True)
                    row_count += 1
                    if show_window:
                        bands = rgb_to_bands(r, g, b) if not nir_mode else []
                        draw_overlay(frame, r, g, b, bright, bands if not nir_mode else None)
                        cv2.imshow("NIR proxy (broad)" if nir_mode else "Color stream (rear)", frame)
                        if cv2.waitKey(1) & 0xFF == ord("q"):
                            break
                time.sleep(0.02)
        except KeyboardInterrupt:
            pass
        if show_window:
            cv2.destroyAllWindows()
        cap.release()
        return

    if watch_mode:
        if nir_mode:
            print("Broad NIR proxy (center ROI). Use with IR pass filter on camera (e.g. Hoya R72). Ctrl+C to stop.")
        elif parsed.rear:
            print("Live color readout from rear camera (center of frame). Ctrl+C to stop.")
        else:
            print("Live color readout (center of frame). Ctrl+C to stop.")
        if not nir_mode:
            print("R G B bright | wavelength bands (nm): " + " | ".join(band_names))
        print("-" * 60)
        try:
            while True:
                ok, frame = cap.read()
                if ok and frame is not None:
                    r, g, b, bright = get_roi_rgb(frame)
                    if nir_mode:
                        print(f"\r  NIR_proxy (broad) = {bright:5.1f}   ", end="", flush=True)
                    else:
                        bands = rgb_to_bands(r, g, b)
                        band_str = "  ".join(f"{v:5.1f}" for _, v in bands)
                        print(f"\r  R={r:5.1f} G={g:5.1f} B={b:5.1f} bright={bright:5.1f}  |  {band_str}   ", end="", flush=True)
                    if show_window:
                        bands = rgb_to_bands(r, g, b) if not nir_mode else []
                        draw_overlay(frame, r, g, b, bright, bands if not nir_mode else None)
                        cv2.imshow("NIR proxy (broad)" if nir_mode else "Color stream", frame)
                        if cv2.waitKey(1) & 0xFF == ord("q"):
                            break
                time.sleep(0.05)
        except KeyboardInterrupt:
            print("\nStopped.")
        if show_window:
            cv2.destroyAllWindows()
        cap.release()
        return

    # Single read
    ok, frame = cap.read()
    cap.release()
    if not ok or frame is None:
        print("Error: No frame from camera.", file=sys.stderr)
        sys.exit(1)
    r, g, b, bright = get_roi_rgb(frame)
    if nir_mode:
        print("Center ROI (one frame) — broad NIR proxy (use with IR pass filter on camera):")
        print(f"  NIR_proxy (broad) = {bright:.1f}")
        return
    bands = rgb_to_bands(r, g, b)
    print("Center ROI (one frame):")
    print(f"  R = {r:.1f}   G = {g:.1f}   B = {b:.1f}   brightness = {bright:.1f}")
    print("  Wavelength bands (proxies from R,G,B):")
    for name, val in bands:
        print(f"    {name}: {val:.1f}")


if __name__ == "__main__":
    main()
