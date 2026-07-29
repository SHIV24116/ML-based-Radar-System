# Project Notes

## Final Capabilities

- Motion detection from the CDM324 Doppler radar waveform.
- Broad object or motion-class prediction using radar-only micro-Doppler features.
- Live object-presence verification with the HC-SR04 ultrasonic sensor.
- Live distance, speed, and motion-direction display from ultrasonic distance history.
- OLED and USB serial output for the final embedded demo.

## Hardware Boundary

- CDM324 radar provides Doppler movement information through the MCP6002-conditioned ADC waveform.
- HC-SR04 provides live presence verification and distance for the final demo.
- Motion direction is inferred from ultrasonic distance trend: decreasing distance means approaching, increasing distance means receding.
- The Python live demo estimates radar speed magnitude for development, but the final embedded workflow displays ultrasonic-derived speed and direction.

## Design Rules

- Radar sampling runs continuously and is never paused while checking ultrasonic presence.
- Ultrasonic distance, speed, and presence are never included in ML training data.
- All firmware constants live in `Firmware/Config.h`.
- `Firmware/ESP32_Main.ino` only orchestrates modules; algorithms live in separate classes.
- Runtime scheduling uses `millis()`/`micros()` instead of blocking `delay()` calls.

## Defense Points

- Radar is useful when motion information is needed without relying on visible light.
- The MCP6002 is suitable for low-voltage ESP32 interfacing because it can operate from a `3.3 V` supply.
- RC filters are required to remove DC drift and high-frequency noise before ADC sampling.
- STFT and FFT statistics are used because object motion creates time-frequency signatures.
- ML works because different moving objects create different Doppler energy patterns.
- The ultrasonic sensor is deliberately excluded from ML training to prevent the classifier from learning distance shortcuts instead of radar signatures.
