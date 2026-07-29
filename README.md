# Radar Object Detection And Classification System

Final project repository for a real-time embedded radar object detection and classification system using CDM324 Doppler radar, MCP6002 signal conditioning, ESP32, HC-SR04 ultrasonic verification, SSD1306 OLED display, and machine learning.

## Final Runtime

The ESP32 continuously samples the conditioned radar waveform, keeps a rolling radar frame, checks ultrasonic presence every `50 ms`, and only runs classification when an object is confirmed. ML uses radar-only features. Ultrasonic distance, speed, presence, and motion direction are used only for live verification and display.

Final OLED output:

```text
Object     : Human
Confidence : 97.4%
Distance   : 2.38 m
Speed      : 0.84 m/s
Motion     : Approaching
```

## Hardware

- CDM324 radar output through AC coupling, virtual ground, MCP6002 amplification, and low-pass filtering to ESP32 `GPIO34`.
- HC-SR04 `TRIG` to `GPIO5` and `ECHO` through a voltage divider to `GPIO18`.
- SSD1306 OLED I2C on `GPIO21` and `GPIO22`.
- ESP32 ADC is configured as `12-bit` with `ADC_11db` attenuation.

## Final Folder Structure

```text
PR project/
  Firmware/
    ESP32_Main.ino
    Config.h
    RadarADC.h/.cpp
    Ultrasonic.h/.cpp
    OLED.h/.cpp
    FeatureExtraction.h/.cpp
    MLInference.h/.cpp
    CircularBuffer.h/.cpp
    SignalProcessing.h/.cpp
    TensorArena.h

  Data Collection/
    serial_logger.py

  DSP/
    radar_dsp.py
    preprocess.py

  ML/
    feature_extraction.py
    train_svm.py
    compare_models.py
    live_predict.py

  Simulation/
    generate_synthetic_dataset.py

  dataset/
  dataset_simulated/
  models/
  outputs/
  docs/
  tools/
  zz_web_dashboard/
```

`ESP32 codes/adc_logger.ino` is kept as the simple development sketch for collecting raw radar ADC samples.

## Firmware Upload

Open `Firmware/ESP32_Main.ino` in Arduino IDE and install these libraries:

- Adafruit SSD1306
- Adafruit GFX
- Wire

Then upload to the ESP32. Runtime constants are in `Firmware/Config.h`.

## Python Setup

```powershell
python -m pip install -r requirements.txt
python "tools/check_environment.py"
```

## Collect Real Radar Data

Upload `ESP32 codes/adc_logger.ino` when recording raw training data, then run:

```powershell
python "Data Collection/serial_logger.py" --port COM5 --label human --seconds 10
python "Data Collection/serial_logger.py" --port COM5 --label fan --seconds 10
python "Data Collection/serial_logger.py" --port COM5 --label background --seconds 10
```

Recommended final classes are `human`, `dog`, `fan`, and `vehicle`; keep `background` recordings for no-object/noise conditions.

## Train And Compare Models

Software-only test:

```powershell
python "Simulation/generate_synthetic_dataset.py" --recordings-per-class 30
python "ML/compare_models.py" --dataset dataset_simulated
```

Real hardware training:

```powershell
python "ML/compare_models.py" --dataset dataset
```

The best model bundle is saved at `models/best_supervised_model.pkl`. Reports and plots are saved under `outputs/model_comparison/`.

## Live Development Demo

```powershell
python "ML/live_predict.py" --port COM5
```

This Python demo predicts class and radar speed magnitude from serial ADC samples. The final embedded firmware adds ultrasonic presence, distance, speed, and motion direction on the OLED.

## Web Dashboard

```powershell
python "zz_web_dashboard\server.py"
```

Open:

```text
http://127.0.0.1:8000
```

The dashboard supports simulation, dataset status, model comparison, signal analysis, serial recording, and live development prediction.

## Documentation

- `docs/software_architecture.md`
- `docs/Dataset_Guide.md`
- `docs/ML_Model_Report.md`
- `docs/User_Manual.md`
- `docs/project_notes.md`
- `docs/model_strategy.md`

## Final Design Rules

- Radar sampling is continuous.
- Ultrasonic is only live presence verification and display support.
- ML uses only radar-derived features.
- Firmware is modular; `ESP32_Main.ino` only orchestrates.
- Constants live in `Firmware/Config.h`.
- Scheduling uses `millis()`/`micros()` instead of blocking loop delays.
