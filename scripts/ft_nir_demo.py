#!/usr/bin/env python3
"""
FT-NIR demo: spectrum ↔ interferogram via Fourier transform.

Shows how an FT spectrometer works in principle:
  1. Synthetic spectrum B(σ) vs wavenumber σ (cm⁻¹) — e.g. a few peaks in the NIR.
  2. Compute interferogram I(δ) = ∫ B(σ) cos(2π σ δ) dσ  (OPD δ in cm).
  3. Recover spectrum by FFT of interferogram: B_recovered ∝ FFT(I).

Peuchant 1987 wavelengths (nm) → wavenumber (cm⁻¹): σ = 1e7/λ.
  2208 nm → 4530,  2190 → 4566,  1940 → 5155,  1734 → 5767,
  1722 → 5807,  1445 → 6920 cm⁻¹.

Usage:
  python scripts/ft_nir_demo.py
  python scripts/ft_nir_demo.py --no-show  # save PNG only
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np


# Peuchant 1987 wavelengths (nm) and approximate wavenumbers (cm^-1)
PEUCHANT_NM = (2208, 2190, 1940, 1734, 1722, 1445, 1680)
PEUCHANT_CM1 = tuple(1e7 / lam for lam in PEUCHANT_NM)  # 4530, 4566, 5155, 5767, 5807, 6920, 5952


def make_synthetic_spectrum(
    sigma: np.ndarray,
    peaks_cm1: tuple[float, ...] = PEUCHANT_CM1,
    width_cm1: float = 40.0,
    amplitude: float = 1.0,
) -> np.ndarray:
    """Gaussian peaks at given wavenumbers (cm^-1)."""
    B = np.zeros_like(sigma, dtype=float)
    for peak in peaks_cm1:
        B += amplitude * np.exp(-((sigma - peak) ** 2) / (2 * width_cm1**2))
    return B


def spectrum_to_interferogram(
    sigma: np.ndarray,
    B: np.ndarray,
    delta: np.ndarray,
) -> np.ndarray:
    """Compute I(δ) = ∫ B(σ) cos(2π σ δ) dσ (numerical integral)."""
    d_sigma = np.diff(sigma)
    d_sigma = np.append(d_sigma, d_sigma[-1])
    I = np.zeros(len(delta), dtype=float)
    for i, d in enumerate(delta):
        I[i] = np.sum(B * np.cos(2 * np.pi * sigma * d) * d_sigma)
    return I


def interferogram_to_spectrum(
    delta: np.ndarray,
    I: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Recover B(σ) from I(δ) via FFT.
    δ in cm → σ in cm^-1. Returns (sigma_recovered, B_recovered).
    """
    N = len(I)
    d_delta = np.median(np.diff(delta)) if N > 1 else delta[1] - delta[0]
    # FFT: k-th coefficient corresponds to wavenumber σ_k = k / (N * d_delta) cm^-1
    I_fft = np.fft.rfft(I)
    k = np.arange(len(I_fft))
    sigma_fft = k / (N * d_delta)
    # Scale: B(σ) ≈ 2 * d_delta * Re(FFT(I)) for real spectrum
    B_recovered = 2 * d_delta * np.real(I_fft)
    B_recovered[0] *= 0.5  # DC
    return sigma_fft, B_recovered


def main() -> None:
    parser = argparse.ArgumentParser(description="FT-NIR demo: spectrum ↔ interferogram.")
    parser.add_argument("--no-show", action="store_true", help="Save PNG only, no plot window")
    parser.add_argument("--out", type=Path, default=None, help="Output PNG path (default: data/figures/ft_nir_demo.png)")
    args = parser.parse_args()

    # Wavenumber grid (NIR: ~4000–7500 cm^-1 ≈ 1333–2500 nm)
    sigma_min, sigma_max = 4000.0, 7500.0
    n_sigma = 3501
    sigma = np.linspace(sigma_min, sigma_max, n_sigma)
    d_sigma = sigma[1] - sigma[0]

    # Synthetic spectrum with peaks near Peuchant wavenumbers
    B = make_synthetic_spectrum(sigma, peaks_cm1=PEUCHANT_CM1, width_cm1=50.0, amplitude=1.0)

    # OPD grid (δ in cm). Resolution Δσ ≈ 1/(2*δ_max). Nyquist σ_nyq = 1/(2*d_δ).
    delta_max = 0.08  # cm (0.8 mm) → resolution ~6 cm^-1
    sigma_nyq = 1.0 / (2 * (delta_max / 2000))  # want Nyquist > sigma_max
    n_delta = 2048
    delta = np.linspace(0, delta_max, n_delta, endpoint=False)
    d_delta = delta[1] - delta[0]

    # Spectrum → interferogram
    I = spectrum_to_interferogram(sigma, B, delta)

    # Interferogram → spectrum (recovery)
    sigma_rec, B_rec = interferogram_to_spectrum(delta, I)

    # Trim recovered spectrum to same range for comparison
    mask = (sigma_rec >= sigma_min) & (sigma_rec <= sigma_max)
    sigma_rec = sigma_rec[mask]
    B_rec = B_rec[mask]
    # Normalize recovered to similar scale as original (FFT scaling is arbitrary)
    if np.max(np.abs(B_rec)) > 1e-10:
        B_rec = B_rec * (np.max(B) / np.max(B_rec))

    # Plot
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(3, 1, figsize=(8, 8))

    axes[0].plot(sigma, B, color="C0", linewidth=1.5, label="Original B(σ)")
    axes[0].set_ylabel("Intensity (arb.)")
    axes[0].set_xlabel("Wavenumber σ (cm⁻¹)")
    axes[0].set_title("1. Synthetic NIR spectrum (peaks near Peuchant wavenumbers)")
    axes[0].legend(loc="upper right")
    axes[0].grid(True, alpha=0.3)
    axes[0].set_xlim(sigma_min, sigma_max)

    axes[1].plot(delta * 1e4, I, color="C1", linewidth=0.8)  # δ in µm for readability
    axes[1].set_ylabel("I(δ)")
    axes[1].set_xlabel("Optical path difference δ (µm)")
    axes[1].set_title("2. Interferogram I(δ) = ∫ B(σ) cos(2π σ δ) dσ")
    axes[1].grid(True, alpha=0.3)

    axes[2].plot(sigma, B, color="C0", alpha=0.7, linewidth=1.5, label="Original")
    axes[2].plot(sigma_rec, B_rec, color="C2", alpha=0.8, linewidth=1, linestyle="--", label="Recovered (FFT of I)")
    axes[2].set_ylabel("Intensity (arb.)")
    axes[2].set_xlabel("Wavenumber σ (cm⁻¹)")
    axes[2].set_title("3. Recovered spectrum from interferogram (FT-NIR principle)")
    axes[2].legend(loc="upper right")
    axes[2].grid(True, alpha=0.3)
    axes[2].set_xlim(sigma_min, sigma_max)

    fig.tight_layout()

    out = args.out or Path(__file__).resolve().parent.parent / "data" / "figures" / "ft_nir_demo.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=150)
    print(f"Saved {out}")
    if not args.no_show:
        plt.show()


if __name__ == "__main__":
    main()
