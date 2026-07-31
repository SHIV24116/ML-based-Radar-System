#include "RadarADC.h"
#include "Config.h"

void RadarADC::begin() {
  analogReadResolution(12);
  analogSetPinAttenuation(Config::RADAR_ADC_PIN, ADC_11db);
  pinMode(Config::RADAR_ADC_PIN, INPUT);
  lastSampleUs_ = micros();
}

void RadarADC::sample() {
  const uint32_t now = micros();
  if (now - lastSampleUs_ < Config::RADAR_SAMPLE_PERIOD_US) {
    return;
  }
  lastSampleUs_ += Config::RADAR_SAMPLE_PERIOD_US;
  buffer_.push(static_cast<uint16_t>(analogRead(Config::RADAR_ADC_PIN)));
}

bool RadarADC::isFrameReady() const {
  return buffer_.isFull();
}

void RadarADC::getFrame(uint16_t *destination, uint16_t length) const {
  buffer_.copyLatest(destination, length);
}

void RadarADC::clear() {
  buffer_.clear();
}
