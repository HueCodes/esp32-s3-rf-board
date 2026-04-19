#!/usr/bin/env python3
"""
ESP32-S3 RF Dev Board - Clean Reroute Script
Regenerates the KiCAD 8 PCB file with new component positions and clean routing.
- RF trace on F.Cu only (0.6mm, 45-degree bends)
- USB D+/D- on F.Cu (0.2mm, short run)
- Power 5V and 3V3 on F.Cu (0.5mm)
- Signal nets use B.Cu for cross-board runs with vias at each end
- No 90-degree corners anywhere
"""

import math
import uuid as uuid_mod

OUTPUT_FILE = "/Users/hugh/Dev/Hardware/esp32-s3-rf-board/esp32-s3-rf-board.kicad_pcb"

BOARD_W = 50.0
BOARD_H = 40.0

POS_ESP32    = (30.0, 20.0)
POS_ANT      = (44.0, 14.0)
POS_UFL      = (44.0, 21.0)
POS_LDO      = (10.0, 32.0)
POS_USBC     = (5.0,  36.0)
POS_CP2102   = (20.0, 33.0)
POS_UART     = (3.0,  10.0)
POS_I2C      = (3.0,  19.0)
POS_SPI      = (3.0,  28.0)
POS_RST_BTN  = (21.0, 3.5)
POS_BOOT_BTN = (30.0, 3.5)
POS_LED_STA  = (20.0, 37.5)
POS_LED_PWR  = (26.0, 37.5)
POS_ESD      = (14.0, 37.0)
POS_TP1      = (11.0, 6.0)
POS_TP2      = (14.0, 6.0)
POS_TP3      = (40.0, 6.0)

RF_TRACE_W   = 0.6
RF_KEEPOUT_R = 5.0

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
}

NET_ID = {v: k for k, v in NETS.items()}

seg_count = 0
via_count = 0


def new_uuid():
    return str(uuid_mod.uuid4())


def fmt(v):
    s = f"{v:.4f}".rstrip('0').rstrip('.')
    return s


def pad_net(name):
    if name and name in NET_ID and NET_ID[name] != 0:
        nid = NET_ID[name]
        return f'(net {nid} "{name}")'
    return ""


def fp_text(kind, text, x, y, layer, size=1.0, thickness=0.15, hide=False):
    hide_str = " hide" if hide else ""
    return (
        f'    (fp_text {kind} "{text}" (at {fmt(x)} {fmt(y)}) (layer "{layer}"){hide_str}\n'
        f'      (effects (font (size {fmt(size)} {fmt(size)}) (thickness {fmt(thickness)}))))'
    )


def fp_courtyard_rect(x1, y1, x2, y2, layer="F.CrtYd"):
    return (
        f'    (fp_line (start {fmt(x1)} {fmt(y1)}) (end {fmt(x2)} {fmt(y1)}) (layer "{layer}") (stroke (width 0.05) (type solid)))\n'
        f'    (fp_line (start {fmt(x2)} {fmt(y1)}) (end {fmt(x2)} {fmt(y2)}) (layer "{layer}") (stroke (width 0.05) (type solid)))\n'
        f'    (fp_line (start {fmt(x2)} {fmt(y2)}) (end {fmt(x1)} {fmt(y2)}) (layer "{layer}") (stroke (width 0.05) (type solid)))\n'
        f'    (fp_line (start {fmt(x1)} {fmt(y2)}) (end {fmt(x1)} {fmt(y1)}) (layer "{layer}") (stroke (width 0.05) (type solid)))'
    )


def fp_fab_rect(x1, y1, x2, y2, layer="F.Fab"):
    return (
        f'    (fp_line (start {fmt(x1)} {fmt(y1)}) (end {fmt(x2)} {fmt(y1)}) (layer "{layer}") (stroke (width 0.1) (type solid)))\n'
        f'    (fp_line (start {fmt(x2)} {fmt(y1)}) (end {fmt(x2)} {fmt(y2)}) (layer "{layer}") (stroke (width 0.1) (type solid)))\n'
        f'    (fp_line (start {fmt(x2)} {fmt(y2)}) (end {fmt(x1)} {fmt(y2)}) (layer "{layer}") (stroke (width 0.1) (type solid)))\n'
        f'    (fp_line (start {fmt(x1)} {fmt(y2)}) (end {fmt(x1)} {fmt(y1)}) (layer "{layer}") (stroke (width 0.1) (type solid)))'
    )


def smd_pad(number, x, y, w, h, net_name="", shape="rect", layer="F.Cu"):
    pn = pad_net(net_name)
    if layer == "F.Cu":
        layers = '(layers "F.Cu" "F.Paste" "F.Mask")'
    else:
        layers = f'(layers "{layer}" "B.Paste" "B.Mask")'
    return (
        f'    (pad "{number}" smd {shape} (at {fmt(x)} {fmt(y)}) (size {fmt(w)} {fmt(h)}) '
        f'{layers}{" " + pn if pn else ""})'
    )


def thru_pad(number, x, y, size, drill, net_name="", shape="circle"):
    pn = pad_net(net_name)
    return (
        f'    (pad "{number}" thru_hole {shape} (at {fmt(x)} {fmt(y)}) (size {fmt(size)} {fmt(size)}) '
        f'(drill {fmt(drill)}) (layers "*.Cu" "*.Mask"){" " + pn if pn else ""})'
    )


def begin_footprint(ref, value, layer, x, y, rotation=0):
    rot_str = f" (rotation {fmt(rotation)})" if rotation != 0 else ""
    u = new_uuid()
    return (
        f'  (footprint "{ref}_fp" (layer "{layer}") (uuid "{u}")\n'
        f'    (at {fmt(x)} {fmt(y)}){rot_str}\n'
        f'    (attr smd)\n'
    )


def begin_fp_thru(ref, value, layer, x, y, rotation=0):
    rot_str = f" (rotation {fmt(rotation)})" if rotation != 0 else ""
    u = new_uuid()
    return (
        f'  (footprint "{ref}_fp" (layer "{layer}") (uuid "{u}")\n'
        f'    (at {fmt(x)} {fmt(y)}){rot_str}\n'
    )


def end_footprint():
    return "  )\n"


def segment(x1, y1, x2, y2, width, layer, net_name):
    global seg_count
    seg_count += 1
    net = NET_ID.get(net_name, 0)
    u = new_uuid()
    return (
        f'  (segment (start {fmt(x1)} {fmt(y1)}) (end {fmt(x2)} {fmt(y2)}) '
        f'(width {fmt(width)}) (layer "{layer}") (net {net}) (tstamp "{u}"))'
    )


def via(x, y, net_name, size=0.8, drill=0.4):
    global via_count
    via_count += 1
    net = NET_ID.get(net_name, 0)
    u = new_uuid()
    return (
        f'  (via (at {fmt(x)} {fmt(y)}) (size {fmt(size)}) (drill {fmt(drill)}) '
        f'(layers "F.Cu" "B.Cu") (net {net}) (tstamp "{u}"))'
    )


