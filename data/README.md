# Data directory layout

Organized by type of data:

| Directory    | Contents |
|-------------|----------|
| **raw/**    | Raw serial dumps from Arduino (e.g. multi-band 1720/940 nm, YOM series). `.txt` files. |
| **timeseries/** | Time series CSVs: pulse oximetry, light sensor, color stream, parsed multi-band (e.g. `*_1720_940.csv`), and capture outputs. |
| **processed/** | Derived test/validation data: `*_test_data.json` (e.g. YOM test, 1720 nm bandpass → reflectance). |
| **reference/** | Reference spectra and synthetic validation: `fat_nir_reference.json`, `cholesterol_reference.json`, `cholesterol_peuchant_synthetic.json`, `peuchant_1987_validation_synthetic.json`. |
| **figures/** | Plots and figures: FFT plots, bandpass plots, pulse ox, light sensor spectrograms, `ft_nir_demo.png`, etc. |

Scripts that read or write under `data/` use these paths (e.g. `scripts/yom_series_fft.py` reads `data/raw/yom_arduino_series_raw.txt`, writes to `data/timeseries/`, `data/figures/`, `data/processed/`).
