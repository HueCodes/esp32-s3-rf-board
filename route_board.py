#!/usr/bin/env python3
"""Reroute the ESP32-S3 RF dev board PCB.

Steps:
  1. Move U2, C7, C8 to new positions.
  2. Fix U2 pad net assignments (VIN=5V, GND, EN=5V, VOUT=3V3, GND).
  3. Fix C7/C8 pad nets (C7 pad1=5V, C8 pad1=5V — both are VIN bulk caps).
  4. Remove all existing segments and vias.
  5. Add all new segments and vias per the routing specification.
  6. Write back the file.
"""

import re
import uuid as uuid_module

PCB_FILE = "/Users/hugh/Dev/Hardware/esp32-s3-rf-board/esp32-s3-rf-board.kicad_pcb"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def new_uuid():
    return str(uuid_module.uuid4())


def fmt(v):
    """Format a float for KiCad: up to 4 decimal places, no trailing zeros."""
    s = f"{v:.4f}"
    s = s.rstrip('0').rstrip('.')
    return s


def route_45(x1, y1, x2, y2):
    """Return list of (ax, ay, bx, by) segment tuples using 45-degree routing."""
    dx = x2 - x1
    dy = y2 - y1
    if abs(dx) < 0.001 or abs(dy) < 0.001:
        return [(x1, y1, x2, y2)]
    diag = min(abs(dx), abs(dy))
    sx = 1 if dx > 0 else -1
    sy = 1 if dy > 0 else -1
    if abs(dx) >= abs(dy):
        # Diagonal first, then horizontal/vertical remainder
        mx = round(x1 + sx * diag, 4)
        my = round(y1 + sy * diag, 4)
        return [(x1, y1, mx, my), (mx, my, x2, y2)]
    else:
        # Horizontal/vertical first, then diagonal
        mx = round(x2 - sx * diag, 4)
        my = round(y2 - sy * diag, 4)
        return [(x1, y1, mx, my), (mx, my, x2, y2)]


def seg(x1, y1, x2, y2, width, net, layer="F.Cu"):
    return (f'  (segment (start {fmt(x1)} {fmt(y1)}) (end {fmt(x2)} {fmt(y2)})'
            f' (width {width}) (layer "{layer}") (net {net}) (tstamp "{new_uuid()}"))')


def via(x, y, net, top="F.Cu", bot="B.Cu", size=0.8, drill=0.4):
    return (f'  (via (at {fmt(x)} {fmt(y)}) (size {size}) (drill {drill})'
            f' (layers "{top}" "{bot}") (net {net}) (tstamp "{new_uuid()}"))')


def route_net(x1, y1, x2, y2, width, net, layer="F.Cu"):
    """Route a net using 45-degree bends, returning a list of segment strings."""
    return [seg(ax, ay, bx, by, width, net, layer)
            for ax, ay, bx, by in route_45(x1, y1, x2, y2)]


# ---------------------------------------------------------------------------
# Load PCB
# ---------------------------------------------------------------------------

with open(PCB_FILE, 'r') as f:
    content = f.read()

# ---------------------------------------------------------------------------
# Step 1: Move components
# ---------------------------------------------------------------------------

# U2: (8 8) -> (8 32)
content = re.sub(
    r'(footprint "U2_fp".*?\(at\s+)8(\s+)8(\))',
    r'\g<1>8\g<2>32\g<3>',
    content, count=1, flags=re.DOTALL
)

# C7: (10.5 9.5) -> (10.5 31.5)
content = re.sub(
    r'(footprint "C7_fp".*?\(at\s+)10\.5(\s+)9\.5(\))',
    r'\g<1>10.5\g<2>31.5\g<3>',
    content, count=1, flags=re.DOTALL
)

# C8: (5.5 9.5) -> (5.5 31.5)
content = re.sub(
    r'(footprint "C8_fp".*?\(at\s+)5\.5(\s+)9\.5(\))',
    r'\g<1>5.5\g<2>31.5\g<3>',
    content, count=1, flags=re.DOTALL
)