def route_45(x1, y1, x2, y2, width, layer, net_name):
    """
    Route from (x1,y1) to (x2,y2) with a single 45-degree bend.
    Returns a list of segment strings.
    Strategy: go diagonally as far as needed on one axis,
    then straight on the remaining axis.
    """
    segs = []
    dx = x2 - x1
    dy = y2 - y1
    adx = abs(dx)
    ady = abs(dy)

    if adx < 1e-6 and ady < 1e-6:
        return segs

    if adx < 1e-6:
        segs.append(segment(x1, y1, x2, y2, width, layer, net_name))
        return segs
    if ady < 1e-6:
        segs.append(segment(x1, y1, x2, y2, width, layer, net_name))
        return segs

    sx = 1.0 if dx > 0 else -1.0
    sy = 1.0 if dy > 0 else -1.0

    if adx >= ady:
        diag = ady
        mx = x1 + sx * diag
        my = y1 + sy * diag
        segs.append(segment(x1, y1, mx, my, width, layer, net_name))
        if abs(mx - x2) > 1e-6:
            segs.append(segment(mx, my, x2, y2, width, layer, net_name))
    else:
        diag = adx
        mx = x1 + sx * diag
        my = y1 + sy * diag
        segs.append(segment(x1, y1, mx, my, width, layer, net_name))
        if abs(my - y2) > 1e-6:
            segs.append(segment(mx, my, x2, y2, width, layer, net_name))

    return segs


def route_via_bcu(x1, y1, x2, y2, net_name, sig_width=0.15, stub_f=0.5):
    """
    Route signal from (x1,y1) on F.Cu via to B.Cu across board then via back to F.Cu at (x2,y2).
    Returns list of strings: via, B.Cu segments, via, short F.Cu stubs.
    """
    lines = []
    v1x = x1 + (0.5 if x2 > x1 else -0.5)
    v1y = y1
    v2x = x2 - (0.5 if x2 > x1 else -0.5)
    v2y = y2

    lines.append(via(v1x, v1y, net_name))
    lines.append(via(v2x, v2y, net_name))

    bcu_segs = route_45(v1x, v1y, v2x, v2y, sig_width, "B.Cu", net_name)
    lines.extend(bcu_segs)

    if abs(x1 - v1x) > 1e-6 or abs(y1 - v1y) > 1e-6:
        lines.append(segment(x1, y1, v1x, v1y, sig_width, "F.Cu", net_name))
    if abs(x2 - v2x) > 1e-6 or abs(y2 - v2y) > 1e-6:
        lines.append(segment(v2x, v2y, x2, y2, sig_width, "F.Cu", net_name))

    return lines


def gen_header():
    return '(kicad_pcb (version 20240108) (generator "pcbnew") (generator_version "8.0")\n'


def gen_general():
    return '''  (general
    (thickness 1.6)
    (legacy_teardrops no)
  )
  (paper "A4")
'''


def gen_layers():
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
    lines = []
    for nid, nname in sorted(NETS.items()):
        if nid == 0:
            lines.append('  (net 0 "")')
        else:
            lines.append(f'  (net {nid} "{nname}")')
    return "\n".join(lines) + "\n"


def gen_board_outline():
    w = BOARD_W
    h = BOARD_H
    edges = [
        (0, 0, w, 0),
        (w, 0, w, h),
        (w, h, 0, h),
        (0, h, 0, 0),
    ]
    lines = []
    for x1, y1, x2, y2 in edges:
        lines.append(
            f'  (gr_line (start {fmt(x1)} {fmt(y1)}) (end {fmt(x2)} {fmt(y2)}) '
            f'(stroke (width 0.05) (type solid)) (layer "Edge.Cuts"))'
        )
    return "\n".join(lines) + "\n"


def gen_silkscreen_labels():
    lines = [
        '  (gr_text "ESP32-S3 RF Dev Board v1.1" (at 25 1.5) (layer "F.SilkS")',
        '    (effects (font (size 1 1) (thickness 0.15))))',
        '  (gr_text "Hugh" (at 25 38.5) (layer "F.SilkS")',
        '    (effects (font (size 0.8 0.8) (thickness 0.12))))',
        '  (gr_text "RF_KEEPOUT" (at 44 20) (layer "Cmts.User")',
        '    (effects (font (size 0.8 0.8) (thickness 0.12))))',
    ]
    return "\n".join(lines) + "\n"


def gen_esp32s3():
    x, y = POS_ESP32
    body = 7.0
    pitch = 0.4
    pw, ph = 0.25, 0.6
    ep_size = 5.7
    half = body / 2.0
    n_side = 14

    pad_nets = {
        1: "GND", 4: "GND", 5: "GND", 6: "GND",
        7: "3V3", 8: "3V3",
        15: "GND",
        16: "SPI_MOSI", 17: "SPI_MISO", 18: "SPI_SCK", 19: "SPI_CS",
        20: "UART_TX", 21: "UART_RX",
        22: "I2C_SDA", 23: "I2C_SCL",
        29: "3V3",
        36: "RF_ANT",
        43: "GND",
        48: "GPIO48_LED",
        51: "EN", 52: "GPIO0",
        53: "GND", 54: "GND", 55: "GND", 56: "GND",
        57: "GND",
    }

    lines = [begin_footprint("U1", "ESP32-S3", "F.Cu", x, y)]
    lines.append(fp_text("reference", "U1", 0, -5, "F.SilkS"))
    lines.append(fp_text("value", "ESP32-S3-WROOM", 0, 5, "F.Fab"))
    lines.append(fp_courtyard_rect(-4.5, -4.5, 4.5, 4.5))
    lines.append(fp_fab_rect(-3.5, -3.5, 3.5, 3.5))
    lines.append(
        '    (fp_circle (center -3.5 3.5) (end -3.2 3.5) (layer "F.Fab") (stroke (width 0.1) (type solid)))'
    )

    start_offset = -((n_side - 1) / 2.0) * pitch

    for i in range(n_side):
        pad_num = i + 1
        px = start_offset + i * pitch
        py = half + ph / 2.0
        net = pad_nets.get(pad_num, "")
        lines.append(smd_pad(pad_num, px, py, pw, ph, net))

    for i in range(n_side):
        pad_num = n_side + i + 1
        py = ((n_side - 1) / 2.0 - i) * pitch
        px = half + ph / 2.0
        net = pad_nets.get(pad_num, "")
        lines.append(smd_pad(pad_num, px, py, ph, pw, net))

    for i in range(n_side):
        pad_num = 2 * n_side + i + 1
        px = ((n_side - 1) / 2.0 - i) * pitch
        py = -(half + ph / 2.0)
        net = pad_nets.get(pad_num, "")
        lines.append(smd_pad(pad_num, px, py, pw, ph, net))

    for i in range(n_side):
        pad_num = 3 * n_side + i + 1
        py = -((n_side - 1) / 2.0 - i) * pitch
        px = -(half + ph / 2.0)
        net = pad_nets.get(pad_num, "")
        lines.append(smd_pad(pad_num, px, py, ph, pw, net))

    lines.append(smd_pad(57, 0, 0, ep_size, ep_size, "GND", shape="rect"))
    lines.append(end_footprint())
    return "\n".join(lines)


