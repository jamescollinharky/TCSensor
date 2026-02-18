#!/usr/bin/env python3
"""
Capture multi-band time series from Arduino serial (multi_band_cycle.ino).
Reads at 9600 baud and appends each line to a CSV file.
Stop with Ctrl+C.
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DEFAULT_OUTPUT = DATA_DIR / "timeseries" / "multi_band_timeseries.csv"
BAUD = 9600


def list_ports():
    try:
        import serial.tools.list_ports
        ports = list(serial.tools.list_ports.comports())
        if not ports:
            print("No serial ports found.")
            return
        for p in ports:
            print(f"  {p.device}\t{p.description}")
    except Exception as e:
        print(f"Could not list ports: {e}")


def main():
    p = argparse.ArgumentParser(
        description="Capture Arduino multi-band serial output to CSV (Option B)."
    )
    p.add_argument(
        "port",
        nargs="?",
        default=None,
        help="Serial port (e.g. /dev/cu.usbmodem* or COM3). Omit to list ports.",
    )
    p.add_argument(
        "-o", "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output CSV path (default: {DEFAULT_OUTPUT})",
    )
    p.add_argument(
        "-l", "--list-ports",
        action="store_true",
        help="List available serial ports and exit.",
    )
    args = p.parse_args()

    if args.list_ports:
        list_ports()
        return 0

    if not args.port:
        print("Usage: python capture_multi_band_serial.py <port> [-o output.csv]")
        print("Use -l to list serial ports.")
        list_ports()
        return 1

    try:
        import serial
    except ImportError:
        print("Install pyserial: pip install pyserial")
        return 1

    args.output.parent.mkdir(parents=True, exist_ok=True)
    print(f"Port: {args.port} @ {BAUD} baud")
    print(f"Output: {args.output}")
    print("Capturing... Ctrl+C to stop.\n")

    try:
        ser = serial.Serial(args.port, BAUD, timeout=1.0)
    except Exception as e:
        print(f"Failed to open {args.port}: {e}")
        return 1

    line_count = 0
    try:
        with open(args.output, "a", newline="", encoding="utf-8") as f:
            while True:
                line = ser.readline()
                if not line:
                    continue
                try:
                    text = line.decode("utf-8").strip()
                except UnicodeDecodeError:
                    continue
                if not text:
                    continue
                f.write(text + "\n")
                f.flush()
                line_count += 1
                if line_count <= 2 or line_count % 100 == 0:
                    print(f"  {line_count} lines")
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        ser.close()

    print(f"Wrote {line_count} lines to {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
