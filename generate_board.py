#!/usr/bin/env python3
"""
ESP32-S3 RF Dev Board - KiCAD 8 Project Generator
Generates complete KiCAD 8 project files in S-expression format.

Board: 50x40mm, 4-layer JLC04161H-7628 stackup
Main IC: ESP32-S3 QFN56 with chip antenna and u.FL connector
USB-UART: CP2102 QFN-28
Power: AP2112K-3.3V SOT-23-5 LDO
ESD: USBLC6-2SC6 on USB D+/D-
v1.1: CC pull-downs, ESD protection, test points
"""

import argparse
import logging
import os
import math
import json
from datetime import datetime

log = logging.getLogger(__name__)

# Board dimensions (mm)
BOARD_W = 50.0
BOARD_H = 40.0

# Component positions (x, y) in mm from top-left origin
POS_ESP32   = (30.0, 20.0)   # ESP32-S3 QFN56 center
POS_ANT     = (44.0, 14.0)   # Johanson chip antenna
POS_UFL     = (44.0, 21.0)   # u.FL connector
POS_LDO     = (8.0,  8.0)    # AP2112K LDO
POS_USBC    = (5.0,  36.0)   # USB-C connector
POS_CP2102  = (14.0, 28.0)   # CP2102 USB-UART bridge
POS_UART    = (3.0,  16.0)   # 4-pin UART header
POS_I2C     = (3.0,  22.0)   # 4-pin I2C header
POS_SPI     = (3.0,  29.0)   # 6-pin SPI header
POS_RST_BTN = (21.0, 3.5)    # Reset button
POS_BOOT_BTN= (30.0, 3.5)    # Boot button (GPIO0)
POS_LED_STA = (20.0, 37.0)   # Status LED
POS_LED_PWR = (26.0, 37.0)   # Power LED
POS_ESD     = (14.0, 37.0)   # USBLC6-2SC6 ESD protection (near USB-C)
POS_TP1     = (11.0, 6.0)    # Test point: 3V3
POS_TP2     = (14.0, 6.0)    # Test point: GND
POS_TP3     = (40.0, 6.0)    # Test point: RF_ANT
POS_XTAL    = (28.4, 11.5)   # 40 MHz crystal Y1, above ESP32-S3 XTAL pins
POS_XTAL_C1 = (24.8, 11.5)   # 12 pF load cap on XTAL_P leg (clear of Y1 courtyard)
POS_XTAL_C2 = (32.0, 11.5)   # 12 pF load cap on XTAL_N leg
POS_R_EN    = (23.5, 9.0)    # 10k EN pull-up to 3V3
POS_R_USBDP = (10.5, 32.0)   # 22R series D+ near CP2102
POS_R_USBDM = (13.0, 32.0)   # 22R series D- near CP2102 (separated from R6)

# RF trace geometry
RF_PIN_X = POS_ESP32[0] + 7.65  # ESP32-S3 pad 36 approximate X offset
RF_PIN_Y = POS_ESP32[1]          # ESP32-S3 pad 36 approximate Y
RF_ANT_X = POS_ANT[0]
RF_ANT_Y = POS_ANT[1]
RF_TRACE_W = 0.6   # 50-ohm microstrip width for 0.2mm prepreg, Er=4.4
RF_KEEPOUT_R = 5.0 # 5mm radius keepout around antenna

# Net dictionary: id -> name
NETS = {
    0:  "",
    1:  "GND",
    2:  "3V3",
    3:  "5V",
    4:  "RF_ANT",
    5:  "USB_DP",
    6:  "USB_DM",
    7:  "UART_TX",
    8:  "UART_RX",
    9:  "I2C_SDA",
    10: "I2C_SCL",
    11: "SPI_MOSI",
    12: "SPI_MISO",
    13: "SPI_SCK",
    14: "SPI_CS",
    15: "GPIO48_LED",
    16: "EN",
    17: "GPIO0",
    18: "LED_STATUS_A",
    19: "LED_POWER_A",
    20: "USB_CC1",
    21: "USB_CC2",
    22: "XTAL_P",
    23: "XTAL_N",
    24: "USB_DP_CP",
    25: "USB_DM_CP",
}

# Net name -> id lookup
NET_ID = {v: k for k, v in NETS.items()}

# Unique ID counter (KiCAD 8 uses uuid-style IDs for footprints/pads/zones)
_uid_counter = 1000

def uid():
    """Return a simple incrementing integer ID formatted for KiCAD."""
    global _uid_counter
    _uid_counter += 1
    return str(_uid_counter)

def net_ref(name):
    """Return S-expression net reference tuple (id, name) for a net name."""
    if name in NET_ID:
        return (NET_ID[name], name)
    return (0, "")

def fmt(v):
    """Format a float to 4 decimal places, stripping trailing zeros."""
    return f"{v:.4f}".rstrip('0').rstrip('.')

def pad_net(name):
    """Return the (net id net_name) S-expr string for a pad, or empty."""
    if name and name in NET_ID and NET_ID[name] != 0:
        nid = NET_ID[name]
        return f'(net {nid} "{name}")'
    return ""


# =============================================================================
# PCB FILE GENERATORS
# =============================================================================

def gen_header():
    """KiCAD 8 PCB file header."""
    return '(kicad_pcb (version 20240108) (generator "pcbnew") (generator_version "8.0")\n'


def gen_general():
    """General board settings block."""
    return f'''  (general
    (thickness 1.6)
    (legacy_teardrops no)
  )
  (paper "A4")
'''


def gen_layers():
    """Layer definitions for 4-layer board."""
    return '''  (layers
    (0 "F.Cu" signal)
    (1 "In1.Cu" power)
    (2 "In2.Cu" power)
    (31 "B.Cu" signal)
    (32 "B.Adhes" user "B.Adhesive")
    (33 "F.Adhes" user "F.Adhesive")
    (34 "B.Paste" user)
    (35 "F.Paste" user)
    (36 "B.SilkS" user "B.Silkscreen")
    (37 "F.SilkS" user "F.Silkscreen")
    (38 "B.Mask" user)
    (39 "F.Mask" user)
    (40 "Dwgs.User" user "User.Drawings")
    (41 "Cmts.User" user "User.Comments")
    (42 "Eco1.User" user "User.Eco1")
    (43 "Eco2.User" user "User.Eco2")
    (44 "Edge.Cuts" user)
    (45 "Margin" user)
    (46 "B.CrtYd" user "B.Courtyard")
    (47 "F.CrtYd" user "F.Courtyard")
    (48 "B.Fab" user)
    (49 "F.Fab" user)
    (50 "User.1" user)
    (51 "User.2" user)
  )
'''


def gen_setup():
    """
    Setup block: stackup, design rules, pad/via/track settings.
    JLC04161H-7628 stackup:
      L1 F.Cu  - 0.035mm copper (signals/RF)
      prepreg  - 0.2mm (7628 x1)  Er=4.4  -> determines 50-ohm trace width
      L2 In1.Cu - 0.035mm copper (solid GND plane)
      core     - 1.065mm (FR4)
      L3 In2.Cu - 0.035mm copper (power)
      prepreg  - 0.2mm (7628 x1)
      L4 B.Cu  - 0.035mm copper (signals)
    Total: ~1.6mm
    """
    return '''  (setup
    (stackup
      (layer "F.SilkS" (type "Top Silk Screen"))
      (layer "F.Paste" (type "Top Solder Paste"))
      (layer "F.Mask" (type "Top Solder Mask") (thickness 0.01))
      (layer "F.Cu" (type "copper") (thickness 0.035))
      (layer "dielectric 1" (type "prepreg") (thickness 0.2) (material "7628") (epsilon_r 4.4) (loss_tangent 0.02))
      (layer "In1.Cu" (type "copper") (thickness 0.035))
      (layer "dielectric 2" (type "core") (thickness 1.065) (material "FR4") (epsilon_r 4.5) (loss_tangent 0.02))
      (layer "In2.Cu" (type "copper") (thickness 0.035))
      (layer "dielectric 3" (type "prepreg") (thickness 0.2) (material "7628") (epsilon_r 4.4) (loss_tangent 0.02))
      (layer "B.Cu" (type "copper") (thickness 0.035))
      (layer "B.Mask" (type "Bottom Solder Mask") (thickness 0.01))
      (layer "B.Paste" (type "Bottom Solder Paste"))
      (layer "B.SilkS" (type "Bottom Silk Screen"))
      (copper_finish "HASL(with lead)")
      (dielectric_constraints no)
    )
    (pad_to_mask_clearance 0.05)
    (solder_mask_min_width 0.05)
    (allow_soldermask_bridges_in_footprints no)
    (pcbplotparams
      (layerselection 0x00010fc_ffffffff)
      (plot_on_all_layers_selection 0x0000000_00000000)
      (disableapertmacros no)
      (usegerberextensions no)
      (usegerberattributes yes)
      (usegerberadvancedattributes yes)
      (creategerberjobfile yes)
      (dashed_line_dash_ratio 12.000000)
      (dashed_line_gap_ratio 3.000000)
      (svgprecision 4)
      (plotframeref no)
      (viasonmask no)
      (mode 1)
      (useauxorigin no)
      (hpglpennumber 1)
      (hpglpenspeed 20)
      (hpglpendiameter 15.000000)
      (dxfpolygonmode yes)
      (dxfimperialunits yes)
      (dxfusepcbnewfont yes)
      (psnegative no)
      (psa4output no)
      (plotreference yes)
      (plotvalue yes)
      (plotfptext yes)
      (plotinvisibletext no)
      (sketchpadsonfab no)
      (subtractmaskfromsilk no)
      (outputformat 1)
      (mirror no)
      (drillshape 0)
      (scaleselection 1)
      (outputdirectory "")
    )
  )
'''


def gen_nets():
    """Net declarations."""
    lines = []
    for nid, nname in sorted(NETS.items()):
        if nid == 0:
            lines.append(f'  (net {nid} "")')
        else:
            lines.append(f'  (net {nid} "{nname}")')
    return "\n".join(lines) + "\n"


# =============================================================================
# BOARD OUTLINE
# =============================================================================

def gen_board_outline():
    """Board outline as 4 gr_line segments on Edge.Cuts layer."""
    w = BOARD_W
    h = BOARD_H
    lines = []
    # Top, Bottom, Left, Right edges
    edges = [
        (0, 0, w, 0),
        (w, 0, w, h),
        (w, h, 0, h),
        (0, h, 0, 0),
    ]
    for x1, y1, x2, y2 in edges:
        lines.append(
            f'  (gr_line (start {fmt(x1)} {fmt(y1)}) (end {fmt(x2)} {fmt(y2)}) '
            f'(stroke (width 0.05) (type solid)) (layer "Edge.Cuts"))'
        )
    return "\n".join(lines) + "\n"


def gen_silkscreen_labels():
    """Board title and author on silkscreen."""
    lines = [
        '  (gr_text "ESP32-S3 RF Dev Board v1.2" (at 25 1.5) (layer "F.SilkS")',
        '    (effects (font (size 1 1) (thickness 0.15))))',
        '  (gr_text "Hugh" (at 25 38.5) (layer "F.SilkS")',
        '    (effects (font (size 0.8 0.8) (thickness 0.12))))',
        '  (gr_text "RF_KEEPOUT" (at 44 20) (layer "Cmts.User")',
        '    (effects (font (size 0.8 0.8) (thickness 0.12))))',
    ]
    return "\n".join(lines) + "\n"


# =============================================================================
# FOOTPRINT HELPERS
# =============================================================================

def fp_text(kind, text, x, y, layer, size=1.0, thickness=0.15, hide=False):
    """Generate a footprint text element (reference or value)."""
    hide_str = " hide" if hide else ""
    return (
        f'    (fp_text {kind} "{text}" (at {fmt(x)} {fmt(y)}) (layer "{layer}"){hide_str}\n'
        f'      (effects (font (size {fmt(size)} {fmt(size)}) (thickness {fmt(thickness)}))))'
    )


def fp_courtyard_rect(x1, y1, x2, y2, layer="F.CrtYd"):
    """Generate a courtyard rectangle."""
    return (
        f'    (fp_line (start {fmt(x1)} {fmt(y1)}) (end {fmt(x2)} {fmt(y1)}) (layer "{layer}") (stroke (width 0.05) (type solid)))\n'
        f'    (fp_line (start {fmt(x2)} {fmt(y1)}) (end {fmt(x2)} {fmt(y2)}) (layer "{layer}") (stroke (width 0.05) (type solid)))\n'
        f'    (fp_line (start {fmt(x2)} {fmt(y2)}) (end {fmt(x1)} {fmt(y2)}) (layer "{layer}") (stroke (width 0.05) (type solid)))\n'
        f'    (fp_line (start {fmt(x1)} {fmt(y2)}) (end {fmt(x1)} {fmt(y1)}) (layer "{layer}") (stroke (width 0.05) (type solid)))'
    )


