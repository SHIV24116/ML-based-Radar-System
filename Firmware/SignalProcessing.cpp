#include "SignalProcessing.h"

#include <math.h>

float adcToVoltage(uint16_t adc) {
  return static_cast<float>(adc) * (3.3f / 4095.0f);
}

float zeroCrossingRate(const float *samples, uint16_t length) {
  if (length < 2) {
    return 0.0f;
  }

  uint16_t crossings = 0;
  for (uint16_t i = 1; i < length; i++) {
    if ((samples[i - 1] <= 0.0f && samples[i] > 0.0f) ||
        (samples[i - 1] >= 0.0f && samples[i] < 0.0f)) {
      crossings++;
    }
  }
  return static_cast<float>(crossings) / static_cast<float>(length - 1);
}

float spectralEntropy(const float *magnitudes, uint16_t length) {
  float total = 0.0f;
  for (uint16_t i = 0; i < length; i++) {
    total += magnitudes[i] + 1e-9f;
  }
  if (total <= 0.0f) {
    return 0.0f;
  }

  float entropy = 0.0f;
  for (uint16_t i = 0; i < length; i++) {
    const float p = (magnitudes[i] + 1e-9f) / total;
    entropy -= p * logf(p);
  }
  return entropy / logf(static_cast<float>(length));
}

uint16_t peakWidthBins(const float *magnitudes, uint16_t length, float peakMagnitude) {
  const float threshold = peakMagnitude * 0.5f;
  uint16_t width = 0;
  for (uint16_t i = 0; i < length; i++) {
    if (magnitudes[i] >= threshold) {
      width++;
    }
  }
  return width;
}
