#!/usr/bin/env python3
"""
Convert ADC counts (bits) to absorption A = -log10(I / I0).
Reference: Beer-Lambert; AN4327 / project docs.
"""

import math

# Counts from serial output (user's data)
# 1720 nm band: (0, 0, 0, 255, 0) = 4th channel
COUNTS_1720 = [
    703, 725, 708, 725, 723, 723, 730, 724, 747, 723, 744, 727,
]

# 10-bit full scale as reference (use 1023 or provide a baseline I0)
I0 = 1023


def counts_to_absorption(count: float, reference: float) -> float:
    """A = -log10(I/I0). Clip ratio to avoid log(0)."""
    if reference <= 0:
        reference = 1.0
    ratio = count / reference
    ratio = max(1e-6, min(1.0, ratio))
    return -math.log10(ratio)


def main():
    print("Band: 1720 nm  |  A = -log10(I/1023)")
    print("Count  ->  Absorption")
    print("-" * 35)
    for c in COUNTS_1720:
        a = counts_to_absorption(c, I0)
        print(f"  {c:4d}   ->   {a:.4f}")
    print("-" * 35)
    print(f"Reference I0 = {I0} (10-bit max)")


if __name__ == "__main__":
    main()