def fp_fab_rect(x1, y1, x2, y2, layer="F.Fab"):
    """Generate a fab layer rectangle (component outline)."""
    return (
        f'    (fp_line (start {fmt(x1)} {fmt(y1)}) (end {fmt(x2)} {fmt(y1)}) (layer "{layer}") (stroke (width 0.1) (type solid)))\n'
        f'    (fp_line (start {fmt(x2)} {fmt(y1)}) (end {fmt(x2)} {fmt(y2)}) (layer "{layer}") (stroke (width 0.1) (type solid)))\n'
        f'    (fp_line (start {fmt(x2)} {fmt(y2)}) (end {fmt(x1)} {fmt(y2)}) (layer "{layer}") (stroke (width 0.1) (type solid)))\n'
        f'    (fp_line (start {fmt(x1)} {fmt(y2)}) (end {fmt(x1)} {fmt(y1)}) (layer "{layer}") (stroke (width 0.1) (type solid)))'
    )


def smd_pad(number, x, y, w, h, net_name="", shape="rect", layer="F.Cu"):
    """Generate a single SMD pad."""
    pn = pad_net(net_name)
    layers = f'(layers "{layer}" "F.Paste" "F.Mask")' if layer == "F.Cu" else f'(layers "{layer}" "B.Paste" "B.Mask")'
    return (
        f'    (pad "{number}" smd {shape} (at {fmt(x)} {fmt(y)}) (size {fmt(w)} {fmt(h)}) '
        f'{layers}{" " + pn if pn else ""})'
    )


def thru_pad(number, x, y, size, drill, net_name="", shape="circle"):
    """Generate a through-hole pad."""
    pn = pad_net(net_name)
    return (
        f'    (pad "{number}" thru_hole {shape} (at {fmt(x)} {fmt(y)}) (size {fmt(size)} {fmt(size)}) '
        f'(drill {fmt(drill)}) (layers "*.Cu" "*.Mask"){" " + pn if pn else ""})'
    )


def begin_footprint(ref, value, layer, x, y, rotation=0):
    """Open a footprint block."""
    rot_str = f" (rotation {fmt(rotation)})" if rotation != 0 else ""
    return (
        f'  (footprint "{ref}_fp" (layer "{layer}")\n'
        f'    (at {fmt(x)} {fmt(y)}){rot_str}\n'
        f'    (attr smd)\n'
    )


def begin_fp_thru(ref, value, layer, x, y, rotation=0):
    """Open a footprint block for through-hole parts."""
    rot_str = f" (rotation {fmt(rotation)})" if rotation != 0 else ""
    return (
        f'  (footprint "{ref}_fp" (layer "{layer}")\n'
        f'    (at {fmt(x)} {fmt(y)}){rot_str}\n'
    )


def end_footprint():
    return "  )\n"


# =============================================================================
# COMPONENT FOOTPRINT GENERATORS
# =============================================================================

def gen_esp32s3():
    """
    ESP32-S3 QFN56 footprint.
    Package: 7x7mm body, 0.4mm pitch, 14 pads per side, 0.25x0.6mm pads.
    Exposed pad (EP) 57: 5.7x5.7mm, GND.

    QFN56 pad numbering (IPC standard, CCW from bottom-left):
      Bottom side: pads 1-14  (left to right)
      Right side:  pads 15-28 (bottom to top)
      Top side:    pads 29-42 (right to left)
      Left side:   pads 43-56 (top to bottom)
    """
    x, y = POS_ESP32
    body = 7.0      # mm, body size
    pitch = 0.4     # mm
    pw, ph = 0.25, 0.6   # pad width, length
    ep_size = 5.7   # exposed pad size
    half = body / 2.0

    # Net assignments for specific pads (pad_number -> net_name)
    # Based on ESP32-S3 QFN56 datasheet pinout
    pad_nets = {
        # Bottom side (pads 1-14, left to right)
        1: "GND", 4: "GND", 5: "GND", 6: "GND",
        7: "3V3", 8: "3V3",
        # Right side (pads 15-28, bottom to top)
        15: "GND",
        20: "UART_TX", 21: "UART_RX",
        22: "I2C_SDA", 23: "I2C_SCL",
        # Top side (pads 29-42, right to left)
        29: "3V3",
        36: "RF_ANT",
        39: "XTAL_P",
        40: "XTAL_N",
        # Left side (pads 43-56, top to bottom)
        43: "GND",
        48: "GPIO48_LED",
        51: "EN", 52: "GPIO0",
        53: "GND", 54: "GND", 55: "GND", 56: "GND",
        # Exposed pad
        57: "GND",
        # SPI pads (approximate placement on right side)
        16: "SPI_MOSI", 17: "SPI_MISO", 18: "SPI_SCK", 19: "SPI_CS",
        # I2C/UART continuation
        24: "I2C_SDA", 25: "I2C_SCL",
    }

    lines = [begin_footprint("U1", "ESP32-S3", "F.Cu", x, y)]
    lines.append(fp_text("reference", "U1", 0, -5, "F.SilkS"))
    lines.append(fp_text("value", "ESP32-S3-WROOM", 0, 5, "F.Fab"))
    lines.append(fp_courtyard_rect(-4.5, -4.5, 4.5, 4.5))
    lines.append(fp_fab_rect(-3.5, -3.5, 3.5, 3.5))

    # Pin 1 marker on fab layer (small circle at pad 1 corner)
    lines.append(
        '    (fp_circle (center -3.5 3.5) (end -3.2 3.5) (layer "F.Fab") (stroke (width 0.1) (type solid)))'
    )

    # Generate perimeter pads
    # Bottom side: pads 1-14, y = +half+ph/2, x from -(13/2*pitch) to +(13/2*pitch)
    # Center offset: (-(14-1)/2 * pitch) for pad 1 to ((14-1)/2 * pitch) for pad 14
    n_side = 14
    start_offset = -((n_side - 1) / 2.0) * pitch

    # Bottom pads (1-14): y = +(half), pads along X axis
    for i in range(n_side):
        pad_num = i + 1
        px = start_offset + i * pitch
        py = half + ph / 2.0
        net = pad_nets.get(pad_num, "")
        lines.append(smd_pad(pad_num, px, py, pw, ph, net))

    # Right pads (15-28): x = +(half), pads along Y axis (bottom to top = increasing pad num)
    for i in range(n_side):
        pad_num = n_side + i + 1  # 15-28
        py = half - i * pitch - start_offset * 0  # from +half/2 downward... actually:
        # Pads go bottom to top: pad 15 at y=+half-(0)*pitch... 
        # Actually right side: pad 15 at bottom, pad 28 at top
        # So y goes from +half_minus to -half_minus
        py = (half - ph/2.0) - i * pitch + ((n_side-1)/2.0 - (n_side-1)/2.0)*pitch
        # Simplified: center first pad at y=+(n_side-1)/2*pitch, last at y=-(n_side-1)/2*pitch
        py = ((n_side - 1) / 2.0 - i) * pitch
        px = half + ph / 2.0
        net = pad_nets.get(pad_num, "")
        lines.append(smd_pad(pad_num, px, py, ph, pw, net))

    # Top pads (29-42): y = -(half), pads along X axis (right to left = increasing pad num)
    for i in range(n_side):
        pad_num = 2 * n_side + i + 1  # 29-42
        px = ((n_side - 1) / 2.0 - i) * pitch  # right to left
        py = -(half + ph / 2.0)
        net = pad_nets.get(pad_num, "")
        lines.append(smd_pad(pad_num, px, py, pw, ph, net))

    # Left pads (43-56): x = -(half), pads along Y axis (top to bottom = increasing pad num)
    for i in range(n_side):
        pad_num = 3 * n_side + i + 1  # 43-56
        py = -((n_side - 1) / 2.0 - i) * pitch  # top to bottom
        px = -(half + ph / 2.0)
        net = pad_nets.get(pad_num, "")
        lines.append(smd_pad(pad_num, px, py, ph, pw, net))

    # Exposed pad (EP) - pad 57
    lines.append(smd_pad(57, 0, 0, ep_size, ep_size, "GND", shape="rect"))

    lines.append(end_footprint())
    return "\n".join(lines)


def gen_johanson_antenna():
    """
    Johanson 2450AT18A100 chip antenna.
    Package: 0402-like ceramic, 1.0x0.5mm body.
    2 pads: pad 1 = RF_ANT, pad 2 = GND (shorted to GND plane).
    Keepout annotation is separate (see zone).
    """
    x, y = POS_ANT
    lines = [begin_footprint("ANT1", "2450AT18A100", "F.Cu", x, y)]
    lines.append(fp_text("reference", "ANT1", 0, -1.2, "F.SilkS"))
    lines.append(fp_text("value", "2450AT18A100", 0, 1.2, "F.Fab"))
    lines.append(fp_courtyard_rect(-0.8, -0.5, 0.8, 0.5))
    lines.append(fp_fab_rect(-0.5, -0.3, 0.5, 0.3))
    lines.append(smd_pad(1, -0.5, 0, 0.5, 0.5, "RF_ANT"))
    lines.append(smd_pad(2,  0.5, 0, 0.5, 0.5, "GND"))
    lines.append(end_footprint())
    return "\n".join(lines)


def gen_ufl_connector():
    """
    u.FL (IPEX) SMD connector.
    Footprint: central signal pad + 2 GND pads.
    """
    x, y = POS_UFL
    lines = [begin_footprint("J2", "UFL_SMD", "F.Cu", x, y)]
    lines.append(fp_text("reference", "J2", 0, -2.5, "F.SilkS"))
    lines.append(fp_text("value", "u.FL", 0, 2.5, "F.Fab"))
    lines.append(fp_courtyard_rect(-2.5, -2.5, 2.5, 2.5))
    lines.append(fp_fab_rect(-2.0, -2.0, 2.0, 2.0))
    # Central signal pad
    lines.append(smd_pad(1, 0, 0, 0.8, 0.8, "RF_ANT"))
    # GND tabs
    lines.append(smd_pad(2, -1.5, 0, 0.7, 1.5, "GND"))
    lines.append(smd_pad(3,  1.5, 0, 0.7, 1.5, "GND"))
    lines.append(end_footprint())
    return "\n".join(lines)


def gen_ap2112k():
    """
    AP2112K-3.3V LDO in SOT-23-5 package.
    Pinout: 1=EN, 2=GND, 3=VIN, 4=NC, 5=VOUT
    Pad pitch 0.95mm, two rows.
    """
    x, y = POS_LDO
    lines = [begin_footprint("U2", "AP2112K-3.3", "F.Cu", x, y)]
    lines.append(fp_text("reference", "U2", 0, -2.2, "F.SilkS"))
    lines.append(fp_text("value", "AP2112K-3.3V", 0, 2.2, "F.Fab"))
    lines.append(fp_courtyard_rect(-1.8, -1.6, 1.8, 1.6))
    lines.append(fp_fab_rect(-1.5, -1.4, 1.5, 1.4))

    # SOT-23-5: 3 pads on left (1,2,3) and 2 on right (4,5) - standard layout
    # Left column (x=-0.95): pads 1,2,3 from top to bottom
    pad_defs = [
        (1, -0.95, -0.95, "EN"),     # pin 1: ENABLE
        (2, -0.95,  0.0,  "GND"),    # pin 2: GND
        (3, -0.95,  0.95, "5V"),     # pin 3: VIN (input from 5V)
        (4,  0.95, -0.475,""),        # pin 4: NC or bypass
        (5,  0.95,  0.475,"3V3"),    # pin 5: VOUT (3.3V output)
    ]
    for pnum, px, py, net in pad_defs:
        lines.append(smd_pad(pnum, px, py, 0.6, 0.9, net))

    lines.append(end_footprint())
    return "\n".join(lines)


def gen_usbc():
    """
    USB-C 16-pin SMD connector (generic mid-mount or top-mount).
    Key nets: VBUS=5V, D+=USB_DP, D-=USB_DM, GND=GND.
    Simplified with main functional pads.
    """
    x, y = POS_USBC
    lines = [begin_footprint("J1", "USB_C_16P", "F.Cu", x, y)]
    lines.append(fp_text("reference", "J1", 0, -5.0, "F.SilkS"))
    lines.append(fp_text("value", "USB-C 16P", 0, 5.0, "F.Fab"))
    lines.append(fp_courtyard_rect(-5.0, -4.5, 5.0, 4.5))
    lines.append(fp_fab_rect(-4.5, -4.0, 4.5, 4.0))

    # USB-C 16-pin: 8 signal pads each side, symmetrical
    # Left side signal pads (approximate positions)
    usbc_pads = [
        # (pad_num, x_rel, y_rel, net)
        (1,  -2.0, -1.5, "GND"),    # GND
        (2,  -1.6, -1.5, "5V"),     # VBUS
        (3,  -1.2, -1.5, "USB_DM"), # D-
        (4,  -0.8, -1.5, "USB_DP"), # D+
        (5,  -0.4, -1.5, "USB_CC1"),  # CC1
        (6,   0.0, -1.5, ""),        # SBU1
        (7,   0.4, -1.5, "5V"),     # VBUS
        (8,   0.8, -1.5, "GND"),    # GND
        # Right side (mirrored)
        (9,  -2.0,  1.5, "GND"),
        (10, -1.6,  1.5, "5V"),
        (11, -1.2,  1.5, "USB_DM"),
        (12, -0.8,  1.5, "USB_DP"),
        (13, -0.4,  1.5, "USB_CC2"),  # CC2
        (14,  0.0,  1.5, ""),
        (15,  0.4,  1.5, "5V"),
        (16,  0.8,  1.5, "GND"),
        # Mounting/shield tabs
        (17, -3.5,  0.0, "GND"),
        (18,  3.5,  0.0, "GND"),
    ]
    for pnum, px, py, net in usbc_pads:
        lines.append(smd_pad(pnum, px, py, 0.3, 0.8, net))

    lines.append(end_footprint())
    return "\n".join(lines)


