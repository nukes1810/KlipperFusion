# sentient

I got tired of watching Bambu and other manufacturers lock down their firmware while charging a premium for features that should exist on every printer. Auto flow calibration, first layer scanning, failure detection — none of this is magic. It's sensors and software. So I built it myself.

This started as a personal project on my Nebula 370 custom CoreXY build. Every feature in here has been printed, broken, fixed, and reprinted. Nothing is theoretical.

The goal is simple — if you built your own printer or run Klipper, you shouldn't have to choose between features and freedom. sentient is the answer to that.

---

## Why This Exists

The 3D printing world is splitting. On one side you have locked-down commercial printers with genuinely impressive software. On the other you have open source machines with incredible hardware potential but no unified intelligence layer to tie it together.

Nobody should have to buy a Bambu to get smart printing. If you have the hardware, you should have the features.

sentient is an open, modular, community-driven intelligence layer for Klipper. Start with zero extra hardware and get smarter printing today. Add sensors to unlock more. Build toward something that matches or beats anything commercial — and actually understand how it works.

---

## What It Does Right Now

No extra hardware needed to start. Install it and your printer gets smarter today.

**Automatic per-filament Z offset calibration** — the first native Klipper module in the project. Prints a small calibration square, scans it with Cartographer, calculates actual layer height vs target, adjusts Z offset iteratively, and saves the result per filament. Run it once per filament type and never touch Z offset again.

```
CALIBRATE_ASA   → heats up, prints square, scans, saves offset
CALIBRATE_PLA   → same for PLA
CALIBRATE_ALL_FILAMENTS → runs all five back to back
```

Every subsequent print automatically applies the saved offset for that filament. Z offset in your slicer stays at zero permanently.

**Nozzle temperature offset compensation** — hardened steel nozzles run cooler at the tip than the heater block reads. sentient intercepts M104 and M109 commands and adds a configurable offset automatically. Set your slicer temps to what you actually want at the nozzle tip. sentient handles the rest.

**Dynamic acceleration by print height** — tall prints have always been a problem on fast printers. Banding, ringing, layer separation. sentient automatically backs off acceleration as the print gets taller, based on your actual input shaper results not guesswork.

```
Under 50mm   → full speed    (100% of your calibrated max accel)
50 to 150mm  → medium speed  (70%)
Over 150mm   → safe speed    (45%)
```

Zone changes happen automatically mid-print. You'll see them in the console and on the dashboard as they happen.

**Smart START_PRINT** — knows what filament you're printing, applies the saved Z offset, heat soaks for ASA/ABS if you have a chamber sensor, sets the right accel zone from the first layer. Slicer just sends the filament type and temperatures. sentient handles everything else.

**Auto shaper calibration** — run it manually when you want. After it runs, max accel updates automatically from your Y axis results. All three speed zones recalculate from the new value. No manual config editing.

**Live web dashboard** — open it on your phone or any browser on your network. Shows current speed zone, print height, chamber temp, humidity, shaper status, nozzle vs block temperature, and a live activity log of everything sentient is doing. Looks like Mainsail. Updates every 2 seconds.

**KlipperScreen integration** — Smart Tune menu on your touchscreen with one-tap accel override, shaper calibration, heat soak, and tune status.

---

## Feature Tiers

sentient grows with your hardware. Every tier adds features, nothing breaks what was already working.

**Tier 0 — Any Klipper printer, no extra hardware**
- Automatic per-filament Z offset calibration (native Klipper module)
- Nozzle temperature offset compensation
- Dynamic accel by height
- Smart START_PRINT with filament awareness
- Auto shaper calibration with max accel update
- Web dashboard
- KlipperScreen menu

**Tier 1 — Add a chamber sensor (SHT3X, BME280, anything)**
- Automatic heat soak for ASA/ABS
- Humidity warnings before prints start
- Chamber condition logging
- Dashboard chamber display

**Tier 2 — Add ADXL345**
- Scheduled shaper calibration
- Resonance monitoring during printing
- Belt tension alerts via Shake&Tune integration

**Tier 3 — Add VL53L5CX ToF sensor** *(hardware built, driver in development)*
- First layer presence detection
- Spaghetti and failure detection
- Layer shift detection
- Gross height tracking and verification

**Tier 4 — Add a camera** *(planned)*
- AI failure detection
- Timelapse with quality tagging
- Optical first layer grading

**Tier 5 — Full fusion** *(the goal)*
- All sensors working as one system
- Self tuning per filament based on print history
- Print quality prediction
- Native Klipper modules throughout, not just macros

---

## Install

```bash
cd ~
git clone https://github.com/nukes1810/sentient.git
cd sentient
./install.sh
```

Add to `printer.cfg`:

```ini
[include sentient.cfg]

[sentient_first_layer]
calibration_x: 30
calibration_y: 30
calibration_size: 40
iterations: 3
tolerance: 0.01
layer_height: 0.20
```

Restart Klipper. You're running Tier 0.

---

## Slicer Setup

Machine start gcode:

