"""Run real-time radar classification from the ESP32 serial stream."""

from __future__ import annotations

import argparse
import pickle
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import serial

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ML_DIR = PROJECT_ROOT / "ML"
DSP_DIR = PROJECT_ROOT / "DSP"
for path in (ML_DIR, DSP_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from feature_extraction import extract_features_from_filtered_signal, estimate_motion_metrics  # noqa: E402
from radar_dsp import (  # noqa: E402
    adc_to_voltage,
    bandpass_filter,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Live radar ML prediction demo.")
    parser.add_argument("--port", default="COM5", help="Serial port used by ESP32.")
    parser.add_argument("--baud", type=int, default=115200, help="Serial baud rate.")
    parser.add_argument("--model", default="models/best_supervised_model.pkl", help="Trained model path.")
    parser.add_argument("--fs", type=float, default=2000.0, help="Sampling frequency in Hz.")
    parser.add_argument("--window-seconds", type=float, default=3.0, help="Samples per prediction window.")
    return parser.parse_args()


def predict_window(samples: list[int], bundle: dict, fs: float) -> tuple[str, float, float]:
    voltage = adc_to_voltage(np.asarray(samples, dtype=float))
    filtered = bandpass_filter(voltage, fs=fs)
    features = extract_features_from_filtered_signal(filtered, fs=fs)
    motion = estimate_motion_metrics(filtered, fs=fs)

    frame = pd.DataFrame([features], columns=bundle["feature_names"])
    model = bundle["model"]
    label = str(model.predict(frame)[0])
    confidence = float(np.max(model.predict_proba(frame))) if hasattr(model, "predict_proba") else 0.0
    return label, confidence, float(motion["radar_speed_mps"])


def main() -> None:
    args = parse_args()
    model_path = PROJECT_ROOT / args.model
    with model_path.open("rb") as f:
        bundle = pickle.load(f)
    window_size = int(args.fs * args.window_seconds)

    print(f"Loaded model: {model_path}")
    print("ML inputs are radar-only features.")
    print("Distance and motion direction are provided by the final ESP32 ultrasonic runtime.")
    print("Collecting live windows. Press Ctrl+C to stop.")

    samples: list[int] = []
    with serial.Serial(args.port, args.baud, timeout=1) as ser:
        time.sleep(2)
        ser.reset_input_buffer()
        while True:
            line = ser.readline().decode(errors="ignore").strip()
            if not line.isdigit():
                continue
            samples.append(int(line))

            if len(samples) >= window_size:
                label, confidence, speed_mps = predict_window(samples[-window_size:], bundle, args.fs)
                print(
                    f"class={label} confidence={confidence:.2f} "
                    f"radar_speed_magnitude={speed_mps:.2f} m/s"
                )
                samples = samples[-window_size // 2 :]


if __name__ == "__main__":
    main()
