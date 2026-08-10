"""Shared DSP utilities for the ML-based Doppler radar project."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy.signal import butter, filtfilt, stft


ADC_MAX = 4095.0
ADC_VREF = 3.3
DEFAULT_FS_HZ = 2000.0
RADAR_FREQUENCY_HZ = 24.0e9
LIGHT_SPEED_MPS = 299_792_458.0


def adc_to_voltage(samples: np.ndarray) -> np.ndarray:
    return samples.astype(float) * (ADC_VREF / ADC_MAX)


def load_recording(path: str | Path) -> np.ndarray:
    """Load a recording saved either as one ADC column or as time/adc/voltage CSV."""
    path = Path(path)

    try:
        frame = pd.read_csv(path)
        if "voltage" in frame.columns:
            voltage = frame["voltage"].dropna().to_numpy(dtype=float)
            if len(voltage) > 0:
                return voltage
        if "adc" in frame.columns:
            adc = pd.to_numeric(frame["adc"], errors="coerce").dropna()
            adc = adc[adc >= 0]
            if len(adc) > 0:
                return adc_to_voltage(adc.to_numpy(dtype=float))
    except pd.errors.EmptyDataError:
        raise ValueError(f"Recording is empty: {path}") from None

    raw = np.loadtxt(path, delimiter=",")
    if raw.ndim > 1:
        raw = raw[:, -1]
    if np.nanmax(raw) > ADC_VREF:
        raw = adc_to_voltage(raw)
    return raw.astype(float)


def remove_dc(signal: np.ndarray) -> np.ndarray:
    return signal - np.mean(signal)


def bandpass_filter(
    signal: np.ndarray,
    fs: float = DEFAULT_FS_HZ,
    low_hz: float = 10.0,
    high_hz: float = 500.0,
    order: int = 4,
) -> np.ndarray:
    centered = remove_dc(signal)
    nyquist = fs / 2.0
    high_hz = min(high_hz, nyquist * 0.95)
    b, a = butter(order, [low_hz / nyquist, high_hz / nyquist], btype="band")
    return filtfilt(b, a, centered)


def compute_fft(signal: np.ndarray, fs: float = DEFAULT_FS_HZ) -> tuple[np.ndarray, np.ndarray]:
    magnitude = np.abs(np.fft.rfft(signal))
    freqs = np.fft.rfftfreq(len(signal), d=1.0 / fs)
    return freqs, magnitude


def compute_stft(
    signal: np.ndarray,
    fs: float = DEFAULT_FS_HZ,
    nperseg: int = 256,
    noverlap: int = 128,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    freqs, times, zxx = stft(signal, fs=fs, nperseg=nperseg, noverlap=noverlap)
    return freqs, times, np.abs(zxx)


def dominant_doppler_frequency(
    freqs: np.ndarray,
    magnitude: np.ndarray,
    min_hz: float = 10.0,
    max_hz: float = 500.0,
) -> float:
    mask = (freqs >= min_hz) & (freqs <= max_hz)
    if not np.any(mask):
        return 0.0
    selected_freqs = freqs[mask]
    selected_magnitude = magnitude[mask]
    return float(selected_freqs[np.argmax(selected_magnitude)])


def estimate_speed_mps(doppler_hz: float, radar_frequency_hz: float = RADAR_FREQUENCY_HZ) -> float:
    """Estimate radial speed magnitude for a monostatic CW Doppler radar."""
    wavelength_m = LIGHT_SPEED_MPS / radar_frequency_hz
    return abs(doppler_hz) * wavelength_m / 2.0
