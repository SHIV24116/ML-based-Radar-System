#include "Config.h"
#include "FeatureExtraction.h"
#include "MLInference.h"
#include "RadarADC.h"
#include "Ultrasonic.h"

RadarADC radar;
Ultrasonic ultrasonic;
FeatureExtraction featureExtraction;
MLInference ml;

uint16_t radarFrame[Config::RADAR_BUFFER_SIZE];
float mlInput[Config::FEATURE_COUNT];

uint32_t lastInferenceMs = 0;
Prediction latestPrediction = {"Unknown", 0.0f};

void setup() {
  Serial.begin(Config::SERIAL_BAUD);

  radar.begin();
  ultrasonic.begin();
  ml.begin();
}

void loop() {

  radar.sample();
  ultrasonic.update();

  uint32_t now = millis();

  if (!ultrasonic.isObjectPresent()) {
    return;
  }

  if (radar.isFrameReady() &&
      now - lastInferenceMs >= Config::INFERENCE_UPDATE_MS) {

    radar.getFrame(radarFrame, Config::RADAR_BUFFER_SIZE);

    RadarFeatures features =
        featureExtraction.extract(
            radarFrame,
            Config::RADAR_BUFFER_SIZE,
            Config::RADAR_SAMPLE_RATE_HZ);

    featureExtraction.normalize(
        features,
        mlInput,
        Config::FEATURE_COUNT);

    latestPrediction =
        ml.predict(
            mlInput,
            Config::FEATURE_COUNT);

    lastInferenceMs = now;

    if (Config::DEBUG_SERIAL) {

      Serial.print("object=");
      Serial.print(latestPrediction.label);

      Serial.print(",confidence=");
      Serial.print(latestPrediction.confidence, 3);

      Serial.print(",distance_m=");
      Serial.print(ultrasonic.getDistanceM(), 2);

      Serial.print(",speed_mps=");
      Serial.print(ultrasonic.getSpeedMps(), 2);

      Serial.print(",motion=");
      Serial.println(
          motionDirectionText(
              ultrasonic.getMotionDirection()));
    }
  }
}