/*
  Project: Real-Time Ultrasonic Object Shape Reconstruction and Motion Signature Visualization
  Board:   ESP32 DevKit V1

  Hardware:
  - HC-SR04 TRIG -> GPIO5
  - HC-SR04 ECHO -> GPIO18 through a voltage divider
  - SG90 servo signal -> GPIO13
  - Sensor and servo use external regulated 5V with common ground

  Serial packet format:
  ANGLE,DISTANCE,TIME
  Example: 54,123.60,10345
*/

#include <ESP32Servo.h>

// Pin definitions.
constexpr int TRIG_PIN = 5;
constexpr int ECHO_PIN = 18;
constexpr int SERVO_PIN = 13;

// Servo sweep configuration.
constexpr int MIN_ANGLE = 30;
constexpr int MAX_ANGLE = 150;
constexpr int STEP_ANGLE = 2;
constexpr int SERVO_DELAY_MS = 15;

// Ultrasonic measurement configuration.
constexpr int NUM_SAMPLES = 3;
constexpr unsigned long ECHO_TIMEOUT_US = 30000;
constexpr float MIN_DISTANCE_CM = 2.0;
constexpr float MAX_DISTANCE_CM = 400.0;
constexpr float SPEED_OF_SOUND_CM_PER_US = 0.0343;

Servo scannerServo;
int currentAngle = MIN_ANGLE;
bool forwardScan = true;

float readDistance();
float getAverageDistance();
bool validDistance(float distanceCm);
void scanServo();
void sendPacket(float distanceCm);

void setup() {
  Serial.begin(115200);

  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  digitalWrite(TRIG_PIN, LOW);

  scannerServo.setPeriodHertz(50);
  scannerServo.attach(SERVO_PIN, 500, 2400);
  scannerServo.write(currentAngle);

  delay(1000);
}

void loop() {
  const float distanceCm = getAverageDistance();
  sendPacket(distanceCm);
  scanServo();
}

float readDistance() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);

  const unsigned long duration = pulseIn(ECHO_PIN, HIGH, ECHO_TIMEOUT_US);
  if (duration == 0) {
    return -1.0;
  }

  return (duration * SPEED_OF_SOUND_CM_PER_US) / 2.0;
}

float getAverageDistance() {
  float total = 0.0;
  int validSamples = 0;

  for (int i = 0; i < NUM_SAMPLES; i++) {
    const float distanceCm = readDistance();
    if (validDistance(distanceCm)) {
      total += distanceCm;
      validSamples++;
    }
    delay(5);
  }

  if (validSamples == 0) {
    return -1.0;
  }
  return total / validSamples;
}

bool validDistance(float distanceCm) {
  return distanceCm >= MIN_DISTANCE_CM && distanceCm <= MAX_DISTANCE_CM;
}

void scanServo() {
  if (forwardScan) {
    currentAngle += STEP_ANGLE;
    if (currentAngle >= MAX_ANGLE) {
      currentAngle = MAX_ANGLE;
      forwardScan = false;
    }
  } else {
    currentAngle -= STEP_ANGLE;
    if (currentAngle <= MIN_ANGLE) {
      currentAngle = MIN_ANGLE;
      forwardScan = true;
    }
  }

  scannerServo.write(currentAngle);
  delay(SERVO_DELAY_MS);
}

void sendPacket(float distanceCm) {
  Serial.print(currentAngle);
  Serial.print(',');
  Serial.print(distanceCm, 2);
  Serial.print(',');
  Serial.println(millis());
}