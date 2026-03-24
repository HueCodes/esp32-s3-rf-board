## Introduction

In this post, I'll walk through designing a **4-layer ESP32-S3 RF development board** in **KiCAD 8**. The board uses the bare **ESP32-S3 QFN56** die instead of a module, which means the RF path (trace impedance, antenna keepout, and ground plane) had to be designed from scratch.

---

## Components

| Ref | Part | Purpose |
|-----|------|---------|
| U1 | ESP32-S3 QFN56 | Dual-core LX7, 2.4GHz WiFi/BT5 |
| U2 | AP2112K-3.3V | 600mA LDO |
| U3 | CP2102-GMR | USB to UART bridge |
| ANT1 | Johanson 2450AT18A100 | 2.4GHz chip antenna |
| J2 | u.FL SMD | RF test port |

Board: **50 x 40 mm**. Manufactured on the **JLC04161H-7628** 4-layer stackup.

---

## Why Bare Die?

ESP32 modules like the WROOM handle the RF design for you: shielded enclosure, integrated antenna, pre-certified. Using the bare QFN56 die means:

- Designing the **50-ohm feedline** from the chip RF pin to the antenna
- Managing copper keepouts on every layer around the antenna
- Getting the GND plane geometry right so impedance calculations hold

It's harder, but it's where the actual RF design work is.

---

## PCB Design in KiCAD 8

### 1. Stackup

| Layer | Function | Thickness |
|-------|----------|-----------|
| L1 F.Cu | Signals, RF trace, components | 0.035mm Cu |
| Prepreg | JLC4161H 7628 | 0.2mm, Er = 4.4 |
| L2 In1.Cu | Solid GND plane | 0.035mm Cu |
| Core | FR4 | 1.065mm |
| L3 In2.Cu | 3.3V power plane | 0.035mm Cu |
| L4 B.Cu | Secondary signals | 0.035mm Cu |

The 0.2mm prepreg between L1 and L2 is what sets the RF trace impedance. L2 is a solid, unbroken GND plane across the entire board.

### 2. RF Trace

The RF trace runs from the ESP32-S3 RF pin to ANT1 on L1. Target impedance: **50 ohms**.

Using the IPC-2141A microstrip formula:

```
Z0 = (87 / sqrt(Er + 1.41)) * ln(5.98h / (0.8w + t))

h = 0.2mm   prepreg thickness
w = 0.6mm   trace width
t = 0.035mm 1 oz copper
Er = 4.4

Z0 ≈ 50 ohm
```

Trace width: **0.6mm**. All bends are 45 degrees. 90-degree corners create impedance discontinuities at 2.4GHz.

### 3. Antenna Keepout

The Johanson 2450AT18A100 requires a copper-free zone around the antenna. I implemented a **5mm radius keepout on F.Cu, B.Cu, and In1.Cu**.

The In1.Cu keepout is the most critical. A solid GND plane directly under the antenna loads its near-field and shifts the resonant frequency off 2.4GHz.

### 4. GND Stitching Vias

Stitching vias connect the F.Cu ground pour to the In1.Cu GND plane along both sides of the RF trace, spaced at **~6mm intervals**. At 2.4GHz, lambda in FR4 is ~60mm, so 6mm is lambda/10. Above that spacing, gaps start to behave as resonant slots.

### 5. Component Placement

- **Antenna**: at the board edge, away from digital switching noise
- **Decoupling caps**: within 2mm of every IC VCC pin
- **LDO**: beside the USB connector for short power distribution
- **CP2102**: beside the ESP32-S3 for short UART runs

---

## Power Supply

The AP2112K-3.3V converts USB 5V to 3.3V at up to 600mA. The ESP32-S3 peaks at ~350mA during WiFi TX, leaving ~250mA of headroom.

- **C7, C8**: 10uF X5R 0805 bulk caps on LDO input and output
- **C1–C11**: 100nF X5R 0402 local decoupling on each IC VCC pin

---

## Firmware

The bring-up firmware uses **ESP-IDF v5**. It runs a WiFi scan every 10 seconds and prints results over UART at 115200 baud, which confirms the RF path is functional after assembly.

```
I (352) rf-board: ESP32-S3 RF Board - firmware v1.0.0
I (362) rf-board: Starting WiFi scan...
I (2512) rf-board: --- WiFi Scan: 8 networks found ---
I (2512) rf-board:   [ 1] RSSI  -42 dBm  CH  6  MyNetwork
I (2512) rf-board:   [ 2] RSSI  -67 dBm  CH 11  Neighbour_2G
```

The status LED on **GPIO48** blinks at 1Hz as a basic alive indicator. Source in `firmware/`.

---

## Conclusion

Using the bare ESP32-S3 die means every RF decision (stackup, trace width, keepout geometry, stitching via spacing) has to be made deliberately. That's the point. All source files and firmware are on GitHub.
