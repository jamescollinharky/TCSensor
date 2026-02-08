# Camera as light sensor

Use your computer’s camera (e.g. front-facing) as a simple light sensor in Python.

## Project structure

```
ldlsensor/
├── data/                  # Outputs (CSV, PNG) and reference inputs
│   └── reference/        # Reference JSON (cholesterol, fat NIR)
├── docs/                  # Papers and notes (Peuchant1987.pdf, reference.txt)
├── scripts/               # Executable entry points
│   ├── light_sensor.py        # Light sensor, time series, spectrogram
│   ├── color_reader.py        # Live R, G, B, wavelength bands, NIR proxy
│   ├── plot_color_stream.py   # Plot & FFT color/NIR stream CSV
│   ├── list_cameras.py        # List camera indices (phone-as-webcam)
│   ├── cholesterol_camera.py  # Camera cholesterol assay demo (enzymatic proxy)
│   ├── cholesterol_peuchant_nir.py  # Peuchant 1987 NIR (synthetic)
│   ├── pulse_ox_camera.py     # Pulse oximetry-style demo (camera)
│   ├── flashlight.py          # Mac fullscreen white (desktop)
│   └── test_camera_led.py     # Camera/LED test
├── src/
│   └── ldlsensor/        # Package (for shared code)
├── web/                   # HTML for phone screen/torch flash (Safari on iPhone)
├── requirements.txt
└── README.md
```

Run scripts from the project root, e.g. `python scripts/light_sensor.py`.

## Setup

```bash
pip install -r requirements.txt
```

On **macOS**, grant **Camera** access to Terminal (or your IDE) in **System Settings → Privacy & Security → Camera**, then run the script again.

### Using your phone as an external webcam

