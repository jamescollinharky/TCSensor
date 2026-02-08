#!/usr/bin/env python3
"""
List available camera devices (indices 0–9). Use this to find your phone's
index when it's connected as an external webcam (e.g. via Iriun, DroidCam, Camo).

Run:  python list_cameras.py
      python list_cameras.py --preview   # show short preview from each camera
"""
import argparse
import sys

try:
    import cv2
except ImportError:
    print("Install opencv-python: pip install opencv-python", file=sys.stderr)
    sys.exit(1)

# On macOS, use AVFoundation so we see built-in + external (e.g. phone) cameras
_CAP = cv2.CAP_AVFOUNDATION if sys.platform == "darwin" else cv2.CAP_ANY


def main():
    parser = argparse.ArgumentParser(
        description="List available cameras. Use to find your phone's index when used as external webcam."
    )
    parser.add_argument(
        "--preview",
        "-p",
        action="store_true",
        help="Show a 2s preview from each working camera (press any key to skip)",
    )
    parsed = parser.parse_args()

    print("Scanning camera indices 0–9...")
    print("-" * 50)

    available = []
    for i in range(10):
        cap = cv2.VideoCapture(i, _CAP)
        if cap.isOpened():
            ok, frame = cap.read()
            cap.release()
            if ok and frame is not None:
                h, w = frame.shape[:2]
                available.append((i, w, h))
                print(f"  Camera {i}: OK  ({w}x{h})")
            else:
                cap = cv2.VideoCapture(i, _CAP)
                cap.release()
                print(f"  Camera {i}: opened but no frame")
        else:
            print(f"  Camera {i}: not available")

    print("-" * 50)
    if not available:
        print("No cameras found.")
        print("If using a phone as webcam: install Iriun (or DroidCam/Camo), start the app on phone and Mac, then run this again.")
        sys.exit(1)

    print(f"Use one of these indices in your scripts, e.g.:")
    print(f"  python light_sensor.py {available[0][0]} --watch")
    print(f"  python cholesterol_camera.py {available[0][0]} --watch")
    if len(available) > 1:
        print(f"  (Try index 1 or 2 for external/phone: python light_sensor.py 1 --watch)")

    if parsed.preview and available:
        print()
        for idx, w, h in available:
            print(f"Preview: camera {idx} (press any key to skip or continue)...")
            cap = cv2.VideoCapture(idx, _CAP)
            if not cap.isOpened():
                continue
            window = f"Camera {idx} (any key to skip)"
            cv2.namedWindow(window, cv2.WINDOW_NORMAL)
            for _ in range(60):  # ~2 s at 30 fps
                ok, frame = cap.read()
                if not ok or frame is None:
                    break
                cv2.imshow(window, frame)
                if cv2.waitKey(33) >= 0:
                    break
            cap.release()
            cv2.destroyWindow(window)
        cv2.destroyAllWindows()
        print("Done.")


if __name__ == "__main__":
    main()
