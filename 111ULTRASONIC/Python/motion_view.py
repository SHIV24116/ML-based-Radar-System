"""Standalone center-beam motion signature viewer."""

from __future__ import annotations

import time
from collections import deque
from typing import Optional

import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtWidgets

from utils import SerialReader, ScanPacket


class MotionView(QtWidgets.QWidget):
    """Scrolling distance-vs-time graph for packets near the center beam."""

    def __init__(self, center_angle: float = 90.0, tolerance: float = 2.0, history_seconds: float = 5.0) -> None:
        super().__init__()
        self.center_angle = center_angle
        self.tolerance = tolerance
        self.history_seconds = history_seconds
        self.times: deque[float] = deque()
        self.distances: deque[float] = deque()
        self.start_time = time.monotonic()
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.plot = pg.PlotWidget(title="Motion Signature")
        self.plot.showGrid(x=True, y=True, alpha=0.3)
        self.plot.setLabel("left", "Distance", units="cm")
        self.plot.setLabel("bottom", "Time", units="s")
        self.curve = self.plot.plot(pen=pg.mkPen(120, 255, 180, width=2), name="Center distance")
        layout.addWidget(self.plot)

    def add_packet(self, packet: ScanPacket) -> None:
        if not packet.is_valid_distance or abs(packet.angle - self.center_angle) > self.tolerance:
            return

        now = time.monotonic() - self.start_time
        self.times.append(now)
        self.distances.append(packet.distance)
        cutoff = now - self.history_seconds
        while self.times and self.times[0] < cutoff:
            self.times.popleft()
            self.distances.popleft()

        self.curve.setData(list(self.times), list(self.distances))
        self.plot.setXRange(max(0.0, now - self.history_seconds), max(self.history_seconds, now), padding=0)
        if self.distances:
            low = min(self.distances)
            high = max(self.distances)
            margin = max(5.0, (high - low) * 0.15)
            self.plot.setYRange(max(0.0, low - margin), high + margin, padding=0)

    def clear(self) -> None:
        self.times.clear()
        self.distances.clear()
        self.start_time = time.monotonic()
        self.curve.setData([], [])


class MotionWindow(QtWidgets.QMainWindow):
    def __init__(self, port: str, baudrate: int) -> None:
        super().__init__()
        self.setWindowTitle("Ultrasonic Motion View")
        self.reader = SerialReader(port, baudrate)
        self.view = MotionView()
        self.setCentralWidget(self.view)
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update_from_serial)
        self.timer.start(5)
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
    window = MotionWindow(port="COM3", baudrate=115200)
    window.resize(900, 520)
    window.show()
    getattr(app, "exec", app.exec_)()


if __name__ == "__main__":
    main()