#include "stepper_ctrl.h"
#include "pins.h"
#include "config.h"
#include "endstop.h"
#include "temperature.h"
#include "fans.h"
#include <AccelStepper.h>

static AccelStepper bedStepper(AccelStepper::DRIVER, BED_STEP_PIN, BED_DIR_PIN);
static AccelStepper zStepper  (AccelStepper::DRIVER, Z_STEP_PIN,   Z_DIR_PIN);
static AccelStepper eStepper  (AccelStepper::DRIVER, E_STEP_PIN,   E_DIR_PIN);

void initSteppers() {
    pinMode(BED_ENABLE_PIN, OUTPUT);
    pinMode(Z_ENABLE_PIN,   OUTPUT);
    pinMode(E_ENABLE_PIN,   OUTPUT);

    enableSteppers();

    bedStepper.setPinsInverted(BED_DIR_INVERT, false, false);
    zStepper.setPinsInverted  (Z_DIR_INVERT,   false, false);
    eStepper.setPinsInverted  (E_DIR_INVERT,   false, false);

    bedStepper.setMaxSpeed(BED_MAX_SPEED_SPS);
    bedStepper.setAcceleration(BED_MAX_ACCEL_SPS);
    zStepper.setMaxSpeed(Z_MAX_SPEED_SPS);
    zStepper.setAcceleration(Z_MAX_ACCEL_SPS);
    eStepper.setMaxSpeed(E_MAX_SPEED_SPS);
    eStepper.setAcceleration(E_MAX_ACCEL_SPS);
}

void runSteppers() {
    bedStepper.run();
    zStepper.run();
    eStepper.run();
}

// Velocity-mode: set speed and move toward a far-away target.
// The stepper accelerates to the requested speed and runs continuously
// until stopXxx() is called.

void startBed(float speedDegPerSec) {
    if (speedDegPerSec == 0.0f) { stopBed(); return; }
    float sps = fabsf(speedDegPerSec) * BED_STEPS_PER_DEG;
    if (sps > BED_MAX_SPEED_SPS) sps = BED_MAX_SPEED_SPS;
    bedStepper.setMaxSpeed(sps);
    long dir = (speedDegPerSec > 0.0f) ? 1000000L : -1000000L;
    bedStepper.moveTo(bedStepper.currentPosition() + dir);
}

void startZ(float speedMmPerSec) {
    if (speedMmPerSec == 0.0f) { stopZ(); return; }
    float sps = fabsf(speedMmPerSec) * Z_STEPS_PER_MM;
    if (sps > Z_MAX_SPEED_SPS) sps = Z_MAX_SPEED_SPS;
    zStepper.setMaxSpeed(sps);
    long dir = (speedMmPerSec > 0.0f) ? 1000000L : -1000000L;
    zStepper.moveTo(zStepper.currentPosition() + dir);
}

void startExtruder(float speedMmPerSec) {
    if (speedMmPerSec == 0.0f) { stopExtruder(); return; }
    float sps = fabsf(speedMmPerSec) * E_STEPS_PER_MM;
    if (sps > E_MAX_SPEED_SPS) sps = E_MAX_SPEED_SPS;
    eStepper.setMaxSpeed(sps);
    long dir = (speedMmPerSec > 0.0f) ? 1000000L : -1000000L;
    eStepper.moveTo(eStepper.currentPosition() + dir);
}

void stopBed()      { bedStepper.stop(); }
void stopZ()        { zStepper.stop(); }
void stopExtruder() { eStepper.stop(); }
void stopAll()      { stopBed(); stopZ(); stopExtruder(); }

void emergencyStop() {
    bedStepper.setCurrentPosition(bedStepper.currentPosition());
    zStepper.setCurrentPosition(zStepper.currentPosition());
    eStepper.setCurrentPosition(eStepper.currentPosition());

    digitalWrite(BED_ENABLE_PIN, HIGH);
    digitalWrite(Z_ENABLE_PIN,   HIGH);
    digitalWrite(E_ENABLE_PIN,   HIGH);

    setHotendTarget(0);
    setFanSpeed(0);
}

void enableSteppers() {
    digitalWrite(BED_ENABLE_PIN, LOW);
    digitalWrite(Z_ENABLE_PIN,   LOW);
    digitalWrite(E_ENABLE_PIN,   LOW);
}

void homeZ() {
    // 1. Lift Z a few mm
    zStepper.setMaxSpeed(HOME_TRAVEL_SPEED_MM_S * Z_STEPS_PER_MM);
    zStepper.move((long)(HOME_LIFT_MM * Z_STEPS_PER_MM));
    while (zStepper.isRunning()) {
        zStepper.run();
        updateTemperature();
    }

    // 2. Probe downward until endstop triggers
    zStepper.setMaxSpeed(HOME_PROBE_SPEED_MM_S * Z_STEPS_PER_MM);
    zStepper.move((long)(-Z_MAX_TRAVEL * Z_STEPS_PER_MM));
    unsigned long deadline = millis() + HOME_TIMEOUT_MS;
    while (zStepper.isRunning()) {
        zStepper.run();
        updateTemperature();
        if (readZEndstop()) {
            zStepper.setCurrentPosition(zStepper.currentPosition());
            break;
        }
        if (millis() > deadline) {
            zStepper.setCurrentPosition(zStepper.currentPosition());
            Serial.println("ERR HOME_TIMEOUT");
            return;
        }
    }

    // 3. Zero and move to rest height
    zStepper.setCurrentPosition(0);
    zStepper.setMaxSpeed(HOME_TRAVEL_SPEED_MM_S * Z_STEPS_PER_MM);
    zStepper.move((long)(HOME_REST_MM * Z_STEPS_PER_MM));
    while (zStepper.isRunning()) {
        zStepper.run();
        updateTemperature();
    }
}

float getBedPosition() { return bedStepper.currentPosition() / BED_STEPS_PER_DEG; }
float getZPosition()   { return zStepper.currentPosition()   / Z_STEPS_PER_MM; }
float getEPosition()   { return eStepper.currentPosition()   / E_STEPS_PER_MM; }

void zeroBed()      { bedStepper.setCurrentPosition(0); }
void zeroZ()        { zStepper.setCurrentPosition(0); }
void zeroExtruder() { eStepper.setCurrentPosition(0); }
