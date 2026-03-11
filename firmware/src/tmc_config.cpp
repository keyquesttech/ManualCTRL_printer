#include "tmc_config.h"
#include "pins.h"
#include "config.h"
#include <Arduino.h>
#include <TMCStepper.h>

HardwareSerial TMCSerial(TMC_RX_PIN, TMC_TX_PIN);

TMC2209Stepper bedTMC(&TMCSerial, TMC_SENSE_RESISTOR, TMC_BED_ADDR);
TMC2209Stepper zTMC  (&TMCSerial, TMC_SENSE_RESISTOR, TMC_Z_ADDR);
TMC2209Stepper eTMC  (&TMCSerial, TMC_SENSE_RESISTOR, TMC_E_ADDR);

static void configureTMC(TMC2209Stepper &drv, uint16_t current_mA, const char *label) {
    if (!drv.begin()) {
        Serial.print("ERR TMC init failed: ");
        Serial.println(label);
    }
    drv.toff(5);
    drv.rms_current(current_mA);
    drv.microsteps(MICROSTEPS);
    drv.en_spreadCycle(false);
    drv.pwm_autoscale(true);
}

void initTMC() {
    TMCSerial.begin(TMC_BAUD);
    delay(100);

    configureTMC(bedTMC, TMC_BED_CURRENT, "bed");
    configureTMC(zTMC,   TMC_Z_CURRENT,   "z");
    configureTMC(eTMC,   TMC_E_CURRENT,   "e");
}