def gen_cp2102():
    """
    CP2102-GMR USB-UART bridge in QFN-28 (5x5mm, 0.5mm pitch, 7 pads/side).
    Key nets: TXD=UART_TX, RXD=UART_RX, VDD=3V3, GND=GND,
              D+=USB_DP, D-=USB_DM.
    Exposed pad: GND.
    """
    x, y = POS_CP2102
    body = 5.0
    pitch = 0.5
    pw, ph = 0.25, 0.7
    half = body / 2.0
    n_side = 7

    cp_nets = {
        # Bottom side pads 1-7
        1: "GND", 2: "USB_DM_CP", 3: "USB_DP_CP", 4: "3V3",
        # Right side pads 8-14
        8: "GND", 9: "UART_TX", 10: "UART_RX",
        # Top side pads 15-21
        15: "3V3", 16: "GND",
        # Left side pads 22-28
        22: "GND",
        # EP
        29: "GND",
    }

    lines = [begin_footprint("U3", "CP2102", "F.Cu", x, y)]
    lines.append(fp_text("reference", "U3", 0, -3.5, "F.SilkS"))
    lines.append(fp_text("value", "CP2102-GMR", 0, 3.5, "F.Fab"))
    lines.append(fp_courtyard_rect(-3.5, -3.5, 3.5, 3.5))
    lines.append(fp_fab_rect(-2.5, -2.5, 2.5, 2.5))

    start_offset = -((n_side - 1) / 2.0) * pitch

    # Bottom pads (1-7)
    for i in range(n_side):
        pad_num = i + 1
        px = start_offset + i * pitch
        py = half + ph / 2.0
        net = cp_nets.get(pad_num, "")
        lines.append(smd_pad(pad_num, px, py, pw, ph, net))

    # Right pads (8-14)
    for i in range(n_side):
        pad_num = n_side + i + 1
        py = ((n_side - 1) / 2.0 - i) * pitch
        px = half + ph / 2.0
        net = cp_nets.get(pad_num, "")
        lines.append(smd_pad(pad_num, px, py, ph, pw, net))

    # Top pads (15-21)
    for i in range(n_side):
        pad_num = 2 * n_side + i + 1
        px = ((n_side - 1) / 2.0 - i) * pitch
        py = -(half + ph / 2.0)
        net = cp_nets.get(pad_num, "")
        lines.append(smd_pad(pad_num, px, py, pw, ph, net))

    # Left pads (22-28)
    for i in range(n_side):
        pad_num = 3 * n_side + i + 1
        py = -((n_side - 1) / 2.0 - i) * pitch
        px = -(half + ph / 2.0)
        net = cp_nets.get(pad_num, "")
        lines.append(smd_pad(pad_num, px, py, ph, pw, net))

    # Exposed pad
    lines.append(smd_pad(29, 0, 0, 3.7, 3.7, "GND"))
    lines.append(end_footprint())
    return "\n".join(lines)


def gen_header_4pin(ref, x, y, nets_list, label):
    """4-pin 2.54mm through-hole header (1x4)."""
    lines = [begin_fp_thru(ref, label, "F.Cu", x, y)]
    lines.append(fp_text("reference", ref, 0, -3.5, "F.SilkS"))
    lines.append(fp_text("value", label, 0, 3.5, "F.Fab"))
    lines.append(fp_courtyard_rect(-1.5, -6.5, 1.5, 6.5))
    lines.append(fp_fab_rect(-1.27, -6.35, 1.27, 6.35))
    for i, net in enumerate(nets_list):
        py = -((len(nets_list) - 1) / 2.0) * 2.54 + i * 2.54
        lines.append(thru_pad(i + 1, 0, py, 1.7, 1.0, net))
    lines.append(end_footprint())
    return "\n".join(lines)


def gen_header_6pin(ref, x, y, nets_list, label):
    """6-pin 2.54mm through-hole header (1x6)."""
    lines = [begin_fp_thru(ref, label, "F.Cu", x, y)]
    lines.append(fp_text("reference", ref, 0, -4.5, "F.SilkS"))
    lines.append(fp_text("value", label, 0, 4.5, "F.Fab"))
    lines.append(fp_courtyard_rect(-1.5, -8.0, 1.5, 8.0))
    lines.append(fp_fab_rect(-1.27, -7.62, 1.27, 7.62))
    for i, net in enumerate(nets_list):
        py = -((len(nets_list) - 1) / 2.0) * 2.54 + i * 2.54
        lines.append(thru_pad(i + 1, 0, py, 1.7, 1.0, net))
    lines.append(end_footprint())
    return "\n".join(lines)


def gen_tactile_button(ref, x, y, label):
    """6x6mm SMD tactile button. 4 pads (2 pairs)."""
    lines = [begin_footprint(ref, label, "F.Cu", x, y)]
    lines.append(fp_text("reference", ref, 0, -4.5, "F.SilkS"))
    lines.append(fp_text("value", label, 0, 4.5, "F.Fab"))
    lines.append(fp_courtyard_rect(-3.5, -3.5, 3.5, 3.5))
    lines.append(fp_fab_rect(-3.0, -3.0, 3.0, 3.0))
    # 4 pads: 2 on each side
    net = "GND" if "RST" in label or "BOOT" in label else ""
    net1 = "EN" if "RST" in label else "GPIO0"
    lines.append(smd_pad(1, -2.5, -1.5, 1.5, 1.0, "GND"))
    lines.append(smd_pad(2,  2.5, -1.5, 1.5, 1.0, "GND"))
    lines.append(smd_pad(3, -2.5,  1.5, 1.5, 1.0, net1))
    lines.append(smd_pad(4,  2.5,  1.5, 1.5, 1.0, net1))
    lines.append(end_footprint())
    return "\n".join(lines)


def gen_led_0402(ref, x, y, net_a, label):
    """0402 LED footprint. Anode=net_a, Cathode=GND."""
    lines = [begin_footprint(ref, label, "F.Cu", x, y)]
    lines.append(fp_text("reference", ref, 0, -1.5, "F.SilkS"))
    lines.append(fp_text("value", label, 0, 1.5, "F.Fab"))
    lines.append(fp_courtyard_rect(-1.1, -0.6, 1.1, 0.6))
    lines.append(fp_fab_rect(-0.6, -0.3, 0.6, 0.3))
    lines.append(smd_pad("A", -0.5, 0, 0.5, 0.5, net_a))
    lines.append(smd_pad("K",  0.5, 0, 0.5, 0.5, "GND"))
    lines.append(end_footprint())
    return "\n".join(lines)


def gen_resistor_0402(ref, x, y, net1, net2, value_str, label):
    """0402 resistor footprint."""
    lines = [begin_footprint(ref, value_str, "F.Cu", x, y)]
    lines.append(fp_text("reference", ref, 0, -1.5, "F.SilkS"))
    lines.append(fp_text("value", value_str, 0, 1.5, "F.Fab"))
    lines.append(fp_courtyard_rect(-1.1, -0.6, 1.1, 0.6))
    lines.append(fp_fab_rect(-0.6, -0.3, 0.6, 0.3))
    lines.append(smd_pad(1, -0.5, 0, 0.5, 0.5, net1))
    lines.append(smd_pad(2,  0.5, 0, 0.5, 0.5, net2))
    lines.append(end_footprint())
    return "\n".join(lines)


def gen_cap_0402(ref, x, y, net1, net2, value_str):
    """0402 capacitor footprint."""
    lines = [begin_footprint(ref, value_str, "F.Cu", x, y)]
    lines.append(fp_text("reference", ref, 0, -1.5, "F.SilkS"))
    lines.append(fp_text("value", value_str, 0, 1.5, "F.Fab"))
    lines.append(fp_courtyard_rect(-1.1, -0.6, 1.1, 0.6))
    lines.append(fp_fab_rect(-0.6, -0.3, 0.6, 0.3))
    lines.append(smd_pad(1, -0.5, 0, 0.5, 0.5, net1))
    lines.append(smd_pad(2,  0.5, 0, 0.5, 0.5, net2))
    lines.append(end_footprint())
    return "\n".join(lines)


def gen_cap_0805(ref, x, y, net1, net2, value_str):
    """0805 capacitor footprint (used for 10uF bulk caps)."""
    lines = [begin_footprint(ref, value_str, "F.Cu", x, y)]
    lines.append(fp_text("reference", ref, 0, -2.0, "F.SilkS"))
    lines.append(fp_text("value", value_str, 0, 2.0, "F.Fab"))
    lines.append(fp_courtyard_rect(-1.7, -0.9, 1.7, 0.9))
    lines.append(fp_fab_rect(-1.2, -0.65, 1.2, 0.65))
    lines.append(smd_pad(1, -0.9, 0, 0.8, 1.0, net1))
    lines.append(smd_pad(2,  0.9, 0, 0.8, 1.0, net2))
    lines.append(end_footprint())
    return "\n".join(lines)


def gen_esd_usblc6(ref, x, y):
    """
    USBLC6-2SC6 ESD protection in SOT-23-6 package.
    Pinout: 1=I/O1 (USB_DM), 2=GND, 3=I/O2 (USB_DP),
            4=I/O2 (USB_DP), 5=VBUS (5V), 6=I/O1 (USB_DM)
    Clamps USB D+/D- to safe levels against ESD events.
    """
    lines = [begin_footprint(ref, "USBLC6-2SC6", "F.Cu", x, y)]
    lines.append(fp_text("reference", ref, 0, -2.2, "F.SilkS"))
    lines.append(fp_text("value", "USBLC6-2SC6", 0, 2.2, "F.Fab"))
    lines.append(fp_courtyard_rect(-1.8, -1.6, 1.8, 1.6))
    lines.append(fp_fab_rect(-1.5, -1.4, 1.5, 1.4))

    # SOT-23-6: 3 pads left (1,2,3), 3 pads right (4,5,6)
    pad_defs = [
        (1, -0.95, -0.95, "USB_DM"),   # I/O1
        (2, -0.95,  0.0,  "GND"),      # GND
        (3, -0.95,  0.95, "USB_DP"),   # I/O2
        (4,  0.95,  0.95, "USB_DP"),   # I/O2
        (5,  0.95,  0.0,  "5V"),       # VBUS
        (6,  0.95, -0.95, "USB_DM"),   # I/O1
    ]
    for pnum, px, py, net in pad_defs:
        lines.append(smd_pad(pnum, px, py, 0.4, 0.7, net))

    lines.append(end_footprint())
    return "\n".join(lines)


def gen_test_point(ref, x, y, net_name, label):
    """
    SMD test point -- 1.5mm round pad on F.Cu.
    Large enough for a scope probe or multimeter tip.
    """
    lines = [begin_footprint(ref, label, "F.Cu", x, y)]
    lines.append(fp_text("reference", ref, 0, -1.8, "F.SilkS"))
    lines.append(fp_text("value", label, 0, 1.8, "F.Fab"))
    lines.append(fp_courtyard_rect(-1.2, -1.2, 1.2, 1.2))
    lines.append(smd_pad(1, 0, 0, 1.5, 1.5, net_name, shape="circle"))
    lines.append(end_footprint())
    return "\n".join(lines)


def gen_crystal_3225(ref, x, y):
    """
    40 MHz crystal in SMD-3225 4-pad package (e.g., NX3225GA-40.000MHz).
    Body 3.2x2.5mm. 4 pads: 1=XTAL_P, 2=GND, 3=XTAL_N, 4=GND.
    Pad pitch 2.2mm horizontal, 1.6mm vertical (IPC-7351 nominal).
    Load caps (12 pF NP0) are separate 0402 parts on each leg to GND.
    """
    lines = [begin_footprint(ref, "40MHz_XTAL", "F.Cu", x, y)]
    lines.append(fp_text("reference", ref, 0, -2.5, "F.SilkS"))
    lines.append(fp_text("value", "40MHz", 0, 2.5, "F.Fab"))
    lines.append(fp_courtyard_rect(-2.0, -1.6, 2.0, 1.6))
    lines.append(fp_fab_rect(-1.6, -1.25, 1.6, 1.25))
    # Pin 1 marker
    lines.append(
        '    (fp_circle (center -1.6 -1.25) (end -1.4 -1.25) (layer "F.SilkS") (stroke (width 0.1) (type solid)))'
    )
    # Pads: pad 1 bottom-left (XTAL_P), 2 bottom-right (GND),
    #       3 top-right (XTAL_N), 4 top-left (GND)
    pads = [
        (1, -1.1,  0.8, "XTAL_P"),
        (2,  1.1,  0.8, "GND"),
        (3,  1.1, -0.8, "XTAL_N"),
        (4, -1.1, -0.8, "GND"),
    ]
    for pnum, px, py, net in pads:
        lines.append(smd_pad(pnum, px, py, 1.2, 1.0, net, shape="rect"))
    lines.append(end_footprint())
    return "\n".join(lines)


