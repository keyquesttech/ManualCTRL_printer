#include "temperature.h"
#include "pins.h"
#include "config.h"
#include <Arduino.h>

static float hotendTemp    = 0.0f;
static float hotendTarget  = 0.0f;
static float pidIntegral   = 0.0f;
static float pidLastError  = 0.0f;
static unsigned long lastPidTime = 0;

static float readThermistor() {
    int raw = analogRead(HOTEND_THERM_PIN);
    if (raw <= 0)    return 999.0f;
    if (raw >= 4095) return 0.0f;

    float resistance = THERM_PULLUP * (float)raw / (4095.0f - (float)raw);
    float steinhart  = logf(resistance / THERM_NOMINAL);
    steinhart /= THERM_BETA;
    steinhart += 1.0f / (THERM_NOMINAL_TEMP + 273.15f);
    steinhart  = 1.0f / steinhart;
    steinhart -= 273.15f;
    return steinhart;
}

void initTemperature() {
    analogReadResolution(12);
    pinMode(HOTEND_HEATER_PIN, OUTPUT);
    digitalWrite(HOTEND_HEATER_PIN, LOW);
}

void updateTemperature() {
    hotendTemp = readThermistor();

    unsigned long now = millis();
    if (now - lastPidTime < PID_INTERVAL_MS) return;
    lastPidTime = now;

    if (hotendTarget <= 0.0f) {
        analogWrite(HOTEND_HEATER_PIN, 0);
        pidIntegral  = 0.0f;
        pidLastError = 0.0f;
        return;
    }

    float dt    = PID_INTERVAL_MS / 1000.0f;
    float error = hotendTarget - hotendTemp;

    pidIntegral += error * dt;
    pidIntegral  = constrain(pidIntegral, -PID_I_MAX, PID_I_MAX);

    float derivative = (error - pidLastError) / dt;
    pidLastError = error;

    float output = PID_KP * error + PID_KI * pidIntegral + PID_KD * derivative;
    int pwm = constrain((int)output, 0, 255);
    analogWrite(HOTEND_HEATER_PIN, pwm);
}

void setHotendTarget(float temp) {
    hotendTarget = constrain(temp, 0.0f, MAX_HOTEND_TEMP);
    pidIntegral  = 0.0f;
    pidLastError = 0.0f;
}

float getHotendTemp()   { return hotendTemp; }
float getHotendTarget() { return hotendTarget; }
