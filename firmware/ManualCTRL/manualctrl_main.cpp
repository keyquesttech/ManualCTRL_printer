#include <Arduino.h>
#include "command_parser.h"
#include "stepper_ctrl.h"
#include "tmc_config.h"
#include "temperature.h"
#include "fans.h"
#include "endstop.h"
#include "safety.h"

void setup() {
    Serial.begin(115200);
    while (!Serial && millis() < 3000)
        ;

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
