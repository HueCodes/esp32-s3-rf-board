# ESP32-S3 RF Dev Board

A 4-layer RF development board built around the bare ESP32-S3 QFN56 die (not a module),
featuring a designed-from-scratch 50-ohm microstrip RF path, CP2102 USB-UART bridge, and
AP2112K LDO power supply.

Board dimensions: **50 x 40 mm**. Stackup: **JLC04161H-7628** (JLCPCB standard 4-layer).

[Blog write-up](https://huecodes.github.io/hardware/esp32-s3-rf-board/)

---

## Why bare die, not a module?

ESP32 modules (WROOM, MINI) integrate a shielded RF section and a PCB trace antenna. They
handle the hard parts so you never have to think about transmission-line matching or antenna
keepouts. Using the bare QFN56 die means designing the RF path from scratch:

- Controlled-impedance microstrip trace from the chip RF pin to the antenna
- Solid GND plane on L2 to define a consistent reference for that trace
- Antenna keepout zones on every layer to prevent detuning from nearby copper
- GND stitching vias at lambda/10 intervals to suppress parallel-plate waveguide modes

The board is deliberately compact (50x40 mm) to make these constraints harder to satisfy.

---

## Block diagram

```
USB-C (J1)
  |
  |-- 5V --> AP2112K LDO --> 3.3V ---- ESP32-S3 (U1)
  |                                         |-- RF pin --> 50-ohm trace --> ANT1 (chip)
  |-- USB D+/D- --> CP2102 (U3) --> UART TX/RX           |-> J2 (u.FL test port)
                                         |
                                         |-- GPIO48 --> D1 (status LED)
                                         |-- UART  --> J3 (2.54mm header)
                                         |-- I2C   --> J4
                                         |-- SPI   --> J5
```

---

## RF design

### Trace impedance

The RF trace runs on L1 (F.Cu) over the solid GND plane on L2 (In1.Cu). The dielectric
separating them is 0.2 mm of JLC4161H 7628 prepreg (Er = 4.4).

Microstrip impedance formula (IPC-2141A approximation):

```
Z0 = (87 / sqrt(Er + 1.41)) * ln(5.98h / (0.8w + t))

h = 0.2 mm (dielectric thickness)
w = 0.6 mm (trace width)
t = 0.035 mm (copper thickness, 1 oz)
Er = 4.4

Z0 ≈ 50 ohm
```

Verified against Saturn PCB Toolkit. A ±10% width tolerance (0.06 mm) shifts impedance by
roughly ±3 ohm, acceptable for a 2.4 GHz short trace.

### Antenna keepout

The Johanson 2450AT18A100 datasheet specifies a copper-free zone around the antenna to
prevent nearby copper from loading the antenna and shifting its resonant frequency. The
implementation uses a **5 mm radius keepout polygon on F.Cu, B.Cu, and In1.Cu**, generated
programmatically in `generate_board.py`.

In1.Cu (GND plane) has an identical 5 mm cutout directly beneath the antenna. This is the
most critical layer: a solid GND plane under the antenna would short its near-field and
collapse radiation resistance.

### GND stitching vias

Stitching vias connect F.Cu ground pours to the In1.Cu GND plane at ~6 mm intervals along
both sides of the RF trace. At 2.4 GHz, lambda in FR4 ≈ 60 mm, so 6 mm is lambda/10 — the
threshold above which via spacing starts to allow resonant slots.

### u.FL test port (J2)

J2 allows connecting a VNA or spectrum analyser during bring-up to measure the actual
delivered power and check return loss (S11). The chip antenna and u.FL port share the
RF_ANT net. Fitting a 0-ohm series jumper (or DNP one side) selects which path is active.

---

## PCB stackup

| Layer | Function | Copper | Dielectric |
|-------|----------|--------|------------|
| L1 F.Cu | Signals, RF trace, components | 35 um | — |
| Prepreg 1 | JLC4161H 7628 | — | 0.2 mm, Er=4.4 |
| L2 In1.Cu | Solid GND plane | 35 um | — |
| Core | FR4 | — | 1.065 mm, Er=4.5 |
| L3 In2.Cu | 3.3V power plane | 35 um | — |
| Prepreg 2 | JLC4161H 7628 | — | 0.2 mm, Er=4.4 |
| L4 B.Cu | Secondary signals | 35 um | — |
| **Total** | | | **1.6 mm** |

Separating GND (L2) and power (L3) onto dedicated inner layers keeps L1/L4 free for signals
and provides low-impedance return paths directly under every trace.

---

## Power supply

The AP2112K-3.3V LDO converts 5V USB power to 3.3V for all ICs.

- Input bulk: 10 uF X5R 0805 (C7) — handles transient current demand during WiFi TX bursts
- Output bulk: 10 uF X5R 0805 (C8) — keeps output stable during load steps
- Local decoupling: 100 nF X5R 0402 caps within 2 mm of each VCC pin (C1-C6, C9-C11)

ESP32-S3 peak current: ~350 mA during WiFi TX. AP2112K rated 600 mA. Margin: ~250 mA.

### USB-C CC resistors

USB-C requires 5.1 kohm pull-downs on CC1 and CC2 for the device to be recognised by a
charger/host. R3 and R4 (5.1k 0402) are placed adjacent to J1 and pull CC1/CC2 to GND.

### USB ESD protection

U4 (USBLC6-2SC6, SOT-23-6) clamps D+ and D- against ESD events. Placed between J1 and U3
on the USB data path.

### Test points

TP1 (3.3V), TP2 (GND), and TP3 (RF_ANT) are 1.5mm SMD pads for probe access during
bring-up without needing to touch 0402 component pads.

---

## Firmware

See [`firmware/`](firmware/) for the ESP-IDF project.

The firmware demonstrates the board working end-to-end:

- WiFi station mode scan — validates the RF path is functional
- Scan results printed via UART at 115200 baud — visible on J3 or via CP2102 USB port
- Status LED (GPIO48) blinks at 1 Hz to indicate the CPU is running

### Prerequisites

- ESP-IDF v5.x (`idf.py` on PATH)
- USB cable connected to J1 (CP2102 provides UART over USB)

### Build and flash

```sh
cd firmware
idf.py set-target esp32s3
idf.py build
idf.py -p /dev/ttyUSB0 flash monitor
```

Expected UART output:

```
I (352) rf-board: ESP32-S3 RF Board - firmware v1.0.0
I (362) rf-board: Starting WiFi scan...
I (2512) rf-board: --- WiFi Scan: 8 networks found ---
I (2512) rf-board:   [ 1] RSSI  -42 dBm  CH  6  MyNetwork
I (2512) rf-board:   [ 2] RSSI  -67 dBm  CH 11  Neighbour_2G
...
```

---

## PCB generation scripts

The KiCAD project files are generated programmatically rather than drawn by hand. This makes
design parameters (trace widths, component positions, keepout radii) version-controlled and
reproducible.

| Script | Purpose |
|--------|---------|
| `generate_board.py` | Generates `.kicad_pcb`, `.kicad_pro`, `.kicad_sch`, `bom.csv` from scratch |
| `reroute_clean.py` | Re-runs routing with updated component positions |
| `fix_pcb.py` | Post-processes PCB file: adds missing UUIDs, fixes zone fill syntax |

```sh
# Regenerate the full project (outputs to current directory by default)
python generate_board.py

# Write to a specific directory
python generate_board.py --output /path/to/project

# Verbose logging
python generate_board.py --verbose
```

---

## Bill of materials

See [`bom.csv`](bom.csv) for full BOM with JLCPCB part numbers.

Key components:

| Ref | Part | Package | Notes |
|-----|------|---------|-------|
| U1 | ESP32-S3FN8 | QFN56 7x7 | Dual-core LX7, 2.4GHz WiFi/BT5, 8 MB internal flash |
| U2 | AP2112K-3.3V | SOT-23-5 | 600 mA LDO |
| U3 | CP2102-GMR | QFN28 5x5 | USB Full-Speed to UART |
| U4 | USBLC6-2SC6 | SOT-23-6 | USB ESD protection |
| Y1 | NX3225GA-40.000MHz | SMD 3.2x2.5 | ESP32-S3 main clock (10 ppm) |
| ANT1 | Johanson 2450AT18A100 | 0402 | 50-ohm chip antenna |
| J2 | u.FL SMD | -- | RF test port |
| R3, R4 | 5.1k 0402 | 0402 | USB CC1/CC2 pull-downs |
| R5 | 10k 0402 | 0402 | EN pull-up to 3V3 |
| R6, R7 | 22R 0402 | 0402 | USB D+/D- series damping |
| C12, C13 | 12pF NP0 0402 | 0402 | Crystal load caps |
| TP1-TP3 | Test points | 1.5mm pad | 3V3, GND, RF_ANT |

---

## Repository structure

```
esp32-s3-rf-board/
├── firmware/                   # ESP-IDF firmware project
│   ├── main/
│   │   ├── main.c              # App entry point
│   │   ├── hw_config.h         # Pin and peripheral definitions
│   │   └── CMakeLists.txt
│   ├── CMakeLists.txt
│   └── sdkconfig.defaults
├── esp32-s3-rf-board.kicad_pcb # PCB layout
├── esp32-s3-rf-board.kicad_pro # Project / design rules
├── esp32-s3-rf-board.kicad_sch # Schematic
├── bom.csv                     # Bill of materials
├── generate_board.py           # PCB generator
├── reroute_clean.py            # Routing script
├── fix_pcb.py                  # Post-processing
└── ESP32-S3-RF-Board-Learning-Guide.md
```

---

## Known limitations (v1.2)

- The schematic is generated programmatically rather than hand-drawn. Symbols
  and nets are real and ERC passes with 0 errors; the remaining 110 warnings
  are cosmetic (off-grid labels, library registration, footprint link
  strings). A GUI pass would clean these up and improve readability.
- Only the pins used by the current design are modelled on the ESP32-S3
  schematic symbol. The PCB footprint has all 57 pads; strapping pins other
  than IO0 are left at their power-on defaults (SPI flash boot, 3.3V).
- **PCB DRC: 33 placement warnings + 120 unconnected nets**. All shorts,
  clearance, and keepout errors have been resolved programmatically. The
  remaining warnings are courtyard overlaps (16), silk-over-copper (15),
  and dangling vias (2) -- none are electrical problems. The 120
  unconnected items are signal/power nets that need routing in Pcbnew
  before Gerber export. Recommended sequence:
  1. Open the PCB in KiCad 9.
  2. Route the remaining nets (mostly power, USB, UART/I2C/SPI fanout).
  3. `kicad-cli pcb drc ...` should report 0 unconnected items before fab.

### DRC progress (for reference)

| Stage | Violations | Unconnected |
|-------|-----------:|------------:|
| Pre-v1.2 baseline      | 447 | 70  |
| After crystal/flash/sch fixes (initial v1.2) | 144 | 122 |
| After programmatic DRC cleanup (final v1.2)  |  33 | 120 |

### Resolved in v1.2

- 40 MHz crystal (Y1, NX3225GA) with 2x 12 pF NP0 load caps (C12, C13) on
  the ESP32-S3 XTAL_P / XTAL_N pins. Without this the chip has no clock.
- U1 changed from generic ESP32-S3 (no flash) to **ESP32-S3FN8** with 8 MB
  of internal flash. No external SPI flash needed; boots directly.
- EN pull-up (R5, 10 kΩ) to 3V3 so the reset button has something to pull
  against and the chip is enabled at power-on.
- 22 Ω series resistors (R6, R7) on USB D+/D- near the CP2102 to damp
  reflections on the full-speed differential pair.
- Decoupling caps repositioned so every VDD pad has a 100 nF cap within
  2 mm of pin centre.
- Real schematic with symbols + nets generated by `generate_board.py`.

### Resolved in v1.1

- CC1/CC2 5.1k pull-down resistors (R3, R4) added for USB power negotiation.
- ESD protection (U4, USBLC6-2SC6) added on USB D+/D-.
- Test points (TP1-TP3) added for 3.3V, GND, and RF_ANT.
