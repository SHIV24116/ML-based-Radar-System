#pragma once

#include <Arduino.h>
#include "CircularBuffer.h"

class RadarADC {
public:
  void begin();
  void sample();
  bool isFrameReady() const;
  void getFrame(uint16_t *destination, uint16_t length) const;
  void clear();

private:
  CircularBuffer buffer_;
  uint32_t lastSampleUs_ = 0;
};
