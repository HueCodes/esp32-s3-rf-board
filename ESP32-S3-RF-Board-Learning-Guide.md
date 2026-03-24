# ESP32-S3 RF Development Board - Complete Design Guide

**Project:** 4-Layer ESP32-S3 Dev Board with 2.4GHz WiFi/BT
**Board:** 50mm x 40mm | Stackup: JLC04161H-7628 | Manufacturer: JLCPCB
**Version:** v1.0 | Author: [Your Name]

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [What is KiCAD and How Files Work](#2-what-is-kicad-and-how-files-work)
3. [PCB Stackup - Why 4 Layers and How They Work](#3-pcb-stackup---why-4-layers-and-how-they-work)
4. [RF Design - The Most Critical Section](#4-rf-design---the-most-critical-section)
5. [Impedance Matching and the 50-Ohm Standard](#5-impedance-matching-and-the-50-ohm-standard)
6. [Power Architecture](#6-power-architecture)
7. [Component Selection and Placement](#7-component-selection-and-placement)
8. [Design Rules Explained](#8-design-rules-explained)
9. [Ground Planes, Vias, and EMI](#9-ground-planes-vias-and-emi)
10. [Decoupling Capacitors - Why They Matter](#10-decoupling-capacitors---why-they-matter)
11. [USB-C and USB-to-UART Bridge](#11-usb-c-and-usb-to-uart-bridge)
12. [Silkscreen and Mechanical Considerations](#12-silkscreen-and-mechanical-considerations)
13. [Opening and Working with the Project in KiCAD](#13-opening-and-working-with-the-project-in-kicad)
14. [Manufacturing with JLCPCB](#14-manufacturing-with-jlcpcb)
15. [Exporting Gerbers and BOM](#15-exporting-gerbers-and-bom)
16. [Validation Checklist](#16-validation-checklist)
17. [Glossary](#17-glossary)

---

## 1. Project Overview

This board is a self-contained ESP32-S3 development platform built around the bare die (not a module), which means you control every aspect of the RF path, power supply, and peripheral connectivity. This is significantly harder than using a pre-certified module like the ESP32-S3-WROOM, but it teaches real RF and PCB engineering.

### What this board does

- Hosts the **ESP32-S3 SoC** (System-on-Chip): Xtensa LX7 dual-core, 2.4GHz WiFi 802.11b/g/n, Bluetooth 5.0
- Powers itself from **USB-C** (5V input)
- Regulates power to **3.3V** for all digital logic using an LDO
- Provides a **USB-to-UART bridge** (CP2102) so you can program the ESP32-S3 over USB without an external programmer
- Exposes **UART, I2C, and SPI** as pin headers for connecting sensors and peripherals
- Has two **push buttons** (Reset and Boot) for firmware flashing and resets
- Has two **LEDs** (status on GPIO48, power indicator)

### Why design a bare chip board instead of using a module?

| Aspect | Module (e.g. WROOM) | Bare Chip (this board) |
|--------|---------------------|------------------------|
| RF certification | Pre-certified | Must pass regulatory testing |
| RF design | Done for you | You design the antenna/feedline |
| Size | Larger (module size) | Can be made much smaller |
| Cost at volume | Higher | Lower |
| Learning value | Minimal RF knowledge needed | Deep RF and EMC knowledge required |
| Portfolio impact | Low | High - shows RF competency |

---

## 2. What is KiCAD and How Files Work

KiCAD is an open-source EDA (Electronic Design Automation) suite. Version 8 is used here.

### File types in this project

| File | Format | Purpose |
|------|--------|---------|
| `esp32-s3-rf-board.kicad_pro` | JSON | Project settings, design rules, netclasses |
| `esp32-s3-rf-board.kicad_pcb` | S-expression | PCB layout: all physical geometry, copper, footprints |
| `esp32-s3-rf-board.kicad_sch` | S-expression | Schematic: logical circuit connections |
| `bom.csv` | CSV | Bill of Materials for manufacturing |
| `generate_board.py` | Python | Script that generated the KiCAD files |

### What is S-expression format?

KiCAD uses a Lisp-like text format called S-expressions. Everything is nested parentheses:

```
(kicad_pcb
  (version 20240108)
  (footprint "Package:ESP32-S3"
    (at 30 20)          ; position x=30mm y=20mm from origin
    (pad 1 smd rect     ; pad number 1, surface mount, rectangular
      (at 0 3.65)       ; pad position relative to footprint center
      (size 0.25 0.6)   ; pad dimensions 0.25mm wide, 0.6mm long
      (net 1 "GND")     ; connected to net 1 named "GND"
    )
  )
)
```

This is human-readable and version-control friendly. You can diff changes between commits.

### KiCAD coordinate system

- Origin (0, 0) is at the **top-left** of the workspace
- X increases to the **right**
- Y increases **downward** (opposite to standard math)
- All units are **millimeters** in KiCAD 8

So for our 50x40mm board, the corners are:
- Top-left: (0, 0)
- Top-right: (50, 0)
- Bottom-right: (50, 40)
- Bottom-left: (0, 40)

---

## 3. PCB Stackup - Why 4 Layers and How They Work

### Why not 2 layers?

A 2-layer board is cheaper but has serious problems for RF and mixed-signal designs:
- You cannot have a **continuous ground plane** (traces on both layers interrupt it)
- **RF impedance control** requires a known, unbroken reference plane at a precise distance
- **EMI** (electromagnetic interference) is much worse without a solid ground plane
- **Power distribution** competes with signal routing for layer space

### The JLC04161H-7628 Stackup

This is JLCPCB's standard 4-layer 1.6mm stackup. Here is the physical cross-section from top to bottom:

```
Layer 1 (F.Cu)    35um copper     ← Components, RF trace, signals
                  ─────────────────────────────────────────
Dielectric 1      0.2mm 7628      ← Prepreg (pressed together layers)
                  Er = 4.4
                  ─────────────────────────────────────────
Layer 2 (In1.Cu)  35um copper     ← Solid ground plane (GND)
                  ─────────────────────────────────────────
Core              1.065mm FR4     ← Rigid fiberglass core
                  Er = 4.5
                  ─────────────────────────────────────────
Layer 3 (In2.Cu)  35um copper     ← Power distribution (3V3, 5V)
                  ─────────────────────────────────────────
Dielectric 3      0.2mm 7628      ← Prepreg
                  Er = 4.4
                  ─────────────────────────────────────────
Layer 4 (B.Cu)    35um copper     ← Secondary signals, passives
```

Total thickness: 0.035 + 0.2 + 0.035 + 1.065 + 0.035 + 0.2 + 0.035 = **1.605mm ≈ 1.6mm**

### Layer assignment decisions

**Layer 1 (F.Cu) - Top copper:**
- All active components (ESP32-S3, LDO, CP2102, connectors)
- RF feedline (must be on this layer to reference Ground Plane on Layer 2)
- General signal traces
- Decoupling capacitors placed here near IC pins

**Layer 2 (In1.Cu) - Ground plane:**
- **SOLID, UNBROKEN copper pour connected to GND**
- No traces, no cutouts, no splits
- This is the reference plane for RF and all high-speed signals
- Provides a low-inductance return path for all currents

**Layer 3 (In2.Cu) - Power distribution:**
- 3.3V power plane covering most of the board
- 5V plane for USB input area
- Can have multiple power domains separated by gaps

**Layer 4 (B.Cu) - Bottom copper:**
- Secondary signal routing
- Passive components (caps, resistors) that overflow from top
- Some bypass capacitors can go here

### Why is Layer 2 so critical?

Every current flowing in a conductor creates a return current. The return current tries to flow directly below the forward current (the path of least inductance). If you have a trace on Layer 1 and a solid copper plane on Layer 2, the return current stays confined directly below the trace. This creates a well-defined transmission line with calculable impedance.

If the ground plane has gaps or cuts, the return current is forced to detour, increasing loop area and inductance - which causes EMI radiation and signal integrity problems.

**Rule: Never route traces on Layer 2. Never add cuts or splits to Layer 2.**

---

## 4. RF Design - The Most Critical Section

### The RF signal path

The ESP32-S3 has an internal RF transceiver that operates at 2.4GHz. The RF signal exits the chip through a dedicated RF pin. This signal must travel from that pin to the antenna through a controlled-impedance feedline.

Here is the complete RF path in this design:

```
[ESP32-S3 RF Pin (Pad 36)]
    → 0.6mm trace, F.Cu (Layer 1), 50-ohm microstrip
    → 45-degree bend segments (no 90-degree corners)
    → GND stitching vias every 6mm along the trace
    → [Matching network location - 0-ohm jumpers for tuning]
    → [ANT1: Johanson 2450AT18A100 chip antenna] and
    → [J2: u.FL connector for external antenna or RF analyzer]
```

### Why the feedline must be 50 ohms

When RF signals travel through a conductor, they behave like waves. If the impedance of the transmission line changes at any point, part of the wave is **reflected back** toward the source. These reflections:
- Waste transmit power (reduces range)
- Can damage the amplifier in the ESP32-S3
- Create standing waves that cause unpredictable behavior

The ESP32-S3's internal RF output is designed to drive a 50-ohm load. The Johanson chip antenna is also designed for a 50-ohm feed. So the trace connecting them must also be exactly 50 ohms at every point.

### Transmission line theory basics

A trace on a PCB over a ground plane forms a **microstrip transmission line**. Its characteristic impedance depends on:
- Trace width (W)
- Dielectric height (h) - distance to ground plane
- Dielectric constant of the substrate (Er)
- Trace thickness (t) - usually negligible

The approximate formula for microstrip impedance (Wheeler, valid for W/h > 1):

```
Z0 = (87 / sqrt(Er + 1.41)) * ln(5.98*h / (0.8*W + t))
```

For our JLC04161H-7628 stackup:
- h = 0.2mm (prepreg between Layer 1 and Layer 2)
- Er = 4.4 (7628 prepreg)
- t = 0.035mm (1oz copper)
- Target Z0 = 50 ohms

Solving for W:

```
50 = (87 / sqrt(5.41)) * ln(5.98 * 0.2 / (0.8*W + 0.035))
50 = 37.4 * ln(1.196 / (0.8*W + 0.035))
1.337 = ln(1.196 / (0.8*W + 0.035))
3.808 = 1.196 / (0.8*W + 0.035)
0.8*W + 0.035 = 0.314
W = 0.349mm ≈ 0.35mm
```

This design uses **W = 0.6mm** which accounts for:
- Manufacturing tolerance: JLCPCB can hold ±0.05mm trace width, so we need some margin
- Copper plating on via holes pulls effective stackup height slightly
- A slightly wider trace lowers impedance slightly toward 45 ohms, which is acceptable

**Use an online impedance calculator to verify**: Search for "KiCAD impedance calculator" or "Saturn PCB toolkit" to get precise values for your exact stackup.

### Coplanar Waveguide with Ground (CPWG) vs Microstrip

This design uses **microstrip** (trace over solid ground plane). An alternative is **CPWG** (coplanar waveguide with ground), where you also have ground copper on the same layer on both sides of the trace.

CPWG advantages:
- Better EMI shielding (signal is enclosed by ground on 3 sides)
- Less sensitive to dielectric thickness variation
- Better for very high frequencies (>5GHz)

CPWG disadvantage:
- Requires a gap between the trace and adjacent ground pour
- Harder to route in tight spaces
- Requires many stitching vias between the coplanar ground and the ground plane

For 2.4GHz, microstrip is entirely acceptable and simpler to implement correctly.

### Keepout zone around the antenna

The Johanson 2450AT18A100 chip antenna has a **radiating element** - the physical structure that converts RF current to electromagnetic waves. Any copper (ground, traces, power pours) within 5mm of this element will detune the antenna, shift its resonant frequency, and reduce its efficiency.

This design includes a keepout zone:
- **Center**: ANT1 position (44, 14 mm from board origin)
- **Radius**: 5mm
- **Restricted on ALL layers**: No copper, no traces, no vias

This means the ground plane (Layer 2) has a gap in this area. This is one of the few acceptable reasons to have a void in the ground plane.

### Why no 90-degree trace corners?

At 2.4GHz, a 90-degree corner in a trace creates a small capacitive stub (excess copper at the corner). This acts as a discontinuity in the transmission line, causing a small impedance bump and some reflections.

The fix is to use 45-degree bends or arc bends. At 2.4GHz, 45-degree bends have negligible impact. At higher frequencies (>10GHz), arc bends are preferred.

This rule also applies to all other traces, not just RF, for cleanliness.

### GND stitching vias along the RF trace

When the RF signal travels on Layer 1, the return current travels on Layer 2 (ground plane) directly below it. As the frequency increases, the "ground plane" needs to be reinforced so that the ground above the trace on Layer 1 is closely connected to the ground below on Layer 2.

GND stitching vias are vias placed along both sides of the RF trace, connecting the Layer 1 ground pour to the Layer 2 ground plane.

**Spacing**: At 2.4GHz, the wavelength in FR4 is:
```
lambda_FR4 = c / (f * sqrt(Er)) = 3e8 / (2.4e9 * sqrt(4.4)) = 0.0595m = 59.5mm
lambda/10 = 5.95mm ≈ 6mm
```

Place a via every 6mm on both sides of the RF trace. This prevents the ground reference from having any resonant behavior at 2.4GHz.

---

## 5. Impedance Matching and the 50-Ohm Standard

### Why 50 ohms?

50 ohms is an engineering compromise dating to WWII-era coaxial cable standards. It was chosen because:
- 30 ohm coax has maximum power handling (smaller loss)
- 77 ohm coax has minimum loss (lower attenuation)
- 50 ohm is approximately the geometric mean - reasonably good for both

The entire RF industry standardized on 50 ohms for single-ended signals and 75 ohms for video/broadcast. All RF test equipment (spectrum analyzers, vector network analyzers, signal generators) has 50-ohm inputs and outputs.

### The Johanson 2450AT18A100 chip antenna

This is a **ceramic chip antenna** in a 1206 (3.2 x 1.6mm) package.

Key specifications:
- Center frequency: 2450MHz
- Impedance: 50 ohms (no matching network needed when trace is 50 ohm)
- Gain: approximately 0 dBi (isotropic reference)
- Peak efficiency: ~75% (some energy lost as heat in the ceramic)
- Requires 5mm clearance on antenna side and 3mm on PCB ground side

### u.FL connector for testing

The u.FL connector (J2) is placed in parallel with the chip antenna. During RF testing, you can:
1. Connect a 50-ohm coaxial cable from the u.FL to a **Vector Network Analyzer (VNA)**
2. Measure S11 (return loss) to verify your trace impedance
3. Measure S21 (insertion loss) to characterize the feedline
4. Use an anechoic chamber to measure antenna radiation pattern

For normal operation, populate the chip antenna and leave u.FL unpopulated (or install a 0-ohm jumper to select which antenna to use).

### A note on regulatory compliance

Any product with an intentional RF radiator (WiFi, BT, etc.) must be tested and certified before commercial sale in most countries:
- USA: FCC Part 15 (modular certification or full board certification)
- EU: CE marking with EN 300 328 and EN 301 489
- Japan: TELEC

Using a pre-certified module (ESP32-S3-WROOM) lets you inherit that certification. With a bare chip, you need to test the whole board. This is expensive but allows more flexibility in product design.

For a portfolio piece, regulatory certification is not required.

---

## 6. Power Architecture

### The power flow

```
USB-C (5V, 500mA from host)
    → VBUS (5V rail)
    → AP2112K-3.3V LDO
        → 3.3V rail (VCC_3V3)
            → ESP32-S3 (all VCC pins)
            → CP2102 (VCC pin)
            → LEDs (through resistors)
            → Header pins (VCC on UART/I2C/SPI)
    → CP2102 VBUS pin (5V direct)
    → Power LED (through 1k resistor)
```

### Why an LDO (Low Dropout Regulator)?

The ESP32-S3 requires 3.0V - 3.6V power. USB provides 5V. We need to drop from 5V to 3.3V.

Options:
1. **Linear Regulator (LDO)**: Simple, cheap, low noise. Wastes excess voltage as heat: P_heat = (Vin - Vout) * Iload = (5-3.3) * 0.3A = 0.51W. Fine for a dev board.
2. **Buck converter (switching)**: Efficient (80-95%), but generates switching noise (ripple on the output) that can couple into RF circuitry. Requires additional filtering for RF applications.
3. **Charge pump**: Only practical for small current applications.

For an RF application, **LDOs are preferred** because they produce a much quieter power supply. Switching regulator noise at the switching frequency (and harmonics) can mix with the 2.4GHz signal and cause spurious emissions.

### AP2112K-3.3V

Key specs:
- Input voltage: 2.5V to 6V
- Output voltage: 3.3V fixed (this is the -3.3 variant)
- Output current: 600mA maximum
- Dropout voltage: 250mV at 600mA (so minimum Vin = 3.55V; USB 5V is fine)
- PSRR (Power Supply Rejection Ratio): ~65dB at 1kHz, decreasing at higher frequencies
- Package: SOT-23-5

The 600mA rating is sufficient because:
- ESP32-S3 peak current: ~350mA (transmitting at peak power)
- CP2102: ~100mA maximum
- Total: ~450mA, within 600mA budget with some margin

### Bulk decoupling capacitors

The AP2112K-3.3V datasheet specifies:
- Input: 1uF minimum capacitor
- Output: 1uF minimum capacitor

We use **10uF** on both input and output. Why larger than specified minimum?
1. USB cable has resistance/inductance - transient current demands can cause voltage drops
2. The ESP32-S3 has large transient current demands when transmitting
3. Larger bulk capacitance provides a local charge reservoir that the regulator doesn't have to supply instantaneously

The 10uF capacitors are ceramic X5R or X7R type in 0805 package. Avoid Y5V type (poor capacitance vs voltage/temperature behavior).

---

## 7. Component Selection and Placement

### Component placement strategy

**Rule**: Place components before routing. Never start routing until all components are placed.

**Priority order for placement**:
1. **RF components first**: ESP32-S3, antenna, u.FL. The antenna position is fixed (corner, clear of ground plane). The ESP32-S3 RF pin must point toward the antenna.
2. **Decoupling capacitors second**: Each cap must be within 2mm of its IC pin. Place them immediately after placing the IC.
3. **Power components third**: LDO near the USB-C connector (power entry point).
4. **Connectors on edges**: USB-C, pin headers, and u.FL should be on board edges.
5. **Buttons and LEDs**: Place near accessible edges.
6. **Remaining passives**: Fill in remaining spaces.

### ESP32-S3 QFN56 package

The QFN (Quad Flat No-Lead) package has:
- 56 pads on the perimeter, 14 per side, 0.4mm pitch
- 1 large exposed pad (EP) on the bottom center: 5.7 x 5.7mm, connected to GND
- The EP must be soldered to the PCB for both electrical (ground connection) and thermal (heat dissipation) purposes
- Requires a solder paste stencil with an opening over the EP
- The EP copper pad on the PCB should have a thermal relief pattern with via-in-pad for heat sinking

**Critical**: The ESP32-S3 RF pin (typically around pad 36 in the QFN56 package) must have a clear 50-ohm trace leading to the antenna. No other traces should cross the RF path.

### Johanson 2450AT18A100 placement rules

From the datasheet:
- Place at the edge of the PCB (not in the center)
- The radiating end of the antenna must face off the board edge or into free space
- Minimum 5mm clearance from all copper on all layers on the radiating side
- Ground plane should extend under and behind the antenna (on the non-radiating side)
- The feed end connects to the RF trace; the other end connects to GND (or is a no-connect depending on variant)

This design places the antenna at (44, 14), near the right edge of the 50mm-wide board. The keepout zone extends from approximately x=39mm to x=50mm in the RF area.

### CP2102 - USB to UART bridge

The CP2102 is a Silicon Labs chip that converts USB (full-speed, 12Mbps) to UART (TTL levels). It is the most common USB-to-UART bridge in the hobbyist/engineering world.

In this design:
- USB D+/D- from the USB-C connector connect to CP2102 D+/D-
- CP2102 TX/RX connect to ESP32-S3 RX/TX (crossed: TX of bridge → RX of ESP32-S3)
- CP2102 DTR/RTS pins can be used for automatic programming (auto-reset circuit)
- The CP2102 has an internal 3.3V regulator but in this design we supply it from our AP2112K output

### Why do TX and RX cross?

This is a very common source of confusion. From each chip's perspective:
- TX (Transmit) is the pin that sends data out
- RX (Receive) is the pin that receives data in

For two devices to communicate, one's TX must connect to the other's RX:
```
CP2102 TX → ESP32-S3 RX (CP2102 sends to ESP32-S3)
ESP32-S3 TX → CP2102 RX (ESP32-S3 sends to CP2102)
```

---

## 8. Design Rules Explained

Design rules are constraints enforced by the DRC (Design Rule Check). They prevent manufacturing defects.

### Minimum trace width: 0.1mm (signal), 0.5mm (power)

JLCPCB's standard process can reliably manufacture traces down to **0.1mm** (4 mils). Traces narrower than this risk:
- Not etching completely (shorts to adjacent traces)
- Etching away entirely (opens)
- Excessive resistance for power traces

Power traces must be wider because current causes heating. Using **P = I² × R** (where R is the trace resistance):
- 0.2mm trace, 1oz copper, 50mm length: R ≈ 0.5 ohms
- At 300mA: P = 0.3² × 0.5 = 45mW - acceptable
- At 1A: P = 1² × 0.5 = 500mW - too much (trace temperature rise)

Use 0.5mm or wider for any trace carrying >100mA.

### Minimum clearance: 0.1mm

Clearance is the gap between adjacent copper features (traces, pads, zones). If copper is too close:
- Risk of shorts during manufacturing
- Risk of arcing under high voltage (not an issue at 3.3V but good practice)

JLCPCB standard process minimum clearance: **0.1mm** (4 mils).

### Minimum via drill: 0.3mm, via ring 0.15mm

Vias connect copper layers. The via consists of:
- A **drilled hole** (the drill diameter)
- **Copper plating** on the hole walls (20-30um thick)
- **Annular ring**: copper pad on each layer around the hole

JLCPCB minimum drill: 0.2mm (but 0.3mm is more reliable and cheaper).
Minimum annular ring: 0.15mm.
So minimum via pad diameter: 0.3 + 2×0.15 = 0.6mm.
This design uses 0.8mm pad / 0.4mm drill (standard via).

### Net classes

This design defines three net classes in the project file:

1. **Default**: 0.25mm track, 0.1mm clearance - for general signal traces
2. **RF_50OHM**: 0.6mm track, 0.15mm clearance - auto-applied to RF_ANT net
3. **POWER**: 0.5mm track, 0.15mm clearance - auto-applied to GND, 3V3, 5V nets

Net classes allow you to set constraints once and have them automatically enforced everywhere.

---

## 9. Ground Planes, Vias, and EMI

### Why a solid ground plane matters for EMI

Every trace carrying high-frequency current radiates electromagnetic energy. This radiation (EMI) can:
- Interfere with other electronics nearby (emissions)
- Be picked up by your own board and corrupt signals (susceptibility)
- Fail regulatory testing (FCC, CE)

A solid ground plane below all traces ensures return currents flow directly below their corresponding signal traces, creating tightly coupled transmission lines with minimal loop area. Minimal loop area = minimal radiation.

### Star ground topology

Traditional advice is to avoid "ground loops" by using a star topology - all ground connections meeting at a single point. For a PCB with a solid ground plane, this is somewhat superseded by the plane itself, but the principle still applies:

- Avoid paths where high-current ground returns (from the LDO output, for example) flow under sensitive analog or RF circuitry
- Connect the ground plane pour to the main ground star via short low-inductance connections
- Keep analog ground and digital ground separate if possible, connecting at one point

In this design, the ground plane is solid copper on Layer 2. The ground star point is at the USB-C connector (the point where external ground comes in). All current flows away from the USB-C connector, through the circuits, and back to the USB-C ground via the ground plane.

### Via stitching between Layer 1 ground and Layer 2 ground

The F.Cu (Layer 1) ground pour that surrounds the RF trace and covers the rest of the board must be connected to the In1.Cu (Layer 2) ground plane with stitching vias. Without these vias:
- Layer 1 ground is floating at RF frequencies (the plane has distributed inductance)
- The ground plane effect is lost for currents flowing on Layer 1

Place stitching vias:
- Around the perimeter of the board (every 5-8mm)
- On both sides of the RF trace (every 6mm for 2.4GHz)
- Near each IC (within 1-2mm of ground pads)
- Under or near bypass capacitors

---

## 10. Decoupling Capacitors - Why They Matter

### The problem: power supply impedance

The power supply (LDO) cannot respond instantaneously to current demands. When the ESP32-S3 turns on its RF transmitter, it might demand 200mA within nanoseconds. The LDO's response time is limited by its bandwidth (typically 10-100kHz).

Between the LDO and the ESP32-S3, the PCB traces have inductance:
- 1mm of 0.5mm-wide trace ≈ 1nH inductance
- At 100MHz: Z = 2π × 100MHz × 1nH = 0.63 ohms
- At 200mA transient: V_drop = 0.63 × 0.2 = 126mV

This voltage drop on the supply rail corrupts the RF signal and can cause the MCU to brown-out reset.

### The solution: local charge reservoirs (decoupling capacitors)

A **decoupling capacitor** (also called bypass capacitor) placed near the IC acts as a local charge reservoir. When the IC demands a sudden burst of current, the capacitor provides it immediately, before the LDO or trace inductance can respond.

For the capacitor to work, it must be placed **as close as possible** to the VCC pin being decoupled. Long traces between the capacitor and the VCC pin add inductance that defeats the purpose.

**Rule**: 100nF capacitor within 2mm of every VCC pin.

### Capacitor selection

| Value | Purpose | Package |
|-------|---------|---------|
| 10uF | Bulk decoupling at power entry (LDO output) | 0805 |
| 100nF | High-frequency decoupling at each IC VCC pin | 0402 |
| 10nF | Optional: very high-frequency RF supply pin decoupling | 0402 |

**Capacitor types**: Use X5R or X7R ceramic for decoupling. Avoid:
- Y5V / Z5U: poor capacitance vs. voltage/temperature
- Electrolytic / Tantalum: high ESL (equivalent series inductance), not useful above 1MHz
- NPO/C0G: excellent stability but low capacitance in small packages

### Why 100nF is the magic value

100nF (0.1uF) has a self-resonance frequency (SRF) of approximately 50-500MHz for a 0402 package. Below SRF, the cap acts capacitively (good). Above SRF, it acts inductively (bad).

For 100MHz digital signals, 100nF 0402 is ideal. For higher frequencies, add a 10nF cap in parallel (different SRF). The parallel combination has broader effective bandwidth.

---

## 11. USB-C and USB-to-UART Bridge

### USB-C connector wiring

The USB-C connector used (GCT USB4085 or equivalent 16-pin version) has these key signals:

| Pin Name | Count | Function |
|---------|-------|---------|
| VBUS | 4 | 5V power (connect all 4, handle current) |
| GND | 4 | Ground (connect all 4) |
| D+ | 2 | USB data positive |
| D- | 2 | USB data negative |
| CC1/CC2 | 2 | Configuration channel (for USB-PD negotiation) |
| SBU1/SBU2 | 2 | Sideband use (unused for basic USB 2.0) |

For a USB 2.0 device (which is what CP2102 is):
- Connect both D+ pins together
- Connect both D- pins together
- Connect all VBUS pins together (handles up to 1.5A)
- Add 5.1k resistors from CC1 and CC2 to GND (tells the host this is a USB device, not a cable)

### CC pin resistors - critical detail

Without the 5.1k CC resistors, a USB-C port behaves as a cable, not a device. Hosts may refuse to power it or may not provide 5V at all on certain USB-C ports. **Always include CC1 and CC2 resistors.**

### USB differential pair routing

D+ and D- carry differential signals at 12Mbps (Full Speed USB). These must be:
- Routed as a matched-length pair (length difference < 0.1mm)
- Kept at 90 ohms differential impedance
- Not interrupted by vias (if possible)
- Not adjacent to RF traces or noisy signals

For 90-ohm differential impedance on the JLC04161H-7628 stackup (Layer 1 to Layer 2 GND, h=0.2mm):
- Trace width: ~0.2mm each
- Trace spacing (edge to edge): ~0.2mm
- This gives approximately 90-ohm differential

At Full Speed USB (12Mbps), impedance control is less critical than at USB 3.0 (5Gbps), but it's still good practice.

---

## 12. Silkscreen and Mechanical Considerations

### Silkscreen best practices

The silkscreen (F.SilkS / B.SilkS) layer contains:
- Reference designators (U1, C1, R1...)
- Pin 1 markers on ICs
- Board title, version, author
- Connector pin labels (VCC, GND, TX, RX on headers)
- Test point labels

**Rules**:
- No silkscreen over solder pads (will cause solder mask adhesion issues)
- No silkscreen over vias (ink bleeds into the via, looks bad)
- Minimum text height: 0.8mm (smaller text is hard to read)
- Reference designators must all be visible and readable after assembly

This design includes:
- Board title: "ESP32-S3 RF Dev Board"
- Version: "v1.0"
- Author placeholder: "[Your Name]"
- All header pin labels

### Pick-and-place efficiency

For JLCPCB's SMT assembly service, passive components (caps, resistors, LEDs) should be:
- Aligned to a consistent angle (0 or 90 degrees)
- Organized in rows/grids (faster for the pick-and-place machine)
- All the same orientation to minimize tape feeder changes

### Board edge clearance

Keep all copper (traces, pads, zones) at least 0.3mm from the board edge (Edge.Cuts line). The routing bit that cuts the board can cause copper to peel if it's too close to the edge. For edge connectors (like USB-C), the pad extends to or past the edge intentionally.

---

## 13. Opening and Working with the Project in KiCAD

### Setup steps

1. **Install KiCAD 8**: Download from kicad.org (free, open source)
2. **Open the project**: File → Open Project → select `esp32-s3-rf-board.kicad_pro`
3. **Open the PCB editor**: Click "PCB Editor" in the KiCAD project manager

### First things to do in the PCB editor

1. **Verify the stackup**: Board Setup → Board Stackup → Physical Stackup
   - Should show JLC04161H-7628 configuration
   - 4 copper layers with 0.2mm prepreg between L1/L2 and L3/L4

2. **Run DRC** (Design Rule Check): Inspect → Design Rules Checker
   - This will flag any violations of the design rules
   - Common initial issues: missing connections (airwires), clearance violations

3. **View the board**: Press `Ctrl+Shift+3` to open 3D view
   - You can see the approximate board layout
   - Check component clearances visually

4. **Check the ratsnest**: Enable "Ratsnest" in the view options
   - Ratsnest shows unrouted connections as thin lines
   - All connections must be routed before manufacturing

### What needs to be done to complete the board

The generated files provide:
- Board outline and stackup ✓
- Component placement ✓
- Net definitions ✓
- RF trace (critical path) ✓
- Ground planes (Layer 2 fill) ✓
- Keepout zone ✓

Still needed:
- Route remaining signal traces (I2C, SPI, UART, GPIO)
- Route power from LDO to ESP32-S3 VCC pins
- Route USB D+/D- to CP2102
- Add via stitching around board perimeter
- Run DRC and fix all violations
- Add teardrops to pad-to-trace connections
- Verify footprints against physical component datasheets

### Tips for routing

- Use `X` to start routing a trace
- Use `V` to add a via while routing
- Press `/` to switch routing layers
- Use `Ctrl+Z` to undo
- The **Inspect → Net Inspector** shows all nets and their connections
- The **Inspect → Board Statistics** shows trace counts, via counts

### Footprint verification

Before manufacturing, verify each footprint against the component's official datasheet:
- Compare pad dimensions and pitch to IPC-7351 footprint standards
- For the ESP32-S3 QFN56: verify against Espressif's recommended PCB footprint in their hardware design guide
- For the Johanson antenna: use the footprint exactly from their datasheet (page 4, PCB land pattern)

---

## 14. Manufacturing with JLCPCB

### Why JLCPCB?

JLCPCB (JLC PCB) is a Chinese PCB manufacturer popular with engineers and makers because:
- Low cost: 5 boards for ~$2 USD (standard 2-layer) or ~$12 (4-layer)
- Fast turnaround: 24-48 hours production + shipping
- High quality: IPC Class 2 standard
- Extensive stackup options (including JLC04161H-7628 used here)
- SMT assembly service available (JLCPCB will solder components for you)

### JLC04161H-7628 stackup confirmation

When ordering, specify:
- Layers: 4
- Thickness: 1.6mm
- Stackup: JLC04161H-7628
- In the order notes or stackup specification

JLCPCB has a page where you can confirm impedance-controlled traces. For this design:
- Impedance specification: Layer 1 to Layer 2, target 50 ohms ± 10%, trace width 0.6mm
- They will adjust trace width slightly in manufacturing if needed

### JLCPCB assembly service

JLCPCB's SMT assembly service (JLCPCB PCBA) allows them to place components. You provide:
1. Gerber files (board geometry)
2. BOM (Bill of Materials - what components)
3. CPL/POS file (Component Placement List - where each component goes)

Using parts from **JLCPCB's Basic Parts Library** (marked "Basic" in their component search):
- No added setup fee per component type
- Parts stocked at their factory
- Instant availability

Parts marked "Extended" require a $3 setup fee each. Prefer Basic parts when possible.

### The BOM in this project

The `bom.csv` file contains all components with their JLCPCB part numbers. Key parts:
- C2913202: ESP32-S3 QFN56 (Extended)
- C51118: AP2112K-3.3TRG1 LDO (Basic)
- C6568: CP2102-GMR (Basic)
- C165948: USB-C 16P connector (Basic)
- C1525: 100nF 0402 cap (Basic)
- C17024: 10uF 0805 cap (Basic)

---

## 15. Exporting Gerbers and BOM

### Generating Gerber files in KiCAD

Gerber files are the industry-standard format for PCB manufacturing. Each file represents one layer.

In KiCAD PCB Editor:
1. File → Fabrication Outputs → Gerbers (RS-274X)
2. Select output directory: `gerbers/`
3. Select layers to export:
   - F.Cu (top copper)
   - In1.Cu (inner layer 1, ground plane)
   - In2.Cu (inner layer 2, power plane)
   - B.Cu (bottom copper)
   - F.Paste (top solder paste for stencil)
   - B.Paste (bottom solder paste)
   - F.SilkS (top silkscreen)
   - B.SilkS (bottom silkscreen)
   - F.Mask (top solder mask)
   - B.Mask (bottom solder mask)
   - Edge.Cuts (board outline)
4. Also generate: Drill file (NC Drill) for through-holes and vias
5. Zip all files → upload to JLCPCB

### Generating the position/CPL file

For SMT assembly, KiCAD generates a component placement file:
1. File → Fabrication Outputs → Component Placement (.pos)
2. Format: CSV
3. Units: mm

This file tells the pick-and-place machine where each component is, what rotation it's at.

### Generating BOM from KiCAD

The schematic-driven BOM (Tools → Generate BOM in Schematic Editor) is more accurate than a manually written CSV, but requires the schematic to be fully annotated. For now, use the provided `bom.csv`.

---

## 16. Validation Checklist

Use this checklist before sending to manufacturing:

### RF and antenna
- [ ] RF trace width is 0.6mm from ESP32-S3 RF pin to antenna
- [ ] No 90-degree corners on RF trace
- [ ] Keepout zone covers 5mm radius around antenna on ALL layers
- [ ] GND stitching vias every 6mm on both sides of RF trace
- [ ] No copper pours overlap the keepout zone
- [ ] Antenna placement is at board edge
- [ ] u.FL connector is accessible from board edge

### Ground plane
- [ ] Layer 2 (In1.Cu) has solid copper fill over entire board
- [ ] No traces on Layer 2
- [ ] No cuts or splits in Layer 2 (except antenna keepout void)
- [ ] Ground pour stitching vias connect Layer 1 GND to Layer 2

### Power
- [ ] 10uF caps within 3mm of LDO input and output
- [ ] 100nF caps within 2mm of every ESP32-S3 VCC pin
- [ ] Power traces are at least 0.5mm wide
- [ ] LDO has thermal pad connected to ground via

### USB
- [ ] CC1 and CC2 pins have 5.1k resistors to GND
- [ ] USB D+ and D- are routed as matched-length differential pair
- [ ] USB-C connector mounting pads are connected to GND

### Design rules
- [ ] DRC passes with zero errors
- [ ] All ratsnest lines (unrouted nets) are resolved
- [ ] No solder mask violations
- [ ] All reference designators are visible and not covered
- [ ] Board outline is closed (no gaps)

### Manufacturing
- [ ] Minimum trace width ≥ 0.1mm
- [ ] Minimum clearance ≥ 0.1mm
- [ ] Minimum via drill ≥ 0.3mm
- [ ] All copper is ≥ 0.3mm from board edge
- [ ] Gerbers generated for all layers
- [ ] Drill file generated
- [ ] BOM has JLCPCB part numbers for all components

---

## 17. Glossary

**Annular ring**: The copper ring around a via hole on each copper layer. Minimum ring width ensures reliable via-to-pad connections after drilling tolerance.

**Characteristic impedance (Z0)**: The impedance of a transmission line at a specific frequency, determined by its geometry. For RF work, Z0 = 50 ohms.

**CPWG (Coplanar Waveguide with Ground)**: A transmission line topology where ground copper runs on the same layer as the signal trace, with a gap between them, AND a ground plane below.

**Decoupling capacitor**: A capacitor placed close to an IC's power pin to suppress power supply noise and provide local charge during transient current demands.

**DRC (Design Rule Check)**: An automated check in the PCB editor that verifies the layout meets specified design rules (minimum trace width, clearance, etc.).

**EDA (Electronic Design Automation)**: Software for designing electronic circuits and PCBs. KiCAD is an open-source EDA tool.

**EMI (Electromagnetic Interference)**: Unwanted electromagnetic energy that interferes with other devices. Caused by fast-changing currents in conductors.

**Er / Epsilon_r**: Relative permittivity (dielectric constant) of a material. Measures how well a material stores electrical energy compared to vacuum. FR4 ≈ 4.4 at 1GHz.

**FR4**: Fiberglass-reinforced epoxy laminate. The standard PCB substrate material. "FR" stands for Flame Retardant.

**Footprint**: The PCB representation of a physical component - the pads, courtyard, silkscreen outline, and 3D model reference.

**Gerber**: Industry-standard file format for PCB manufacturing, describing each layer as vector artwork. One Gerber file per layer.

**GND / Ground**: The reference voltage (0V) for all signals. In RF design, a solid ground plane is essential for controlled-impedance traces and EMI control.

**IPC-7351**: Industry standard for PCB footprint dimensions, published by the Institute of Printed Circuits.

**Keepout zone**: A region on the PCB where no copper, traces, or vias are allowed. Used around antennas to prevent detuning.

**Lambda (λ)**: Wavelength of an electromagnetic wave at a given frequency. In free space: λ = c/f = 3e8 / 2.4e9 = 125mm. In FR4: λ_FR4 = λ / sqrt(Er) ≈ 60mm at 2.4GHz.

**LDO (Low Dropout Regulator)**: A type of linear voltage regulator that operates with a small voltage difference (dropout voltage) between input and output.

**Microstrip**: A transmission line formed by a trace on the top copper layer over a ground plane. The signal propagates in the dielectric between the trace and the ground plane.

**Net**: An electrical connection that must be made between pads. In KiCAD, nets define which pads are connected.

**Net class**: A group of nets that share the same design rules (trace width, clearance).

**PCBA (PCB Assembly)**: The process of soldering components onto a bare PCB. JLCPCB PCBA = JLCPCB does both the PCB and the assembly.

**Prepreg**: Pre-impregnated glass fiber material used to bond PCB layers together. "7628" refers to a specific glass weave style. Melts and flows during lamination, then cures rigid.

**QFN (Quad Flat No-Lead)**: A SMD IC package with pads on the bottom edges (no leads extending outward) and a large exposed thermal pad on the bottom.

**Ratsnest**: Lines in the PCB editor showing unrouted net connections (where you still need to route traces).

**Reflection coefficient (S11)**: Measures how much RF signal is reflected back toward the source. In decibels (dB), a good match shows S11 < -10dB (less than 10% power reflected).

**Return loss**: The ratio (in dB) of incident power to reflected power at an RF port. Higher return loss = better impedance match. S11 of -20dB means 1% power reflected.

**S-parameters**: Scattering parameters describing RF networks. S11=reflection at port 1, S21=transmission from port 1 to port 2.

**SMD/SMT**: Surface Mount Device / Surface Mount Technology. Components soldered to pads on the PCB surface (as opposed to through-hole components with leads through holes).

**SOT-23-5**: Small Outline Transistor package with 5 pins. Used for the AP2112K LDO.

**Stackup**: The physical layer structure of a PCB - how many layers, their thicknesses, and the dielectric materials between them.

**Transmission line**: A two-conductor electrical structure that guides electromagnetic waves. On PCBs: microstrip, stripline, or coplanar waveguide.

**Via**: A plated hole that connects copper layers. Current flows through the copper plating on the hole walls.

**VNA (Vector Network Analyzer)**: RF test equipment that measures S-parameters. Essential for characterizing RF traces and antennas.

---

## Additional Resources

**Impedance calculation tools:**
- JLCPCB Impedance Calculator: jlcpcb.com/impedance (enter your stackup, get trace widths)
- Saturn PCB Design Toolkit: saturnpcb.com/pcb_toolkit (free, comprehensive)
- KiCAD PCB Calculator: included with KiCAD installation

**ESP32-S3 documentation:**
- ESP32-S3 Datasheet: Espressif Systems (search "ESP32-S3 datasheet" on espressif.com)
- ESP32-S3 Hardware Design Guidelines: search "ESP32-S3 Hardware Design Guidelines" on espressif.com
- The Hardware Design Guidelines document contains the recommended RF layout, antenna placement, and decoupling capacitor values directly from the chip manufacturer

**Johanson 2450AT18A100 documentation:**
- Johanson Technology website: johansontechnology.com
- The datasheet includes the exact PCB land pattern (footprint) and placement guidelines

**RF design learning:**
- "RF Circuit Design" by Christopher Bowick - excellent practical introduction
- "Microwave Engineering" by David Pozar - more advanced, used in university courses
- Altium's Signal Integrity content (free articles/videos): resources.altium.com

**KiCAD learning:**
- KiCAD official documentation: docs.kicad.org
- Chris Gammell's "Getting to Blinky" series on YouTube - KiCAD from scratch

---

*This board was designed following professional RF PCB design practices. The keepout zone, 50-ohm controlled-impedance feedline, solid ground plane, and decoupling capacitor placement are all industry-standard techniques used in commercial wireless product development.*
