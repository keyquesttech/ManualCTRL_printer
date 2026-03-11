#include <Arduino.h>
#include "command_parser.h"
#include "stepper_ctrl.h"
#include "tmc_config.h"
#include "temperature.h"
#include "fans.h"
#include "endstop.h"
#include "safety.h"

void setup() {
    // Let USB VBUS and PHY stabilize before CDC init (helps enumeration on some boards)
    delay(200);

    Serial.begin(115200);
    // Do not block on Serial — host connects when CDC enumerates

    initEndstops();
    initFans();
    initTemperature();
    initTMC();
    initSteppers();
    initSafety();

    Serial.println("ok READY ManualCTRL v1.0");
}

void loop() {
    processSerialCommands();
    runSteppers();
    updateTemperature();
    updateHotendFan(getHotendTemp());
    checkSafety();
}
