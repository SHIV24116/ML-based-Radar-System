#pragma once

#include <Arduino.h>
#include "Config.h"

struct Prediction {
  String label;
  float confidence;
};

class MLInference {
public:
  bool begin();
  Prediction predict(const float *features, uint16_t length);

private:
  bool ready_ = false;
};
