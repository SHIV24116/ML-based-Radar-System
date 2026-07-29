#include "OLED.h"
#include "Config.h"

#include <Wire.h>

OLEDDisplay::OLEDDisplay()
    : display_(Config::OLED_WIDTH, Config::OLED_HEIGHT, &Wire, Config::OLED_RESET_PIN) {}

bool OLEDDisplay::begin() {
  Wire.begin(Config::OLED_SDA_PIN, Config::OLED_SCL_PIN);
  return display_.begin(SSD1306_SWITCHCAPVCC, 0x3C);
}

void OLEDDisplay::showSplash() {
  display_.clearDisplay();
  display_.setTextColor(SSD1306_WHITE);
  display_.setTextSize(1);
  display_.setCursor(0, 8);
  display_.println("RADAR OBJECT");
  display_.println("DETECTOR");
  display_.println();
  display_.println("Initializing...");
  display_.display();
}

void OLEDDisplay::showWaiting() {
  display_.clearDisplay();
  display_.setTextColor(SSD1306_WHITE);
  display_.setTextSize(1);
  display_.setCursor(0, 0);
  display_.println("Status: Monitoring");
  display_.println();
  display_.println("Waiting for");
  display_.println("Object...");
  display_.display();
}

void OLEDDisplay::showObject(
    const Prediction &prediction,
    float distanceM,
    float speedMps,
    MotionDirection direction) {
  display_.clearDisplay();
  display_.setTextColor(SSD1306_WHITE);
  display_.setTextSize(1);
  display_.setCursor(0, 0);
  display_.print("Object: ");
  display_.println(prediction.label);
  display_.print("Conf: ");
  display_.print(prediction.confidence * 100.0f, 1);
  display_.println("%");
  display_.print("Dist: ");
  display_.print(distanceM, 2);
  display_.println(" m");
  display_.print("Speed: ");
  display_.print(speedMps, 2);
  display_.println(" m/s");
  display_.print("Motion: ");
  display_.println(motionDirectionText(direction));
  display_.display();
}

void OLEDDisplay::showError(const String &message) {
  display_.clearDisplay();
  display_.setTextColor(SSD1306_WHITE);
  display_.setTextSize(1);
  display_.setCursor(0, 0);
  display_.println("ERROR");
  display_.println(message);
  display_.display();
}

void OLEDDisplay::clear() {
  display_.clearDisplay();
  display_.display();
}
