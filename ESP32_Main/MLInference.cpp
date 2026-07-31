#include "MLInference.h"

bool MLInference::begin() {
  ready_ = false;
  return true;
}

Prediction MLInference::predict(const float *features, uint16_t length) {
  (void)length;

  Prediction prediction;
  prediction.label = "Unknown";
  prediction.confidence = 0.0f;

  // Replace this fallback with TensorFlow Lite Micro inference after exporting
  // Models/model.tflite to a C array. The fallback keeps the firmware usable
  // for hardware bring-up and verifies the full sensor/display workflow.
  if (!ready_) {
    const float peakHz = features[4];
    const float energy = features[3];
    if (energy > 0.01f && peakHz >= 10.0f) {
      prediction.label = peakHz < 80.0f ? "Human" : "Moving";
      prediction.confidence = min(0.80f, 0.45f + energy);
    }
    return prediction;
  }

  return prediction;
}