def gen_johanson_antenna():
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
    x, y = POS_UFL
    lines = [begin_footprint("J2", "UFL_SMD", "F.Cu", x, y)]
    lines.append(fp_text("reference", "J2", 0, -2.5, "F.SilkS"))
    lines.append(fp_text("value", "u.FL", 0, 2.5, "F.Fab"))
    lines.append(fp_courtyard_rect(-2.5, -2.5, 2.5, 2.5))
    lines.append(fp_fab_rect(-2.0, -2.0, 2.0, 2.0))
    lines.append(smd_pad(1, 0, 0, 0.8, 0.8, "RF_ANT"))
    lines.append(smd_pad(2, -1.5, 0, 0.7, 1.5, "GND"))
    lines.append(smd_pad(3,  1.5, 0, 0.7, 1.5, "GND"))
    lines.append(end_footprint())
    return "\n".join(lines)


def gen_ap2112k():
    x, y = POS_LDO
    lines = [begin_footprint("U2", "AP2112K-3.3", "F.Cu", x, y)]
    lines.append(fp_text("reference", "U2", 0, -2.2, "F.SilkS"))
    lines.append(fp_text("value", "AP2112K-3.3V", 0, 2.2, "F.Fab"))
    lines.append(fp_courtyard_rect(-1.8, -1.6, 1.8, 1.6))
    lines.append(fp_fab_rect(-1.5, -1.4, 1.5, 1.4))
    pad_defs = [
        (1, -0.95, -0.95, "EN"),
        (2, -0.95,  0.0,  "GND"),
        (3, -0.95,  0.95, "5V"),
        (4,  0.95, -0.475,""),
        (5,  0.95,  0.475,"3V3"),
    ]
    for pnum, px, py, net in pad_defs:
        lines.append(smd_pad(pnum, px, py, 0.6, 0.9, net))
    lines.append(end_footprint())
    return "\n".join(lines)


def gen_usbc():
    x, y = POS_USBC
    lines = [begin_footprint("J1", "USB_C_16P", "F.Cu", x, y)]
    lines.append(fp_text("reference", "J1", 0, -5.0, "F.SilkS"))
    lines.append(fp_text("value", "USB-C 16P", 0, 5.0, "F.Fab"))
    lines.append(fp_courtyard_rect(-5.0, -4.5, 5.0, 4.5))
    lines.append(fp_fab_rect(-4.5, -4.0, 4.5, 4.0))
    usbc_pads = [
        (1,  -2.0, -1.5, "GND"),
        (2,  -1.6, -1.5, "5V"),
        (3,  -1.2, -1.5, "USB_DM"),
        (4,  -0.8, -1.5, "USB_DP"),
        (5,  -0.4, -1.5, "USB_CC1"),
        (6,   0.0, -1.5, ""),
        (7,   0.4, -1.5, "5V"),
        (8,   0.8, -1.5, "GND"),
        (9,  -2.0,  1.5, "GND"),
        (10, -1.6,  1.5, "5V"),
        (11, -1.2,  1.5, "USB_DM"),
        (12, -0.8,  1.5, "USB_DP"),
        (13, -0.4,  1.5, "USB_CC2"),
        (14,  0.0,  1.5, ""),
        (15,  0.4,  1.5, "5V"),
        (16,  0.8,  1.5, "GND"),
        (17, -3.5,  0.0, "GND"),
        (18,  3.5,  0.0, "GND"),
    ]
    for pnum, px, py, net in usbc_pads:
        lines.append(smd_pad(pnum, px, py, 0.3, 0.8, net))
    lines.append(end_footprint())
    return "\n".join(lines)


def gen_cp2102():
    x, y = POS_CP2102
    body = 5.0
    pitch = 0.5
    pw, ph = 0.25, 0.7
    half = body / 2.0
    n_side = 7

    cp_nets = {
        1: "GND", 2: "USB_DM", 3: "USB_DP", 4: "3V3",
        8: "GND", 9: "UART_TX", 10: "UART_RX",
        15: "3V3", 16: "GND",
        22: "GND",
        29: "GND",
    }

    lines = [begin_footprint("U3", "CP2102", "F.Cu", x, y)]
    lines.append(fp_text("reference", "U3", 0, -3.5, "F.SilkS"))
    lines.append(fp_text("value", "CP2102-GMR", 0, 3.5, "F.Fab"))
    lines.append(fp_courtyard_rect(-3.5, -3.5, 3.5, 3.5))
    lines.append(fp_fab_rect(-2.5, -2.5, 2.5, 2.5))

    start_offset = -((n_side - 1) / 2.0) * pitch

    for i in range(n_side):
        pad_num = i + 1
        px = start_offset + i * pitch
        py = half + ph / 2.0
        net = cp_nets.get(pad_num, "")
        lines.append(smd_pad(pad_num, px, py, pw, ph, net))

    for i in range(n_side):
        pad_num = n_side + i + 1
        py = ((n_side - 1) / 2.0 - i) * pitch
        px = half + ph / 2.0
        net = cp_nets.get(pad_num, "")
        lines.append(smd_pad(pad_num, px, py, ph, pw, net))

    for i in range(n_side):
        pad_num = 2 * n_side + i + 1
        px = ((n_side - 1) / 2.0 - i) * pitch
        py = -(half + ph / 2.0)
        net = cp_nets.get(pad_num, "")
        lines.append(smd_pad(pad_num, px, py, pw, ph, net))

    for i in range(n_side):
        pad_num = 3 * n_side + i + 1
        py = -((n_side - 1) / 2.0 - i) * pitch
        px = -(half + ph / 2.0)
        net = cp_nets.get(pad_num, "")
        lines.append(smd_pad(pad_num, px, py, ph, pw, net))

    lines.append(smd_pad(29, 0, 0, 3.7, 3.7, "GND"))
    lines.append(end_footprint())
    return "\n".join(lines)


