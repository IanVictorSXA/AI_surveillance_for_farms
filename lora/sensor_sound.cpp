#include <Arduino.h>

static const int SENSOR_OUT_PIN = 12; // radar O -> GPIO12
static const int SPEAKER_PIN    = 4;  // amp input (white wire)

int pwmResolution = 8;
int dutyMid = 128;     // loudest square-wave into amp
int freq = 2500;

const unsigned long playDuration = 3000;
const unsigned long cooldownTime = 2000;
unsigned long lastTrigger = 0;

void playSound(unsigned long ms) {
  ledcWriteTone(SPEAKER_PIN, freq);
  ledcWrite(SPEAKER_PIN, dutyMid);
  delay(ms);
  ledcWrite(SPEAKER_PIN, 0);
  ledcWriteTone(SPEAKER_PIN, 0);
}

void setup() {
  Serial.begin(115200);
  delay(300);

  pinMode(SENSOR_OUT_PIN, INPUT_PULLUP); // pull-up so unplugged reads 1

  if (!ledcAttach(SPEAKER_PIN, freq, pwmResolution)) {
    Serial.println("ledcAttach failed");
    while (1) delay(200);
  }
  ledcWrite(SPEAKER_PIN, 0);

  Serial.println("Ready: motion -> sound");
}

void loop() {
  int motion = digitalRead(SENSOR_OUT_PIN);

  // print occasionally
  static unsigned long lastPrint = 0;
  if (millis() - lastPrint > 300) {
    lastPrint = millis();
    Serial.print("Radar OUT = ");
    Serial.println(motion);
  }

  // MOST radar OUT pins pull LOW when detected
  if (motion == LOW) {
    unsigned long now = millis();
    if (now - lastTrigger > cooldownTime) {
      lastTrigger = now;
      Serial.println("Detected -> sound");
      playSound(playDuration);
    }
  }

  delay(20);
}