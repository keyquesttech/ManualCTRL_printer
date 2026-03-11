#pragma once

// BTT SKR Mini E3 V3.0 — Pin definitions
// Stepper sockets used: Y (bed rotation), Z (nozzle height), E (extruder)

// ── Bed rotation stepper (Y socket) ────────────────────────
#define BED_STEP_PIN    PB10
#define BED_DIR_PIN     PB2
#define BED_ENABLE_PIN  PB11
#define BED_DIR_INVERT  true

// ── Z axis stepper (Z socket) ──────────────────────────────
#define Z_STEP_PIN      PB0
#define Z_DIR_PIN       PC5
#define Z_ENABLE_PIN    PB1
#define Z_DIR_INVERT    false

// ── Extruder stepper (E socket) ────────────────────────────
#define E_STEP_PIN      PB3
#define E_DIR_PIN       PB4
#define E_ENABLE_PIN    PD2
#define E_DIR_INVERT    false

// ── TMC2209 UART (shared single-bus) ──────────────────────
#define TMC_RX_PIN      PC11
#define TMC_TX_PIN      PC10
#define TMC_BED_ADDR    2
#define TMC_Z_ADDR      1
#define TMC_E_ADDR      3

// ── Heater / thermistor ───────────────────────────────────
#define HOTEND_HEATER_PIN   PC8
#define HOTEND_THERM_PIN    PA0

// ── Fans ──────────────────────────────────────────────────
#define FAN_PART_PIN        PC6
#define FAN_HOTEND_PIN      PC7

// ── Endstops ──────────────────────────────────────────────
#define Z_ENDSTOP_PIN       PC2

// ── Beeper ────────────────────────────────────────────────
#define BEEPER_PIN          PB5
