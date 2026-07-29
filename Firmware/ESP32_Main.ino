#include "Config.h"
#include "FeatureExtraction.h"
#include "MLInference.h"
#include "OLED.h"
#include "RadarADC.h"
#include "Ultrasonic.h"

RadarADC radar;
Ultrasonic ultrasonic;
OLEDDisplay oled;
FeatureExtraction featureExtraction;
MLInference ml;

uint16_t radarFrame[Config::RADAR_BUFFER_SIZE];
float mlInput[Config::FEATURE_COUNT];

uint32_t lastOledUpdateMs = 0;
uint32_t lastInferenceMs = 0;
Prediction latestPrediction = {"Unknown", 0.0f};

void setup() {
  Serial.begin(Config::SERIAL_BAUD);
  radar.begin();
  ultrasonic.begin();

  if (!oled.begin()) {
    if (Config::DEBUG_SERIAL) {
      Serial.println("OLED initialization failed");
    }
  } else {
    oled.showSplash();
  }

  ml.begin();
}

void loop() {
  radar.sample();
  ultrasonic.update();

  const uint32_t now = millis();
  const bool objectPresent = ultrasonic.isObjectPresent();

  if (!objectPresent) {
    if (now - lastOledUpdateMs >= Config::OLED_UPDATE_MS) {
      oled.showWaiting();
      lastOledUpdateMs = now;
    }
    return;
  }

  if (radar.isFrameReady() && now - lastInferenceMs >= Config::INFERENCE_UPDATE_MS) {
    radar.getFrame(radarFrame, Config::RADAR_BUFFER_SIZE);
    const RadarFeatures features = featureExtraction.extract(
        radarFrame,
        Config::RADAR_BUFFER_SIZE,
        Config::RADAR_SAMPLE_RATE_HZ);
    featureExtraction.normalize(features, mlInput, Config::FEATURE_COUNT);
    latestPrediction = ml.predict(mlInput, Config::FEATURE_COUNT);
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
      Serial.println(motionDirectionText(ultrasonic.getMotionDirection()));
    }
  }

  if (now - lastOledUpdateMs >= Config::OLED_UPDATE_MS) {
    oled.showObject(
        latestPrediction,
        ultrasonic.getDistanceM(),
        ultrasonic.getSpeedMps(),
        ultrasonic.getMotionDirection());
    lastOledUpdateMs = now;
  }
}