# =============================================================================
# RF TRACE AND STITCHING VIAS
# =============================================================================

def gen_rf_trace():
    """
    50-ohm RF trace from ESP32-S3 pad 36 to chip antenna.
    Uses 45-degree bends (no 90-degree corners) on F.Cu.
    Width: 0.6mm (50-ohm microstrip on 0.2mm prepreg, Er=4.4).

    Route: ESP32-S3 RF pin -> 45-deg diagonal -> antenna pad.
    Pin 36 is on the top side of ESP32-S3, approximately at:
      x = POS_ESP32[0] + (36 - 29 - 6.5) * 0.4  (from top-left of top side)
    For QFN56 top side: pads 29-42, right to left
      pad 36 is the 8th pad from right = index 7 from right = index 6 from left in top
      x_offset = ((14-1)/2 - 7) * 0.4 = (6.5-7)*0.4 = -0.2mm from center
    So pad 36 position (world coords):
      x = POS_ESP32[0] + (-0.2) = 29.8
      y = POS_ESP32[1] - (7/2 + 0.3) = 20 - 3.8 = 16.2  (top of body + pad protrusion)
    """
    # Pad 36 world coordinates (top side, pad index from right = 36-29=7)
    pad36_x = POS_ESP32[0] + ((14-1)/2.0 - 7) * 0.4  # 29.8
    pad36_y = POS_ESP32[1] - (7.0/2.0 + 0.6/2.0)      # 16.2 (top face + pad half-height)

    ant_x = POS_ANT[0] - 0.5  # Antenna pad 1
    ant_y = POS_ANT[1]

    # Diagonal 45-deg route: go up-right from pad36 to ant
    # We need to route from (pad36_x, pad36_y) to (ant_x, ant_y)
    # Delta: dx = ant_x - pad36_x, dy = ant_y - pad36_y
    # Use a 2-segment route with 45-deg diagonal then horizontal/vertical

    dx = ant_x - pad36_x
    dy = ant_y - pad36_y  # negative = going up

    # Strategy: go diagonally until aligned in one axis, then straight
    # dy is negative (going up), dx is positive (going right)
    # Diagonal portion: min(abs(dx), abs(dy)) in both directions
    diag = min(abs(dx), abs(dy))
    # After diagonal, remaining is straight horizontal
    # Mid point after diagonal:
    mid_x = pad36_x + diag  # moving right
    mid_y = pad36_y - diag  # moving up

    net_id = NET_ID["RF_ANT"]
    lines = [
        f'  (segment (start {fmt(pad36_x)} {fmt(pad36_y)}) (end {fmt(mid_x)} {fmt(mid_y)}) '
        f'(width {RF_TRACE_W}) (layer "F.Cu") (net {net_id}))',
        f'  (segment (start {fmt(mid_x)} {fmt(mid_y)}) (end {fmt(ant_x)} {fmt(ant_y)}) '
        f'(width {RF_TRACE_W}) (layer "F.Cu") (net {net_id}))',
    ]

    return pad36_x, pad36_y, ant_x, ant_y, mid_x, mid_y, "\n".join(lines)


def gen_gnd_stitching_vias(pad36_x, pad36_y, mid_x, mid_y, ant_x, ant_y):
    """
    GND stitching vias every 6mm along the RF trace.
    At 2.4GHz in FR4, lambda/10 ~ 8.5mm, so 6mm spacing is conservative.
    Vias are placed adjacent to (not on) the RF trace, with 0.3mm clearance.
    Via size: 0.8mm outer / 0.4mm drill.
    """
    via_spacing = 6.0
    via_offset = 1.2  # mm offset from trace center (perpendicular)
    net_id = NET_ID["GND"]
    lines = []

    def vias_along_segment(x1, y1, x2, y2):
        """Place vias along a segment at via_spacing intervals."""
        seg_len = math.sqrt((x2-x1)**2 + (y2-y1)**2)
        if seg_len < 1.0:
            return []
        n_vias = max(1, int(seg_len / via_spacing))
        dx = (x2 - x1) / seg_len
        dy = (y2 - y1) / seg_len
        # Perpendicular direction (rotate 90 deg)
        px, py = -dy, dx
        v = []
        for i in range(n_vias):
            t = (i + 0.5) / n_vias
            cx = x1 + t * (x2 - x1)
            cy = y1 + t * (y2 - y1)
            # Place via on both sides of trace
            v.append((cx + px * via_offset, cy + py * via_offset))
            v.append((cx - px * via_offset, cy - py * via_offset))
        return v

    all_via_positions = []
    all_via_positions += vias_along_segment(pad36_x, pad36_y, mid_x, mid_y)
    all_via_positions += vias_along_segment(mid_x, mid_y, ant_x, ant_y)

    for vx, vy in all_via_positions:
        lines.append(
            f'  (via (at {fmt(vx)} {fmt(vy)}) (size 0.8) (drill 0.4) '
            f'(layers "F.Cu" "B.Cu") (net {net_id}))'
        )

    return "\n".join(lines)


# =============================================================================
# POWER TRACES
# =============================================================================

def gen_power_traces():
    """Simple power distribution traces connecting key components."""
    gnd = NET_ID["GND"]
    v33 = NET_ID["3V3"]
    v5  = NET_ID["5V"]
    lines = []

    # USB-C VBUS to LDO input (5V rail)
    lines.append(
        f'  (segment (start {fmt(POS_USBC[0]+1)} {fmt(POS_USBC[1])}) '
        f'(end {fmt(POS_LDO[0])} {fmt(POS_LDO[1]+1)}) '
        f'(width 0.5) (layer "F.Cu") (net {v5}))'
    )
    # LDO output to ESP32-S3 3V3
    lines.append(
        f'  (segment (start {fmt(POS_LDO[0]+1)} {fmt(POS_LDO[1])}) '
        f'(end {fmt(POS_ESP32[0]-4.5)} {fmt(POS_ESP32[1])}) '
        f'(width 0.5) (layer "F.Cu") (net {v33}))'
    )
    # LDO output to CP2102 VDD
    lines.append(
        f'  (segment (start {fmt(POS_LDO[0]+1)} {fmt(POS_LDO[1]+0.5)}) '
        f'(end {fmt(POS_CP2102[0]-3)} {fmt(POS_CP2102[1])}) '
        f'(width 0.5) (layer "F.Cu") (net {v33}))'
    )

    return "\n".join(lines)


# =============================================================================
# COPPER ZONES
# =============================================================================

def gen_zones():
    """
    Generate copper fill zones:
    1. Solid GND plane on In1.Cu (entire board)
    2. 3V3 power pour on In2.Cu (partial board, left 2/3)
    3. Keepout zone around antenna (all layers, circle approximated as polygon)
    """
    gnd_net = NET_ID["GND"]
    v33_net = NET_ID["3V3"]
    lines = []

    # --- GND Plane on In1.Cu (solid, entire board) ---
    lines.append(f'''  (zone (net {gnd_net}) (net_name "GND") (layer "In1.Cu") (name "GND_PLANE")
    (hatch edge 0.508)
    (connect_pads (clearance 0.1))
    (min_thickness 0.25)
    (filled_areas_thickness no)
    (fill yes (thermal_gap 0.3) (thermal_bridge_width 0.3))
    (polygon
      (pts
        (xy 0 0) (xy {fmt(BOARD_W)} 0) (xy {fmt(BOARD_W)} {fmt(BOARD_H)}) (xy 0 {fmt(BOARD_H)})
      )
    )
  )''')

    # --- 3V3 Power Pour on In2.Cu (left 2/3 of board) ---
    lines.append(f'''  (zone (net {v33_net}) (net_name "3V3") (layer "In2.Cu") (name "3V3_POWER")
    (hatch edge 0.508)
    (connect_pads (clearance 0.2))
    (min_thickness 0.25)
    (filled_areas_thickness no)
    (fill yes (thermal_gap 0.4) (thermal_bridge_width 0.4))
    (polygon
      (pts
        (xy 0 5) (xy 38 5) (xy 38 {fmt(BOARD_H-5)}) (xy 0 {fmt(BOARD_H-5)})
      )
    )
  )''')

    # --- RF Keepout Zone (circle approx as 36-sided polygon) ---
    # No copper on ANY layer within 5mm radius of antenna center
    # Also no traces allowed in this region
    cx, cy = POS_ANT
    r = RF_KEEPOUT_R
    n_pts = 36
    pts = []
    for i in range(n_pts):
        angle = 2 * math.pi * i / n_pts
        px = cx + r * math.cos(angle)
        py = cy + r * math.sin(angle)
        pts.append(f"(xy {fmt(px)} {fmt(py)})")

    pts_str = " ".join(pts)
    lines.append(f'''  (zone (net 0) (net_name "") (layer "F.Cu") (name "RF_KEEPOUT")
    (hatch edge 0.508)
    (keepout (tracks not_allowed) (vias not_allowed) (pads not_allowed) (copperpour not_allowed) (footprints allowed))
    (polygon
      (pts
        {pts_str}
      )
    )
  )''')

    # Same keepout on B.Cu
    lines.append(f'''  (zone (net 0) (net_name "") (layer "B.Cu") (name "RF_KEEPOUT_BOTT")
    (hatch edge 0.508)
    (keepout (tracks not_allowed) (vias not_allowed) (pads not_allowed) (copperpour not_allowed) (footprints allowed))
    (polygon
      (pts
        {pts_str}
      )
    )
  )''')

    # In1.Cu keepout (keep GND plane clear of antenna)
    lines.append(f'''  (zone (net 0) (net_name "") (layer "In1.Cu") (name "RF_KEEPOUT_GND")
    (hatch edge 0.508)
    (keepout (tracks not_allowed) (vias not_allowed) (pads not_allowed) (copperpour not_allowed) (footprints allowed))
    (polygon
      (pts
        {pts_str}
      )
    )
  )''')

    return "\n".join(lines)


# =============================================================================
# DECOUPLING CAPACITORS
# =============================================================================

def gen_decoupling_caps():
    """
    Place 100nF decoupling caps adjacent to ESP32-S3 power pins.
    ESP32-S3 VDD pads in this layout: 7, 8 (bottom-centre, world y~23.8)
    and 29 (top-right, world y~16.2).
    Every VDD pad has a 100nF cap whose centre is within 2mm of the pad
    centre. Additional bypass caps distribute decoupling around the chip.
    Place 10uF bulk caps at LDO input and output.
    """
    lines = []
    cx, cy = POS_ESP32

    # 100nF decoupling caps near ESP32-S3 power pins (0402)
    # Pad 29 world coords = (cx+2.6, cy-3.8).  Caps C1/C3 flank it at 1.7mm.
    # Pads 7,8 world coords = (cx-0.2,cy+3.8), (cx+0.2,cy+3.8).  C2 sits 1.7mm
    # below them. C4-C6 are distributed bypass around the chip.
    # Note: RF trace runs from pad 36 (world ~29.8, 16.2) diagonally to
    # (32.0, 14.0) then horizontally to the antenna at (43.5, 14.0). Keep
    # decoupling caps clear of y ~ 14 above the chip.
    decap_positions = [
        ("C1",  cx + 4.0, cy - 3.8, "100nF"),   # 1.4mm right of pad 29 (3V3, top)
        ("C2",  cx + 0.0, cy + 5.5, "100nF"),   # 1.7mm below pads 7/8 (3V3, bottom)
        ("C3",  cx + 4.0, cy - 2.0, "100nF"),   # right-side bypass above pad 28
        ("C4",  cx - 4.0, cy - 2.0, "100nF"),   # left-side bypass, upper
        ("C5",  cx - 2.6, cy + 5.5, "100nF"),   # bottom-left bypass
        ("C6",  cx + 2.6, cy + 5.5, "100nF"),   # bottom-right bypass
    ]
    for ref, x, y, val in decap_positions:
        lines.append(gen_cap_0402(ref, x, y, "3V3", "GND", val))

    # 10uF bulk cap at LDO input (5V side)
    lx, ly = POS_LDO
    lines.append(gen_cap_0805("C7", lx + 2.5, ly + 1.5, "5V", "GND", "10uF"))
    # 10uF bulk cap at LDO output (3V3 side)
    lines.append(gen_cap_0805("C8", lx - 2.5, ly + 1.5, "3V3", "GND", "10uF"))

    # 100nF bypass caps for USB-C power lines
    lines.append(gen_cap_0402("C9",  POS_USBC[0] + 2.0, POS_USBC[1] - 3.0, "5V",  "GND", "100nF"))
    lines.append(gen_cap_0402("C10", POS_USBC[0] + 2.0, POS_USBC[1] - 4.5, "5V",  "GND", "100nF"))

    # 100nF bypass for CP2102
    lines.append(gen_cap_0402("C11", POS_CP2102[0] + 4.0, POS_CP2102[1], "3V3", "GND", "100nF"))

    return "\n".join(lines)