# ---------------------------------------------------------------------------
# Step 2: Fix U2 pad net assignments
# U2 SOT-23-5 actual pinout for AP2112K:
#   pad 1 (at -0.95 -0.95) = VIN  → net 3 5V
#   pad 2 (at -0.95  0.00) = GND  → net 1 GND
#   pad 3 (at -0.95 +0.95) = EN   → net 3 5V (tied to VIN for always-on)
#   pad 4 (at +0.95 -0.475) = VOUT → net 2 3V3
#   pad 5 (at +0.95 +0.475) = GND  → net 1 GND
# ---------------------------------------------------------------------------

# We need to find the U2_fp block and replace pad net definitions inside it.
# Extract U2_fp block
u2_match = re.search(r'(  \(footprint "U2_fp".*?\n  \))', content, re.DOTALL)
if u2_match:
    u2_block = u2_match.group(1)
    u2_new = u2_block

    # pad 1: currently net 16 "EN" -> net 3 "5V"
    u2_new = re.sub(
        r'(\(pad "1" smd rect \(at -0\.95 -0\.95\).*?)\(net \d+ "[^"]*"\)',
        r'\g<1>(net 3 "5V")',
        u2_new
    )
    # pad 2: net 1 GND — already correct, but ensure
    u2_new = re.sub(
        r'(\(pad "2" smd rect \(at -0\.95 0\).*?)\(net \d+ "[^"]*"\)',
        r'\g<1>(net 1 "GND")',
        u2_new
    )
    # pad 3: currently net 3 "5V" — already correct per file (keep EN=5V)
    u2_new = re.sub(
        r'(\(pad "3" smd rect \(at -0\.95 0\.95\).*?)\(net \d+ "[^"]*"\)',
        r'\g<1>(net 3 "5V")',
        u2_new
    )
    # pad 4: currently no net -> net 2 "3V3"
    # It may have no (net ...) at all, or have one. Handle both.
    if re.search(r'\(pad "4".*?\(net \d+', u2_new, re.DOTALL):
        u2_new = re.sub(
            r'(\(pad "4" smd rect \(at 0\.95 -0\.475\).*?)\(net \d+ "[^"]*"\)',
            r'\g<1>(net 2 "3V3")',
            u2_new
        )
    else:
        # Insert net before closing paren of pad 4
        u2_new = re.sub(
            r'(\(pad "4" smd rect \(at 0\.95 -0\.475\) \(size[^)]+\) \(layers[^)]+\))\s*(\(uuid)',
            r'\g<1> (net 2 "3V3") \g<2>',
            u2_new
        )
    # pad 5: currently net 2 "3V3" -> net 1 "GND"
    u2_new = re.sub(
        r'(\(pad "5" smd rect \(at 0\.95 0\.475\).*?)\(net \d+ "[^"]*"\)',
        r'\g<1>(net 1 "GND")',
        u2_new
    )

    content = content.replace(u2_block, u2_new)

# ---------------------------------------------------------------------------
# Step 3: Fix C7 pad 1 net (was 3V3, should be 5V — VIN bulk cap)
# C8 pad 1 net (was 3V3, should be 5V — also VIN side)
# ---------------------------------------------------------------------------

# C7 pad 1: net 3 "5V" — already correct per file inspection
# C8 pad 1: currently net 2 "3V3" -> should be net 3 "5V"
c8_match = re.search(r'(  \(footprint "C8_fp".*?\n  \))', content, re.DOTALL)
if c8_match:
    c8_block = c8_match.group(1)
    c8_new = re.sub(
        r'(\(pad "1" smd rect \(at -0\.9 0\).*?)\(net \d+ "[^"]*"\)',
        r'\g<1>(net 3 "5V")',
        c8_block
    )
    content = content.replace(c8_block, c8_new)

# ---------------------------------------------------------------------------
# Step 4: Remove all existing segments and vias
# ---------------------------------------------------------------------------

# Remove standalone segment lines
content = re.sub(r'\n  \(segment [^\n]+\)', '', content)
# Remove standalone via lines
content = re.sub(r'\n  \(via [^\n]+\)', '', content)

