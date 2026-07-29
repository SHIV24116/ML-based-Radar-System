#pragma once

#include <Arduino.h>
#include "Config.h"

struct RadarFeatures {
  float mean;
  float variance;
  float rms;
  float energy;
  float fftPeakHz;
  float fftPeakMagnitude;
  float spectralEntropy;
  float peakWidth;
  float standardDeviation;
  float zeroCrossingRate;
  float maximum;
  float minimum;
  float signalRange;
  float spectralCentroid;
};

class FeatureExtraction {
public:
  RadarFeatures extract(const uint16_t *frame, uint16_t length, float sampleRateHz);
  void normalize(const RadarFeatures &features, float *output, uint16_t length) const;

private:
  void computeSpectrum(const float *samples, uint16_t length, float sampleRateHz);

  static constexpr uint16_t FFT_BINS = Config::RADAR_BUFFER_SIZE / 2;
  float magnitudes_[FFT_BINS] = {0.0f};
};
