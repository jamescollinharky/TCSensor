# NIR multi-band sensor (Arduino + Python)

Arduino Uno controls multi-band NIR LEDs; cycle through bands and merge readings into one time series. Run scripts from the **project root**; they resolve `data/` and `data/reference/` relative to the repo.

## Project structure

```
ldlsensor/
├── data/                  # Outputs (CSV, PNG, JSON) and reference inputs
│   └── reference/         # Reference JSON (cholesterol, fat NIR)
├── docs/                  # Papers and notes (Peuchant1987.pdf, reference.txt)
├── arduino/
│   └── multi_band_cycle/  # Sketch: cycle LEDs, output merged CSV
├── scripts/               # Executable entry points
│   ├── capture_multi_band_serial.py  # Serial → CSV (Option B)
│   ├── cholesterol_peuchant_nir.py   # Peuchant 1987 NIR (synthetic)
│   ├── plot_pulse_ox_fft.py          # FFT on color-band CSV
│   ├── yom_series_fft.py             # Parse Arduino dump, FFT, bandpass
│   ├── validate_peuchant_nir.py      # Validate Peuchant formula
│   └── counts_to_absorption.py      # Counts → absorption / reflectance
├── src/
│   └── ldlsensor/         # Package
├── requirements.txt
└── README.md
```

## Setup

```bash
pip install -r requirements.txt
```

## Arduino multi-band cycle

1. Open `arduino/multi_band_cycle/multi_band_cycle.ino` in the Arduino IDE and upload to an Uno.
2. The sketch cycles through LEDs (1300, 1460, 1650, 1720, 1900 nm) one at a time and prints one CSV row per cycle: `ms,1300,1460,1650,1720,1900`.

**Capture (Option A)** — Serial Monitor at 9600 baud: save or copy the output; it’s already merged CSV.

**Capture (Option B)** — Python script:

```bash
# List serial ports
python scripts/capture_multi_band_serial.py -l

# Capture to default data/multi_band_timeseries.csv
python scripts/capture_multi_band_serial.py /dev/cu.usbmodem14101

# Custom output path
python scripts/capture_multi_band_serial.py /dev/cu.usbmodem14101 -o data/my_capture.csv
```

Stop with Ctrl+C. Requires `pyserial` (in `requirements.txt`).

## Other scripts

### Peuchant 1987 NIR (synthetic)

[Peuchant et al.](https://pubs.acs.org/doi/10.1021/ac00142a017) measured serum cholesterol by NIR reflectance at 7 wavelengths. The script uses **synthetic** reflectance to demonstrate TC/LDL via the formula and Friedewald. **Not for medical use.**

```bash
python scripts/cholesterol_peuchant_nir.py
```

Output: table of synthetic TC and LDL; `data/cholesterol_peuchant_synthetic.json`.

### FFT and validation

- **plot_pulse_ox_fft.py** — FFT on a color-band CSV (e.g. `data/pulse_ox_color_timeseries.csv`): elapsed_sec, R, G, B.
- **yom_series_fft.py** — Parse Arduino serial dump (e.g. `data/yom_arduino_series_raw.txt`), save CSV, FFT, bandpass plots.
- **validate_peuchant_nir.py** — Validate Peuchant NIR formula on synthetic data.
- **counts_to_absorption.py** — Convert counts to absorption and reflectance for the 7-wavelength chain.

See `docs/reference.txt` for a compact command list.
