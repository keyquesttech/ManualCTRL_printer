#include "endstop.h"
#include "pins.h"
#include <Arduino.h>

void initEndstops() {
    pinMode(Z_ENDSTOP_PIN, INPUT_PULLUP);
}

bool readZEndstop() {
    return digitalRead(Z_ENDSTOP_PIN) == LOW;
}
