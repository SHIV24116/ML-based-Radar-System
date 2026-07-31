"""Shared helpers for the ESP32 ultrasonic scanner visualizations."""

from __future__ import annotations

import csv
import math
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional, Sequence

import numpy as np
from scipy.fft import fft, fftfreq

try:
    import serial
    from serial import SerialException
except ImportError:  # pragma: no cover - handled at runtime with a clear error.
    serial = None

    class SerialException(Exception):
        """Fallback exception used when pyserial is not installed."""


MIN_DISTANCE_CM = 2.0
MAX_DISTANCE_CM = 400.0
DEFAULT_BAUDRATE = 115200


@dataclass(slots=True)
class ScanPacket:
    """One decoded packet from the ESP32 serial stream."""

    angle: float
    distance: float
    timestamp_ms: int
    received_at: float

    @property
    def is_valid_distance(self) -> bool:
        return validate_distance(self.distance)


class PacketDecodeError(ValueError):
    """Raised when a serial line cannot be decoded into a ScanPacket."""


class SerialReader:
    """Small, defensive wrapper around pyserial for scanner packets."""

    def __init__(self, port: str = "COM3", baudrate: int = DEFAULT_BAUDRATE, timeout: float = 0.05) -> None:
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.ser = None
        self.last_error = "Not connected"

    @property
    def connected(self) -> bool:
        return bool(self.ser and self.ser.is_open)

    def connect(self) -> None:
        if serial is None:
            raise RuntimeError("pyserial is not installed. Run: pip install -r requirements.txt")
        if self.connected:
            return
        self.ser = serial.Serial(self.port, self.baudrate, timeout=self.timeout)
        self.last_error = ""

    def read_packet(self) -> Optional[ScanPacket]:
        if not self.connected:
            return None
        try:
            raw = self.ser.readline()
            if not raw:
                return None
            return decode_packet(raw.decode("utf-8", errors="ignore"))
        except (UnicodeDecodeError, PacketDecodeError) as exc:
            self.last_error = str(exc)
            return None
        except SerialException as exc:
            self.last_error = f"Serial error: {exc}"
            self.close()
            return None

    def close(self) -> None:
        if self.ser is not None:
            try:
                self.ser.close()
            finally:
                self.ser = None
                self.last_error = "Disconnected"


def decode_packet(line: str) -> ScanPacket:
    """Decode ANGLE,DISTANCE,TIME into a typed packet."""

    cleaned = line.strip()
    parts = [part.strip() for part in cleaned.split(",")]
    if len(parts) != 3:
        raise PacketDecodeError(f"Expected 3 comma-separated values, got: {cleaned!r}")

    try:
        angle = float(parts[0])
        distance = float(parts[1])
        timestamp_ms = int(float(parts[2]))
    except ValueError as exc:
        raise PacketDecodeError(f"Invalid numeric packet: {cleaned!r}") from exc

    if not 0.0 <= angle <= 180.0:
        raise PacketDecodeError(f"Angle out of servo range: {angle}")

    return ScanPacket(angle=angle, distance=distance, timestamp_ms=timestamp_ms, received_at=time.time())


def validate_distance(distance: float, min_d: float = MIN_DISTANCE_CM, max_d: float = MAX_DISTANCE_CM) -> bool:
    return math.isfinite(distance) and min_d <= distance <= max_d


def polar_to_cartesian(angle_deg: float, distance_cm: float) -> tuple[float, float]:
    theta = math.radians(angle_deg)
    return distance_cm * math.cos(theta), distance_cm * math.sin(theta)


def scan_to_xy(scan_points: Iterable[tuple[float, float]]) -> tuple[np.ndarray, np.ndarray]:
    xs: list[float] = []
    ys: list[float] = []
    for angle, distance in scan_points:
        if validate_distance(distance):
            x, y = polar_to_cartesian(angle, distance)
            xs.append(x)
            ys.append(y)
    return np.asarray(xs, dtype=float), np.asarray(ys, dtype=float)


def moving_average(data: Sequence[float], window: int = 5) -> np.ndarray:
    values = np.asarray(data, dtype=float)
    if values.size == 0 or window <= 1:
        return values
    if values.size < window:
        return values.copy()
    kernel = np.ones(window, dtype=float) / window
    return np.convolve(values, kernel, mode="same")


def normalize(signal: Sequence[float]) -> np.ndarray:
    values = np.asarray(signal, dtype=float)
    if values.size == 0:
        return values
    std = np.std(values)
    if std == 0:
        return values - np.mean(values)
    return (values - np.mean(values)) / std


def calculate_fft(signal: Sequence[float], sample_rate: float) -> tuple[np.ndarray, np.ndarray]:
    values = np.asarray(signal, dtype=float)
    if values.size < 2 or sample_rate <= 0:
        return np.asarray([], dtype=float), np.asarray([], dtype=float)
    windowed = (values - np.mean(values)) * np.hanning(values.size)
    amplitudes = np.abs(fft(windowed))[: values.size // 2]
    frequencies = fftfreq(values.size, 1.0 / sample_rate)[: values.size // 2]
    return frequencies, amplitudes


def dominant_frequency(signal: Sequence[float], sample_rate: float) -> tuple[float, float]:
    frequencies, amplitudes = calculate_fft(signal, sample_rate)
    if amplitudes.size == 0:
        return 0.0, 0.0
    start = 1 if amplitudes.size > 1 else 0
    peak_index = int(np.argmax(amplitudes[start:]) + start)
    return float(frequencies[peak_index]), float(amplitudes[peak_index])


def save_scan_csv(path: str | Path, packets: Iterable[ScanPacket]) -> None:
    """Persist packets for future dataset-recorder work without coupling the GUI to ML."""

    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["angle", "distance", "timestamp_ms", "received_at"])
        for packet in packets:
            writer.writerow([packet.angle, packet.distance, packet.timestamp_ms, f"{packet.received_at:.6f}"])