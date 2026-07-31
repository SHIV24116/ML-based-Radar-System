#pragma once

#include <Arduino.h>

float adcToVoltage(uint16_t adc);
float zeroCrossingRate(const float *samples, uint16_t length);
float spectralEntropy(const float *magnitudes, uint16_t length);
uint16_t peakWidthBins(const float *magnitudes, uint16_t length, float peakMagnitude);
