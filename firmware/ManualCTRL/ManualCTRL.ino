#include <Arduino.h>

/* Forward declarations only — avoid including custom headers in .ino so STM32 toolchain parses setup/loop correctly */
extern void initEndstops(void);
extern void initFans(void);
extern void initTemperature(void);
extern void initTMC(void);
extern void initSteppers(void);
extern void initSafety(void);
extern void processSerialCommands(void);
extern void runSteppers(void);
extern void updateTemperature(void);
extern void updateHotendFan(float);
extern float getHotendTemp(void);
extern void checkSafety(void);

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
