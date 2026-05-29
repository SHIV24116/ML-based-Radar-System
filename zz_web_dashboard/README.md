# Web Interface

Run from the project root:

```powershell
python "zz_web_dashboard\server.py"
```

Open:

```text
http://127.0.0.1:8000
```

The dashboard uses the existing backend modules:

- `Simulation/generate_synthetic_dataset.py`
- `ML/compare_models.py`
- `DSP/radar_dsp.py`
- `Data Collection/serial_logger.py` behavior for serial recording

No extra web framework is required.

## Live Detection

Use `Simulated playback` to test the live UI without hardware. Once the ESP32 is
streaming ADC values, switch the mode to `ESP32 serial`, enter the COM port, and
start live detection. The panel shows the current class, confidence, speed
magnitude, and recent prediction history.