def gen_header_4pin(ref, x, y, nets_list, label):
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
    lines = [begin_footprint(ref, label, "F.Cu", x, y)]
    lines.append(fp_text("reference", ref, 0, -4.5, "F.SilkS"))
    lines.append(fp_text("value", label, 0, 4.5, "F.Fab"))
    lines.append(fp_courtyard_rect(-3.5, -3.5, 3.5, 3.5))
    lines.append(fp_fab_rect(-3.0, -3.0, 3.0, 3.0))
    net1 = "EN" if "RST" in label else "GPIO0"
    lines.append(smd_pad(1, -2.5, -1.5, 1.5, 1.0, "GND"))
    lines.append(smd_pad(2,  2.5, -1.5, 1.5, 1.0, "GND"))
    lines.append(smd_pad(3, -2.5,  1.5, 1.5, 1.0, net1))
    lines.append(smd_pad(4,  2.5,  1.5, 1.5, 1.0, net1))
    lines.append(end_footprint())
    return "\n".join(lines)


def gen_led_0402(ref, x, y, net_a, label):
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
    lines = [begin_footprint(ref, "USBLC6-2SC6", "F.Cu", x, y)]
    lines.append(fp_text("reference", ref, 0, -2.2, "F.SilkS"))
    lines.append(fp_text("value", "USBLC6-2SC6", 0, 2.2, "F.Fab"))
    lines.append(fp_courtyard_rect(-1.8, -1.6, 1.8, 1.6))
    lines.append(fp_fab_rect(-1.5, -1.4, 1.5, 1.4))
    pad_defs = [
        (1, -0.95, -0.95, "USB_DM"),
        (2, -0.95,  0.0,  "GND"),
        (3, -0.95,  0.95, "USB_DP"),
        (4,  0.95,  0.95, "USB_DP"),
        (5,  0.95,  0.0,  "5V"),
        (6,  0.95, -0.95, "USB_DM"),
    ]
    for pnum, px, py, net in pad_defs:
        lines.append(smd_pad(pnum, px, py, 0.4, 0.7, net))
    lines.append(end_footprint())
    return "\n".join(lines)


def gen_test_point(ref, x, y, net_name, label):
    lines = [begin_footprint(ref, label, "F.Cu", x, y)]
    lines.append(fp_text("reference", ref, 0, -1.5, "F.SilkS"))
    lines.append(fp_text("value", label, 0, 1.5, "F.Fab"))
    lines.append(fp_courtyard_rect(-1.2, -1.2, 1.2, 1.2))
    lines.append(smd_pad(1, 0, 0, 1.5, 1.5, net_name, shape="circle"))
    lines.append(end_footprint())
    return "\n".join(lines)


def gen_decoupling_caps():
    lines = []
    cx, cy = POS_ESP32

    decap_positions = [
        ("C1",  cx - 5.0, cy - 5.0, "100nF"),
        ("C2",  cx - 5.0, cy + 5.0, "100nF"),
        ("C3",  cx + 5.0, cy - 5.0, "100nF"),
        ("C4",  cx + 5.0, cy + 5.0, "100nF"),
        ("C5",  cx,       cy - 6.0, "100nF"),
        ("C6",  cx,       cy + 6.0, "100nF"),
    ]
    for ref, x, y, val in decap_positions:
        lines.append(gen_cap_0402(ref, x, y, "3V3", "GND", val))

    lx, ly = POS_LDO
    lines.append(gen_cap_0805("C7", lx + 2.5, ly, "5V", "GND", "10uF"))
    lines.append(gen_cap_0805("C8", lx - 2.5, ly, "3V3", "GND", "10uF"))
    lines.append(gen_cap_0402("C9",  POS_USBC[0] + 2.0, POS_USBC[1] - 3.0, "5V",  "GND", "100nF"))
    lines.append(gen_cap_0402("C10", POS_USBC[0] + 2.0, POS_USBC[1] - 4.5, "5V",  "GND", "100nF"))
    lines.append(gen_cap_0402("C11", POS_CP2102[0] + 4.0, POS_CP2102[1],   "3V3", "GND", "100nF"))

    return "\n".join(lines)