# ---------------------------------------------------------------------------
# Step 5: Build all new routing
# ---------------------------------------------------------------------------

lines = []

# === NET 4 (RF_ANT) — 0.6mm — keep existing RF spine, reroute ===
# RF spine: U1 pad 36 (29.8, 16.2) -> diagonal to (32, 14) -> horizontal to ANT1 (43.5, 14)
lines.append(seg(29.8, 16.2, 32.0, 14.0, 0.6, 4))
lines.append(seg(32.0, 14.0, 43.5, 14.0, 0.6, 4))

# RF GND stitching vias (net 1) flanking the RF trace
lines.append(via(31.7485, 15.9485, 1))
lines.append(via(30.0515, 14.2515, 1))
lines.append(via(37.75, 15.2, 1))
lines.append(via(37.75, 12.8, 1))
lines.append(via(34.0, 15.2, 1))
lines.append(via(34.0, 12.8, 1))
lines.append(via(42.0, 15.2, 1))
lines.append(via(42.0, 12.8, 1))

# === NET 3 (5V) — 0.8mm power ===
# J1 pad 2 (3.4, 34.5) <-> J1 pad 7 (5.4, 34.5): horizontal bus segment
lines.append(seg(3.4, 34.5, 5.4, 34.5, 0.8, 3))

# J1 pad 2 -> U2 pad 1: U2 is now at (8,32), pad 1 at (8-0.95, 32-0.95) = (7.05, 31.05)
# Route: (3.4, 34.5) -> 45 degree to (7.05, 31.05)
# dx=3.65, dy=-3.45 -> diag=3.45, go diag first then horizontal
# Actually use route_net
for s in route_net(3.4, 34.5, 7.05, 31.05, 0.8, 3):
    lines.append(s)

# U2 pad 1 (7.05, 31.05) -> U2 pad 3 EN (7.05, 32.95): short vertical
lines.append(seg(7.05, 31.05, 7.05, 32.95, 0.8, 3))

# U2 pad 1 -> C9 pad 1 (6.5, 33.0): via 45
for s in route_net(7.05, 31.05, 6.5, 33.0, 0.8, 3):
    lines.append(s)

# C7 pad 1 (9.6, 31.5) -> U2 pad 1 (7.05, 31.05)
for s in route_net(9.6, 31.5, 7.05, 31.05, 0.8, 3):
    lines.append(s)

# C8 pad 1 (4.6, 31.5) -> 5V bus at J1 (3.4, 34.5)
for s in route_net(4.6, 31.5, 3.4, 34.5, 0.8, 3):
    lines.append(s)

# === NET 2 (3V3) — 0.8mm power ===
# U2 pad 4 VOUT (8.95, 31.525) -> C10 pad 1 (6.5, 31.5)
for s in route_net(8.95, 31.525, 6.5, 31.5, 0.8, 2):
    lines.append(s)

# Via from U2 VOUT to In2.Cu 3V3 plane
lines.append(via(9.5, 30.5, 2, top="F.Cu", bot="In2.Cu"))

# Short trace from U2 pad 4 to the plane via
for s in route_net(8.95, 31.525, 9.5, 30.5, 0.8, 2):
    lines.append(s)

# 3V3 distribution: plane via (9.5, 30.5) -> U1 VCC pads
# Route to U1 pad 7 (29.8, 23.8) — F.Cu trace from plane via
for s in route_net(9.5, 30.5, 29.8, 23.8, 0.8, 2):
    lines.append(s)

# U1 pad 7 -> pad 8 (30.2, 23.8): short horizontal
lines.append(seg(29.8, 23.8, 30.2, 23.8, 0.8, 2))

# U1 pad 29 (32.6, 16.2) -> nearby C5 pad 1 (29.5, 14.0) then via to In2.Cu
for s in route_net(32.6, 16.2, 29.5, 14.0, 0.8, 2):
    lines.append(s)
lines.append(via(29.5, 14.0, 2, top="F.Cu", bot="In2.Cu"))