# =============================================================================
# MAIN PCB FILE ASSEMBLY
# =============================================================================

def gen_pcb():
    """Assemble the complete .kicad_pcb S-expression file."""
    parts = []
    parts.append(gen_header())
    parts.append(gen_general())
    parts.append(gen_layers())
    parts.append(gen_setup())
    parts.append(gen_nets())
    parts.append(gen_board_outline())
    parts.append(gen_silkscreen_labels())

    # --- Footprints ---
    parts.append(gen_esp32s3())
    parts.append(gen_johanson_antenna())
    parts.append(gen_ufl_connector())
    parts.append(gen_ap2112k())
    parts.append(gen_usbc())
    parts.append(gen_cp2102())

    # Headers
    parts.append(gen_header_4pin(
        "J3", POS_UART[0], POS_UART[1],
        ["GND", "3V3", "UART_TX", "UART_RX"],
        "UART_4P"
    ))
    parts.append(gen_header_4pin(
        "J4", POS_I2C[0], POS_I2C[1],
        ["GND", "3V3", "I2C_SDA", "I2C_SCL"],
        "I2C_4P"
    ))
    parts.append(gen_header_6pin(
        "J5", POS_SPI[0], POS_SPI[1],
        ["GND", "3V3", "SPI_MOSI", "SPI_MISO", "SPI_SCK", "SPI_CS"],
        "SPI_6P"
    ))

    # Buttons
    parts.append(gen_tactile_button("SW1", POS_RST_BTN[0],  POS_RST_BTN[1],  "RST_BTN"))
    parts.append(gen_tactile_button("SW2", POS_BOOT_BTN[0], POS_BOOT_BTN[1], "BOOT_BTN"))

    # LEDs and resistors
    parts.append(gen_led_0402("D1", POS_LED_STA[0] - 1.5, POS_LED_STA[1], "LED_STATUS_A", "LED_RED"))
    parts.append(gen_led_0402("D2", POS_LED_PWR[0] - 1.5, POS_LED_PWR[1], "LED_POWER_A",  "LED_GRN"))
    parts.append(gen_resistor_0402("R1", POS_LED_STA[0] + 1.5, POS_LED_STA[1],
                                   "GPIO48_LED", "LED_STATUS_A", "330R", "330R"))
    parts.append(gen_resistor_0402("R2", POS_LED_PWR[0] + 1.5, POS_LED_PWR[1],
                                   "3V3", "LED_POWER_A", "1k", "1k"))

    # CC pull-down resistors (5.1K from CC1/CC2 to GND for USB power negotiation)
    parts.append(gen_resistor_0402("R3", 11.5, 38.0,
                                   "USB_CC1", "GND", "5.1k", "5.1k"))
    parts.append(gen_resistor_0402("R4", 11.5, 36.0,
                                   "USB_CC2", "GND", "5.1k", "5.1k"))

    # ESD protection on USB D+/D-
    parts.append(gen_esd_usblc6("U4", POS_ESD[0], POS_ESD[1]))

    # Test points
    parts.append(gen_test_point("TP1", POS_TP1[0], POS_TP1[1], "3V3", "TP_3V3"))
    parts.append(gen_test_point("TP2", POS_TP2[0], POS_TP2[1], "GND", "TP_GND"))
    parts.append(gen_test_point("TP3", POS_TP3[0], POS_TP3[1], "RF_ANT", "TP_RF"))

    # 40 MHz crystal (Y1) and 12 pF NP0 load caps on XTAL_P / XTAL_N.
    # The ESP32-S3 QFN56 bare die has no internal clock source: without
    # this crystal the chip will not boot, no WiFi, no BT.
    parts.append(gen_crystal_3225("Y1", POS_XTAL[0], POS_XTAL[1]))
    parts.append(gen_cap_0402("C12", POS_XTAL_C1[0], POS_XTAL_C1[1],
                              "XTAL_P", "GND", "12pF"))
    parts.append(gen_cap_0402("C13", POS_XTAL_C2[0], POS_XTAL_C2[1],
                              "XTAL_N", "GND", "12pF"))

    # EN pull-up (10k to 3V3). Keeps the chip enabled at power-up and
    # gives the reset button something to pull low against.
    parts.append(gen_resistor_0402("R5", POS_R_EN[0], POS_R_EN[1],
                                   "3V3", "EN", "10k", "10k"))

    # 22R series resistors on USB D+/D- between CP2102 and USBLC6. Damps
    # ringing on the USB full-speed differential pair. Placed near CP2102.
    parts.append(gen_resistor_0402("R6", POS_R_USBDP[0], POS_R_USBDP[1],
                                   "USB_DP_CP", "USB_DP", "22R", "22R"))
    parts.append(gen_resistor_0402("R7", POS_R_USBDM[0], POS_R_USBDM[1],
                                   "USB_DM_CP", "USB_DM", "22R", "22R"))

    # Decoupling caps
    parts.append(gen_decoupling_caps())

    # --- RF Trace and stitching vias ---
    pad36_x, pad36_y, ant_x, ant_y, mid_x, mid_y, rf_traces = gen_rf_trace()
    parts.append(rf_traces)
    parts.append(gen_gnd_stitching_vias(pad36_x, pad36_y, mid_x, mid_y, ant_x, ant_y))

    # --- Power traces ---
    parts.append(gen_power_traces())

    # --- Copper zones ---
    parts.append(gen_zones())

    # Close root expression
    parts.append(")\n")

    return "\n".join(parts)


# =============================================================================
# SCHEMATIC FILE (.kicad_sch)
#
# The schematic is generated programmatically alongside the PCB so design
# intent is captured in one place. Each component is represented by a
# minimal rectangular symbol with real pins; net connectivity is expressed
# via global labels attached at pin endpoints. ERC should pass with no
# errors. A hand-drawn GUI pass can be layered on later for presentation.
# =============================================================================

ROOT_SHEET_UUID = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
SCH_PROJECT     = "esp32-s3-rf-board"

SCH_PIN_LEN = 2.54
SCH_GRID    = 2.54

_sch_uuid_ctr = 2000
def su():
    """Return a pseudo-UUID for a schematic element."""
    global _sch_uuid_ctr
    _sch_uuid_ctr += 1
    return f"{_sch_uuid_ctr:08x}-0000-0000-0000-000000000000"


def sch_symbol_ic(name, prefix, left_pins, right_pins, fp=""):
    """
    Define a rectangular IC symbol in lib_symbols.
    left_pins/right_pins: list of (pin_number, pin_name).
    """
    n = max(len(left_pins), len(right_pins))
    body_half_h = (n + 1) * SCH_GRID / 2.0
    body_half_w = 7.62
    pin_x = body_half_w + SCH_PIN_LEN

    lines = [f'    (symbol "custom:{name}"']
    lines.append(f'      (pin_names (offset 1.016))')
    lines.append(f'      (exclude_from_sim no)')
    lines.append(f'      (in_bom yes)')
    lines.append(f'      (on_board yes)')
    lines.append(f'      (property "Reference" "{prefix}" (at 0 {fmt(body_half_h + 2.54)} 0) (effects (font (size 1.27 1.27))))')
    lines.append(f'      (property "Value" "{name}" (at 0 {fmt(body_half_h + 1.0)} 0) (effects (font (size 1.27 1.27))))')
    lines.append(f'      (property "Footprint" "{fp}" (at 0 {fmt(-body_half_h - 2.54)} 0) (effects (font (size 1.27 1.27)) (hide yes)))')
    lines.append(f'      (property "Datasheet" "" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))')
    lines.append(f'      (property "Description" "" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))')

    lines.append(f'      (symbol "{name}_0_1"')
    lines.append(f'        (rectangle (start {fmt(-body_half_w)} {fmt(-body_half_h)}) (end {fmt(body_half_w)} {fmt(body_half_h)})')
    lines.append(f'          (stroke (width 0.254) (type default)) (fill (type background))))')

    lines.append(f'      (symbol "{name}_1_1"')
    for i, (pnum, pname) in enumerate(left_pins):
        py = body_half_h - SCH_GRID - i * SCH_GRID
        lines.append(f'        (pin passive line (at {fmt(-pin_x)} {fmt(py)} 0) (length {fmt(SCH_PIN_LEN)})')
        lines.append(f'          (name "{pname}" (effects (font (size 1.0 1.0))))')
        lines.append(f'          (number "{pnum}" (effects (font (size 1.0 1.0)))))')
    for i, (pnum, pname) in enumerate(right_pins):
        py = body_half_h - SCH_GRID - i * SCH_GRID
        lines.append(f'        (pin passive line (at {fmt(pin_x)} {fmt(py)} 180) (length {fmt(SCH_PIN_LEN)})')
        lines.append(f'          (name "{pname}" (effects (font (size 1.0 1.0))))')
        lines.append(f'          (number "{pnum}" (effects (font (size 1.0 1.0)))))')
    lines.append(f'      )')
    lines.append(f'      (embedded_fonts no)')
    lines.append(f'    )')
    return "\n".join(lines), body_half_w, body_half_h, pin_x


def sch_symbol_passive2(name, prefix, fp=""):
    """Two-pin passive symbol (R, C, LED). Pins on top (1) and bottom (2)."""
    lines = [f'    (symbol "custom:{name}"']
    lines.append(f'      (pin_numbers (hide yes))')
    lines.append(f'      (pin_names (offset 0) (hide yes))')
    lines.append(f'      (exclude_from_sim no)')
    lines.append(f'      (in_bom yes)')
    lines.append(f'      (on_board yes)')
    lines.append(f'      (property "Reference" "{prefix}" (at 2.54 1.27 0) (effects (font (size 1.27 1.27)) (justify left)))')
    lines.append(f'      (property "Value" "{name}" (at 2.54 -1.27 0) (effects (font (size 1.27 1.27)) (justify left)))')
    lines.append(f'      (property "Footprint" "{fp}" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))')
    lines.append(f'      (property "Datasheet" "" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))')
    lines.append(f'      (property "Description" "" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))')

    lines.append(f'      (symbol "{name}_0_1"')
    if prefix == "C":
        lines.append(f'        (polyline (pts (xy -2.032 -0.762) (xy 2.032 -0.762)) (stroke (width 0.508) (type default)) (fill (type none)))')
        lines.append(f'        (polyline (pts (xy -2.032 0.762) (xy 2.032 0.762)) (stroke (width 0.508) (type default)) (fill (type none)))')
    elif prefix == "D":
        lines.append(f'        (polyline (pts (xy 0 1.27) (xy 0 -1.27) (xy -1.27 0) (xy 0 1.27)) (stroke (width 0.254) (type default)) (fill (type outline)))')
        lines.append(f'        (polyline (pts (xy -1.27 1.27) (xy -1.27 -1.27)) (stroke (width 0.254) (type default)) (fill (type none)))')
    else:  # R default
        lines.append(f'        (rectangle (start -1.016 -2.286) (end 1.016 2.286) (stroke (width 0.254) (type default)) (fill (type none)))')
    lines.append(f'      )')

    lines.append(f'      (symbol "{name}_1_1"')
    lines.append(f'        (pin passive line (at 0 3.81 270) (length 1.524)')
    lines.append(f'          (name "~" (effects (font (size 1.27 1.27))))')
    lines.append(f'          (number "1" (effects (font (size 1.27 1.27)))))')
    lines.append(f'        (pin passive line (at 0 -3.81 90) (length 1.524)')
    lines.append(f'          (name "~" (effects (font (size 1.27 1.27))))')
    lines.append(f'          (number "2" (effects (font (size 1.27 1.27)))))')
    lines.append(f'      )')
    lines.append(f'      (embedded_fonts no)')
    lines.append(f'    )')
    return "\n".join(lines)


def sch_global_label(text, x, y, rot=0):
    """Global label at (x, y). Use rot=0 for left-pointing, 180 for right-pointing."""
    return (
        f'  (global_label "{text}" (shape input) (at {fmt(x)} {fmt(y)} {rot})\n'
        f'    (effects (font (size 1.27 1.27)) (justify {"left" if rot == 0 else "right"}))\n'
        f'    (uuid "{su()}")\n'
        f'    (property "Intersheetrefs" "${{INTERSHEET_REFS}}" (at 0 0 0)\n'
        f'      (effects (font (size 1.27 1.27)) (justify left) hide))\n'
        f'  )'
    )


