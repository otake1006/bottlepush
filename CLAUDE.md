# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ETRobocon application for **RasPike-ART**: a platform that connects a Raspberry Pi (running TOPPERS/ASP3 RTOS) to a LEGO SPIKE Prime hub over USB. The Raspberry Pi side is written in C using TOPPERS ITRON APIs and the SPIKE-RT-compatible PUP API.

## Build & Run Commands

All `make` commands are run from `sdk/workspace/` (the parent of this project directory).

```bash
# Build this project
make img=bottlepush

# Run on Raspberry Pi (after build)
make start

# Update SPIKE firmware (DFU mode required first)
make -f ../common/Makefile.raspike-art update_spike

# Clean build artifacts
make clean

# Clean RasPike-ART library (needed after libraspike-art updates)
make clean_art
```

There is no test suite; verification is done by running on hardware.

## Architecture

### Task model (TOPPERS/ASP3)

Tasks and cyclic handlers are declared in `app.cfg` using TOPPERS kernel object macros (`CRE_TSK`, `CRE_CYC`). Key patterns:

- `main_task` (`TA_ACT`): runs once at startup — initializes devices, waits for start trigger, then activates cyclic handlers with `sta_cyc()`.
- `tracer_task`: activated every `LINE_TRACER_PERIOD` (100 ms) by `CRE_CYC`. Must call `ext_tsk()` at the end.
- Stack size, priorities, and periods are defined in `app.h`.

### File layout of a project

```
app.h          — task priorities, periods, stack size, extern declarations
app.c          — main_task: device init, start trigger, sta_cyc()
app.cfg        — TOPPERS kernel object definitions (tasks, cyclic handlers)
Makefile.inc   — USE_RASPIKE_ART=1, APPL_COBJS, APPL_DIRS, INCLUDES
LineTracer/    — component module compiled separately via APPL_DIRS
```

### SPIKE PUP API

Include headers from `spike/pup/` or `spike/hub/`. Use `spikeapi.h` (not `ev3api.h`).

| Header | Key functions |
|---|---|
| `spike/pup/motor.h` | `pup_motor_get_device`, `pup_motor_setup`, `pup_motor_set_power`, `pup_motor_get_count` |
| `spike/pup/colorsensor.h` | `pup_color_sensor_get_device`, `pup_color_sensor_color` (→ `pup_color_hsv_t`), `pup_color_sensor_reflection` |
| `spike/pup/forcesensor.h` | `pup_force_sensor_get_device`, `pup_force_sensor_touched` |
| `spike/hub/imu.h` | 3-axis IMU |
| `spike/hub/display.h` | Hub display |

**Critical**: `pup_color_sensor_color(pdev, surface)` returns `pup_color_hsv_t` — a struct with `h` (0–359°), `s` (0–100%), `v` (0–100%). There is no color-name enum for the return value; detect colors by checking HSV ranges.

### Port assignments (this project)

| Port | Device |
|---|---|
| A | Right motor (`PUP_DIRECTION_CLOCKWISE`) |
| B | Left motor (`PUP_DIRECTION_COUNTERCLOCKWISE`) |
| D | Force sensor (start trigger) |
| E | Color sensor |

### Adding a new module

1. Create a subdirectory (e.g., `MyModule/MyModule.c`, `MyModule/MyModule.h`).
2. Add to `Makefile.inc`:
   ```makefile
   APPL_COBJS += MyModule.o
   APPL_DIRS  += $(mkfile_path)MyModule
   INCLUDES   += -I$(mkfile_path)MyModule
   ```
3. `ATT_MOD("app.o")` in `app.cfg` covers `app.c`; each additional `.o` needs its own `ATT_MOD` or must be listed in `APPL_COBJS`.

## HSV Blue Detection Reference

Blue hue center is 240°. Typical thresholds for distinguishing blue from the floor/line:

```c
hsv.h >= 200 && hsv.h <= 280   // hue range for blue
hsv.s >= 50                    // exclude gray/white
hsv.v >= 30                    // exclude black
```
