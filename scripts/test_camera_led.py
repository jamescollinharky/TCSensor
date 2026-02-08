#!/usr/bin/env python3
"""
Test whether the camera's status LED turns on when the camera is in use.
The LED is not software-controllable; this only checks if it turns on
when we open the camera and capture frames.
"""
import sys
import time

try:
    import cv2
except ImportError:
    print("Install opencv-python: pip install opencv-python", file=sys.stderr)
    sys.exit(1)


def main():
    print("Opening camera for 5 seconds. Check if the camera LED turns on.")
    print("(On many Macs it's a small green dot near the camera lens.)")
    print("-" * 50)

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        cap = cv2.VideoCapture(1)
    if not cap.isOpened():
        print("Error: Could not open camera.", file=sys.stderr)
        sys.exit(1)

    # Warm-up frame
    cap.read()

    for i in range(5):
        ok, frame = cap.read()
        status = "OK" if ok else "fail"
        print(f"  {i + 1}s  capture {status}  (LED should be on if your hardware has one)")
        time.sleep(1)

    cap.release()
    print("-" * 50)
    print("Camera closed. Did the LED turn on while the camera was open?")
    print("Note: The LED cannot be controlled by software; it is tied to camera activity.")


if __name__ == "__main__":
    main()