```
START_PRINT BED_TEMP=[first_layer_bed_temperature] EXTRUDER_TEMP=[first_layer_temperature] FILAMENT=[filament_type] CHAMBER_TEMP=[chamber_temperature]
```

**Z offset in slicer: 0** — sentient applies the correct offset per filament automatically.

**Filament start/end gcode: leave blank** — sentient handles Z offset and temperature compensation automatically.

Set chamber temp in filament presets:
- ASA / ABS → 40
- Everything else → 0

---

## Z Offset Calibration

Run once per filament type. Never touch Z offset again.

```
CALIBRATE_PLA
CALIBRATE_PETG
CALIBRATE_ASA
CALIBRATE_ABS
CALIBRATE_TPU
```

Or calibrate everything at once:

```
CALIBRATE_ALL_FILAMENTS
```

Check saved offsets anytime:

```
SENTIENT_STATUS
```

---

## Nozzle Temperature Offset

If your nozzle tip reads cooler than your heater block (common with hardened steel nozzles), configure the offset once and forget it:

```ini
[gcode_macro _TEMP_OFFSET_VARS]
variable_nozzle_temp_offset: 51   # your measured gap
```

Your slicer temperatures now refer to the actual nozzle tip temperature. sentient compensates the block temperature automatically.

Adjust on the fly:
```
SET_NOZZLE_OFFSET OFFSET=45
DISABLE_NOZZLE_OFFSET
ENABLE_NOZZLE_OFFSET
NOZZLE_OFFSET_STATUS
```

---

## Dashboard

After install, open from any browser on your network:

```
http://[your-printer-ip]:8080
```

---

## Hardware This Was Built On

- Nebula 370 custom CoreXY (370x370x400mm)
- Xol toolhead with CNC lightweight mount
- Rapido HF V2 hotend
- Sherpa Mini extruder
- Cartographer V4 probe
- EBB36 Gen 2 toolhead CAN board
- TMC5160 X/Y drivers
- SHT3X chamber sensor (temp + humidity)
- ADXL345 via Cartographer
- Hardened steel 0.4mm nozzle
- MGN12 linear rails
- Rock 2A SBC running Armbian

It works on other printers too. If you get it running on yours, open a PR with your config and it'll go in the examples folder.

---

## Custom Sensor Hardware

sentient includes a custom PCB design for Tier 3 sensing:

**sentient Sensor Board v1**
- VL53L5CX 8x8 ToF multizone ranging sensor
- AMS1117-3.3 onboard 5V→3.3V regulation
- I2C pull-up resistors and decoupling caps
- Solder jumper for RST (GPIO or always-on)
- INT pin with pull-up, GPIO breakout
- SM06B-SRSS-TB 6-pin JST SH connector to EBB36
- Designed to mount on Xol toolhead faceplate
- JLCPCB-ready gerbers in `/hardware/sentient_sensor_v1/`

---

## Roadmap

- [x] Dynamic accel by height
- [x] Smart macros
- [x] Auto shaper calibration with max accel update
- [x] Web dashboard (Mainsail-style)
- [x] KlipperScreen integration
- [x] Chamber heat soak
- [x] Humidity monitoring
- [x] Nozzle temperature offset compensation
- [x] Per-filament Z offset calibration (native Klipper module)
- [x] Automatic Z offset application in START_PRINT
- [x] Custom sensor PCB design (VL53L5CX)
- [ ] One line installer script
- [ ] VL53L5CX native Klipper driver
- [ ] First layer optical scanning
- [ ] Real time flow compensation
- [ ] Failure detection
- [ ] Moonraker update manager integration
- [ ] Full native Klipper module suite

---

## Want to Help?

This project needs people who know what they're doing. Specifically:

- **Python developers** who know Klipper internals — the end goal is native modules not just macros
- **People with different printer setups** — the more hardware this is tested on the better
- **Sensor people** — if you've worked with ToF sensors, I2C, or computer vision on embedded systems
- **PCB designers** — the sensor board needs refinement and community testing
- **People who are just fed up** with locked down firmware and want to do something about it

Open an issue, start a discussion, or just submit a PR. Everything is welcome.

If you find a bug, open an issue with your printer config and what happened. If you want a feature, explain what problem it solves. That's it.

---

## License

MIT. Use it however you want. Build on it. Fork it. Sell a product with it if you want. Just don't lock it down — that's kind of the whole point.

---

## Thanks

- [Klipper](https://github.com/Klipper3d/klipper) — none of this exists without it
- [KAMP](https://github.com/kyleisah/Klipper-Adaptive-Meshing-Purging) — showed how to do modular Klipper additions properly
- [Klippain Shake&Tune](https://github.com/Frix-x/klippain-shaketune) — the gold standard for community Klipper tools
- [Cartographer3D](https://cartographer3d.com) — the probe that makes the Z calibration system possible
- Everyone in the Klipper community who answered questions, shared configs, and kept pushing what custom printers can do

---

*This is a real project built on a real printer. Everything checked off in the roadmap has been running in daily use. The rest is where it's going — contributions welcome at every step.*
