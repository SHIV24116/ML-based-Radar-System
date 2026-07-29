# Radar Object Detection Dashboard

Run from the project root:

```powershell
python "zz_web_dashboard\server.py"
```

Open:

```text
http://127.0.0.1:8000
```

## Connected Components

The dashboard is connected to these project modules:

- `Simulation/generate_synthetic_dataset.py` for software-only radar recordings.
- `ML/compare_models.py` and `ML/train_svm.py` for model comparison and training.
- `ML/feature_extraction.py` for radar-only ML feature extraction.
- `DSP/radar_dsp.py` for FFT, STFT, filtering, Doppler frequency, and radar speed magnitude.
- `Data Collection/serial_logger.py` behavior for raw ESP32 ADC recording.
- `Firmware/ESP32_Main.ino` serial telemetry format for final live ultrasonic results.

## Live Detection Modes

### Simulated Playback

Uses saved CSV recordings from `dataset_simulated` or `dataset`, runs radar ML prediction, and creates simulated ultrasonic presence values so the final UI can be tested without hardware.

Displayed fields:

- Presence
- Detected class
- Confidence
- Distance
- Ultrasonic speed
- Radar speed magnitude
- Motion direction
- Samples seen
- Recent result history
- Green circular live presence map

### ESP32 Serial / Final Telemetry

This mode accepts two serial formats:

Raw ADC logger format:

```text
2048
2051
2044
```

Final firmware telemetry format:

```text
object=Human,confidence=0.974,distance_m=2.38,speed_mps=0.84,motion=Approaching
```

In the final telemetry format, `speed_mps` is treated as ultrasonic-derived live speed. The dashboard uses it for the ultrasonic speed field and the green circular map.

## Green Circular Map

The map is driven by ultrasonic presence and distance:

- No object: marker hidden and state shows no object.
- Object present: marker appears in green.
- Distance controls how far the marker appears from the center.
- Motion direction changes the marker angle between approaching and receding states.

## Signal And Features

The Signal & Features section now returns Doppler metrics plus the full radar-only ML feature vector used by the model. Ultrasonic values are not part of this feature vector.