1. **Install a “phone as webcam” app** (phone + Mac on same Wi‑Fi or USB):
   - **[Iriun](https://iriun.com)** – free, works with iPhone and Android
   - **Camo** or **EpocCam** – iPhone
   - **DroidCam** – Android

2. **Start the app** on both your phone and your Mac so the phone appears as a camera.

3. **Find the phone’s camera index:**
   ```bash
   python scripts/list_cameras.py
   ```
   Use `python scripts/list_cameras.py --preview` to see a short preview from each camera and identify the phone.

4. **Use that index** in the scripts (e.g. if the phone is index `1`):
   ```bash
   python scripts/light_sensor.py 1 --watch
   python scripts/cholesterol_camera.py 1 --reference
   python scripts/pulse_ox_camera.py 1
   ```

### Flash the iPhone screen and read colors on the camera

You can’t control the iPhone’s **LED** flashlight from the Mac, but you can use the **iPhone screen** as a flashing light and read R, G, B with the camera:

1. **On the iPhone:** Open `web/flashlight_phone.html` in Safari (e.g. air-drop it or serve the project folder and open the URL). Tap the screen to start flashing white/black; choose frequency (Hz) or “Steady white”.
2. **On the Mac:** Point the camera at the iPhone screen (use the Mac camera, or the phone-as-webcam for the other device). Run:
   ```bash
   python scripts/color_reader.py --watch
   ```
   Use `python scripts/color_reader.py 1 --watch` if the camera you’re using is index 1.

   You’ll see live R, G, B and brightness; they’ll jump when the screen flashes white vs black.

### Camera + IR filter (broad NIR proxy)

To get a **broad near‑infrared (NIR) signal** from the camera:

1. **Attach an IR pass filter** to the lens (e.g. **Hoya R72**, 720 nm cutoff) so the sensor sees mostly NIR and little visible light.
2. Run the color reader in NIR mode (reports mean intensity from the center ROI as a single "NIR proxy" value):

   ```bash
   python scripts/color_reader.py --nir --watch
   python scripts/color_reader.py --nir --stream   # CSV: timestamp,NIR_proxy_broad
   python scripts/color_reader.py --nir            # single read
   ```

   Use `--rear` if the filtered camera is your phone used as a webcam:  
   `python scripts/color_reader.py --rear --nir --watch`

This gives one broad NIR band, not the multi‑wavelength NIR used in lab methods (e.g. Peuchant). For multi‑wavelength NIR you need a dedicated NIR spectrometer or filtered sensor.

## Usage

**Single reading:**

```bash
python scripts/light_sensor.py
```

**Continuous (live) light level:**

```bash
python scripts/light_sensor.py --watch
```

**Time series (record then plot):**

```bash
# Record until Ctrl+C (samples every 1 s), then save CSV + show plot
python scripts/light_sensor.py --record

# Record for 60 seconds, sample every 0.5 s
python scripts/light_sensor.py --record --duration 60 --interval 0.5

# Plot an existing CSV (no camera)
python scripts/light_sensor.py --plot
python scripts/light_sensor.py --plot my_data.csv
```

Recorded data is saved in `data/` as `light_sensor_timeseries.csv` (columns: `timestamp`, `brightness`). Each record produces a time series plot (`light_sensor_timeseries.png`) and a **spectrogram** (`light_sensor_timeseries_spectrogram.png`): time vs frequency, so you can see periodic flashing or flicker.

**Flash + spectrogram (point camera at screen):**

The camera’s LED isn’t software-controllable. Use the **screen as a flashing light**: the script flashes the screen white/black at a chosen frequency while recording. Point the camera at the screen.

```bash
# Flash at 2 Hz for 10 s, record at ~30 Hz, then show time series + spectrogram
python scripts/light_sensor.py --record --flash 2 --duration 10

# Flash at 5 Hz for 6 s
python scripts/light_sensor.py --record --flash 5 --duration 6
```

The spectrogram will show a band at the flash frequency (e.g. 2 Hz or 5 Hz).

**Plot spectrogram from an existing CSV (no camera):**

```bash
python scripts/light_sensor.py --spectrogram
python scripts/light_sensor.py --spectrogram my_data.csv
```

**Use a different camera** (e.g. front camera as index 1):

```bash
python scripts/light_sensor.py 1
python scripts/light_sensor.py 1 --watch
python scripts/light_sensor.py 1 --record
```

Output: brightness 0–255 and 0–100%. In `--watch` mode you get a simple bar and updating values.

### Test pulse oximeter (camera PPG)

A **test pulse oximeter** uses the camera in reflectance mode (like [pulse oximetry](https://en.wikipedia.org/wiki/Pulse_oximetry)): place your finger over the camera lens so that light reflects from the tissue. The script estimates **pulse (BPM)** from the PPG waveform and an **uncalibrated SpO2-like value** from the ratio of red vs green channel pulsations. **Not for medical use**; for testing and education only.

```bash
python scripts/pulse_ox_camera.py
```

Use good ambient light (or the screen). Hold your finger still for at least 5–10 seconds.

### Camera cholesterol assay demo (Peuchant-style)

A **camera-based cholesterol assay demo** inspired by the enzymatic method (e.g. [Peuchant 1987](https://www.degruyter.com/document/doi/10.1515/cclm.1987.25.12.915)): cholesterol esterase + cholesterol oxidase + peroxidase produce a colored quinoneimine product read at ~500 nm. This script uses the camera’s **red channel** as a proxy for that absorbance and reports an uncalibrated **absorbance proxy** and **cholesterol index**. **Not for medical use**; the camera is not a spectrophotometer and values require calibration with known standards.

1. Capture a **reference (blank)** — point camera at blank strip or white card:
   ```bash
   python scripts/cholesterol_camera.py --reference
   ```
2. **Measure** a sample (test strip or cuvette) using the saved reference:
   ```bash
   python scripts/cholesterol_camera.py --measure
   ```
3. **Live readout** (with reference loaded):
   ```bash
   python scripts/cholesterol_camera.py --watch
   ```

### Peuchant 1987 NIR methodology (synthetic)

[Peuchant et al. (Anal. Chem. 1987)](https://pubs.acs.org/doi/10.1021/ac00142a017) measured serum cholesterol by **near-infrared reflectance** at 7 wavelengths (1445, 1680, 1722, 1734, 1940, 2190, 2208 nm) with the formula **TC = bias + Σ aᵢ log(1/Rᵢ)**. The script **cholesterol_peuchant_nir.py** uses **synthetic** reflectance values (no real NIR hardware) to demonstrate the calculation and estimates **LDL** via the Friedewald equation (TC − HDL − TG/2.2 in mmol/L). **Not for medical use.**

```bash
python scripts/cholesterol_peuchant_nir.py
```

Output: table of synthetic TC and LDL (mmol/L and mg/dL), and `data/cholesterol_peuchant_synthetic.json` with reflectance and lipid values. Run with `--fat-test` to apply the formula to `data/reference/fat_nir_reference.json`.
