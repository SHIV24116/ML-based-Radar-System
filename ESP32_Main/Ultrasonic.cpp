#include "Ultrasonic.h"
#include "Config.h"
#include <math.h>

void Ultrasonic::begin() {
  pinMode(Config::ULTRASONIC_TRIG_PIN, OUTPUT);
  pinMode(Config::ULTRASONIC_ECHO_PIN, INPUT);
  digitalWrite(Config::ULTRASONIC_TRIG_PIN, LOW);
  lastUpdateMs_ = millis();
}

void Ultrasonic::update() {
  const uint32_t now = millis();
  if (now - lastUpdateMs_ < Config::ULTRASONIC_UPDATE_MS) {
    return;
  }

  digitalWrite(Config::ULTRASONIC_TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(Config::ULTRASONIC_TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(Config::ULTRASONIC_TRIG_PIN, LOW);

  const uint32_t durationUs = pulseInLong(
      Config::ULTRASONIC_ECHO_PIN,
      HIGH,
      Config::ULTRASONIC_TIMEOUT_US);
   
  previousDistanceM_ = distanceM_;
  const float dt = max((now - lastUpdateMs_) / 1000.0f, 0.001f);
  lastUpdateMs_ = now;

  if (durationUs == 0) {
    present_ = false;
    speedMps_ = 0.0f;
    direction_ = MotionDirection::Unknown;
    return;
  }

  distanceM_ = (durationUs * 0.000343f) / 2.0f;
  present_ = distanceM_ >= Config::PRESENCE_MIN_DISTANCE_M &&
             distanceM_ <= Config::PRESENCE_DISTANCE_THRESHOLD_M;

  if (previousDistanceM_ <= 0.0f || !present_) {
    speedMps_ = 0.0f;
    direction_ = present_ ? MotionDirection::Stationary : MotionDirection::Unknown;
    return;
  }

  const float delta = distanceM_ - previousDistanceM_;
  speedMps_ = fabs(delta) / dt;
  if (fabs(delta) / dt < Config::SPEED_DEADBAND_MPS) {
    direction_ = MotionDirection::Stationary;
  } else if (delta < 0.0f) {
    direction_ = MotionDirection::Approaching;
  } else {
    direction_ = MotionDirection::Receding;
  }
}

float Ultrasonic::getDistanceM() const {
  return distanceM_;
}

float Ultrasonic::getSpeedMps() const {
  return speedMps_;
}

bool Ultrasonic::isObjectPresent() const {
  return present_;
}

MotionDirection Ultrasonic::getMotionDirection() const {
  return direction_;
}

const char *motionDirectionText(MotionDirection direction) {
  switch (direction) {
    case MotionDirection::Approaching:
      return "Approaching";
    case MotionDirection::Receding:
      return "Receding";
    case MotionDirection::Stationary:
      return "Stationary";
    default:
      return "Unknown";
  }
}