# Via at U1 pad 7 position to In2.Cu for local bypass
lines.append(via(29.8, 24.2, 2, top="F.Cu", bot="In2.Cu"))
lines.append(seg(29.8, 23.8, 29.8, 24.2, 0.8, 2))

# R2 pad 1 (27.0, 37.0) — 3V3 supply via plane
lines.append(via(27.0, 36.0, 2, top="F.Cu", bot="In2.Cu"))
lines.append(seg(27.0, 37.0, 27.0, 36.0, 0.8, 2))

# C1-C6 decoupling cap 3V3 connections via In2.Cu vias
# C1 (25,15) pad1=(24.1,15), C2 (25,25) pad1=(24.1,25)
# C3 (35,15) pad1=(34.1,15), C4 (35,25) pad1=(34.1,25)
# C5 (30,14) pad1=(29.1,14), C6 (30,26) pad1=(29.1,26)
for (cx, cy) in [(25,15),(25,25),(35,15),(35,25),(30,14),(30,26)]:
    lines.append(via(cx-0.4, cy-0.4, 2, top="F.Cu", bot="In2.Cu"))

# === NET 1 (GND) — vias to In1.Cu plane ===
gnd_via_positions = [
    # J1 GND mounting
    (3.0, 33.8), (3.0, 38.2),
    # U2 GND pads after move (near 7.05,32 and 8.95,32.475)
    (6.8, 32.0), (8.7, 32.5),
    # U3 EP GND vias
    (13.5, 27.5), (14.5, 28.5), (13.5, 28.5), (14.5, 27.5),
    # D1 K cathode
    (19.0, 38.5),
    # D2 K cathode
    (25.0, 38.5),
    # SW1 GND
    (23.5, 3.5),
    # SW2 GND
    (32.5, 3.5),
    # C8 GND pad 2 (6.4, 31.5)
    (6.4, 30.8),
    # C7 GND pad 2 (11.4, 31.5)
    (11.4, 30.8),
    # J2 GND pads
    (42.5, 22.0), (45.5, 22.0),
    # USB-C GND mounting pads
    (1.5, 36.5), (8.5, 36.5),
]
# U1 EP via grid (9 vias under exposed pad at ~30,20)
u1_ep_vias = [
    (28.5, 18.5), (30.0, 18.5), (31.5, 18.5),
    (28.5, 20.0), (30.0, 20.0), (31.5, 20.0),
    (28.5, 21.5), (30.0, 21.5), (31.5, 21.5),
]
# Perimeter GND stitching
perimeter_gnd = [
    (25.0, 15.5), (30.0, 15.5), (35.0, 15.5),
    (25.0, 24.5), (30.0, 24.5), (35.0, 24.5),
    (25.0, 20.0), (34.5, 20.0),
]

for (vx, vy) in gnd_via_positions + u1_ep_vias + perimeter_gnd:
    lines.append(via(vx, vy, 1, top="F.Cu", bot="In1.Cu"))

# GND short traces for J2 to nearby vias
lines.append(seg(42.5, 21.0, 42.5, 22.0, 0.8, 1))
lines.append(seg(45.5, 21.0, 45.5, 22.0, 0.8, 1))

# GND trace: D1 K (19.0, 37.0) -> GND via
lines.append(seg(19.0, 37.0, 19.0, 38.5, 0.8, 1))
# GND trace: D2 K (25.0, 37.0) -> GND via
lines.append(seg(25.0, 37.0, 25.0, 38.5, 0.8, 1))

# GND trace: C9 pad 2 (7.5, 33.0) -> GND plane
lines.append(via(7.5, 33.5, 1, top="F.Cu", bot="In1.Cu"))
lines.append(seg(7.5, 33.0, 7.5, 33.5, 0.8, 1))

# GND trace: C10 pad 2 (7.5, 31.5) -> GND plane
lines.append(via(7.5, 30.8, 1, top="F.Cu", bot="In1.Cu"))
lines.append(seg(7.5, 31.5, 7.5, 30.8, 0.8, 1))

# GND trace: C11 pad 2 (18.5, 28.0) -> GND plane
lines.append(via(18.5, 29.0, 1, top="F.Cu", bot="In1.Cu"))
lines.append(seg(18.5, 28.0, 18.5, 29.0, 0.8, 1))