def sch_instance_ic(lib_name, ref, value, footprint, x, y, left_nets, right_nets,
                   n_left_pins, n_right_pins):
    """
    Place an IC symbol instance and emit global labels at each pin endpoint.
    left_nets/right_nets: list of net-name strings indexed like left_pins.
    """
    n = max(n_left_pins, n_right_pins)
    body_half_h = (n + 1) * SCH_GRID / 2.0
    body_half_w = 7.62
    pin_x = body_half_w + SCH_PIN_LEN

    out = []
    uid = su()
    out.append(f'  (symbol (lib_id "custom:{lib_name}") (at {fmt(x)} {fmt(y)} 0) (unit 1)')
    out.append(f'    (exclude_from_sim no) (in_bom yes) (on_board yes) (dnp no)')
    out.append(f'    (uuid "{uid}")')
    out.append(f'    (property "Reference" "{ref}" (at {fmt(x)} {fmt(y - body_half_h - 2.54)} 0) (effects (font (size 1.27 1.27))))')
    out.append(f'    (property "Value" "{value}" (at {fmt(x)} {fmt(y - body_half_h - 1.0)} 0) (effects (font (size 1.27 1.27))))')
    out.append(f'    (property "Footprint" "{footprint}" (at {fmt(x)} {fmt(y)} 0) (effects (font (size 1.27 1.27)) hide))')
    out.append(f'    (property "Datasheet" "" (at {fmt(x)} {fmt(y)} 0) (effects (font (size 1.27 1.27)) hide))')
    out.append(f'    (property "Description" "" (at {fmt(x)} {fmt(y)} 0) (effects (font (size 1.27 1.27)) hide))')

    # Pin UUIDs (one per pin)
    for i in range(n_left_pins):
        out.append(f'    (pin "L{i+1}" (uuid "{su()}"))')
    for i in range(n_right_pins):
        out.append(f'    (pin "R{i+1}" (uuid "{su()}"))')

    out.append(f'    (instances')
    out.append(f'      (project "{SCH_PROJECT}"')
    out.append(f'        (path "/{ROOT_SHEET_UUID}"')
    out.append(f'          (reference "{ref}") (unit 1))))')
    out.append(f'  )')

    # Emit global labels at each pin's wire-connection point.
    # KiCad schematic y grows downward but symbol-local y is mathematical
    # (positive = up), so world_y = instance_y - local_y. Empty net string
    # means "intentionally unconnected" -> emit a no_connect marker instead.
    for i, net in enumerate(left_nets):
        local_py = body_half_h - SCH_GRID - i * SCH_GRID
        py = y - local_py
        px = x - pin_x
        if net:
            out.append(sch_global_label(net, px, py, rot=180))
        else:
            out.append(f'  (no_connect (at {fmt(px)} {fmt(py)}) (uuid "{su()}"))')
    for i, net in enumerate(right_nets):
        local_py = body_half_h - SCH_GRID - i * SCH_GRID
        py = y - local_py
        px = x + pin_x
        if net:
            out.append(sch_global_label(net, px, py, rot=0))
        else:
            out.append(f'  (no_connect (at {fmt(px)} {fmt(py)}) (uuid "{su()}"))')
    return "\n".join(out)


def sch_instance_passive(lib_name, ref, value, footprint, x, y, net_top, net_bot):
    """
    Place a 2-pin passive symbol. Pin 1 at (x, y-3.81), pin 2 at (x, y+3.81).
    Wait: pin at (0, 3.81) orientation 270 -> endpoint at (0, 3.81+1.524)=(0, 5.334)?
    The pin definition: (at 0 3.81 270) length 1.524 means pin stub goes in 270°
    direction (-Y) from (0, 3.81), so stub runs from (0, 3.81) to (0, 2.286).
    Wire-connection point = (0, 3.81) -- the outer end.
    For instance placed at (x, y), pin 1 wire point = (x, y + 3.81),
    pin 2 wire point = (x, y - 3.81).
    """
    out = []
    uid = su()
    out.append(f'  (symbol (lib_id "custom:{lib_name}") (at {fmt(x)} {fmt(y)} 0) (unit 1)')
    out.append(f'    (exclude_from_sim no) (in_bom yes) (on_board yes) (dnp no)')
    out.append(f'    (uuid "{uid}")')
    out.append(f'    (property "Reference" "{ref}" (at {fmt(x + 2.54)} {fmt(y - 1.27)} 0) (effects (font (size 1.27 1.27)) (justify left)))')
    out.append(f'    (property "Value" "{value}" (at {fmt(x + 2.54)} {fmt(y + 1.27)} 0) (effects (font (size 1.27 1.27)) (justify left)))')
    out.append(f'    (property "Footprint" "{footprint}" (at {fmt(x)} {fmt(y)} 0) (effects (font (size 1.27 1.27)) hide))')
    out.append(f'    (property "Datasheet" "" (at {fmt(x)} {fmt(y)} 0) (effects (font (size 1.27 1.27)) hide))')
    out.append(f'    (property "Description" "" (at {fmt(x)} {fmt(y)} 0) (effects (font (size 1.27 1.27)) hide))')
    out.append(f'    (pin "1" (uuid "{su()}"))')
    out.append(f'    (pin "2" (uuid "{su()}"))')
    out.append(f'    (instances')
    out.append(f'      (project "{SCH_PROJECT}"')
    out.append(f'        (path "/{ROOT_SHEET_UUID}"')
    out.append(f'          (reference "{ref}") (unit 1))))')
    out.append(f'  )')
    # Pin 1 at (x, y + 3.81) - top; pin 2 at (x, y - 3.81) - bottom
    # (pin def uses y=+3.81 for pin 1, relative to body origin — we invert for
    # schematic world coords because the KiCad origin has y growing downward)
    if net_top:
        out.append(sch_global_label(net_top, x, y - 3.81, rot=90))
    if net_bot:
        out.append(sch_global_label(net_bot, x, y + 3.81, rot=270))
    return "\n".join(out)


# ----- ESP32-S3 symbol (only pins used in this design) -----
ESP32_LEFT_PINS = [
    ("7",  "VDD3P3"),       # 3V3 power
    ("8",  "VDD3P3"),       # 3V3 power
    ("29", "VDD_SPI"),      # 3V3 power
    ("16", "IO11/MOSI"),
    ("17", "IO13/MISO"),
    ("18", "IO12/CLK"),
    ("19", "IO10/CS"),
    ("20", "IO43/TXD0"),
    ("21", "IO44/RXD0"),
    ("22", "IO8/SDA"),
    ("23", "IO9/SCL"),
    ("48", "IO48/LED"),
]
ESP32_RIGHT_PINS = [
    ("36", "LNA_IN"),       # RF
    ("39", "XTAL_P"),
    ("40", "XTAL_N"),
    ("51", "CHIP_PU"),      # EN
    ("52", "IO0"),          # GPIO0 (boot strap)
    ("1",  "GND"),
    ("4",  "GND"),
    ("15", "GND"),
    ("43", "GND"),
    ("56", "GND"),
    ("57", "EP/GND"),
]
ESP32_LEFT_NETS = [
    "3V3", "3V3", "3V3",
    "SPI_MOSI", "SPI_MISO", "SPI_SCK", "SPI_CS",
    "UART_TX", "UART_RX",
    "I2C_SDA", "I2C_SCL",
    "GPIO48_LED",
]
ESP32_RIGHT_NETS = [
    "RF_ANT", "XTAL_P", "XTAL_N",
    "EN", "GPIO0",
    "GND", "GND", "GND", "GND", "GND", "GND",
]

# ----- AP2112K-3.3 -----
AP2112_LEFT_PINS  = [("1","EN"), ("2","GND"), ("3","VIN")]
AP2112_RIGHT_PINS = [("5","VOUT"), ("4","NC")]
AP2112_LEFT_NETS  = ["3V3", "GND", "5V"]
AP2112_RIGHT_NETS = ["3V3", ""]   # pin 4 NC: marked with no_connect below

# ----- CP2102 -----
CP2102_LEFT_PINS = [
    ("4",  "VDD"),
    ("15", "VDD"),
    ("1",  "GND"),
    ("8",  "GND"),
    ("16", "GND"),
    ("22", "GND"),
    ("29", "EP"),
]
CP2102_RIGHT_PINS = [
    ("2",  "D-"),
    ("3",  "D+"),
    ("9",  "TXD"),
    ("10", "RXD"),
]
CP2102_LEFT_NETS  = ["3V3","3V3","GND","GND","GND","GND","GND"]
CP2102_RIGHT_NETS = ["USB_DM_CP","USB_DP_CP","UART_TX","UART_RX"]

# ----- USBLC6-2SC6 -----
USBLC6_LEFT_PINS  = [("5","VBUS"), ("2","GND")]
USBLC6_RIGHT_PINS = [("1","I/O1"), ("6","I/O1"), ("3","I/O2"), ("4","I/O2")]
USBLC6_LEFT_NETS  = ["5V", "GND"]
USBLC6_RIGHT_NETS = ["USB_DM", "USB_DM", "USB_DP", "USB_DP"]

# ----- USB-C 16P -----
USBC_LEFT_PINS = [
    ("A4","VBUS"), ("A9","VBUS"), ("B4","VBUS"), ("B9","VBUS"),
    ("A1","GND"), ("A12","GND"), ("B1","GND"), ("B12","GND"),
    ("S1","SHIELD"),
]
USBC_RIGHT_PINS = [
    ("A6","D+"), ("A7","D-"), ("B6","D+"), ("B7","D-"),
    ("A5","CC1"), ("B5","CC2"),
]
USBC_LEFT_NETS  = ["5V","5V","5V","5V","GND","GND","GND","GND","GND"]
USBC_RIGHT_NETS = ["USB_DP","USB_DM","USB_DP","USB_DM","USB_CC1","USB_CC2"]

# ----- Crystal 4-pad -----
XTAL_LEFT_PINS  = [("1","XI"), ("4","GND")]
XTAL_RIGHT_PINS = [("3","XO"), ("2","GND")]
XTAL_LEFT_NETS  = ["XTAL_P", "GND"]
XTAL_RIGHT_NETS = ["XTAL_N", "GND"]

# ----- Chip antenna 2-pad (ANT1) -----
ANT_LEFT_PINS  = [("1","RF")]
ANT_RIGHT_PINS = [("2","GND")]

# ----- u.FL 3-pad -----
UFL_LEFT_PINS  = [("1","SIG")]
UFL_RIGHT_PINS = [("2","GND"), ("3","GND")]

# ----- Headers -----
HDR4_LEFT_PINS  = [("1",""), ("2",""), ("3",""), ("4","")]
HDR4_RIGHT_PINS = []
HDR6_LEFT_PINS  = [("1",""), ("2",""), ("3",""), ("4",""), ("5",""), ("6","")]
HDR6_RIGHT_PINS = []

# ----- Tactile button (2 logical nets, 4 pads) -----
BTN_LEFT_PINS  = [("1","A"), ("3","B")]
BTN_RIGHT_PINS = [("2","A"), ("4","B")]

# ----- Test point -----
TP_LEFT_PINS  = [("1","TP")]
TP_RIGHT_PINS = []


def gen_lib_symbols():
    """Define all symbols used in the schematic."""
    blocks = []

    # ICs (rectangular multi-pin)
    blocks.append(sch_symbol_ic("ESP32-S3FN8", "U",
                                ESP32_LEFT_PINS, ESP32_RIGHT_PINS,
                                "QFN-56_7x7mm_P0.4mm")[0])
    blocks.append(sch_symbol_ic("AP2112K-3.3", "U",
                                AP2112_LEFT_PINS, AP2112_RIGHT_PINS,
                                "SOT-23-5")[0])
    blocks.append(sch_symbol_ic("CP2102", "U",
                                CP2102_LEFT_PINS, CP2102_RIGHT_PINS,
                                "QFN-28_5x5mm_P0.5mm")[0])
    blocks.append(sch_symbol_ic("USBLC6-2SC6", "U",
                                USBLC6_LEFT_PINS, USBLC6_RIGHT_PINS,
                                "SOT-23-6")[0])
    blocks.append(sch_symbol_ic("USB_C_16P", "J",
                                USBC_LEFT_PINS, USBC_RIGHT_PINS,
                                "USB-C_SMD_16P")[0])
    blocks.append(sch_symbol_ic("XTAL_3225_4P", "Y",
                                XTAL_LEFT_PINS, XTAL_RIGHT_PINS,
                                "XTAL_SMD_3225_4P")[0])
    blocks.append(sch_symbol_ic("ANT_CHIP_2P", "ANT",
                                ANT_LEFT_PINS, ANT_RIGHT_PINS,
                                "ANT_0402_1x0.5mm")[0])
    blocks.append(sch_symbol_ic("UFL_SMD", "J",
                                UFL_LEFT_PINS, UFL_RIGHT_PINS,
                                "U.FL_SMD")[0])
    blocks.append(sch_symbol_ic("Header_1x04", "J",
                                HDR4_LEFT_PINS, HDR4_RIGHT_PINS,
                                "PinHeader_1x04_P2.54mm")[0])
    blocks.append(sch_symbol_ic("Header_1x06", "J",
                                HDR6_LEFT_PINS, HDR6_RIGHT_PINS,
                                "PinHeader_1x06_P2.54mm")[0])
    blocks.append(sch_symbol_ic("SW_Tactile", "SW",
                                BTN_LEFT_PINS, BTN_RIGHT_PINS,
                                "SW_Tactile_6x6mm")[0])
    blocks.append(sch_symbol_ic("TestPoint_SMD", "TP",
                                TP_LEFT_PINS, TP_RIGHT_PINS,
                                "TP_SMD_1.5mm")[0])

    # Passives
    blocks.append(sch_symbol_passive2("R", "R", "R_0402"))
    blocks.append(sch_symbol_passive2("C", "C", "C_0402"))
    blocks.append(sch_symbol_passive2("C_Bulk", "C", "C_0805"))
    blocks.append(sch_symbol_passive2("LED", "D", "LED_0402"))

    return "\n".join(blocks)


