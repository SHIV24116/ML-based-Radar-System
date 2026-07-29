#pragma once

#include <Arduino.h>
#include "Config.h"

class CircularBuffer {
public:
  void clear();
  void push(uint16_t sample);
  bool isFull() const;
  uint16_t size() const;
  void copyLatest(uint16_t *destination, uint16_t length) const;

private:
  uint16_t data_[Config::RADAR_BUFFER_SIZE] = {0};
  uint16_t head_ = 0;
  uint16_t count_ = 0;
};