def gen_routing():
    """
    Generate all routing segments and vias.
    Returns a list of strings.
    """
    lines = []

    def add(lst):
        lines.extend(lst)

    def seg(x1, y1, x2, y2, w, layer, net):
        lines.append(segment(x1, y1, x2, y2, w, layer, net))

    def v(x, y, net):
        lines.append(via(x, y, net))

    SIG_W  = 0.15
    PWR_W  = 0.5
    USB_W  = 0.2

    # -----------------------------------------------------------------------
    # ESP32-S3 pad world-coordinate helpers
    # Footprint at POS_ESP32 = (30, 20)
    # Right side (pads 15-28): px = 30 + 3.5 + 0.3 = 33.8, py = 20 + (6.5-i)*0.4 (i=0..13, pad15+i)
    # Left side  (pads 43-56): px = 30 - 3.5 - 0.3 = 26.2, py = 20 - (6.5-i)*0.4 (i=0..13, pad43+i)
    # Top side   (pads 29-42): py = 20 - 3.5 - 0.3 = 16.2, px = 30 + (6.5-i)*0.4 (i=0..13, pad29+i)
    # Bottom side(pads 1-14):  py = 20 + 3.5 + 0.3 = 23.8, px = 30 + (-6.5+i)*0.4 (i=0..13, pad1+i)
    # -----------------------------------------------------------------------
    ex, ey = POS_ESP32

    # Right side: pad = 15 + i, i=0..13
    def esp_right(pad_num):
        i = pad_num - 15
        return (ex + 3.5 + 0.3, ey + (6.5 - i) * 0.4)

    # Left side: pad = 43 + i, i=0..13
    def esp_left(pad_num):
        i = pad_num - 43
        return (ex - 3.5 - 0.3, ey - (6.5 - i) * 0.4)

    # Top side: pad = 29 + i, i=0..13
    def esp_top(pad_num):
        i = pad_num - 29
        return (ex + (6.5 - i) * 0.4, ey - 3.5 - 0.3)

    # Bottom side: pad = 1 + i, i=0..13
    def esp_bot(pad_num):
        i = pad_num - 1
        return (ex + (-6.5 + i) * 0.4, ey + 3.5 + 0.3)

    # -----------------------------------------------------------------------
    # RF TRACE: pad 36 (top side, i=7) to ANT1 pad 1 on F.Cu, 0.6mm
    # -----------------------------------------------------------------------
    rf_start = esp_top(36)   # (29.8, 16.2)
    rf_end   = (POS_ANT[0] - 0.5, POS_ANT[1])  # (43.5, 14.0)

    add(route_45(rf_start[0], rf_start[1], rf_end[0], rf_end[1], RF_TRACE_W, "F.Cu", "RF_ANT"))

    # GND stitching vias alongside RF trace
    rf_dx = rf_end[0] - rf_start[0]
    rf_dy = rf_end[1] - rf_start[1]
    rf_len = math.sqrt(rf_dx**2 + rf_dy**2)
    via_spacing = 6.0
    via_offset  = 1.2
    n_rf_vias = max(1, int(rf_len / via_spacing))
    ux = rf_dx / rf_len
    uy = rf_dy / rf_len
    px_perp = -uy
    py_perp =  ux
    for k in range(n_rf_vias):
        t = (k + 0.5) / n_rf_vias
        cx = rf_start[0] + t * rf_dx
        cy = rf_start[1] + t * rf_dy
        v(cx + px_perp * via_offset, cy + py_perp * via_offset, "GND")
        v(cx - px_perp * via_offset, cy - py_perp * via_offset, "GND")

    # -----------------------------------------------------------------------
    # USB D+/D- : J1 pads to CP2102 pads, short runs on F.Cu 0.2mm
    # J1 at (5, 36): pad4 = D+ at rel(-0.8, -1.5), pad3 = D- at rel(-1.2, -1.5)
    # CP2102 at (20, 33): pad3 = D+ at rel(start_offset+2*0.5, half+ph/2)
    #   CP2102 bottom: start_offset = -1.5, pad3 (i=2): px=-1.5+1.0=-0.5, py=2.5+0.35=2.85
    #   pad2 (i=1): px=-1.5+0.5=-1.0, py=2.85
    # -----------------------------------------------------------------------
    j1x, j1y = POS_USBC
    cpx, cpy = POS_CP2102
    cp_ph = 0.7
    cp_half = 2.5

    cp_bot_py = cpy + cp_half + cp_ph / 2.0   # 35.85
    cp_bot_start = -1.5

    j1_dp_x = j1x + (-0.8)
    j1_dp_y = j1y + (-1.5)
    j1_dm_x = j1x + (-1.2)
    j1_dm_y = j1y + (-1.5)

    cp_dp_x = cpx + (cp_bot_start + 2 * 0.5)  # pad3, i=2
    cp_dp_y = cp_bot_py
    cp_dm_x = cpx + (cp_bot_start + 1 * 0.5)  # pad2, i=1
    cp_dm_y = cp_bot_py

    # USB_CC1: J1 pad5 -> R3 pad1
    # R3 at (11.5, 38), pad1 at rel(-0.5, 0) = (11, 38)
    j1_cc1_x = j1x + (-0.4)
    j1_cc1_y = j1y + (-1.5)
    r3_x = 11.5 - 0.5
    r3_y = 38.0
    add(route_45(j1_cc1_x, j1_cc1_y, r3_x, r3_y, SIG_W, "F.Cu", "USB_CC1"))

    # USB_CC2: J1 pad13 -> R4 pad1
    # R4 at (11.5, 36), pad1 at rel(-0.5, 0) = (11, 36)
    j1_cc2_x = j1x + (-0.4)
    j1_cc2_y = j1y + (1.5)
    r4_x = 11.5 - 0.5
    r4_y = 36.0
    add(route_45(j1_cc2_x, j1_cc2_y, r4_x, r4_y, SIG_W, "F.Cu", "USB_CC2"))

    # USB ESD: Route USB D+/D- through U4
    # U4 at POS_ESD = (14, 37)
    esd_x, esd_y = POS_ESD
    # J1 D+ to U4 pad3 at (esd_x-0.95, esd_y+0.95)
    add(route_45(j1_dp_x, j1_dp_y, esd_x - 0.95, esd_y + 0.95, USB_W, "F.Cu", "USB_DP"))
    # U4 pad4 to CP2102 D+ at (esd_x+0.95, esd_y+0.95)
    add(route_45(esd_x + 0.95, esd_y + 0.95, cp_dp_x, cp_dp_y, USB_W, "F.Cu", "USB_DP"))
    # J1 D- to U4 pad1 at (esd_x-0.95, esd_y-0.95)
    add(route_45(j1_dm_x, j1_dm_y, esd_x - 0.95, esd_y - 0.95, USB_W, "F.Cu", "USB_DM"))
    # U4 pad6 to CP2102 D- at (esd_x+0.95, esd_y-0.95)
    add(route_45(esd_x + 0.95, esd_y - 0.95, cp_dm_x, cp_dm_y, USB_W, "F.Cu", "USB_DM"))

    # -----------------------------------------------------------------------
    # 5V POWER: J1 VBUS pads to LDO pin3 (VIN) on F.Cu 0.5mm
    # J1 pad2 = 5V at rel(-1.6, -1.5), pad7 = 5V at rel(0.4, -1.5)
    # LDO at (10, 32): pin3 (VIN) at rel(-0.95, 0.95) -> world (9.05, 32.95)
    # -----------------------------------------------------------------------
    ldox, ldoy = POS_LDO
    ldo_vin_x = ldox + (-0.95)
    ldo_vin_y = ldoy + 0.95

    j1_5v_x = j1x + (-1.6)
    j1_5v_y = j1y + (-1.5)

    add(route_45(j1_5v_x, j1_5v_y, ldo_vin_x, ldo_vin_y, PWR_W, "F.Cu", "5V"))

    # -----------------------------------------------------------------------
    # 3V3 POWER DISTRIBUTION: LDO pin5 (VOUT) to ESP32-S3 pads 7,8,29 + CP2102 pad4 + headers + LEDs
    # LDO pin5 at rel(0.95, 0.475) -> world (10.95, 32.475)
    # ESP32-S3 pad7 (bottom, i=6): (30+(-6.5+6)*0.4, 23.8) = (29.8, 23.8)
    # ESP32-S3 pad8 (bottom, i=7): (30+(-6.5+7)*0.4, 23.8) = (30.2, 23.8)
    # ESP32-S3 pad29 (top, i=0): (30+(6.5-0)*0.4, 16.2) = (32.6, 16.2)
    # CP2102 pad4 (bottom, i=3): cpx+(-1.5+1.5) = cpx+0 = 20, y=35.85
    # -----------------------------------------------------------------------
    ldo_vout_x = ldox + 0.95
    ldo_vout_y = ldoy + 0.475

    esp_3v3_b7  = esp_bot(7)    # (29.8, 23.8)
    esp_3v3_b8  = esp_bot(8)    # (30.2, 23.8)
    esp_3v3_t29 = esp_top(29)   # (32.6, 16.2)
    cp_3v3_x    = cpx + (cp_bot_start + 3 * 0.5)   # pad4, i=3 -> -1.5+1.5=0
    cp_3v3_y    = cp_bot_py

    # Main 3V3 bus: LDO out to a junction point near center bottom of ESP32
    bus_x = esp_3v3_b7[0]
    bus_y = ldoy

    add(route_45(ldo_vout_x, ldo_vout_y, bus_x, bus_y, PWR_W, "F.Cu", "3V3"))
    add(route_45(bus_x, bus_y, esp_3v3_b7[0], esp_3v3_b7[1], PWR_W, "F.Cu", "3V3"))
    add(route_45(esp_3v3_b7[0], esp_3v3_b7[1], esp_3v3_b8[0], esp_3v3_b8[1], PWR_W, "F.Cu", "3V3"))
    add(route_45(esp_3v3_t29[0], esp_3v3_t29[1], bus_x, bus_y, PWR_W, "F.Cu", "3V3"))
    add(route_45(cp_3v3_x, cp_3v3_y, ldo_vout_x, ldo_vout_y, PWR_W, "F.Cu", "3V3"))

    # 3V3 to headers: J3 pin2 (3V3), J4 pin2, J5 pin2
    # J3 pin2 at (3, 10 - 1.27) = (3, 8.73)
    # J4 pin2 at (3, 19 - 1.27) = (3, 17.73)
    # J5 pin2 at (3, 28 - 3.81) = (3, 24.19)
    j3x, j3y = POS_UART
    j4x, j4y = POS_I2C
    j5x, j5y = POS_SPI

    j3_3v3 = (j3x, j3y - 1.27)
    j4_3v3 = (j4x, j4y - 1.27)
    j5_3v3 = (j5x, j5y - 3.81)

    # Route 3V3 from LDO out down the left side to all headers
    left_bus_x = 1.5
    add(route_45(ldo_vout_x, ldo_vout_y, left_bus_x, ldo_vout_y, PWR_W, "F.Cu", "3V3"))
    add(route_45(left_bus_x, ldo_vout_y, left_bus_x, j5_3v3[1], PWR_W, "F.Cu", "3V3"))
    add(route_45(left_bus_x, j5_3v3[1], j5_3v3[0], j5_3v3[1], PWR_W, "F.Cu", "3V3"))
    add(route_45(left_bus_x, j4_3v3[1], j4_3v3[0], j4_3v3[1], PWR_W, "F.Cu", "3V3"))
    add(route_45(left_bus_x, j3_3v3[1], j3_3v3[0], j3_3v3[1], PWR_W, "F.Cu", "3V3"))

    # Connect the left bus between the junction points
    add(route_45(left_bus_x, j5_3v3[1], left_bus_x, j4_3v3[1], PWR_W, "F.Cu", "3V3"))
    add(route_45(left_bus_x, j4_3v3[1], left_bus_x, j3_3v3[1], PWR_W, "F.Cu", "3V3"))

    # 3V3 to R2 (power LED resistor) at (POS_LED_PWR[0]+1.5, POS_LED_PWR[1]) = (27.5, 37.5)
    r2_in_x = POS_LED_PWR[0] + 1.5
    r2_in_y = POS_LED_PWR[1]
    add(route_45(ldo_vout_x, ldo_vout_y, r2_in_x, r2_in_y, PWR_W, "F.Cu", "3V3"))

    # -----------------------------------------------------------------------
    # UART_TX (net 7): ESP32 pad20 -> via -> B.Cu -> via -> CP2102 pad9 AND J3 pin3
    # ESP32 pad20 right side: i=20-15=5, py=20+(6.5-5)*0.4=20.6, px=33.8
    # CP2102 pad9: right side i=9-8=1, py=33+(3-1)*0.5=34.0, px=20+2.5+0.35=22.85
    # J3 pin3 (UART_TX): (3, 10+1.27) = (3, 11.27)
    # -----------------------------------------------------------------------
    esp_tx = esp_right(20)    # (33.8, 20.6)
    cp_tx_x = cpx + 2.5 + 0.35   # 22.85
    cp_tx_y = cpy + (3 - 1) * 0.5  # 34.0
    j3_tx   = (j3x, j3y + 1.27)   # (3, 11.27)

    add(route_via_bcu(esp_tx[0], esp_tx[1], cp_tx_x, cp_tx_y, "UART_TX", SIG_W))
    add(route_via_bcu(esp_tx[0], esp_tx[1], j3_tx[0], j3_tx[1], "UART_TX", SIG_W))

    # -----------------------------------------------------------------------
    # UART_RX (net 8): ESP32 pad21 -> via -> B.Cu -> via -> CP2102 pad10 AND J3 pin4
    # ESP32 pad21: i=21-15=6, py=20+(6.5-6)*0.4=20.2, px=33.8
    # CP2102 pad10: right side i=10-8=2, py=33+(3-2)*0.5=33.5, px=22.85
    # J3 pin4 (UART_RX): (3, 10+3.81) = (3, 13.81)
    # -----------------------------------------------------------------------
    esp_rx = esp_right(21)
    cp_rx_x = cpx + 2.5 + 0.35
    cp_rx_y = cpy + (3 - 2) * 0.5
    j3_rx   = (j3x, j3y + 3.81)

    add(route_via_bcu(esp_rx[0], esp_rx[1], cp_rx_x, cp_rx_y, "UART_RX", SIG_W))
    add(route_via_bcu(esp_rx[0], esp_rx[1], j3_rx[0], j3_rx[1], "UART_RX", SIG_W))

    # -----------------------------------------------------------------------
    # I2C_SDA (net 9): ESP32 pad22 -> B.Cu -> J4 pin3
    # ESP32 pad22: i=22-15=7, py=20+(6.5-7)*0.4=19.8, px=33.8
    # J4 pin3 (I2C_SDA): (3, 19+1.27) = (3, 20.27)
    # -----------------------------------------------------------------------
    esp_sda = esp_right(22)
    j4_sda  = (j4x, j4y + 1.27)
    add(route_via_bcu(esp_sda[0], esp_sda[1], j4_sda[0], j4_sda[1], "I2C_SDA", SIG_W))

    # -----------------------------------------------------------------------
    # I2C_SCL (net 10): ESP32 pad23 -> B.Cu -> J4 pin4
    # ESP32 pad23: i=23-15=8, py=20+(6.5-8)*0.4=19.4, px=33.8
    # J4 pin4 (I2C_SCL): (3, 19+3.81) = (3, 22.81)
    # -----------------------------------------------------------------------
    esp_scl = esp_right(23)
    j4_scl  = (j4x, j4y + 3.81)
    add(route_via_bcu(esp_scl[0], esp_scl[1], j4_scl[0], j4_scl[1], "I2C_SCL", SIG_W))

    # -----------------------------------------------------------------------
    # SPI_MOSI (net 11): ESP32 pad16 -> B.Cu -> J5 pin3
    # ESP32 pad16: i=16-15=1, py=20+(6.5-1)*0.4=22.2, px=33.8
    # J5 pin3 (SPI_MOSI): (3, 28-2.54) = (3, 26.73) ... actually (3, 28+(-2)*1.27) = (3,25.46)?
    # J5 6-pin: py = -(5/2)*2.54 + i*2.54; i=0..5
    # pin3 = i=2: py = -6.35 + 5.08 = -1.27 -> world y = 28-1.27 = 26.73
    # -----------------------------------------------------------------------
    esp_mosi = esp_right(16)
    j5_mosi  = (j5x, j5y - 1.27)
    add(route_via_bcu(esp_mosi[0], esp_mosi[1], j5_mosi[0], j5_mosi[1], "SPI_MOSI", SIG_W))

    # -----------------------------------------------------------------------
    # SPI_MISO (net 12): ESP32 pad17 -> B.Cu -> J5 pin4
    # ESP32 pad17: i=2, py=20+(6.5-2)*0.4=21.8, px=33.8
    # J5 pin4 = i=3: py = -6.35+7.62 = 1.27 -> world y = 29.27
    # -----------------------------------------------------------------------
    esp_miso = esp_right(17)
    j5_miso  = (j5x, j5y + 1.27)
    add(route_via_bcu(esp_miso[0], esp_miso[1], j5_miso[0], j5_miso[1], "SPI_MISO", SIG_W))

    # -----------------------------------------------------------------------
    # SPI_SCK (net 13): ESP32 pad18 -> B.Cu -> J5 pin5
    # ESP32 pad18: i=3, py=20+(6.5-3)*0.4=21.4, px=33.8
    # J5 pin5 = i=4: py = -6.35+10.16 = 3.81 -> world y = 31.81
    # -----------------------------------------------------------------------
    esp_sck = esp_right(18)
    j5_sck  = (j5x, j5y + 3.81)
    add(route_via_bcu(esp_sck[0], esp_sck[1], j5_sck[0], j5_sck[1], "SPI_SCK", SIG_W))

    # -----------------------------------------------------------------------
    # SPI_CS (net 14): ESP32 pad19 -> B.Cu -> J5 pin6
    # ESP32 pad19: i=4, py=20+(6.5-4)*0.4=21.0, px=33.8
    # J5 pin6 = i=5: py = -6.35+12.7 = 6.35 -> world y = 34.35
    # -----------------------------------------------------------------------
    esp_cs = esp_right(19)
    j5_cs  = (j5x, j5y + 6.35)
    add(route_via_bcu(esp_cs[0], esp_cs[1], j5_cs[0], j5_cs[1], "SPI_CS", SIG_W))

    # -----------------------------------------------------------------------
    # GPIO48_LED (net 15): ESP32 pad48 -> F.Cu -> R1 pad1 (input)
    # pad48: left side i=48-43=5, py=20-(6.5-5)*0.4=19.4, px=26.2
    # R1 at (POS_LED_STA[0]+1.5, POS_LED_STA[1]) = (21.5, 37.5), pad1 at rel(-0.5, 0) = (21, 37.5)
    # -----------------------------------------------------------------------
    esp_led = esp_left(48)   # (26.2, 19.4) -- wait, left side formula: py = 20 - (6.5-i)*0.4
    # Actually: esp_left(48): i=48-43=5, return (26.2, 20 - (6.5-5)*0.4) = (26.2, 19.4)
    r1_in_x = POS_LED_STA[0] + 1.5 - 0.5  # 21.0
    r1_in_y = POS_LED_STA[1]               # 37.5
    add(route_45(esp_led[0], esp_led[1], r1_in_x, r1_in_y, SIG_W, "F.Cu", "GPIO48_LED"))

    # -----------------------------------------------------------------------
    # LED_STATUS_A (net 18): R1 pad2 -> D1 pad A
    # R1 pad2 at (21.5+0.5, 37.5) = (22.0, 37.5)
    # D1 at (POS_LED_STA[0]-1.5, POS_LED_STA[1]) = (18.5, 37.5), pad A at rel(-0.5,0) = (18.0, 37.5)
    # -----------------------------------------------------------------------
    r1_out_x = POS_LED_STA[0] + 1.5 + 0.5  # 22.0
    r1_out_y = POS_LED_STA[1]
    d1_a_x   = POS_LED_STA[0] - 1.5 - 0.5  # 18.0
    d1_a_y   = POS_LED_STA[1]
    seg(r1_out_x, r1_out_y, d1_a_x, d1_a_y, SIG_W, "F.Cu", "LED_STATUS_A")

    # LED_POWER_A (net 19): R2 pad2 -> D2 pad A
    # R2 at (27.5, 37.5), pad2 at (28.0, 37.5)
    # D2 at (24.5, 37.5), pad A at (24.0, 37.5)
    r2_out_x = POS_LED_PWR[0] + 1.5 + 0.5   # 28.0
    r2_out_y = POS_LED_PWR[1]
    d2_a_x   = POS_LED_PWR[0] - 1.5 - 0.5   # 24.0
    d2_a_y   = POS_LED_PWR[1]
    seg(r2_out_x, r2_out_y, d2_a_x, d2_a_y, SIG_W, "F.Cu", "LED_POWER_A")

    # -----------------------------------------------------------------------
    # EN (net 16): ESP32 pad51 -> SW1 (RST button at 21, 3.5)
    # pad51: left side i=51-43=8, py=20-(6.5-8)*0.4=20.6, px=26.2
    # SW1 pad3 at rel(-2.5, 1.5) -> world (18.5, 5.0)
    # -----------------------------------------------------------------------
    esp_en = esp_left(51)     # (26.2, 20.6)
    sw1_x  = POS_RST_BTN[0] - 2.5   # 18.5
    sw1_y  = POS_RST_BTN[1] + 1.5   # 5.0
    add(route_45(esp_en[0], esp_en[1], sw1_x, sw1_y, SIG_W, "F.Cu", "EN"))

    # -----------------------------------------------------------------------
    # GPIO0 (net 17): ESP32 pad52 -> SW2 (BOOT button at 30, 3.5)
    # pad52: left side i=52-43=9, py=20-(6.5-9)*0.4=21.0, px=26.2
    # SW2 pad3 at rel(-2.5, 1.5) -> world (27.5, 5.0)
    # -----------------------------------------------------------------------
    esp_gpio0 = esp_left(52)   # (26.2, 21.0)
    sw2_x     = POS_BOOT_BTN[0] - 2.5   # 27.5
    sw2_y     = POS_BOOT_BTN[1] + 1.5   # 5.0
    add(route_45(esp_gpio0[0], esp_gpio0[1], sw2_x, sw2_y, SIG_W, "F.Cu", "GPIO0"))

    # -----------------------------------------------------------------------
    # GND: short stubs to connect J3/J4/J5 pin1 GND pads
    # J3 pin1 (GND): (3, 10-3.81) = (3, 6.19)
    # J4 pin1 (GND): (3, 19-3.81) = (3, 15.19)
    # J5 pin1 (GND): (3, 28-6.35) = (3, 21.65)
    # Connect them down the left edge to a GND bus (GND plane handles most of it)
    # -----------------------------------------------------------------------
    gnd_bus_x = 1.2
    j3_gnd = (j3x, j3y - 3.81)
    j4_gnd = (j4x, j4y - 3.81)
    j5_gnd = (j5x, j5y - 6.35)

    seg(j3_gnd[0], j3_gnd[1], gnd_bus_x, j3_gnd[1], SIG_W, "F.Cu", "GND")
    seg(j4_gnd[0], j4_gnd[1], gnd_bus_x, j4_gnd[1], SIG_W, "F.Cu", "GND")
    seg(j5_gnd[0], j5_gnd[1], gnd_bus_x, j5_gnd[1], SIG_W, "F.Cu", "GND")
    seg(gnd_bus_x, j3_gnd[1], gnd_bus_x, j5_gnd[1], SIG_W, "F.Cu", "GND")

    return lines


