const int adcPin = 34;        // ESP32 ADC pin
const int sampleDelay = 500; // microseconds (~2 kHz)

void setup() {
  Serial.begin(115200);
  analogReadResolution(12);  // 0–4095
}

void loop() {
  int sample = analogRead(adcPin);
  Serial.println(sample);
  delayMicroseconds(sampleDelay);
}