# SW1 GND pad 2/4 connections (23.5, 2.0) and (23.5, 5.0)
lines.append(seg(23.5, 2.0, 23.5, 3.5, 0.8, 1))
lines.append(seg(23.5, 5.0, 23.5, 3.5, 0.8, 1))
# SW2 GND pad 2/4 connections (32.5, 2.0) and (32.5, 5.0)
lines.append(seg(32.5, 2.0, 32.5, 3.5, 0.8, 1))
lines.append(seg(32.5, 5.0, 32.5, 3.5, 0.8, 1))

# C7 GND (11.4, 31.5) -> GND via
lines.append(seg(11.4, 31.5, 11.4, 30.8, 0.8, 1))

# C8 GND (6.4, 31.5) -> GND via
lines.append(seg(6.4, 31.5, 6.4, 30.8, 0.8, 1))

# === NET 5 (USB_DP) — 0.2mm differential ===
# J1 D+ pad (4.2, 34.5) -> U3 D+ (16.85, 28.5)
# Route: (4.2, 34.5) -> (10.35, 28.5) diagonal -> (16.85, 28.5) horizontal
lines.append(seg(4.2, 34.5, 10.35, 28.35, 0.2, 5))
lines.append(seg(10.35, 28.35, 16.85, 28.35, 0.2, 5))
# Also connect duplicate D+ pads on USB-C (pad 12 at 4.2, 37.5)
for s in route_net(4.2, 37.5, 4.2, 34.5, 0.2, 5):
    lines.append(s)

# === NET 6 (USB_DM) — 0.2mm differential ===
# J1 D- pad (3.8, 34.5) -> U3 D- (16.85, 28.0)
lines.append(seg(3.8, 34.5, 9.85, 28.5, 0.2, 6))
lines.append(seg(9.85, 28.5, 16.85, 28.5, 0.2, 6))
# Also connect duplicate D- pads on USB-C (pad 11 at 3.8, 37.5)
for s in route_net(3.8, 37.5, 3.8, 34.5, 0.2, 6):
    lines.append(s)

# === NET 7 (UART_TX) — 0.25mm ===
# CP2102 TX (pad 13 at 16.85, 27.0) -> U1 UART_RX (33.8, 20.2)
for s in route_net(16.85, 27.0, 33.8, 20.2, 0.25, 7):
    lines.append(s)
# J3 pad 3 (3.0, 17.27) -> CP2102 TX (16.85, 27.0)
# Route down then right
lines.append(seg(3.0, 17.27, 3.0, 27.0, 0.25, 7))
lines.append(seg(3.0, 27.0, 16.85, 27.0, 0.25, 7))

# === NET 8 (UART_RX) — 0.25mm ===
# CP2102 RX (pad 14 at 16.85, 26.5) -> U1 UART_TX (33.8, 20.6)
lines.append(seg(16.85, 26.5, 16.85, 20.6, 0.25, 8))
lines.append(seg(16.85, 20.6, 33.8, 20.6, 0.25, 8))
# J3 pad 4 (3.0, 19.81) -> CP2102 RX (16.85, 26.5)
lines.append(seg(3.0, 19.81, 3.0, 26.5, 0.25, 8))
lines.append(seg(3.0, 26.5, 16.85, 26.5, 0.25, 8))

# === NET 9 (I2C_SDA) — 0.25mm ===
# J4 pad 3 (3.0, 23.27) -> U1 pad 22 (33.8, 19.8)
# dx=30.8, dy=-3.47 -> diag=3.47, go diag first
for s in route_net(3.0, 23.27, 33.8, 19.8, 0.25, 9):
    lines.append(s)

# === NET 10 (I2C_SCL) — 0.25mm ===
# J4 pad 4 (3.0, 25.81) -> U1 pad 23 (33.8, 19.4)
for s in route_net(3.0, 25.81, 33.8, 19.4, 0.25, 10):
    lines.append(s)