def gen_zones():
    gnd_net = NET_ID["GND"]
    v33_net = NET_ID["3V3"]
    lines = []

    gnd_uuid = new_uuid()
    lines.append(f'''  (zone (net {gnd_net}) (net_name "GND") (layer "In1.Cu") (uuid "{gnd_uuid}")
    (hatch edge 0.508)
    (connect_pads (clearance 0.1))
    (min_thickness 0.25)
    (filled_areas_thickness no)
    (placement (enabled no) (sheetname ""))
    (fill (thermal_gap 0.508) (thermal_bridge_width 0.508))
    (polygon
      (pts
        (xy 0 0) (xy {fmt(BOARD_W)} 0) (xy {fmt(BOARD_W)} {fmt(BOARD_H)}) (xy 0 {fmt(BOARD_H)})
      )
    )
  )''')

    v33_uuid = new_uuid()
    lines.append(f'''  (zone (net {v33_net}) (net_name "3V3") (layer "In2.Cu") (uuid "{v33_uuid}")
    (hatch edge 0.508)
    (connect_pads (clearance 0.2))
    (min_thickness 0.25)
    (filled_areas_thickness no)
    (placement (enabled no) (sheetname ""))
    (fill (thermal_gap 0.508) (thermal_bridge_width 0.508))
    (polygon
      (pts
        (xy 0 5) (xy 38 5) (xy 38 {fmt(BOARD_H-5)}) (xy 0 {fmt(BOARD_H-5)})
      )
    )
  )''')

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

    for layer_name, zone_name in [("F.Cu", "RF_KEEPOUT_F"), ("B.Cu", "RF_KEEPOUT_B"), ("In1.Cu", "RF_KEEPOUT_GND")]:
        zu = new_uuid()
        lines.append(f'''  (zone (net 0) (net_name "") (layer "{layer_name}") (uuid "{zu}") (name "{zone_name}")
    (hatch edge 0.508)
    (placement (enabled no) (sheetname ""))
    (keepout (tracks not_allowed) (vias not_allowed) (pads not_allowed) (copperpour not_allowed) (footprints allowed))
    (polygon
      (pts
        {pts_str}
      )
    )
  )''')

    return "\n".join(lines)


