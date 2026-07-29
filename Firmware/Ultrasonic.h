#pragma once

#include <Arduino.h>

enum class MotionDirection {
  Unknown,
  Approaching,
  Receding,
  Stationary
};

class Ultrasonic {
public:
  void begin();
  void update();
  float getDistanceM() const;
  float getSpeedMps() const;
  bool isObjectPresent() const;
  MotionDirection getMotionDirection() const;

private:
  float distanceM_ = 0.0f;
  float previousDistanceM_ = 0.0f;
  float speedMps_ = 0.0f;
  bool present_ = false;
  MotionDirection direction_ = MotionDirection::Unknown;
  uint32_t lastUpdateMs_ = 0;
};

const char *motionDirectionText(MotionDirection direction);
