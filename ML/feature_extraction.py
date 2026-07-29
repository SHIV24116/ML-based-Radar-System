"""Radar-only feature extraction for object classification.

The live ultrasonic readings are intentionally not used here. Distance,
presence, and ultrasonic speed are runtime verification/display values, not ML
training inputs.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DSP_DIR = PROJECT_ROOT / "DSP"
if str(DSP_DIR) not in sys.path:
    sys.path.insert(0, str(DSP_DIR))

from radar_dsp import (  # noqa: E402
    bandpass_filter,
    compute_fft,
    compute_stft,
    dominant_doppler_frequency,
    estimate_speed_mps,
    load_recording,
)


def extract_features_from_spectrogram(spec: np.ndarray) -> list[float]:
    return [
        float(np.mean(spec)),
        float(np.std(spec)),
        float(np.max(spec)),
        float(np.sum(spec)),
        float(np.percentile(spec, 75)),
        float(np.percentile(spec, 95)),
    ]


def band_energy(freqs: np.ndarray, magnitude: np.ndarray, low_hz: float, high_hz: float) -> float:
    mask = (freqs >= low_hz) & (freqs < high_hz)
    if not np.any(mask):
        return 0.0
    return float(np.sum(magnitude[mask] ** 2))


def spectral_entropy(magnitude: np.ndarray) -> float:
    power = magnitude.astype(float) ** 2
    total = float(np.sum(power) + 1e-12)
    probability = power / total
    return float(-np.sum(probability * np.log2(probability + 1e-12)) / np.log2(len(probability)))


def zero_crossing_rate(signal: np.ndarray) -> float:
    if len(signal) < 2:
        return 0.0
    return float(np.mean(np.diff(np.signbit(signal)) != 0))


def peak_width_bins(magnitude: np.ndarray, peak_index: int) -> float:
    if len(magnitude) == 0:
        return 0.0
    threshold = float(magnitude[peak_index]) * 0.5
    return float(np.sum(magnitude >= threshold))


def estimate_motion_metrics(filtered: np.ndarray, fs: float = 2000.0) -> dict[str, float]:
    freqs, magnitude = compute_fft(filtered, fs=fs)
    dominant_hz = dominant_doppler_frequency(freqs, magnitude)
    return {
        "dominant_hz": float(dominant_hz),
        "radar_speed_mps": float(estimate_speed_mps(dominant_hz)),
    }


def extract_features_from_filtered_signal(filtered: np.ndarray, fs: float = 2000.0) -> list[float]:
    freqs, magnitude = compute_fft(filtered, fs=fs)
    _, _, spec = compute_stft(filtered, fs=fs)

    dominant_hz = dominant_doppler_frequency(freqs, magnitude)
    magnitude_sum = float(np.sum(magnitude) + 1e-12)
    spectral_centroid = float(np.sum(freqs * magnitude) / magnitude_sum)
    spectral_bandwidth = float(np.sqrt(np.sum(((freqs - spectral_centroid) ** 2) * magnitude) / magnitude_sum))
    peak_index = int(np.argmax(magnitude)) if len(magnitude) else 0

    low_band_energy = band_energy(freqs, magnitude, 10.0, 80.0)
    mid_band_energy = band_energy(freqs, magnitude, 80.0, 180.0)
    high_band_energy = band_energy(freqs, magnitude, 180.0, 500.0)
    total_band_energy = low_band_energy + mid_band_energy + high_band_energy + 1e-12

    features = extract_features_from_spectrogram(spec)
    features.extend(
        [
            dominant_hz,
            spectral_centroid,
            spectral_bandwidth,
            low_band_energy / total_band_energy,
            mid_band_energy / total_band_energy,
            high_band_energy / total_band_energy,
            float(np.mean(filtered)),
            float(np.var(filtered)),
            float(np.sqrt(np.mean(filtered**2))),
            float(np.sum(filtered**2)),
            spectral_entropy(magnitude),
            peak_width_bins(magnitude, peak_index),
            zero_crossing_rate(filtered),
            float(np.max(filtered)),
            float(np.min(filtered)),
            float(np.ptp(filtered)),
        ]
    )
    return features


def extract_features_from_file(csv_path: str | Path, fs: float = 2000.0) -> list[float]:
    signal = load_recording(csv_path)
    filtered = bandpass_filter(signal, fs=fs)
    return extract_features_from_filtered_signal(filtered, fs=fs)


FEATURE_NAMES = [
    "spec_mean",
    "spec_std",
    "spec_max",
    "spec_sum",
    "spec_p75",
    "spec_p95",
    "dominant_hz",
    "spectral_centroid",
    "spectral_bandwidth",
    "low_band_ratio_10_80",
    "mid_band_ratio_80_180",
    "high_band_ratio_180_500",
    "signal_mean",
    "signal_variance",
    "signal_rms",
    "signal_energy",
    "spectral_entropy",
    "peak_width_bins",
    "zero_crossing_rate",
    "signal_max",
    "signal_min",
    "signal_range",
]
