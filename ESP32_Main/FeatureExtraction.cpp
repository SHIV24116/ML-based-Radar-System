#include "FeatureExtraction.h"

#include <math.h>
#include "SignalProcessing.h"

RadarFeatures FeatureExtraction::extract(const uint16_t *frame, uint16_t length, float sampleRateHz) {
  RadarFeatures features{};
  if (length == 0) {
    return features;
  }

  static float centered[Config::RADAR_BUFFER_SIZE];
  float sum = 0.0f;
  features.minimum = 100000.0f;
  features.maximum = -100000.0f;

  for (uint16_t i = 0; i < length; i++) {
    const float voltage = adcToVoltage(frame[i]);
    centered[i] = voltage;
    sum += voltage;
    features.minimum = min(features.minimum, voltage);
    features.maximum = max(features.maximum, voltage);
  }

  features.mean = sum / static_cast<float>(length);
  float sqSum = 0.0f;
  float energy = 0.0f;
  for (uint16_t i = 0; i < length; i++) {
    centered[i] -= features.mean;
    sqSum += centered[i] * centered[i];
    energy += centered[i] * centered[i];
  }

  features.variance = sqSum / static_cast<float>(length);
  features.standardDeviation = sqrtf(features.variance);
  features.rms = sqrtf(energy / static_cast<float>(length));
  features.energy = energy;
  features.signalRange = features.maximum - features.minimum;
  features.zeroCrossingRate = ::zeroCrossingRate(centered, length);

  computeSpectrum(centered, length, sampleRateHz);
  const uint16_t bins = length / 2;
  float magnitudeSum = 1e-9f;
  float weightedFrequency = 0.0f;
  uint16_t peakIndex = 0;
  features.fftPeakMagnitude = 0.0f;

  for (uint16_t i = 1; i < bins; i++) {
    const float frequency = (static_cast<float>(i) * sampleRateHz) / static_cast<float>(length);
    const float magnitude = magnitudes_[i];
    magnitudeSum += magnitude;
    weightedFrequency += frequency * magnitude;
    if (frequency >= 10.0f && frequency <= 500.0f && magnitude > features.fftPeakMagnitude) {
      features.fftPeakMagnitude = magnitude;
      peakIndex = i;
    }
  }

  features.fftPeakHz = (static_cast<float>(peakIndex) * sampleRateHz) / static_cast<float>(length);
  features.spectralEntropy = ::spectralEntropy(magnitudes_, bins);
  features.peakWidth = static_cast<float>(peakWidthBins(magnitudes_, bins, features.fftPeakMagnitude));
  features.spectralCentroid = weightedFrequency / magnitudeSum;
  return features;
}

void FeatureExtraction::normalize(const RadarFeatures &features, float *output, uint16_t length) const {
  if (length < Config::FEATURE_COUNT) {
    return;
  }

  output[0] = features.mean;
  output[1] = features.variance;
  output[2] = features.rms;
  output[3] = features.energy;
  output[4] = features.fftPeakHz;
  output[5] = features.fftPeakMagnitude;
  output[6] = features.spectralEntropy;
  output[7] = features.peakWidth;
  output[8] = features.standardDeviation;
  output[9] = features.zeroCrossingRate;
  output[10] = features.maximum;
  output[11] = features.minimum;
  output[12] = features.signalRange;
  output[13] = features.spectralCentroid;
}

void FeatureExtraction::computeSpectrum(const float *samples, uint16_t length, float sampleRateHz) {
  (void)sampleRateHz;
  const uint16_t bins = length / 2;
  for (uint16_t k = 0; k < bins; k++) {
    float real = 0.0f;
    float imag = 0.0f;
    for (uint16_t n = 0; n < length; n++) {
      const float angle = -2.0f * PI * static_cast<float>(k) * static_cast<float>(n) / static_cast<float>(length);
      real += samples[n] * cosf(angle);
      imag += samples[n] * sinf(angle);
    }
    magnitudes_[k] = sqrtf(real * real + imag * imag);
  }
}