def gen_schematic():
    """
    Generate the full KiCAD 8 schematic (.kicad_sch). Uses custom symbols
    defined in the embedded lib_symbols block; connectivity is expressed
    with global_label elements at pin endpoints (same label = same net).
    """
    now = datetime.now().strftime("%Y-%m-%d")
    global _sch_uuid_ctr
    _sch_uuid_ctr = 2000

    lib = gen_lib_symbols()

    placements = []

    # --- ICs placed across the sheet ---
    # Sheet = A3 landscape (420 x 297 mm); origin top-left, +Y downward.
    # ESP32-S3 centre: (200, 130)
    placements.append(sch_instance_ic(
        "ESP32-S3FN8", "U1", "ESP32-S3FN8", "QFN-56_7x7mm_P0.4mm",
        200, 130, ESP32_LEFT_NETS, ESP32_RIGHT_NETS,
        len(ESP32_LEFT_PINS), len(ESP32_RIGHT_PINS),
    ))

    # AP2112K LDO, top-left
    placements.append(sch_instance_ic(
        "AP2112K-3.3", "U2", "AP2112K-3.3", "SOT-23-5",
        80, 50, AP2112_LEFT_NETS, AP2112_RIGHT_NETS,
        len(AP2112_LEFT_PINS), len(AP2112_RIGHT_PINS),
    ))

    # CP2102, upper-right
    placements.append(sch_instance_ic(
        "CP2102", "U3", "CP2102-GMR", "QFN-28_5x5mm_P0.5mm",
        330, 80, CP2102_LEFT_NETS, CP2102_RIGHT_NETS,
        len(CP2102_LEFT_PINS), len(CP2102_RIGHT_PINS),
    ))

    # USBLC6-2SC6 ESD, between CP2102 and USB-C
    placements.append(sch_instance_ic(
        "USBLC6-2SC6", "U4", "USBLC6-2SC6", "SOT-23-6",
        330, 180, USBLC6_LEFT_NETS, USBLC6_RIGHT_NETS,
        len(USBLC6_LEFT_PINS), len(USBLC6_RIGHT_PINS),
    ))

    # USB-C, far right
    placements.append(sch_instance_ic(
        "USB_C_16P", "J1", "USB_C_16P", "USB-C_SMD_16P",
        395, 180, USBC_LEFT_NETS, USBC_RIGHT_NETS,
        len(USBC_LEFT_PINS), len(USBC_RIGHT_PINS),
    ))

    # Crystal Y1 and load caps, top-centre
    placements.append(sch_instance_ic(
        "XTAL_3225_4P", "Y1", "40MHz_NX3225GA", "XTAL_SMD_3225_4P",
        130, 40, XTAL_LEFT_NETS, XTAL_RIGHT_NETS,
        len(XTAL_LEFT_PINS), len(XTAL_RIGHT_PINS),
    ))
    placements.append(sch_instance_passive("C", "C12", "12pF", "C_0402",
                                           95, 40, "XTAL_P", "GND"))
    placements.append(sch_instance_passive("C", "C13", "12pF", "C_0402",
                                           165, 40, "XTAL_N", "GND"))

    # Antenna + u.FL (RF path), bottom-right of ESP32
    placements.append(sch_instance_ic(
        "ANT_CHIP_2P", "ANT1", "2450AT18A100", "ANT_0402_1x0.5mm",
        270, 80, ["RF_ANT"], ["GND"], 1, 1,
    ))
    placements.append(sch_instance_ic(
        "UFL_SMD", "J2", "U.FL_SMD", "U.FL_SMD",
        270, 110, ["RF_ANT"], ["GND", "GND"], 1, 2,
    ))

    # Headers (left side)
    placements.append(sch_instance_ic(
        "Header_1x04", "J3", "1x04_2.54mm", "PinHeader_1x04_P2.54mm",
        40, 130, ["GND", "3V3", "UART_TX", "UART_RX"], [], 4, 0,
    ))
    placements.append(sch_instance_ic(
        "Header_1x04", "J4", "1x04_2.54mm", "PinHeader_1x04_P2.54mm",
        40, 160, ["GND", "3V3", "I2C_SDA", "I2C_SCL"], [], 4, 0,
    ))
    placements.append(sch_instance_ic(
        "Header_1x06", "J5", "1x06_2.54mm", "PinHeader_1x06_P2.54mm",
        40, 200, ["GND","3V3","SPI_MOSI","SPI_MISO","SPI_SCK","SPI_CS"], [], 6, 0,
    ))

    # Buttons (to the right of ESP32)
    placements.append(sch_instance_ic(
        "SW_Tactile", "SW1", "SW_TACT_6x6", "SW_Tactile_6x6mm",
        270, 140, ["GND", "EN"], ["GND", "EN"], 2, 2,
    ))
    placements.append(sch_instance_ic(
        "SW_Tactile", "SW2", "SW_TACT_6x6", "SW_Tactile_6x6mm",
        270, 170, ["GND", "GPIO0"], ["GND", "GPIO0"], 2, 2,
    ))

    # LEDs + series resistors (bottom-left of ESP32)
    placements.append(sch_instance_passive("LED", "D1", "LED_RED", "LED_0402",
                                           130, 200, "LED_STATUS_A", "GND"))
    placements.append(sch_instance_passive("R", "R1", "330R", "R_0402",
                                           130, 180, "GPIO48_LED", "LED_STATUS_A"))
    placements.append(sch_instance_passive("LED", "D2", "LED_GRN", "LED_0402",
                                           160, 200, "LED_POWER_A", "GND"))
    placements.append(sch_instance_passive("R", "R2", "1k", "R_0402",
                                           160, 180, "3V3", "LED_POWER_A"))

    # USB CC pull-downs
    placements.append(sch_instance_passive("R", "R3", "5.1k", "R_0402",
                                           360, 160, "USB_CC1", "GND"))
    placements.append(sch_instance_passive("R", "R4", "5.1k", "R_0402",
                                           375, 160, "USB_CC2", "GND"))

    # EN pull-up and USB series Rs
    placements.append(sch_instance_passive("R", "R5", "10k", "R_0402",
                                           240, 120, "3V3", "EN"))
    placements.append(sch_instance_passive("R", "R6", "22R", "R_0402",
                                           360, 80, "USB_DP_CP", "USB_DP"))
    placements.append(sch_instance_passive("R", "R7", "22R", "R_0402",
                                           360, 95, "USB_DM_CP", "USB_DM"))

    # Decoupling and bulk caps
    decap_specs = [
        ("C1",  "100nF", 95,  110, "3V3"),
        ("C2",  "100nF", 95,  125, "3V3"),
        ("C3",  "100nF", 95,  140, "3V3"),
        ("C4",  "100nF", 95,  155, "3V3"),
        ("C5",  "100nF", 95,  170, "3V3"),
        ("C6",  "100nF", 95,  185, "3V3"),
        ("C9",  "100nF", 375, 210, "5V"),
        ("C10", "100nF", 385, 210, "5V"),
        ("C11", "100nF", 305, 110, "3V3"),
    ]
    for ref, val, x, y, top_net in decap_specs:
        placements.append(sch_instance_passive("C", ref, val, "C_0402",
                                               x, y, top_net, "GND"))

    # Bulk caps at LDO in/out
    placements.append(sch_instance_passive("C_Bulk", "C7", "10uF", "C_0805",
                                           60, 60, "5V", "GND"))
    placements.append(sch_instance_passive("C_Bulk", "C8", "10uF", "C_0805",
                                           100, 60, "3V3", "GND"))

    # Test points
    placements.append(sch_instance_ic(
        "TestPoint_SMD", "TP1", "TP_3V3", "TP_SMD_1.5mm",
        20, 40, ["3V3"], [], 1, 0,
    ))
    placements.append(sch_instance_ic(
        "TestPoint_SMD", "TP2", "TP_GND", "TP_SMD_1.5mm",
        20, 60, ["GND"], [], 1, 0,
    ))
    placements.append(sch_instance_ic(
        "TestPoint_SMD", "TP3", "TP_RF", "TP_SMD_1.5mm",
        280, 50, ["RF_ANT"], [], 1, 0,
    ))

    # Schematic notes (text blocks)
    notes = []
    notes.append('  (text "ESP32-S3 RF Dev Board v1.2 -- schematic generated by generate_board.py"')
    notes.append('    (at 20 15 0) (effects (font (size 2 2) bold))')
    notes.append(f'    (uuid "{su()}"))')
    notes.append('  (text "Strapping pins at boot:\\n  IO0 must be HIGH  -- SW2 pulls low to enter download mode\\n  IO45 / IO46 -- leave at default (SPI boot + voltage select)"')
    notes.append('    (at 20 240 0) (effects (font (size 1.5 1.5)))')
    notes.append(f'    (uuid "{su()}"))')
    notes.append('  (text "Power tree: USB-C 5V -> USBLC6 (ESD) -> AP2112K-3.3 LDO -> 3V3 rail.\\nNote: AP2112K EN is tied to VIN to keep LDO always on when power is applied."')
    notes.append('    (at 20 255 0) (effects (font (size 1.5 1.5)))')
    notes.append(f'    (uuid "{su()}"))')
    notes.append('  (text "RF: 50-ohm microstrip from ESP32 LNA_IN to chip antenna (ANT1).\\nLoad caps C12/C13 = 12 pF NP0 (CL ~ 8-10 pF; crystal datasheet CL nominal 8 pF)."')
    notes.append('    (at 20 270 0) (effects (font (size 1.5 1.5)))')
    notes.append(f'    (uuid "{su()}"))')

    placements_str = "\n".join(placements)
    notes_str = "\n".join(notes)

    return f'''(kicad_sch
  (version 20250114)
  (generator "eeschema")
  (generator_version "9.0")
  (uuid "{ROOT_SHEET_UUID}")
  (paper "A3")
  (title_block
    (title "ESP32-S3 RF Dev Board")
    (date "{now}")
    (rev "1.2")
    (company "Hugh")
    (comment 1 "ESP32-S3FN8 QFN56 + Johanson 2450AT18A100 chip antenna")
    (comment 2 "4-layer JLC04161H-7628 stackup; 40 MHz crystal; 8MB internal flash")
    (comment 3 "RF trace: 0.6mm 50-ohm microstrip on 0.2mm prepreg Er=4.4")
    (comment 4 "USB-UART: CP2102 | Power: AP2112K-3.3V LDO")
  )
  (lib_symbols
{lib}
  )
{placements_str}
{notes_str}
  (sheet_instances
    (path "/" (page "1"))
  )
  (embedded_fonts no)
)
'''


# =============================================================================
# PROJECT FILE (.kicad_pro)
# =============================================================================

