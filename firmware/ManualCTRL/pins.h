#pragma once

// BTT SKR Mini E3 V3.0 — Pin definitions (defaults; overridable via build -D from web config)
// Stepper sockets used: Y (bed rotation), Z (nozzle height), E (extruder)

// ── Bed rotation stepper (Y socket) ────────────────────────
#ifndef BED_STEP_PIN
#define BED_STEP_PIN    PB10
#endif
#ifndef BED_DIR_PIN
#define BED_DIR_PIN     PB2
#endif
#ifndef BED_ENABLE_PIN
#define BED_ENABLE_PIN  PB11
#endif
#ifndef BED_DIR_INVERT
#define BED_DIR_INVERT  true
#endif

// ── Z axis stepper (Z socket) ──────────────────────────────
#ifndef Z_STEP_PIN
#define Z_STEP_PIN      PB0
#endif
#ifndef Z_DIR_PIN
#define Z_DIR_PIN       PC5
#endif
#ifndef Z_ENABLE_PIN
#define Z_ENABLE_PIN    PB1
#endif
#ifndef Z_DIR_INVERT
#define Z_DIR_INVERT    false
#endif

// ── Extruder stepper (E socket) ────────────────────────────
#ifndef E_STEP_PIN
#define E_STEP_PIN      PB3
#endif
#ifndef E_DIR_PIN
#define E_DIR_PIN       PB4
#endif
#ifndef E_ENABLE_PIN
#define E_ENABLE_PIN    PD2
#endif
#ifndef E_DIR_INVERT
#define E_DIR_INVERT    false
#endif

// ── TMC2209 UART (shared single-bus) ──────────────────────
#ifndef TMC_RX_PIN
#define TMC_RX_PIN      PC11
#endif
#ifndef TMC_TX_PIN
#define TMC_TX_PIN      PC10
#endif
#ifndef TMC_BED_ADDR
#define TMC_BED_ADDR    2
#endif
#ifndef TMC_Z_ADDR
#define TMC_Z_ADDR      1
#endif
#ifndef TMC_E_ADDR
#define TMC_E_ADDR      3
#endif

// ── Heater / thermistor ───────────────────────────────────
#ifndef HOTEND_HEATER_PIN
#define HOTEND_HEATER_PIN   PC8
#endif
#ifndef HOTEND_THERM_PIN
#define HOTEND_THERM_PIN    PA0
#endif

// ── Fans ──────────────────────────────────────────────────
#ifndef FAN_PART_PIN
#define FAN_PART_PIN        PC6
#endif
#ifndef FAN_HOTEND_PIN
#define FAN_HOTEND_PIN      PC7
#endif

// ── Endstops ──────────────────────────────────────────────
#ifndef Z_ENDSTOP_PIN
#define Z_ENDSTOP_PIN       PC2
#endif

// ── Beeper ────────────────────────────────────────────────
#ifndef BEEPER_PIN
#define BEEPER_PIN          PB5
#endif
