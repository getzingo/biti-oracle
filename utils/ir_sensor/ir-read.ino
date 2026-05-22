// Arduino Nano IR Temperature Sensor Reader
// Seeed Studio Grove IR Temperature Sensor v1.2
// Uses INTERNAL 1.1V reference for ADC (manufacturer spec)
// A6 = OBJ (object temperature, thermopile)
// A7 = SUR (ambient temperature, NTC thermistor)

const int OBJ_PIN = A6;  // object temperature (thermopile)
const int SUR_PIN = A7;  // surrounding temperature (NTC)
const int SAMPLES = 10;

void setup() {
  Serial.begin(9600);
  analogReference(INTERNAL);  // 1.1V internal reference
  delay(100);
}

void loop() {
  long sum_obj = 0, sum_sur = 0;
  for (int i = 0; i < SAMPLES; i++) {
    sum_obj += analogRead(OBJ_PIN);
    sum_sur += analogRead(SUR_PIN);
    delay(5);
  }
  int avg_obj = sum_obj / SAMPLES;
  int avg_sur = sum_sur / SAMPLES;

  // Format: IR:A6=obj_val,A7=sur_val
  Serial.print("IR:");
  Serial.print("A6=");
  Serial.print(avg_obj);
  Serial.print(",A7=");
  Serial.println(avg_sur);

  delay(1000);
}