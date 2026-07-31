#pragma once

#include <Arduino.h>

namespace Config {
constexpr uint8_t RADAR_ADC_PIN = 34;
constexpr uint8_t ULTRASONIC_TRIG_PIN = 5;
constexpr uint8_t ULTRASONIC_ECHO_PIN = 18;
constexpr uint8_t OLED_SDA_PIN = 21;
constexpr uint8_t OLED_SCL_PIN = 22;

constexpr uint32_t SERIAL_BAUD = 115200;
constexpr uint16_t RADAR_BUFFER_SIZE = 512;
constexpr uint16_t FEATURE_COUNT = 14;
constexpr float RADAR_SAMPLE_RATE_HZ = 2000.0f;
constexpr uint32_t RADAR_SAMPLE_PERIOD_US = 500;

constexpr uint32_t ULTRASONIC_UPDATE_MS = 50;
constexpr uint32_t OLED_UPDATE_MS = 250;
constexpr uint32_t INFERENCE_UPDATE_MS = 300;
constexpr uint32_t ULTRASONIC_TIMEOUT_US = 25000;

constexpr float PRESENCE_DISTANCE_THRESHOLD_M = 3.50f;
constexpr float PRESENCE_MIN_DISTANCE_M = 0.02f;
constexpr float SPEED_DEADBAND_MPS = 0.05f;
constexpr float DETECTION_CONFIDENCE_THRESHOLD = 0.55f;

constexpr int OLED_WIDTH = 128;
constexpr int OLED_HEIGHT = 64;
constexpr int OLED_RESET_PIN = -1;

constexpr bool DEBUG_SERIAL = true;
}
