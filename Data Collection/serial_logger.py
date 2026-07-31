"""Record labeled Doppler radar ADC samples from the ESP32 serial stream.

Example:
    python "Data Collection/serial_logger.py" --port COM5 --label human --seconds 10
"""

from __future__ import annotations

import argparse
import csv
import time
from datetime import datetime
from pathlib import Path

import serial


ADC_MAX = 4095b  
ADC_VREF = 3.3


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Log ESP32 radar ADC samples to CSV.")
    parser.add_argument("--port", default="COM5", help="Serial port used by the ESP32.")
    parser.add_argument("--baud", type=int, default=115200, help="Serial baud rate.")
    parser.add_argument("--label", required=True, help="Class label, for example human or fan.")
    parser.add_argument("--seconds", type=float, default=10.0, help="Recording duration.")
    parser.add_argument("--out-dir", default="dataset", help="Dataset root folder.")
    return parser.parse_args()


def adc_to_voltage(adc_value: int) -> float:
    return adc_value * (ADC_VREF / ADC_MAX)


def main() -> None:
    args = parse_args()
    label = args.label.lower().strip()
    label_dir = Path(args.out_dir) / label
    label_dir.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = label_dir / f"{label}_{stamp}.csv"

    print(f"Opening {args.port} at {args.baud} baud...")
    rows: list[tuple[float, int, float]] = []

    with serial.Serial(args.port, args.baud, timeout=1) as ser:
        time.sleep(2)
        ser.reset_input_buffer()
        start = time.perf_counter()

        while time.perf_counter() - start < args.seconds:
            raw_line = ser.readline().decode(errors="ignore").strip()
            if not raw_line.isdigit():
                continue

            timestamp_s = time.perf_counter() - start
            adc_value = int(raw_line)
            rows.append((timestamp_s, adc_value, adc_to_voltage(adc_value)))

    with output_path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["time_s", "adc", "voltage"])
        writer.writerows(rows)

    print(f"Saved {len(rows)} samples to {output_path}")


if __name__ == "__main__":
    main()
