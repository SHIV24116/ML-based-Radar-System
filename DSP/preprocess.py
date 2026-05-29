"""CLI helper for inspecting one recorded radar CSV file."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt

from radar_dsp import (
    bandpass_filter,
    compute_fft,
    compute_stft,
    dominant_doppler_frequency,
    estimate_speed_mps,
    load_recording,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Preprocess and plot a radar recording.")
    parser.add_argument("csv_path", help="Path to a recorded CSV file.")
    parser.add_argument("--fs", type=float, default=2000.0, help="Sampling frequency in Hz.")
    parser.add_argument("--show-stft", action="store_true", help="Also show the STFT spectrogram.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    csv_path = Path(args.csv_path)

    signal = load_recording(csv_path)
    filtered = bandpass_filter(signal, fs=args.fs)
    freqs, magnitude = compute_fft(filtered, fs=args.fs)
    stft_freqs, times, spectrogram = compute_stft(filtered, fs=args.fs)

    dominant_hz = dominant_doppler_frequency(freqs, magnitude)
    speed_mps = estimate_speed_mps(dominant_hz)

    print(f"Samples: {len(signal)}")
    print(f"Dominant Doppler frequency: {dominant_hz:.2f} Hz")
    print(f"Estimated speed magnitude: {speed_mps:.2f} m/s")
    print("Direction and distance are future extensions for this hardware setup.")

    plt.figure(figsize=(10, 4))
    plt.plot(freqs, magnitude)
    plt.title(f"FFT: {csv_path.name}")
    plt.xlabel("Frequency (Hz)")
    plt.ylabel("Magnitude")
    plt.xlim(0, 500)
    plt.tight_layout()
    plt.show()

    if args.show_stft:
        plt.figure(figsize=(10, 4))
        plt.pcolormesh(times, stft_freqs, spectrogram, shading="gouraud")
        plt.title(f"STFT Spectrogram: {csv_path.name}")
        plt.xlabel("Time (s)")
        plt.ylabel("Frequency (Hz)")
        plt.ylim(0, 500)
        plt.colorbar(label="Magnitude")
        plt.tight_layout()
        plt.show()


if __name__ == "__main__":
    main()
