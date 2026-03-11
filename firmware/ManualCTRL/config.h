#pragma once

// ── Stepper microstepping ─────────────────────────────────
#define MICROSTEPS              16
#define STEPS_PER_REV           (200L * MICROSTEPS)   // 3200

// ── Bed rotation (Y stepper socket, 80T:20T belt) ────────
#define BED_ROTATION_DISTANCE   90.0f     // degrees of bed per motor revolution
#define BED_STEPS_PER_DEG       (STEPS_PER_REV / BED_ROTATION_DISTANCE)  // ~35.56
#define BED_MAX_VELOCITY        200.0f    // deg/s
#define BED_MAX_ACCEL           1000.0f   // deg/s²
#define BED_MAX_SPEED_SPS       (BED_MAX_VELOCITY * BED_STEPS_PER_DEG)
#define BED_MAX_ACCEL_SPS       (BED_MAX_ACCEL * BED_STEPS_PER_DEG)

// ── Z axis (leadscrew, 4 mm pitch) ──────────────────────
#define Z_ROTATION_DISTANCE     4.0f      // mm per motor revolution
#define Z_STEPS_PER_MM          (STEPS_PER_REV / Z_ROTATION_DISTANCE)    // 800
#define Z_MAX_VELOCITY          10.0f     // mm/s
#define Z_MAX_ACCEL             50.0f     // mm/s²
#define Z_MAX_SPEED_SPS         (Z_MAX_VELOCITY * Z_STEPS_PER_MM)
#define Z_MAX_ACCEL_SPS         (Z_MAX_ACCEL * Z_STEPS_PER_MM)
#define Z_MAX_TRAVEL            155.0f    // mm

// ── Extruder (Orbiter 2.0) ─────────────────────────────
#define E_ROTATION_DISTANCE     4.637f    // mm filament per motor revolution
#define E_STEPS_PER_MM          (STEPS_PER_REV / E_ROTATION_DISTANCE)    // ~690
#define E_MAX_VELOCITY          120.0f    // mm/s
#define E_MAX_ACCEL             5000.0f   // mm/s²
#define E_MAX_SPEED_SPS         (E_MAX_VELOCITY * E_STEPS_PER_MM)
#define E_MAX_ACCEL_SPS         (E_MAX_ACCEL * E_STEPS_PER_MM)

// ── TMC2209 driver currents ─────────────────────────────
#define TMC_BED_CURRENT         580       // mA RMS
#define TMC_Z_CURRENT           580       // mA RMS
#define TMC_E_CURRENT           650       // mA RMS
#define TMC_SENSE_RESISTOR      0.11f     // ohms (standard for BTT boards)
#define TMC_BAUD                115200

// ── Thermistor (100 K NTC, 4.7 K pull-up) ──────────────
#define THERM_PULLUP            4700.0f   // pull-up resistor (Ω)
#define THERM_NOMINAL           100000.0f // nominal resistance at 25 °C
#define THERM_NOMINAL_TEMP      25.0f     // °C
#define THERM_BETA              3950.0f   // beta coefficient
#define MAX_HOTEND_TEMP         260.0f    // hard limit °C

// ── PID tuning ──────────────────────────────────────────
#define PID_KP                  20.0f
#define PID_KI                  1.0f
#define PID_KD                  100.0f
#define PID_I_MAX               255.0f
#define PID_INTERVAL_MS         100

// ── Hotend fan auto-on threshold ────────────────────────
#define HOTEND_FAN_THRESHOLD    50.0f     // °C

// ── Homing defaults ─────────────────────────────────────
#define HOME_LIFT_MM            5.0f
#define HOME_PROBE_SPEED_MM_S   5.0f
#define HOME_TRAVEL_SPEED_MM_S  10.0f
#define HOME_REST_MM            10.0f
#define HOME_TIMEOUT_MS         60000UL
