#include "safety.h"
#include "config.h"
#include "temperature.h"
#include "stepper_ctrl.h"
#include "fans.h"
#include <Arduino.h>

static bool safetyEnabled       = true;
static unsigned long lastCheck  = 0;
static float prevTemp           = 0.0f;
static int stagnantCount        = 0;

void initSafety() {
    safetyEnabled  = true;
    stagnantCount  = 0;
    prevTemp       = 0.0f;
}

void checkSafety() {
    if (!safetyEnabled) return;

    unsigned long now = millis();
    if (now - lastCheck < 2000) return;
    lastCheck = now;

    float temp   = getHotendTemp();
    float target = getHotendTarget();

    if (target > 50.0f && temp < target - 20.0f) {
        if (fabsf(temp - prevTemp) < 1.0f) {
            stagnantCount++;
            if (stagnantCount > 15) {
                emergencyStop();
                setHotendTarget(0);
                setFanSpeed(0);
                Serial.println("ERR THERMAL_RUNAWAY");
            }
        } else {
            stagnantCount = 0;
        }
    } else {
        stagnantCount = 0;
    }

    if (temp > MAX_HOTEND_TEMP + 10.0f) {
        emergencyStop();
        setHotendTarget(0);
        setFanSpeed(0);
        Serial.println("ERR OVER_TEMPERATURE");
    }

    prevTemp = temp;
}

void setSafety(bool enabled) {
    safetyEnabled = enabled;
    if (enabled) {
        stagnantCount = 0;
        prevTemp = getHotendTemp();
    }
}

bool isSafetyOn() {
    return safetyEnabled;
}
