#include "fans.h"
#include "pins.h"
#include "config.h"
#include <Arduino.h>

static int partFanSpeed = 0;

void initFans() {
    pinMode(FAN_PART_PIN, OUTPUT);
    pinMode(FAN_HOTEND_PIN, OUTPUT);
    analogWrite(FAN_PART_PIN, 0);
    analogWrite(FAN_HOTEND_PIN, 0);
}

void setFanSpeed(int speed) {
    partFanSpeed = constrain(speed, 0, 255);
    analogWrite(FAN_PART_PIN, partFanSpeed);
}

void updateHotendFan(float hotendTemp) {
    analogWrite(FAN_HOTEND_PIN, (hotendTemp > HOTEND_FAN_THRESHOLD) ? 255 : 0);
}

int getFanSpeed() {
    return partFanSpeed;
}
