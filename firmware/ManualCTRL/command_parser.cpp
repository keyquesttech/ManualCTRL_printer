#include "command_parser.h"
#include "stepper_ctrl.h"
#include "temperature.h"
#include "fans.h"
#include "safety.h"
#include <Arduino.h>

static char cmdBuf[128];
static uint8_t cmdLen = 0;

static float parseParam(const char *str, char key) {
    const char *p = str;
    while (*p) {
        if (*p == key) return atof(p + 1);
        p++;
    }
    return 0.0f;
}

static void reportStatus() {
    Serial.print("T:");    Serial.print(getHotendTemp(), 1);
    Serial.print(" TT:");  Serial.print(getHotendTarget(), 1);
    Serial.print(" Y:");   Serial.print(getBedPosition(), 2);
    Serial.print(" Z:");   Serial.print(getZPosition(), 2);
    Serial.print(" E:");   Serial.print(getEPosition(), 2);
    Serial.print(" FAN:"); Serial.print(getFanSpeed());
    Serial.print(" SAF:"); Serial.println(isSafetyOn() ? 1 : 0);
}

static void executeCommand(const char *cmd) {
    if (strncmp(cmd, "MOV ", 4) == 0) {
        char axis = cmd[4];
        float val = atof(cmd + 5);
        if      (axis == 'B') startBed(val);
        else if (axis == 'Z') startZ(val);
        else if (axis == 'E') startExtruder(val);
        else { Serial.println("ERR bad axis"); return; }
        Serial.println("ok");

    } else if (strncmp(cmd, "STOP", 4) == 0) {
        if (cmd[4] == ' ') {
            char axis = cmd[5];
            if      (axis == 'B') stopBed();
            else if (axis == 'Z') stopZ();
            else if (axis == 'E') stopExtruder();
            else stopAll();
        } else {
            stopAll();
        }
        Serial.println("ok");

    } else if (strncmp(cmd, "TEMP ", 5) == 0) {
        setHotendTarget(atof(cmd + 5));
        Serial.println("ok");

    } else if (strncmp(cmd, "FAN ", 4) == 0) {
        setFanSpeed(atoi(cmd + 4));
        Serial.println("ok");

    } else if (strncmp(cmd, "HOME", 4) == 0) {
        homeZ();
        Serial.println("ok");

    } else if (strncmp(cmd, "ESTOP", 5) == 0) {
        emergencyStop();
        Serial.println("ok");

    } else if (strncmp(cmd, "ENABLE", 6) == 0) {
        enableSteppers();
        Serial.println("ok");

    } else if (strncmp(cmd, "ZERO ", 5) == 0) {
        char axis = cmd[5];
        if      (axis == 'B') zeroBed();
        else if (axis == 'Z') zeroZ();
        else if (axis == 'E') zeroExtruder();
        Serial.println("ok");

    } else if (strncmp(cmd, "SAFETY ", 7) == 0) {
        setSafety(strncmp(cmd + 7, "ON", 2) == 0);
        Serial.println("ok");

    } else if (strncmp(cmd, "STATUS", 6) == 0) {
        reportStatus();
        Serial.println("ok");

    } else {
        Serial.print("ERR unknown: ");
        Serial.println(cmd);
    }
}

void processSerialCommands() {
    while (Serial.available()) {
        char c = Serial.read();
        if (c == '\n' || c == '\r') {
            if (cmdLen > 0) {
                cmdBuf[cmdLen] = '\0';
                executeCommand(cmdBuf);
                cmdLen = 0;
            }
        } else if (cmdLen < sizeof(cmdBuf) - 1) {
            cmdBuf[cmdLen++] = c;
        }
    }
}
