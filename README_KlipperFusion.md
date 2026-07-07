# KlipperFusion

I got tired of watching Bambu and other manufacturers lock down their firmware while charging a premium for features that should exist on every printer. Auto flow calibration, first layer scanning, failure detection — none of this is magic. It's sensors and software. So I built it myself.

This started as a personal project on my Nebula 370 custom CoreXY build. Every feature in here has been printed, broken, fixed, and reprinted. Nothing is theoretical.

The goal is simple — if you built your own printer or run Klipper, you shouldn't have to choose between features and freedom. KlipperFusion is the answer to that.

---

## Why This Exists

The 3D printing world is splitting. On one side you have locked-down commercial printers with genuinely impressive software. On the other you have open source machines with incredible hardware potential but no unified intelligence layer to tie it together.

Nobody should have to buy a Bambu to get smart printing. If you have the hardware, you should have the features.

KlipperFusion is an open, modular, community-driven intelligence layer for Klipper. Start with zero extra hardware and get smarter printing today. Add sensors to unlock more. Build toward something that matches or beats anything commercial — and actually understand how it works.

---

## What It Does Right Now

No extra hardware needed to start. Install it and your printer gets smarter today.

**Dynamic acceleration by print height** — tall prints have always been a problem on fast printers. Banding, ringing, layer separation. KlipperFusion automatically backs off acceleration as the print gets taller, based on your actual input shaper results not guesswork.

```
Under 50mm   → full speed    (100% of your calibrated max accel)
50 to 150mm  → medium speed  (70%)
Over 150mm   → safe speed    (45%)
```

Zone changes happen automatically mid-print. You'll see them in the console and on the dashboard as they happen.

**Smart START_PRINT** — knows what filament you're printing, heat soaks for ASA/ABS if you have a chamber sensor, checks shaper calibration age, sets the right accel zone from the first layer.

**Auto shaper scheduling** — run calibration manually when you want it. After it runs, max accel updates automatically from your Y axis results. No more guessing what number to put in printer.cfg.

**Live web dashboard** — open it on your phone or any browser on your network. Shows current speed zone, print height, chamber conditions, shaper status, and a plain English activity log of everything the system is doing.

**KlipperScreen integration** — Smart Tune menu on your touchscreen. One tap to override speed zone, run shaper, or check status mid print.

---

## Feature Tiers

KlipperFusion grows with your hardware. Every tier adds features, nothing breaks what was already working.

**Tier 0 — Any Klipper printer, no extra hardware**
- Dynamic accel by height
- Smart start/end macros
- Auto shaper scheduling with max accel update
- Web dashboard
- KlipperScreen menu

**Tier 1 — Add a chamber sensor (SHT3X, BME280, anything)**
- Automatic heat soak for ASA/ABS
- Humidity warnings before prints start
- Chamber condition logging

**Tier 2 — Add ADXL345**
- Scheduled shaper calibration
- Resonance monitoring during printing
- Belt tension alerts via Shake&Tune integration

**Tier 3 — Add VL53L5CX ToF sensor** *(in development)*
- First layer optical scanning
- Real time flow compensation from actual surface readings
- Spaghetti and failure detection
- Layer shift detection

**Tier 4 — Add a camera** *(planned)*
- AI failure detection
- Timelapse with quality tagging

**Tier 5 — Full fusion** *(the goal)*
- All sensors working as one system
- Self tuning per filament
- Print quality prediction
- Eventually a native Klipper module, not just macros

---

## Install

```bash
cd ~
git clone https://github.com/nukes1810/KlipperFusion.git
cd KlipperFusion
./install.sh
```

Add to `printer.cfg`:

```ini
[include klipper_fusion.cfg]
```

Restart Klipper. You're running Tier 0.

---

## Slicer Setup

Machine start gcode:

```
START_PRINT BED_TEMP=[first_layer_bed_temperature] EXTRUDER_TEMP=[first_layer_temperature] FILAMENT=[filament_type] CHAMBER_TEMP=[chamber_temperature]
```

Set chamber temp in your filament presets:
- ASA / ABS → 40
- Everything else → 0

---

## Dashboard

After install, open from any browser:

```
http://[your-printer-ip]/klipper_fusion
```

Shows everything in plain English. No digging through console logs.

---

## Hardware This Was Built On

- Nebula 370 custom CoreXY
- Xol toolhead
- Rapido HF V2 hotend
- Sherpa Mini extruder
- Cartographer probe
- EBB36 Gen 2 toolhead board
- SHT3X chamber sensor
- ADXL345 via Cartographer

It works on other printers too. If you get it running on yours, open a PR with your config and it'll go in the examples folder.

---

## Roadmap

- [x] Dynamic accel by height
- [x] Smart macros
- [x] Auto shaper scheduling
- [x] Max accel auto-update from shaper results
- [x] Web dashboard
- [x] KlipperScreen integration
- [x] Chamber heat soak
- [x] Humidity monitoring
- [ ] One line installer
- [ ] VL53L5CX Klipper driver
- [ ] First layer optical scanning
- [ ] Real time flow compensation
- [ ] Failure detection
- [ ] Moonraker update manager
- [ ] Native Klipper module

---

## Want to Help?

This project needs people who know what they're doing. Specifically:

- **Python developers** who know Klipper internals — the end goal is native modules not just macros
- **People with different printer setups** — the more hardware this is tested on the better
- **Sensor people** — if you've worked with ToF sensors, I2C, or computer vision on embedded systems
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
- Everyone in the Klipper community who answered questions, shared configs, and kept pushing what custom printers can do

---

*This is a real project built on a real printer. Everything in the current feature set has been running in daily use. The roadmap is where it's going — contributions welcome at every step.*
