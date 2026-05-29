# Project Notes

## Confirmed Capabilities

- Motion detection from Doppler shift.
- Broad class prediction using micro-Doppler features.
- Speed magnitude estimation from dominant Doppler frequency.

## Future Extensions

- Distance/range estimation requires range-capable radar methods such as FMCW, pulsed radar, or additional hardware support.
- Direction detection requires phase information, typically using I/Q radar outputs or a quadrature receiver.

## Defense Points

- Radar is useful when motion information is needed without relying on visible light.
- The MCP6002 is suitable for low-voltage ESP32 interfacing because it can operate from a `3.3 V` supply.
- RC filters are required to remove DC drift and high-frequency noise before ADC sampling.
- STFT is used because object motion changes over time, and micro-Doppler patterns are time-frequency signatures.
- ML works because different moving objects create different Doppler energy patterns.
