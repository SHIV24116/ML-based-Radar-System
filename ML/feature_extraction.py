"""Feature extraction for radar STFT spectrograms."""

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


def extract_features_from_filtered_signal(filtered: np.ndarray, fs: float = 2000.0) -> list[float]:
    freqs, magnitude = compute_fft(filtered, fs=fs)
    _, _, spec = compute_stft(filtered, fs=fs)

    dominant_hz = dominant_doppler_frequency(freqs, magnitude)
    speed_mps = estimate_speed_mps(dominant_hz)
    magnitude_sum = float(np.sum(magnitude) + 1e-12)
    spectral_centroid = float(np.sum(freqs * magnitude) / magnitude_sum)
    spectral_bandwidth = float(np.sqrt(np.sum(((freqs - spectral_centroid) ** 2) * magnitude) / magnitude_sum))

    low_band_energy = band_energy(freqs, magnitude, 10.0, 80.0)
    mid_band_energy = band_energy(freqs, magnitude, 80.0, 180.0)
    high_band_energy = band_energy(freqs, magnitude, 180.0, 500.0)
    total_band_energy = low_band_energy + mid_band_energy + high_band_energy + 1e-12

    features = extract_features_from_spectrogram(spec)
    features.extend(
        [
            dominant_hz,
            speed_mps,
            spectral_centroid,
            spectral_bandwidth,
            low_band_energy / total_band_energy,
            mid_band_energy / total_band_energy,
            high_band_energy / total_band_energy,
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
    "speed_mps",
    "spectral_centroid",
    "spectral_bandwidth",
    "low_band_ratio_10_80",
    "mid_band_ratio_80_180",
    "high_band_ratio_180_500",
]