def gen_pcb():
    parts = []
    parts.append(gen_header())
    parts.append(gen_general())
    parts.append(gen_layers())
    parts.append(gen_setup())
    parts.append(gen_nets())
    parts.append(gen_board_outline())
    parts.append(gen_silkscreen_labels())

    parts.append(gen_esp32s3())
    parts.append(gen_johanson_antenna())
    parts.append(gen_ufl_connector())
    parts.append(gen_ap2112k())
    parts.append(gen_usbc())
    parts.append(gen_cp2102())

    parts.append(gen_header_4pin("J3", POS_UART[0], POS_UART[1],
                                 ["GND", "3V3", "UART_TX", "UART_RX"], "UART_4P"))
    parts.append(gen_header_4pin("J4", POS_I2C[0], POS_I2C[1],
                                 ["GND", "3V3", "I2C_SDA", "I2C_SCL"], "I2C_4P"))
    parts.append(gen_header_6pin("J5", POS_SPI[0], POS_SPI[1],
                                 ["GND", "3V3", "SPI_MOSI", "SPI_MISO", "SPI_SCK", "SPI_CS"], "SPI_6P"))

    parts.append(gen_tactile_button("SW1", POS_RST_BTN[0],  POS_RST_BTN[1],  "RST_BTN"))
    parts.append(gen_tactile_button("SW2", POS_BOOT_BTN[0], POS_BOOT_BTN[1], "BOOT_BTN"))

    parts.append(gen_led_0402("D1", POS_LED_STA[0] - 1.5, POS_LED_STA[1], "LED_STATUS_A", "LED_RED"))
    parts.append(gen_led_0402("D2", POS_LED_PWR[0] - 1.5, POS_LED_PWR[1], "LED_POWER_A",  "LED_GRN"))
    parts.append(gen_resistor_0402("R1", POS_LED_STA[0] + 1.5, POS_LED_STA[1],
                                   "GPIO48_LED", "LED_STATUS_A", "330R", "330R"))
    parts.append(gen_resistor_0402("R2", POS_LED_PWR[0] + 1.5, POS_LED_PWR[1],
                                   "3V3", "LED_POWER_A", "1k", "1k"))

    # CC pull-down resistors
    parts.append(gen_resistor_0402("R3", 11.5, 38.0,
                                   "USB_CC1", "GND", "5.1k", "5.1k"))
    parts.append(gen_resistor_0402("R4", 11.5, 36.0,
                                   "USB_CC2", "GND", "5.1k", "5.1k"))
    # ESD protection
    parts.append(gen_esd_usblc6("U4", POS_ESD[0], POS_ESD[1]))
    # Test points
    parts.append(gen_test_point("TP1", POS_TP1[0], POS_TP1[1], "3V3", "TP_3V3"))
    parts.append(gen_test_point("TP2", POS_TP2[0], POS_TP2[1], "GND", "TP_GND"))
    parts.append(gen_test_point("TP3", POS_TP3[0], POS_TP3[1], "RF_ANT", "TP_RF"))

    parts.append(gen_decoupling_caps())

    routing_lines = gen_routing()
    parts.append("\n".join(routing_lines))

    parts.append(gen_zones())
    parts.append(")\n")

    return "\n".join(parts)


if __name__ == "__main__":
    content = gen_pcb()

    if ";" in content:
        print("WARNING: semicolons found in output - scanning for offending lines:")
        for i, line in enumerate(content.splitlines()):
            if ";" in line:
                print(f"  Line {i+1}: {line!r}")

    paren_open  = content.count("(")
    paren_close = content.count(")")
    if paren_open != paren_close:
        print(f"WARNING: unbalanced parentheses: {paren_open} open, {paren_close} close")
    else:
        print(f"Parentheses balanced: {paren_open} pairs")

    with open(OUTPUT_FILE, "w") as f:
        f.write(content)

    import os
    file_size = os.path.getsize(OUTPUT_FILE)
    print(f"Segments generated : {seg_count}")
    print(f"Vias generated     : {via_count}")
    print(f"File size          : {file_size} bytes")
    print(f"Output written to  : {OUTPUT_FILE}")
    print("Done")
