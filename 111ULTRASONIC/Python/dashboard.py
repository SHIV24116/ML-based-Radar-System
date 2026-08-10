"""Professional PyQt5 dashboard for the ESP32 ultrasonic scanner."""

from __future__ import annotations

import time
from collections import deque
from typing import Optional

import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtWidgets

from fft_view import FFTView
from motion_view import MotionView
from shape_view import ShapeView
from utils import DEFAULT_BAUDRATE, SerialReader, ScanPacket


class InfoPanel(QtWidgets.QFrame):
    """Status and telemetry panel for the live scanner stream."""

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("infoPanel")
        self.labels: dict[str, QtWidgets.QLabel] = {}
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(10)

        title = QtWidgets.QLabel("Scanner Telemetry")
        title.setObjectName("panelTitle")
        layout.addWidget(title)

        for key in (
            "Connection Status",
            "Current Angle",
            "Current Distance",
            "Packet Rate",
            "FPS",
            "Scan Status",
            "Dominant Frequency",
            "Last Error",
        ):
            row = QtWidgets.QHBoxLayout()
            name = QtWidgets.QLabel(key)
            value = QtWidgets.QLabel("--")
            value.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
            value.setObjectName("valueLabel")
            row.addWidget(name)
            row.addWidget(value)
            layout.addLayout(row)
            self.labels[key] = value

        layout.addStretch(1)

    def set_value(self, key: str, value: str) -> None:
        if key in self.labels:
            self.labels[key].setText(value)


