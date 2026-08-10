#include "CircularBuffer.h"

void CircularBuffer::clear() {
  head_ = 0;
  count_ = 0;
}

void CircularBuffer::push(uint16_t sample) {
  data_[head_] = sample;
  head_ = (head_ + 1) % Config::RADAR_BUFFER_SIZE;
  if (count_ < Config::RADAR_BUFFER_SIZE) {
    count_++;
  }
}

bool CircularBuffer::isFull() const {
  return count_ == Config::RADAR_BUFFER_SIZE;
}

uint16_t CircularBuffer::size() const {
  return count_;
}

void CircularBuffer::copyLatest(uint16_t *destination, uint16_t length) const {
  if (length > count_) {
    length = count_;
  }

  const uint16_t start = (head_ + Config::RADAR_BUFFER_SIZE - length) % Config::RADAR_BUFFER_SIZE;
  for (uint16_t i = 0; i < length; i++) {
    destination[i] = data_[(start + i) % Config::RADAR_BUFFER_SIZE];
  }
}
