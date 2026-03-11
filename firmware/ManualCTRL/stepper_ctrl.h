#pragma once

void  initSteppers();
void  runSteppers();

void  startBed(float speedDegPerSec);
void  startZ(float speedMmPerSec);
void  startExtruder(float speedMmPerSec);

void  stopBed();
void  stopZ();
void  stopExtruder();
void  stopAll();

void  emergencyStop();
void  enableSteppers();

void  homeZ();

float getBedPosition();
float getZPosition();
float getEPosition();

void  zeroBed();
void  zeroZ();
void  zeroExtruder();
