const int adcPin = 34;          // ESP32 ADC pin connected to conditioned radar signal
const int sampleDelayUs = 500;  // 500 us gives about 2 kHz sampling

void setup() {
  Serial.begin(115200);
  analogReadResolution(12);    // 0 to 4095
  analogSetPinAttenuation(adcPin, ADC_11db); // Allows readings close to 3.3 V
}

void loop() {
  int sample = analogRead(adcPin);
  Serial.println(sample);
  delayMicroseconds(sampleDelayUs);
}
