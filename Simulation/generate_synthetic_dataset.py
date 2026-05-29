"""Generate simulated Doppler radar recordings while the hardware is not ready.

The synthetic data is not a replacement for real measurements. It exists so the
DSP, feature extraction, model comparison, and live-demo software can be tested
before the circuit is available.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path

import numpy as np


ADC_MAX = 4095
ADC_VREF = 3.3
MIDPOINT_V = 1.65


@dataclass(frozen=True)
class ClassProfile:
    label: str
    base_freq_range: tuple[float, float]
    amplitude_range: tuple[float, float]
    bursty: bool
    harmonic: bool


PROFILES = [
    ClassProfile("background", (12.0, 35.0), (0.005, 0.025), False, False),
    ClassProfile("fan", (90.0, 220.0), (0.045, 0.12), False, True),
    ClassProfile("human", (25.0, 120.0), (0.08, 0.24), True, False),
    ClassProfile("pet", (45.0, 180.0), (0.035, 0.12), True, False),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create simulated radar CSV recordings.")
    parser.add_argument("--out-dir", default="dataset_simulated", help="Output dataset root.")
    parser.add_argument("--classes", nargs="+", default=[p.label for p in PROFILES], help="Classes to create.")
    parser.add_argument("--recordings-per-class", type=int, default=30, help="CSV files per class.")
    parser.add_argument("--seconds", type=float, default=6.0, help="Recording length.")
    parser.add_argument("--fs", type=float, default=2000.0, help="Sampling frequency in Hz.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed.")
    return parser.parse_args()


def envelope(t: np.ndarray, rng: np.random.Generator, bursty: bool) -> np.ndarray:
    if not bursty:
        return 0.85 + 0.15 * np.sin(2 * np.pi * rng.uniform(0.2, 0.8) * t)

    env = np.zeros_like(t)
    burst_count = rng.integers(2, 5)
    for _ in range(burst_count):
        center = rng.uniform(t[0] + 0.4, t[-1] - 0.4)
        width = rng.uniform(0.18, 0.7)
        env += np.exp(-0.5 * ((t - center) / width) ** 2)
    env = env / max(float(np.max(env)), 1e-9)
    return 0.15 + 0.85 * env


def make_signal(profile: ClassProfile, t: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    base_freq = rng.uniform(*profile.base_freq_range)
    amplitude = rng.uniform(*profile.amplitude_range)

    if profile.label == "background":
        motion = rng.normal(0.0, amplitude, size=len(t))
    else:
        modulation = 1.0 + 0.12 * np.sin(2 * np.pi * rng.uniform(0.2, 1.2) * t)
        phase_jitter = 0.15 * np.sin(2 * np.pi * rng.uniform(0.4, 2.5) * t)
        motion = np.sin(2 * np.pi * base_freq * modulation * t + phase_jitter)
        if profile.harmonic:
            motion += 0.45 * np.sin(2 * np.pi * 2.0 * base_freq * t)
        motion *= amplitude * envelope(t, rng, profile.bursty)

    drift = 0.015 * np.sin(2 * np.pi * rng.uniform(0.05, 0.25) * t)
    noise = rng.normal(0.0, rng.uniform(0.008, 0.025), size=len(t))
    voltage = MIDPOINT_V + drift + motion + noise
    return np.clip(voltage, 0.0, ADC_VREF)


def voltage_to_adc(voltage: np.ndarray) -> np.ndarray:
    return np.rint(voltage * ADC_MAX / ADC_VREF).astype(int)


def write_recording(path: Path, t: np.ndarray, voltage: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    adc = voltage_to_adc(voltage)
    with path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["time_s", "adc", "voltage"])
        writer.writerows(zip(t, adc, voltage))


def main() -> None:
    args = parse_args()
    rng = np.random.default_rng(args.seed)
    out_dir = Path(args.out_dir)
    profiles = {profile.label: profile for profile in PROFILES}
    selected_profiles = [profiles[label] for label in args.classes if label in profiles]

    if not selected_profiles:
        raise SystemExit(f"No valid classes selected. Valid classes: {sorted(profiles)}")

    sample_count = int(args.seconds * args.fs)
    t = np.arange(sample_count) / args.fs

    for profile in selected_profiles:
        for index in range(args.recordings_per_class):
            voltage = make_signal(profile, t, rng)
            path = out_dir / profile.label / f"{profile.label}_sim_{index + 1:03d}.csv"
            write_recording(path, t, voltage)

    print(f"Generated {len(selected_profiles) * args.recordings_per_class} recordings in {out_dir}")


if __name__ == "__main__":
    main()
