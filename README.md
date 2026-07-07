# KlipperFusion 🖨️

> Open-source print intelligence for Klipper — adaptive flow, failure detection, and real-time sensor fusion for any 3D printer.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Klipper](https://img.shields.io/badge/Klipper-Compatible-green.svg)](https://github.com/Klipper3d/klipper)
[![Status](https://img.shields.io/badge/Status-Active%20Development-blue.svg)]()

---

## What is KlipperFusion?

KlipperFusion is a modular, printer-agnostic intelligence layer for Klipper that brings commercial printer capabilities to any machine. Built and battle-tested on a custom Nebula 370 CoreXY with Xol toolhead, it is designed to work on any Klipper-based printer regardless of size, kinematics, or sensor configuration.

The goal is simple — give every Klipper printer the kind of smart, self-aware behavior that commercial printers like Bambu Lab charge thousands of dollars for, but fully open, fully customizable, and fully yours.

---

## Philosophy

- **Modular** — use only what you have. Zero extra hardware required to start.
- **Printer agnostic** — CoreXY, bed slinger, delta, toolchanger — all supported.
- **Progressive** — add sensors to unlock more features automatically.
- **Community driven** — built in the open, improved by everyone.
- **No lock-in** — your printer, your code, your data.

---

## Feature Tiers

KlipperFusion uses a tiered system. Every tier builds on the last. Start at Tier 0 today with no extra hardware.

### Tier 0 — Base (Any Klipper Printer, No Extra Hardware)
- ✅ Dynamic acceleration by print height
- ✅ Smart START_PRINT with filament type awareness
- ✅ Automatic input shaper scheduling
- ✅ Live speed zone display (Full / Medium / Conservative)
- ✅ Real-time web dashboard
- ✅ Manual accel override macros
- ✅ KlipperScreen menu integration

### Tier 1 — Chamber Awareness (+ SHT3X / BME280 / Any Chamber Sensor)
- ✅ Automatic heat soak for ASA/ABS
- ✅ Humidity monitoring with filament drying warnings
- ✅ Chamber temperature tracking per print
- ✅ Enclosure condition logging

### Tier 2 — Resonance Intelligence (+ ADXL345)
- ✅ Scheduled input shaper auto-calibration
- ✅ Post-calibration max_accel auto-update
- ✅ Belt tension monitoring via Shake&Tune integration
- ✅ Resonance anomaly detection during printing

### Tier 3 — Optical Intelligence (+ VL53L5CX ToF Sensor) *Coming Soon*
- 🔜 First layer optical scanning
- 🔜 Real-time flow compensation from surface readings
- 🔜 Spaghetti and failure detection
- 🔜 Layer shift detection
- 🔜 Adaptive Z offset per zone

### Tier 4 — Vision (+ Camera) *Coming Soon*
- 🔜 AI-powered failure detection via Obico integration
- 🔜 Timelapse with automatic quality tagging
- 🔜 Visual first layer grading

### Tier 5 — Full Fusion *Future*
- 🔜 All sensors working as one unified system
- 🔜 Machine learning print quality prediction
- 🔜 Self-tuning per filament based on print history
- 🔜 Native Klipper module integration

---

## Quick Start

### Requirements
- Klipper installed and running
- Moonraker installed and running
- Mainsail or Fluidd web interface

### Installation

```bash
cd ~
git clone https://github.com/nukes1810/KlipperFusion.git
cd KlipperFusion
./install.sh
```

Then add to your `printer.cfg`:

```ini
[include klipper_fusion.cfg]
```

Restart Klipper and you're running Tier 0.

---

## Configuration

Basic configuration in `klipper_fusion.cfg`:

```ini
[fusion_core]
# Enable features based on your hardware
smart_tune: True          # Dynamic accel by height (Tier 0)
auto_shaper: True         # Scheduled shaper calibration (Tier 0)
shaper_interval: 14       # Days between auto-calibration

# Tier 1 - uncomment if you have a chamber sensor
# heat_soak: True
# humidity_warn: True
# chamber_sensor: enclosure_temp

# Tier 3 - uncomment when VL53L5CX is installed
# tof_sensor: True
# flow_compensation: True
# failure_detection: True
```

### Machine Start Gcode (OrcaSlicer / PrusaSlicer)

```
START_PRINT BED_TEMP=[first_layer_bed_temperature] EXTRUDER_TEMP=[first_layer_temperature] FILAMENT=[filament_type] CHAMBER_TEMP=[chamber_temperature]
```

### Filament Chamber Temperatures

Set in your slicer filament presets:
- ASA → 40°C
- ABS → 40°C
- PLA → 0 (skips heat soak)
- PETG → 0 (skips heat soak)

---

## Dynamic Acceleration System

KlipperFusion automatically adjusts acceleration based on print height to eliminate banding and resonance artifacts on tall prints.

| Zone | Height | Acceleration | Why |
|---|---|---|---|
| 🟢 Full Speed | Z < 50mm | 100% of max_accel | Part is short and rigid |
| 🟡 Medium Speed | Z 50-150mm | 70% of max_accel | Reducing vibration risk |
| 🔴 Safe Speed | Z > 150mm | 45% of max_accel | Tall prints need stability |

Accel values are calculated automatically from your input shaper results after every calibration run. No manual tuning required.

---

## Web Dashboard

KlipperFusion includes a real-time web dashboard accessible from any browser on your network.

After installation open:
```
http://[your-printer-ip]/klipper_fusion
```

**Dashboard shows:**
- Current speed zone in plain English
- Print height and progress
- Chamber temperature and humidity
- Nozzle and bed temperatures
- Input shaper calibration status
- Live activity log of all tuning events

---

## KlipperScreen Integration

KlipperFusion adds a **Smart Tune** menu to KlipperScreen with:
- One-tap accel zone override
- Run shaper calibration button
- Heat soak controls
- Live tune status

---

## Supported Hardware

### Probes / Bed Leveling
- Cartographer (recommended)
- Beacon
- BLTouch / CR Touch
- Any Klipper-compatible probe

### Chamber Sensors
- SHT3X (recommended)
- BME280
- AHT10
- Any Klipper temperature sensor

### Accelerometers
- ADXL345 (recommended)
- LIS2DW
- MPU-9250

### ToF Sensors (Tier 3 — Coming Soon)
- VL53L5CX (recommended — 8x8 zone array)
- VL53L1X (single zone)

### Tested Printers
- Nebula 370 (CoreXY) — primary development platform
- More coming as community contributes configs

---

## Roadmap

- [x] Dynamic accel by height
- [x] Smart START_PRINT macro
- [x] Auto shaper scheduling
- [x] Post-calibration max_accel auto-update
- [x] Web dashboard
- [x] KlipperScreen integration
- [x] Chamber heat soak
- [x] Humidity monitoring
- [ ] One-line installer script
- [ ] VL53L5CX native Klipper driver
- [ ] First layer optical scanning
- [ ] Real-time flow compensation
- [ ] Failure detection
- [ ] Moonraker update manager integration
- [ ] ML print quality prediction
- [ ] Native Klipper module (no macros)

---

## Contributing

KlipperFusion is built by the community for the community. Contributions welcome:

- **Sensor drivers** — add support for new sensors
- **Printer configs** — share your working configuration
- **Bug reports** — open an issue with your printer details
- **Feature requests** — open a discussion
- **Documentation** — help others get started

Please read `CONTRIBUTING.md` before submitting a pull request.

---

## Project Status

KlipperFusion is in **active development**. Tier 0 and Tier 1 are stable and running in daily use. Tier 3 (VL53L5CX optical scanning) is in development with hardware arriving soon.

This project started as a personal build log for a Nebula 370 custom printer and grew into something the whole community can benefit from. Every feature was built, tested, and refined through real printing — not just theory.

---

## License

MIT License — see [LICENSE](LICENSE) for details.

Use it, modify it, build on it, share it. That's the point.

---

## Acknowledgements

- [Klipper](https://github.com/Klipper3d/klipper) — the firmware that makes all of this possible
- [KAMP](https://github.com/kyleisah/Klipper-Adaptive-Meshing-Purging) — inspiration for the modular approach
- [Klippain Shake&Tune](https://github.com/Frix-x/klippain-shaketune) — shaper calibration integration
- The entire Klipper community for pushing what's possible

---

*Built on a Nebula 370 with Xol toolhead, Rapido HF V2, Sherpa Mini, and Cartographer. Designed to work on everything.*
