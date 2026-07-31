"""Standalone real-time FFT viewer for center-beam motion."""

from __future__ import annotations

from collections import deque

import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtWidgets

from utils import SerialReader, ScanPacket, calculate_fft, dominant_frequency


class FFTView(QtWidgets.QWidget):
    """Frequency spectrum of the center-angle distance signal."""

    def __init__(self, sample_rate: float = 20.0, max_samples: int = 1024) -> None:
        super().__init__()
        self.sample_rate = sample_rate
        self.samples: deque[float] = deque(maxlen=max_samples)
        self.latest_dominant = (0.0, 0.0)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.plot = pg.PlotWidget(title="FFT Spectrum")
        self.plot.showGrid(x=True, y=True, alpha=0.3)
        self.plot.setLabel("left", "Amplitude")
        self.plot.setLabel("bottom", "Frequency", units="Hz")
        self.curve = self.plot.plot(pen=pg.mkPen(255, 220, 90, width=2), name="Spectrum")
        self.peak_label = pg.TextItem(color="#fca5a5", anchor=(0, 1))
        self.plot.addItem(self.peak_label)
        layout.addWidget(self.plot)

    def add_packet(self, packet: ScanPacket, center_angle: float = 90.0, tolerance: float = 2.0) -> None:
        if packet.is_valid_distance and abs(packet.angle - center_angle) <= tolerance:
            self.samples.append(packet.distance)

    def refresh(self) -> None:
        if len(self.samples) < 64:
            return
        signal = np.asarray(self.samples, dtype=float)
        frequencies, amplitudes = calculate_fft(signal, self.sample_rate)
        self.curve.setData(frequencies, amplitudes)
        self.latest_dominant = dominant_frequency(signal, self.sample_rate)
        frequency, amplitude = self.latest_dominant
        self.peak_label.setText(f"Dominant: {frequency:.2f} Hz")
        self.peak_label.setPos(frequency, amplitude)
        if frequencies.size:
            self.plot.setXRange(0, float(frequencies[-1]), padding=0)
        if amplitudes.size:
            self.plot.setYRange(0, float(np.max(amplitudes)) * 1.15 + 1.0, padding=0)

    def clear(self) -> None:
        self.samples.clear()
        self.latest_dominant = (0.0, 0.0)
        self.curve.setData([], [])
        self.peak_label.setText("")


class FFTWindow(QtWidgets.QMainWindow):
    def __init__(self, port: str, baudrate: int) -> None:
        super().__init__()
        self.setWindowTitle("Ultrasonic FFT View")
        self.reader = SerialReader(port, baudrate)
        self.view = FFTView()
        self.setCentralWidget(self.view)
        self.read_timer = QtCore.QTimer(self)
        self.read_timer.timeout.connect(self.update_from_serial)
        self.read_timer.start(5)
        self.fft_timer = QtCore.QTimer(self)
        self.fft_timer.timeout.connect(self.view.refresh)
        self.fft_timer.start(1000)
        try:
            self.reader.connect()
            self.statusBar().showMessage(f"Connected to {port} @ {baudrate}")
        except Exception as exc:  # noqa: BLE001
            self.statusBar().showMessage(str(exc))

    def update_from_serial(self) -> None:
        packet = self.reader.read_packet()
        if packet is not None:
            self.view.add_packet(packet)
        elif self.reader.last_error:
            self.statusBar().showMessage(self.reader.last_error)

    def closeEvent(self, event) -> None:  # type: ignore[override]
        self.reader.close()
        event.accept()


def main() -> None:
    app = QtWidgets.QApplication([])
    pg.setConfigOptions(antialias=True, background="#111827", foreground="#d1d5db")
    window = FFTWindow(port="COM3", baudrate=115200)
    window.resize(900, 520)
    window.show()
    getattr(app, "exec", app.exec_)()


if __name__ == "__main__":
    main()