# === NET 11 (SPI_MOSI) — 0.25mm ===
# J5 pad 3 (3.0, 27.73) -> U1 pad 16 (33.8, 22.2)
for s in route_net(3.0, 27.73, 33.8, 22.2, 0.25, 11):
    lines.append(s)

# === NET 12 (SPI_MISO) — 0.25mm ===
# J5 pad 4 (3.0, 30.27) -> U1 pad 17 (33.8, 21.8)
for s in route_net(3.0, 30.27, 33.8, 21.8, 0.25, 12):
    lines.append(s)

# === NET 13 (SPI_SCK) — 0.25mm ===
# J5 pad 5 (3.0, 32.81) -> U1 pad 18 (33.8, 21.4)
for s in route_net(3.0, 32.81, 33.8, 21.4, 0.25, 13):
    lines.append(s)

# === NET 14 (SPI_CS) — 0.25mm ===
# J5 pad 6 (3.0, 35.35) -> U1 pad 19 (33.8, 21.0)
for s in route_net(3.0, 35.35, 33.8, 21.0, 0.25, 14):
    lines.append(s)

# === NET 15 (GPIO48_LED) — 0.25mm ===
# U1 pad 48 (26.2, 19.4) -> R1 pad 1 (21.0, 37.0)
# dx=-5.2, dy=17.6 -> diag=5.2, go straight (vertical) first, then diagonal
for s in route_net(26.2, 19.4, 21.0, 37.0, 0.25, 15):
    lines.append(s)

# === NET 16 (EN/Reset) — 0.25mm ===
# U1 pad 51 (26.2, 20.6) -> SW1 pad 1 (18.5, 2.0)
lines.append(seg(26.2, 20.6, 26.2, 2.0, 0.25, 16))
lines.append(seg(26.2, 2.0, 18.5, 2.0, 0.25, 16))
# Connect SW1 pad 1 (18.5, 2.0) <-> SW1 pad 3 (18.5, 5.0)
lines.append(seg(18.5, 2.0, 18.5, 5.0, 0.25, 16))

# === NET 17 (GPIO0/Boot) — 0.25mm ===
# U1 pad 52 (26.2, 21.0) -> SW2 pad 1 (27.5, 2.0)
lines.append(seg(26.2, 21.0, 27.5, 21.0, 0.25, 17))
lines.append(seg(27.5, 21.0, 27.5, 2.0, 0.25, 17))
# Connect SW2 pad 1 (27.5, 2.0) <-> SW2 pad 3 (27.5, 5.0)
lines.append(seg(27.5, 2.0, 27.5, 5.0, 0.25, 17))

# === NET 18 (LED_STATUS_A) — 0.25mm ===
# R1 pad 2 (22.0, 37.0) -> D1 pad A (18.0, 37.0)
lines.append(seg(22.0, 37.0, 18.0, 37.0, 0.25, 18))

# === NET 19 (LED_POWER_A) — 0.25mm ===
# R2 pad 2 (28.0, 37.0) -> D2 pad A (24.0, 37.0)
lines.append(seg(28.0, 37.0, 24.0, 37.0, 0.25, 19))

# === C11 U3 decoupling ===
# C11 pad 1 (17.5, 28.0) -> U3 VCC pad (16.85, 27.5): short route, net 2 (3V3)
for s in route_net(17.5, 28.0, 16.85, 27.5, 0.25, 2):
    lines.append(s)
# C11 also needs 3V3 from plane
lines.append(via(17.5, 27.5, 2, top="F.Cu", bot="In2.Cu"))
lines.append(seg(17.5, 28.0, 17.5, 27.5, 0.25, 2))

# U3 VCC from In2.Cu plane via
lines.append(via(16.5, 27.0, 2, top="F.Cu", bot="In2.Cu"))
lines.append(seg(16.85, 27.5, 16.5, 27.0, 0.25, 2))

# J3 pad 1 (3.0, 12.19) — 3V3 VCC header supply
lines.append(via(3.5, 12.19, 2, top="F.Cu", bot="In2.Cu"))
lines.append(seg(3.0, 12.19, 3.5, 12.19, 0.25, 2))

