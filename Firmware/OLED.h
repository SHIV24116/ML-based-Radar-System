#pragma once

#include <Arduino.h>
#include <Adafruit_SSD1306.h>
#include "MLInference.h"
#include "Ultrasonic.h"

class OLEDDisplay {
public:
  OLEDDisplay();
  bool begin();
  void showSplash();
  void showWaiting();
  void showObject(const Prediction &prediction, float distanceM, float speedMps, MotionDirection direction);
  void showError(const String &message);
  void clear();

private:
  Adafruit_SSD1306 display_;
};
