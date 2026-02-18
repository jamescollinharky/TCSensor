/*
 * Multi-band NIR sensor: cycle through LEDs one at a time and output
 * one time-series row per cycle (ms, 1300, 1460, 1650, 1720, 1900).
 * Common-anode LEDs: 0 = on, 255 = off.
 * Sensor on A5.
 */

const int LED_1300_PIN = 3;
const int LED_1460_PIN = 5;
const int LED_1650_PIN = 6;
const int LED_1720_PIN = 9;
const int LED_1900_PIN = 10;
const int SENSOR_PIN = A5;

// PWM value for "LED on" (0 = max for common anode). Reduce if needed.
const int LED_ON_PWM = 0;
const int LED_OFF_PWM = 255;

// Delay after switching LED before reading (ms). Increase if readings are noisy.
const int STABILIZE_MS = 3;

// Optional: delay between full cycles (ms). 0 = as fast as possible.
const int CYCLE_DELAY_MS = 0;

// Band order for cycling
const int BAND_PINS[] = {
  LED_1300_PIN,
  LED_1460_PIN,
  LED_1650_PIN,
  LED_1720_PIN,
  LED_1900_PIN
};
const int NUM_BANDS = 5;

int values[5];  // 1300, 1460, 1650, 1720, 1900
bool headerSent = false;

void allLedsOff() {
  analogWrite(LED_1300_PIN, LED_OFF_PWM);
  analogWrite(LED_1460_PIN, LED_OFF_PWM);
  analogWrite(LED_1650_PIN, LED_OFF_PWM);
  analogWrite(LED_1720_PIN, LED_OFF_PWM);
  analogWrite(LED_1900_PIN, LED_OFF_PWM);
}

void setup() {
  Serial.begin(9600);
  pinMode(LED_1300_PIN, OUTPUT);
  pinMode(LED_1460_PIN, OUTPUT);
  pinMode(LED_1650_PIN, OUTPUT);
  pinMode(LED_1720_PIN, OUTPUT);
  pinMode(LED_1900_PIN, OUTPUT);
  allLedsOff();
}

void loop() {
  unsigned long t0 = millis();

  // Cycle: one band on at a time, read sensor
  for (int i = 0; i < NUM_BANDS; i++) {
    allLedsOff();
    analogWrite(BAND_PINS[i], LED_ON_PWM);
    delay(STABILIZE_MS);
    values[i] = analogRead(SENSOR_PIN);
  }
  allLedsOff();

  // One CSV row per cycle (merge-friendly time series)
  if (!headerSent) {
    Serial.println("ms,1300,1460,1650,1720,1900");
    headerSent = true;
  }
  Serial.print(t0);
  Serial.print(",");
  Serial.print(values[0]);
  Serial.print(",");
  Serial.print(values[1]);
  Serial.print(",");
  Serial.print(values[2]);
  Serial.print(",");
  Serial.print(values[3]);
  Serial.print(",");
  Serial.println(values[4]);

  if (CYCLE_DELAY_MS > 0) {
    delay(CYCLE_DELAY_MS);
  }
}
