"""Standalone real-time 2D shape reconstruction viewer."""

from __future__ import annotations

from typing import Optional

import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtWidgets

from utils import SerialReader, ScanPacket, polar_to_cartesian, validate_distance


class ShapeView(QtWidgets.QWidget):
    """Plot one completed servo sweep as an ultrasonic point cloud and outline."""

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.current_scan: dict[int, float] = {}
        self.last_angle: Optional[float] = None
        self.last_step_direction = 0
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.plot = pg.PlotWidget(title="Live Shape Reconstruction")
        self.plot.setAspectLocked(True)
        self.plot.showGrid(x=True, y=True, alpha=0.3)
        self.plot.setXRange(-430, 430)
        self.plot.setYRange(0, 430)
        self.plot.setLabel("left", "Y", units="cm")
        self.plot.setLabel("bottom", "X", units="cm")
        self.plot.addLegend(offset=(10, 10))

        self.points = pg.ScatterPlotItem(size=7, brush=pg.mkBrush(80, 200, 255), name="Scan points")
        self.outline = pg.PlotCurveItem(pen=pg.mkPen(255, 210, 90, width=2), name="Object outline")
        self.origin = pg.ScatterPlotItem(x=[0], y=[0], size=12, brush=pg.mkBrush(255, 90, 90), name="Sensor")
        self.left_boundary = pg.PlotCurveItem(pen=pg.mkPen(100, 100, 100, width=1, style=QtCore.Qt.DashLine))
        self.right_boundary = pg.PlotCurveItem(pen=pg.mkPen(100, 100, 100, width=1, style=QtCore.Qt.DashLine))

        self.plot.addItem(self.outline)
        self.plot.addItem(self.points)
        self.plot.addItem(self.origin)
        self.plot.addItem(self.left_boundary)
        self.plot.addItem(self.right_boundary)
        self._draw_boundaries()
        layout.addWidget(self.plot)

    def _draw_boundaries(self) -> None:
        left_x, left_y = polar_to_cartesian(30, 400)
        right_x, right_y = polar_to_cartesian(150, 400)
        self.left_boundary.setData([0, left_x], [0, left_y])
        self.right_boundary.setData([0, right_x], [0, right_y])

    def add_packet(self, packet: ScanPacket) -> bool:
        """Add a packet and return True when a completed sweep was drawn."""

        if not packet.is_valid_distance:
            return False

        angle = int(round(packet.angle))
        completed = False

        if self.last_angle is not None:
            delta = packet.angle - self.last_angle
            step_direction = 1 if delta > 0 else -1 if delta < 0 else 0

            # The ESP32 sweep reverses gradually at 30 deg and 150 deg.
            # Render the finished pass when the angular direction flips.
            if (
                step_direction != 0
                and self.last_step_direction != 0
                and step_direction != self.last_step_direction
                and len(self.current_scan) >= 5
            ):
                self.render_scan()
                self.current_scan.clear()
                completed = True

            if step_direction != 0:
                self.last_step_direction = step_direction

        self.current_scan[angle] = packet.distance
        self.last_angle = packet.angle

        return completed

    def render_scan(self) -> None:
        xs: list[float] = []
        ys: list[float] = []
        for angle in sorted(self.current_scan):
            distance = self.current_scan[angle]
            if validate_distance(distance):
                x, y = polar_to_cartesian(angle, distance)
                xs.append(x)
                ys.append(y)
        self.points.setData(xs, ys)
        self.outline.setData(xs, ys)

    def clear(self) -> None:
        self.current_scan.clear()
        self.last_angle = None
        self.last_step_direction = 0
        self.points.setData([], [])
        self.outline.setData([], [])


class ShapeWindow(QtWidgets.QMainWindow):
    def __init__(self, port: str, baudrate: int) -> None:
        super().__init__()
        self.setWindowTitle("Ultrasonic Shape View")
        self.reader = SerialReader(port, baudrate)
        self.view = ShapeView()
        self.setCentralWidget(self.view)
        self.statusBar().showMessage("Connecting...")
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update_from_serial)
        self.timer.start(5)
        try:
            self.reader.connect()
            self.statusBar().showMessage(f"Connected to {port} @ {baudrate}")
        except Exception as exc:  # noqa: BLE001 - GUI must not crash.
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
    window = ShapeWindow(port="COM3", baudrate=115200)
    window.resize(900, 850)
    window.show()
    getattr(app, "exec", app.exec_)()


if __name__ == "__main__":
    main()