# J4 pad 1 (3.0, 18.19) — 3V3 VCC header supply
lines.append(via(3.5, 18.19, 2, top="F.Cu", bot="In2.Cu"))
lines.append(seg(3.0, 18.19, 3.5, 18.19, 0.25, 2))

# J5 pad 1 (3.0, 22.65) — 3V3 VCC header supply
lines.append(via(3.5, 22.65, 2, top="F.Cu", bot="In2.Cu"))
lines.append(seg(3.0, 22.65, 3.5, 22.65, 0.25, 2))

# J3 pad 2 (3.0, 14.73) — GND
lines.append(via(3.5, 14.73, 1, top="F.Cu", bot="In1.Cu"))
lines.append(seg(3.0, 14.73, 3.5, 14.73, 0.25, 1))

# J4 pad 2 (3.0, 20.73) — GND
lines.append(via(3.5, 20.73, 1, top="F.Cu", bot="In1.Cu"))
lines.append(seg(3.0, 20.73, 3.5, 20.73, 0.25, 1))

# J5 pad 2 (3.0, 25.19) — GND
lines.append(via(3.5, 25.19, 1, top="F.Cu", bot="In1.Cu"))
lines.append(seg(3.0, 25.19, 3.5, 25.19, 0.25, 1))

# ---------------------------------------------------------------------------
# Step 6: Insert new routing before the zones section
# ---------------------------------------------------------------------------

routing_block = '\n'.join(lines) + '\n'

# Find the start of the zones section
zone_start = content.find('\n  (zone ')
if zone_start == -1:
    # Fallback: find closing paren of last footprint
    zone_start = content.rfind('\n  (footprint')
    # find end of that footprint
    # Actually find the last ')' before ')'
    raise RuntimeError("Could not locate zones section in PCB file")

# Insert routing block before zone section
content = content[:zone_start] + '\n' + routing_block + content[zone_start:]

# ---------------------------------------------------------------------------
# Step 7: Write back
# ---------------------------------------------------------------------------

with open(PCB_FILE, 'w') as f:
    f.write(content)

print("PCB file written.")

# ---------------------------------------------------------------------------
# Step 8: Validation report
# ---------------------------------------------------------------------------

with open(PCB_FILE, 'r') as f:
    final = f.read()

# Parenthesis balance
opens = final.count('(')
closes = final.count(')')
print(f"Parenthesis balance: opens={opens}, closes={closes}, diff={opens-closes}")

# Count segments and vias
seg_count = len(re.findall(r'\n  \(segment ', final))
via_count = len(re.findall(r'\n  \(via ', final))
print(f"Segments added: {seg_count}")
print(f"Vias added: {via_count}")

# Check for stale routing artifacts
if 'keepout_settings' in final:
    print("WARNING: 'keepout_settings' found in file")
else:
    print("OK: No 'keepout_settings' found")

if 'fill yes' in final:
    print("WARNING: 'fill yes' found in file")
else:
    print("OK: No 'fill yes' found")

# Check U2 position was updated
if '(at 8 32)' in final:
    print("OK: U2 moved to (8, 32)")
else:
    print("WARNING: U2 position not found at (8, 32)")

if '(at 10.5 31.5)' in final:
    print("OK: C7 moved to (10.5, 31.5)")
else:
    print("WARNING: C7 position not found at (10.5, 31.5)")

if '(at 5.5 31.5)' in final:
    print("OK: C8 moved to (5.5, 31.5)")
else:
    print("WARNING: C8 position not found at (5.5, 31.5)")

# Check old positions are gone (from moved components)
if '(at 8 8)' in final:
    print("WARNING: old U2 position (at 8 8) still present")
else:
    print("OK: Old U2 position removed")

if '(at 10.5 9.5)' in final:
    print("WARNING: old C7 position (at 10.5 9.5) still present")
else:
    print("OK: Old C7 position removed")

if '(at 5.5 9.5)' in final:
    print("WARNING: old C8 position (at 5.5 9.5) still present")
else:
    print("OK: Old C8 position removed")

print("Done.")