class UltrasonicDashboard(QtWidgets.QMainWindow):
    """Single-window dashboard that coordinates serial input and all views."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("ESP32 Ultrasonic Shape Reconstruction Dashboard")
        self.reader: Optional[SerialReader] = None
        self.paused = False
        self.packet_times: deque[float] = deque(maxlen=300)
        self.frame_times: deque[float] = deque(maxlen=120)
        self.latest_packet: Optional[ScanPacket] = None
        self.sweep_count = 0
        self._build_ui()
        self._apply_theme()
        self.read_timer = QtCore.QTimer(self)
        self.read_timer.timeout.connect(self.read_serial)
        self.read_timer.start(5)
        self.ui_timer = QtCore.QTimer(self)
        self.ui_timer.timeout.connect(self.refresh_status)
        self.ui_timer.start(250)
        self.fft_timer = QtCore.QTimer(self)
        self.fft_timer.timeout.connect(self.fft_view.refresh)
        self.fft_timer.start(1000)

    def _build_ui(self) -> None:
        central = QtWidgets.QWidget()
        root = QtWidgets.QVBoxLayout(central)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(12)

        toolbar = QtWidgets.QHBoxLayout()
        self.port_input = QtWidgets.QLineEdit("COM3")
        self.port_input.setFixedWidth(110)
        self.baud_input = QtWidgets.QSpinBox()
        self.baud_input.setRange(9600, 921600)
        self.baud_input.setValue(DEFAULT_BAUDRATE)
        self.baud_input.setSingleStep(9600)

        self.connect_button = QtWidgets.QPushButton("Connect")
        self.disconnect_button = QtWidgets.QPushButton("Disconnect")
        self.pause_button = QtWidgets.QPushButton("Pause")
        self.resume_button = QtWidgets.QPushButton("Resume")
        self.clear_button = QtWidgets.QPushButton("Clear")

        self.connect_button.clicked.connect(self.connect_serial)
        self.disconnect_button.clicked.connect(self.disconnect_serial)
        self.pause_button.clicked.connect(self.pause)
        self.resume_button.clicked.connect(self.resume)
        self.clear_button.clicked.connect(self.clear_views)

        toolbar.addWidget(QtWidgets.QLabel("Port"))
        toolbar.addWidget(self.port_input)
        toolbar.addWidget(QtWidgets.QLabel("Baud"))
        toolbar.addWidget(self.baud_input)
        toolbar.addSpacing(12)
        for button in (self.connect_button, self.disconnect_button, self.pause_button, self.resume_button, self.clear_button):
            toolbar.addWidget(button)
        toolbar.addStretch(1)
        root.addLayout(toolbar)

        splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        top = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        bottom = QtWidgets.QSplitter(QtCore.Qt.Horizontal)

        self.shape_view = ShapeView()
        self.motion_view = MotionView(history_seconds=5.0)
        self.fft_view = FFTView(sample_rate=20.0, max_samples=1024)
        self.info_panel = InfoPanel()

        top.addWidget(self.shape_view)
        top.addWidget(self.motion_view)
        bottom.addWidget(self.fft_view)
        bottom.addWidget(self.info_panel)
        top.setSizes([700, 550])
        bottom.setSizes([700, 350])
        splitter.addWidget(top)
        splitter.addWidget(bottom)
        splitter.setSizes([600, 420])
        root.addWidget(splitter, 1)

        self.setCentralWidget(central)
        self.statusBar().showMessage("Ready")
        self.info_panel.set_value("Connection Status", "Disconnected")
        self.info_panel.set_value("Scan Status", "Idle")

    def _apply_theme(self) -> None:
        pg.setConfigOptions(antialias=True, background="#0f172a", foreground="#d1d5db")
        self.setStyleSheet(
            """
            QMainWindow, QWidget { background: #0f172a; color: #d1d5db; font-family: Segoe UI, Arial; font-size: 10pt; }
            QLineEdit, QSpinBox { background: #111827; border: 1px solid #334155; border-radius: 4px; padding: 6px; color: #f8fafc; }
            QPushButton { background: #1f2937; border: 1px solid #475569; border-radius: 4px; padding: 7px 14px; color: #f8fafc; }
            QPushButton:hover { background: #334155; }
            QPushButton:pressed { background: #0ea5e9; color: #04131f; }
            QFrame#infoPanel { background: #111827; border: 1px solid #334155; border-radius: 6px; padding: 10px; }
            QLabel#panelTitle { color: #f8fafc; font-size: 14pt; font-weight: 600; padding-bottom: 8px; }
            QLabel#valueLabel { color: #93c5fd; font-weight: 600; }
            QStatusBar { background: #111827; color: #cbd5e1; }
            """
        )

    def connect_serial(self) -> None:
        self.disconnect_serial()
        port = self.port_input.text().strip() or "COM3"
        baudrate = int(self.baud_input.value())
        self.reader = SerialReader(port=port, baudrate=baudrate)
        try:
            self.reader.connect()
        except Exception as exc:  # noqa: BLE001 - keep GUI alive and show the issue.
            self.reader = None
            self.statusBar().showMessage(str(exc))
            self.info_panel.set_value("Connection Status", "Failed")
            self.info_panel.set_value("Last Error", str(exc))
            return
        self.packet_times.clear()
        self.statusBar().showMessage(f"Connected to {port} @ {baudrate}")
        self.info_panel.set_value("Connection Status", f"Connected ({port})")
        self.info_panel.set_value("Last Error", "--")

    def disconnect_serial(self) -> None:
        if self.reader is not None:
            self.reader.close()
        self.reader = None
        self.info_panel.set_value("Connection Status", "Disconnected")
        self.info_panel.set_value("Scan Status", "Idle")

    def pause(self) -> None:
        self.paused = True
        self.info_panel.set_value("Scan Status", "Paused")

    def resume(self) -> None:
        self.paused = False
        self.info_panel.set_value("Scan Status", "Running" if self.reader else "Idle")

    def clear_views(self) -> None:
        self.shape_view.clear()
        self.motion_view.clear()
        self.fft_view.clear()
        self.packet_times.clear()
        self.frame_times.clear()
        self.latest_packet = None
        self.sweep_count = 0
        self.statusBar().showMessage("Views cleared")

    def read_serial(self) -> None:
        if self.paused or self.reader is None or not self.reader.connected:
            return
        packets_read = 0
        for _ in range(20):
            packet = self.reader.read_packet()
            if packet is None:
                break
            packets_read += 1
            self.process_packet(packet)
        if packets_read:
            self.frame_times.append(time.monotonic())
        elif self.reader and self.reader.last_error:
            self.info_panel.set_value("Last Error", self.reader.last_error)

    def process_packet(self, packet: ScanPacket) -> None:
        self.latest_packet = packet
        now = time.monotonic()
        self.packet_times.append(now)
        if self.shape_view.add_packet(packet):
            self.sweep_count += 1
        self.motion_view.add_packet(packet)
        self.fft_view.add_packet(packet)

    def refresh_status(self) -> None:
        now = time.monotonic()
        while self.packet_times and self.packet_times[0] < now - 1.0:
            self.packet_times.popleft()
        while self.frame_times and self.frame_times[0] < now - 1.0:
            self.frame_times.popleft()

        packet_rate = len(self.packet_times)
        fps = len(self.frame_times)
        self.info_panel.set_value("Packet Rate", f"{packet_rate} pkt/s")
        self.info_panel.set_value("FPS", f"{fps}")
        frequency, amplitude = self.fft_view.latest_dominant
        self.info_panel.set_value("Dominant Frequency", f"{frequency:.2f} Hz ({amplitude:.0f})")

        if self.latest_packet is not None:
            self.info_panel.set_value("Current Angle", f"{self.latest_packet.angle:.1f} deg")
            if self.latest_packet.is_valid_distance:
                self.info_panel.set_value("Current Distance", f"{self.latest_packet.distance:.1f} cm")
            else:
                self.info_panel.set_value("Current Distance", "Out of range")
        if not self.paused:
            if self.reader and self.reader.connected:
                self.info_panel.set_value("Scan Status", f"Running - sweeps {self.sweep_count}")
            else:
                self.info_panel.set_value("Scan Status", "Idle")

    def closeEvent(self, event) -> None:  # type: ignore[override]
        self.disconnect_serial()
        event.accept()


def main() -> None:
    app = QtWidgets.QApplication([])
    window = UltrasonicDashboard()
    window.resize(1280, 860)
    window.show()
    runner = getattr(app, "exec", app.exec_)
    runner()


if __name__ == "__main__":
    main()