def gen_project():
    """KiCAD 8 project file in JSON format."""
    proj = {
        "board": {
            "design_settings": {
                "defaults": {
                    "board_outline_line_width": 0.05,
                    "copper_line_width": 0.2,
                    "copper_text_italic": False,
                    "copper_text_size_h": 1.5,
                    "copper_text_size_v": 1.5,
                    "copper_text_thickness": 0.3,
                    "copper_text_upright": False,
                    "courtyard_line_width": 0.05,
                    "fab_line_width": 0.1,
                    "fab_text_italic": False,
                    "fab_text_size_h": 1.0,
                    "fab_text_size_v": 1.0,
                    "fab_text_thickness": 0.15,
                    "fab_text_upright": False,
                    "other_line_width": 0.1,
                    "other_text_italic": False,
                    "other_text_size_h": 1.0,
                    "other_text_size_v": 1.0,
                    "other_text_thickness": 0.15,
                    "other_text_upright": False,
                    "pct_board_thickness": 0.0,
                    "silk_line_width": 0.1,
                    "silk_text_italic": False,
                    "silk_text_size_h": 1.0,
                    "silk_text_size_v": 1.0,
                    "silk_text_thickness": 0.15,
                    "silk_text_upright": False,
                },
                "diff_pair_dimensions": [],
                "drc_exclusions": [],
                "meta": {"version": 2},
                "rule_severities": {},
                "rules": {
                    "min_clearance": 0.1,
                    "min_copper_edge_clearance": 0.5,
                    "min_hole_clearance": 0.25,
                    "min_hole_to_hole": 0.25,
                    "min_microvia_diameter": 0.2,
                    "min_microvia_drill": 0.1,
                    "min_resolved_spokes": 2,
                    "min_silk_clearance": 0.0,
                    "min_text_height": 0.5,
                    "min_text_thickness": 0.08,
                    "min_through_hole_diameter": 0.3,
                    "min_track_width": 0.1,
                    "min_via_annular_width": 0.15,
                    "min_via_diameter": 0.4,
                    "use_height_for_length_calcs": True,
                },
                "track_widths": [0.2, 0.5, 1.0],
                "via_dimensions": [{"diameter": 0.8, "drill": 0.4}],
                "zones_allow_external_fillets": False,
            },
            "layer_presets": [],
            "viewports": [],
        },
        "boards": [],
        "cvpcb": {"equivalence_files": []},
        "erc": {
            "erc_exclusions": [],
            "meta": {"version": 0},
            "pin_map": [],
            "rule_severities": {},
        },
        "libraries": {
            "pinned_footprint_libs": [],
            "pinned_symbol_libs": [],
        },
        "meta": {
            "filename": "esp32-s3-rf-board.kicad_pro",
            "version": 1,
        },
        "net_settings": {
            "classes": [
                {
                    "bus_width": 12,
                    "clearance": 0.1,
                    "diff_pair_gap": 0.25,
                    "diff_pair_via_gap": 0.25,
                    "diff_pair_width": 0.2,
                    "line_style": 0,
                    "microvia_diameter": 0.3,
                    "microvia_drill": 0.1,
                    "name": "Default",
                    "pcb_color": "rgba(0, 0, 0, 0.000)",
                    "schematic_color": "rgba(0, 0, 0, 0.000)",
                    "track_width": 0.25,
                    "via_diameter": 0.8,
                    "via_drill": 0.4,
                    "wire_width": 6,
                },
                {
                    "bus_width": 12,
                    "clearance": 0.15,
                    "diff_pair_gap": 0.25,
                    "diff_pair_via_gap": 0.25,
                    "diff_pair_width": 0.2,
                    "line_style": 0,
                    "microvia_diameter": 0.3,
                    "microvia_drill": 0.1,
                    "name": "RF_50OHM",
                    "pcb_color": "rgba(0, 0, 0, 0.000)",
                    "schematic_color": "rgba(0, 0, 0, 0.000)",
                    "track_width": 0.6,
                    "via_diameter": 0.8,
                    "via_drill": 0.4,
                    "wire_width": 6,
                },
                {
                    "bus_width": 12,
                    "clearance": 0.15,
                    "diff_pair_gap": 0.25,
                    "diff_pair_via_gap": 0.25,
                    "diff_pair_width": 0.2,
                    "line_style": 0,
                    "microvia_diameter": 0.3,
                    "microvia_drill": 0.1,
                    "name": "POWER",
                    "pcb_color": "rgba(0, 0, 0, 0.000)",
                    "schematic_color": "rgba(0, 0, 0, 0.000)",
                    "track_width": 0.5,
                    "via_diameter": 0.8,
                    "via_drill": 0.4,
                    "wire_width": 6,
                },
            ],
            "meta": {"version": 3},
            "net_colors": None,
            "netclass_assignments": None,
            "netclass_patterns": [
                {"netclass": "RF_50OHM", "pattern": "RF_ANT"},
                {"netclass": "POWER", "pattern": "3V3"},
                {"netclass": "POWER", "pattern": "5V"},
                {"netclass": "POWER", "pattern": "GND"},
            ],
        },
        "pcbnew": {
            "last_paths": {
                "gencad": "",
                "idf": "",
                "netlist": "",
                "plot": "",
                "pos_files": "",
                "specctra_dsn": "",
                "step": "",
                "svg": "",
                "vrml": "",
            },
            "page_layout_descr_file": "",
        },
        "schematic": {
            "annotate_start_num": 0,
            "bom_fmt_preset": "",
            "bom_fmt_settings": {},
            "bom_presets": [],
            "bus_alias_map": {},
            "connection_grid_size": 50.0,
            "default_bus_thickness": 12.0,
            "default_junction_size": 40.0,
            "default_line_thickness": 6.0,
            "default_net_thickness": 6.0,
            "default_text_size": 50.0,
            "drawing_sheet_file": "",
            "field_names": [],
            "filter_mouse_wheel_events": 0,
            "format_version": 1,
            "intersheets_ref_own_page": False,
            "intersheets_ref_prefix": "",
            "intersheets_ref_short": False,
            "intersheets_ref_show": False,
            "intersheets_ref_suffix": "",
            "junction_size_choice": 3,
            "label_size_ratio": 0.375,
            "meta": {"version": 1},
            "net_format_name": "",
            "ngspice_settings": None,
            "operating_point_overlay_i_precision": 3,
            "operating_point_overlay_i_range": "~A",
            "operating_point_overlay_v_precision": 3,
            "operating_point_overlay_v_range": "~V",
            "page_layout_descr_file": "",
            "pin_symbol_size": 25.0,
            "plot_directory": "",
            "spice_current_sheet_as_root": False,
            "spice_external_command": "spice %I",
            "spice_model_current_sheet_as_root": True,
            "subpart_first_id": 65,
            "subpart_id_separator": 0,
        },
        "sheets": [["a1b2c3d4-e5f6-7890-abcd-ef1234567890", "Root"]],
        "text_variables": {},
    }
    return json.dumps(proj, indent=2)


# =============================================================================
# BOM CSV
# =============================================================================

def gen_bom():
    """
    Bill of Materials in CSV format for JLCPCB SMT assembly.
    Columns: Ref, Value, Footprint, JLCPCB_Part, Qty, Description
    """
    header = "Ref,Value,Footprint,JLCPCB_Part,Qty,Description"
    rows = [
        # Ref,         Value,              Footprint,         JLCPCB,    Qty, Description
        ("U1",         "ESP32-S3FN8",      "QFN-56_7x7mm_P0.4mm",  "C2913204", 1,  "ESP32-S3 WiFi BT SoC QFN56, 8MB internal flash"),
        ("U2",         "AP2112K-3.3TRG1",  "SOT-23-5",        "C51118",   1,  "600mA LDO 3.3V output"),
        ("U3",         "CP2102-GMR",       "QFN-28_5x5mm_P0.5mm",  "C6568",    1,  "USB to UART bridge"),
        ("U4",         "USBLC6-2SC6",      "SOT-23-6",        "C7519",    1,  "USB ESD protection TVS diode array"),
        ("Y1",         "40MHz_NX3225GA",   "XTAL_SMD_3225_4P","C9040",    1,  "40 MHz SMD crystal 3.2x2.5mm 4-pad, 10ppm"),
        ("ANT1",       "2450AT18A100",     "ANT_0402_1x0.5mm","C167687",  1,  "2.4GHz chip antenna 50-ohm"),
        ("J1",         "USB_C_16P",        "USB-C_SMD_16P",   "C165948",  1,  "USB-C receptacle 16-pin"),
        ("J2",         "U.FL_SMD",         "U.FL_SMD",        "C88374",   1,  "u.FL/IPEX RF connector"),
        ("J3",         "1x04 2.54mm",      "PinHeader_1x04_P2.54mm", "C49661",   1,  "4-pin UART header"),
        ("J4",         "1x04 2.54mm",      "PinHeader_1x04_P2.54mm", "C49661",   1,  "4-pin I2C header"),
        ("J5",         "1x06 2.54mm",      "PinHeader_1x06_P2.54mm", "C124378",  1,  "6-pin SPI header"),
        ("SW1",        "SW_TACT_6x6",      "SW_Tactile_6x6mm","C318884",  1,  "Reset tactile switch 6x6mm"),
        ("SW2",        "SW_TACT_6x6",      "SW_Tactile_6x6mm","C318884",  1,  "Boot tactile switch 6x6mm"),
        ("D1",         "LED_RED",          "LED_0402",        "C2286",    1,  "Red LED 0402 status"),
        ("D2",         "LED_GRN",          "LED_0402",        "C2297",    1,  "Green LED 0402 power"),
        ("R1",         "330R",             "R_0402",          "C23197",   1,  "330 ohm resistor 0402 (status LED)"),
        ("R2",         "1k",               "R_0402",          "C11702",   1,  "1k ohm resistor 0402 (power LED)"),
        ("R3",         "5.1k",             "R_0402",          "C25905",   1,  "5.1k ohm 1% 0402 USB CC1 pull-down"),
        ("R4",         "5.1k",             "R_0402",          "C25905",   1,  "5.1k ohm 1% 0402 USB CC2 pull-down"),
        ("R5",         "10k",              "R_0402",          "C25804",   1,  "10k ohm 0402 EN pull-up to 3V3"),
        ("R6",         "22R",              "R_0402",          "C22975",   1,  "22 ohm 0402 USB D+ series resistor"),
        ("R7",         "22R",              "R_0402",          "C22975",   1,  "22 ohm 0402 USB D- series resistor"),
        ("TP1",        "TP_3V3",           "TP_SMD_1.5mm",    "C17228",   1,  "Test point 3.3V rail"),
        ("TP2",        "TP_GND",           "TP_SMD_1.5mm",    "C17228",   1,  "Test point GND"),
        ("TP3",        "TP_RF",            "TP_SMD_1.5mm",    "C17228",   1,  "Test point RF_ANT"),
        ("C1,C2,C3,C4,C5,C6,C9,C10,C11", "100nF", "C_0402", "C1525",   9,  "100nF 0402 decoupling capacitor"),
        ("C7,C8",      "10uF",             "C_0805",          "C17024",   2,  "10uF 0805 bulk capacitor"),
        ("C12,C13",    "12pF",             "C_0402",          "C1652",    2,  "12 pF NP0 0402 crystal load cap"),
    ]

    lines = [header]
    for row in rows:
        ref, val, fp, jlc, qty, desc = row
        lines.append(f'"{ref}","{val}","{fp}","{jlc}",{qty},"{desc}"')

    return "\n".join(lines) + "\n"


# =============================================================================
# ENTRY POINT
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Generate KiCAD 8 project files for the ESP32-S3 RF Dev Board."
    )
    parser.add_argument(
        "--output", "-o",
        default=os.path.dirname(os.path.abspath(__file__)),
        help="Directory to write generated files into (default: script directory)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable debug-level logging",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s  %(message)s",
    )

    output_dir = os.path.abspath(args.output)
    os.makedirs(output_dir, exist_ok=True)

    files = {
        "esp32-s3-rf-board.kicad_pro": gen_project(),
        "esp32-s3-rf-board.kicad_pcb": gen_pcb(),
        "esp32-s3-rf-board.kicad_sch": gen_schematic(),
        "bom.csv":                      gen_bom(),
    }

    log.info("Generating KiCAD 8 project in: %s", output_dir)

    total_bytes = 0
    for filename, content in files.items():
        path = os.path.join(output_dir, filename)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        size = os.path.getsize(path)
        total_bytes += size
        log.info("  %-45s %8s bytes", filename, f"{size:,}")

    log.info("  %-45s %8s bytes total", "", f"{total_bytes:,}")
    log.info("")
    log.info("Board summary:")
    log.info("  Dimensions : %g x %g mm (4-layer)", BOARD_W, BOARD_H)
    log.info("  Stackup    : JLC04161H-7628")
    log.info("               L1 F.Cu   0.035mm  signals/RF")
    log.info("               L2 In1.Cu 0.035mm  solid GND plane")
    log.info("               L3 In2.Cu 0.035mm  3V3 power plane")
    log.info("               L4 B.Cu   0.035mm  signals")
    log.info("  RF trace   : %gmm (50-ohm microstrip, 0.2mm prepreg, Er=4.4)", RF_TRACE_W)
    log.info("  Keepout    : %gmm radius around ANT1 (%g, %g)",
             RF_KEEPOUT_R, POS_ANT[0], POS_ANT[1])
    log.info("  Design rules:")
    log.info("               Min clearance  : 0.1mm")
    log.info("               Min track      : 0.1mm")
    log.info("               Min via drill  : 0.4mm (annular 0.15mm)")
    log.debug("Component placement:")
    log.debug("  U1   ESP32-S3 QFN56               (%g, %g)", *POS_ESP32)
    log.debug("  U2   AP2112K-3.3V SOT-23-5        (%g, %g)", *POS_LDO)
    log.debug("  U3   CP2102 QFN-28                (%g, %g)", *POS_CP2102)
    log.debug("  U4   USBLC6-2SC6 ESD              (%g, %g)", *POS_ESD)
    log.debug("  ANT1 Johanson 2450AT18A100        (%g, %g)", *POS_ANT)
    log.debug("  J1   USB-C 16P                    (%g, %g)", *POS_USBC)
    log.debug("  J2   u.FL connector               (%g, %g)", *POS_UFL)
    log.debug("  TP1  Test point 3V3               (%g, %g)", *POS_TP1)
    log.debug("  TP2  Test point GND               (%g, %g)", *POS_TP2)
    log.debug("  TP3  Test point RF_ANT            (%g, %g)", *POS_TP3)
    log.info("")
    log.info("Done. Open esp32-s3-rf-board.kicad_pro in KiCAD 8 to view.")


if __name__ == "__main__":
    main()
