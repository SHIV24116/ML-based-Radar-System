# Radar Object Detection And Classification System

## Objective

This project detects moving objects using a CDM324 Doppler radar, verifies live presence with an HC-SR04 ultrasonic sensor, extracts radar-only signal features, runs ML classification, and displays object, confidence, distance, speed, and motion direction on an OLED.

## Runtime Flow

1. ESP32 boots and initializes radar ADC, ultrasonic pins, OLED, serial debug, and ML inference.
2. Radar ADC samples continuously into a circular buffer at `2000 Hz`.
3. Ultrasonic updates every `50 ms` to verify whether an object is within the configured distance range.
4. If no object is present, the OLED shows monitoring/waiting status.
5. If object presence is verified, the latest radar frame is copied from the rolling buffer.
6. Radar-only features are extracted from the copied frame.
7. ML inference predicts the object class and confidence.
8. OLED and serial debug show prediction, confidence, ultrasonic distance, ultrasonic speed, and motion direction.

## Module Map

- `Firmware/Config.h`: pins, sample rates, thresholds, buffer sizes, and debug flags.
- `Firmware/RadarADC.*`: non-stopping ADC acquisition and rolling frame access.
- `Firmware/CircularBuffer.*`: latest-frame storage for radar samples.
- `Firmware/Ultrasonic.*`: distance, speed, presence, and direction.
- `Firmware/FeatureExtraction.*`: mean, RMS, variance, energy, FFT peak, entropy, zero crossings, range, and spectral centroid.
- `Firmware/MLInference.*`: inference wrapper and current hardware bring-up fallback.
- `Firmware/OLED.*`: splash, waiting, object, and error screens.
- `Firmware/ESP32_Main.ino`: controller orchestration only.
- `ML/`: offline feature extraction, training, model comparison, and live development prediction.
- `DSP/`: shared signal processing utilities.
- `Data Collection/`: serial recording tool for labeled radar samples.
- `zz_web_dashboard/`: local demo dashboard for simulation, training, analysis, collection, and live prediction.

## ML Input Rule

The classifier input is only radar-derived features. Ultrasonic distance, speed, object presence, and motion direction are runtime values and must not be added to the feature CSV or model input vector.
