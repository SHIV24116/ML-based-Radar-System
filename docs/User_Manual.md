# User Manual

## Hardware Connections

- CDM324 conditioned radar output to ESP32 `GPIO34`.
- HC-SR04 `TRIG` to `GPIO5`.
- HC-SR04 `ECHO` through a voltage divider to `GPIO18`.
- SSD1306 OLED I2C `SDA` to `GPIO21`.
- SSD1306 OLED I2C `SCL` to `GPIO22`.
- Common ground across radar circuit, ultrasonic sensor, OLED, and ESP32.

## Final Firmware

Open `Firmware/ESP32_Main.ino` in Arduino IDE. Install:

- Adafruit SSD1306
- Adafruit GFX
- Wire

Upload to ESP32. The device will show an initializing splash screen, then wait for object presence. When an object is confirmed by ultrasonic distance, the OLED shows object class, confidence, distance, speed, and motion direction.

## Development Data Logger

Use `ESP32 codes/adc_logger.ino` only when collecting raw radar training data:

```powershell
python "Data Collection/serial_logger.py" --port COM5 --label human --seconds 10
```

## Dashboard

Start the local dashboard:

```powershell
python "zz_web_dashboard/server.py"
```

Open:

```text
http://127.0.0.1:8000
```

Use it to generate simulated data, compare models, inspect signals, record real ESP32 data, and run the Python live development demo.
