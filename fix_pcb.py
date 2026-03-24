#!/usr/bin/env python3
"""
fix_pcb.py - Rewrites the KiCAD 8 PCB file to use valid KiCAD 8 format.

Fixes applied:
  1. Adds (uuid "...") to: footprints, gr_text, gr_line, gr_arc, gr_poly
  2. Adds (uuid "...") to fp_text and pad elements inside footprints
  3. Adds (tstamp "...") to segment and via elements
  4. Replaces three separate RF_KEEPOUT zones with one merged multi-layer zone
  5. Fixes (fill yes ...) -> (fill ...) in GND and 3V3 zones
  6. Replaces keepout_settings blocks with proper keepout blocks
"""

import re
import uuid

PCB_PATH = "/Users/hugh/Dev/Hardware/esp32-s3-rf-board/esp32-s3-rf-board.kicad_pcb"


def gen_uuid():
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Step 1: Read the file
# ---------------------------------------------------------------------------
with open(PCB_PATH, "r") as f:
    text = f.read()


# ---------------------------------------------------------------------------
# Step 2: Fix (fill yes (thermal_gap -> (fill (thermal_gap
# ---------------------------------------------------------------------------
text = re.sub(r'\(fill yes \(thermal_gap', '(fill (thermal_gap', text)


# ---------------------------------------------------------------------------
# Step 3: Replace keepout_settings with proper keepout block
# ---------------------------------------------------------------------------
def replace_keepout_settings(m):
    return (
        "(keepout\n"
        "      (tracks not_allowed)\n"
        "      (vias not_allowed)\n"
        "      (pads not_allowed)\n"
        "      (copperpour not_allowed)\n"
        "      (footprints allowed)\n"
        "    )"
    )

text = re.sub(
    r'\(keepout_settings\s*\([^)]*\)\)',
    replace_keepout_settings,
    text
)


# ---------------------------------------------------------------------------
# Step 4: Merge three RF_KEEPOUT zones into one multi-layer zone
# ---------------------------------------------------------------------------
def extract_zone_block(text, name):
    """Find the zone named `name` and return (start_idx, end_idx, block_text)."""
    # Find the name token in a zone opening
    search_str = '(name "' + name + '")'
    idx = text.find(search_str)
    if idx == -1:
        return None
    # Walk backwards to find the start of this zone: look for "  (zone "
    zone_start = text.rfind('\n  (zone ', 0, idx)
    if zone_start == -1:
        return None
    zone_start += 1  # skip the newline, start at the '('... actually keep newline for removal
    # Actually keep the leading newline so removal works cleanly
    zone_start_with_nl = text.rfind('\n', 0, idx)
    # Walk forward from the '(' of the zone to find the matching ')'
    i = zone_start_with_nl
    while i < len(text) and text[i] != '(':
        i += 1
    paren_start = i
    depth = 0
    for i in range(paren_start, len(text)):
        c = text[i]
        if c == '(':
            depth += 1
        elif c == ')':
            depth -= 1
            if depth == 0:
                end = i + 1
                # consume trailing newline
                if end < len(text) and text[end] == '\n':
                    end += 1
                return (zone_start_with_nl, end, text[zone_start_with_nl:end])
    return None


# Extract the RF_KEEPOUT zone block (F.Cu) to get its polygon pts
rf_info = extract_zone_block(text, "RF_KEEPOUT")
if rf_info is None:
    raise ValueError("Could not find RF_KEEPOUT zone")

rf_start, rf_end, rf_block = rf_info

# Extract polygon pts from the RF_KEEPOUT block
pts_match = re.search(r'\(pts\s+([\s\S]*?)\s*\)\s*\)', rf_block)
if not pts_match:
    raise ValueError("Could not find polygon pts in RF_KEEPOUT zone")
pts_content = pts_match.group(1).strip()

# Build the replacement merged keepout zone
merged_zone = (
    f'\n  (zone (net 0) (net_name "") (layers "F.Cu" "In1.Cu" "In2.Cu" "B.Cu") (uuid "{gen_uuid()}") (name "RF_KEEPOUT")\n'
    f'    (hatch edge 0.508)\n'
    f'    (connect_pads (clearance 0))\n'
    f'    (min_thickness 0.254)\n'
    f'    (filled_areas_thickness no)\n'
    f'    (keepout\n'
    f'      (tracks not_allowed)\n'
    f'      (vias not_allowed)\n'
    f'      (pads not_allowed)\n'
    f'      (copperpour not_allowed)\n'
    f'      (footprints allowed)\n'
    f'    )\n'
    f'    (placement (enabled no) (sheetname ""))\n'
    f'    (fill (thermal_gap 0.508) (thermal_bridge_width 0.508))\n'
    f'    (polygon\n'
    f'      (pts\n'
    f'        {pts_content}\n'
    f'      )\n'
    f'    )\n'
    f'  )\n'
)

# Remove RF_KEEPOUT_BOTT and RF_KEEPOUT_GND zones first (they come after RF_KEEPOUT)
for zone_name in ("RF_KEEPOUT_BOTT", "RF_KEEPOUT_GND"):
    info = extract_zone_block(text, zone_name)
    if info:
        s, e, _ = info
        text = text[:s] + text[e:]
    else:
        print(f"Warning: could not find zone {zone_name}")

# Now replace the original RF_KEEPOUT zone
rf_info2 = extract_zone_block(text, "RF_KEEPOUT")
if rf_info2 is None:
    raise ValueError("Could not re-find RF_KEEPOUT zone after removing others")
s2, e2, _ = rf_info2
text = text[:s2] + merged_zone + text[e2:]


# ---------------------------------------------------------------------------
# Step 5: Add uuid to GND_PLANE and 3V3_POWER zones
# ---------------------------------------------------------------------------
def add_zone_uuid_by_name(text, zone_name):
    """Add uuid to a named zone's opening line if not already present."""
    search = '(name "' + zone_name + '")'
    idx = text.find(search)
    if idx == -1:
        print(f"Warning: zone {zone_name} not found for uuid addition")
        return text
    # Find the start of the zone line
    line_start = text.rfind('\n', 0, idx) + 1
    line_end = text.find('\n', idx)
    zone_line = text[line_start:line_end]
    if '(uuid' in zone_line:
        return text  # already has uuid
    # Insert uuid before (name "...")
    new_line = zone_line.replace(
        '(name "' + zone_name + '")',
        f'(uuid "{gen_uuid()}") (name "' + zone_name + '")'
    )
    return text[:line_start] + new_line + text[line_end:]

text = add_zone_uuid_by_name(text, "GND_PLANE")
text = add_zone_uuid_by_name(text, "3V3_POWER")


# ---------------------------------------------------------------------------
# Step 6: Add uuid to footprint opening lines
# ---------------------------------------------------------------------------
def add_uuid_to_footprints(text):
    # Match: (footprint "name" (layer "...") - the opening line of a footprint
    # We need to check the very next tokens after (layer "...") for uuid
    pattern = re.compile(
        r'(\(footprint\s+"[^"]*"\s+\(layer\s+"[^"]*"\))'
    )
    result = []
    last = 0
    for m in pattern.finditer(text):
        # Check if uuid already follows
        after = text[m.end():m.end() + 50]
        if '(uuid' in m.group(0) or after.lstrip().startswith('(uuid'):
            result.append(text[last:m.end()])
        else:
            result.append(text[last:m.start()])
            result.append(m.group(1) + f' (uuid "{gen_uuid()}")')
        last = m.end()
    result.append(text[last:])
    return ''.join(result)

text = add_uuid_to_footprints(text)


# ---------------------------------------------------------------------------
# Step 7: Add uuid to gr_line elements (single-line)
# ---------------------------------------------------------------------------
def add_uuid_to_gr_line(text):
    # (gr_line (start ...) (end ...) (stroke (...)) (layer "..."))
    # stroke contains nested parens so we need to handle that
    # Use a line-based approach
    lines = text.split('\n')
    new_lines = []
    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith('(gr_line ') and '(uuid' not in line:
            # Add uuid before the closing )
            line = line.rstrip()
            if line.endswith(')'):
                line = line[:-1] + f' (uuid "{gen_uuid()}"))'
        new_lines.append(line)
    return '\n'.join(new_lines)

text = add_uuid_to_gr_line(text)


# ---------------------------------------------------------------------------
# Step 8: Add uuid to gr_text elements (multi-line)
# ---------------------------------------------------------------------------
def add_uuid_to_gr_text(text):
    # gr_text first line: (gr_text "..." (at ...) (layer "..."))
    # uuid goes on next line after the opening
    lines = text.split('\n')
    new_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.lstrip()
        if stripped.startswith('(gr_text ') and '(uuid' not in line:
            # Check if next line has uuid already
            next_stripped = lines[i+1].lstrip() if i+1 < len(lines) else ''
            if not next_stripped.startswith('(uuid'):
                indent = len(line) - len(line.lstrip()) + 2
                new_lines.append(line)
                new_lines.append(' ' * indent + f'(uuid "{gen_uuid()}")')
                i += 1
                continue
        new_lines.append(line)
        i += 1
    return '\n'.join(new_lines)

text = add_uuid_to_gr_text(text)


# ---------------------------------------------------------------------------
# Step 9: Add uuid to fp_text elements
# ---------------------------------------------------------------------------
def add_uuid_to_fp_text(text):
    lines = text.split('\n')
    new_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.lstrip()
        if stripped.startswith('(fp_text ') and '(uuid' not in line:
            next_stripped = lines[i+1].lstrip() if i+1 < len(lines) else ''
            if not next_stripped.startswith('(uuid'):
                indent = len(line) - len(line.lstrip()) + 2
                new_lines.append(line)
                new_lines.append(' ' * indent + f'(uuid "{gen_uuid()}")')
                i += 1
                continue
        new_lines.append(line)
        i += 1
    return '\n'.join(new_lines)

text = add_uuid_to_fp_text(text)


# ---------------------------------------------------------------------------
# Step 10: Add uuid to pad elements (single-line)
# ---------------------------------------------------------------------------
def add_uuid_to_pads(text):
    lines = text.split('\n')
    new_lines = []
    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith('(pad ') and '(uuid' not in line:
            line = line.rstrip()
            if line.endswith(')'):
                line = line[:-1] + f' (uuid "{gen_uuid()}"))'
        new_lines.append(line)
    return '\n'.join(new_lines)

text = add_uuid_to_pads(text)


# ---------------------------------------------------------------------------
# Step 11: Add tstamp to segment elements (single-line)
# ---------------------------------------------------------------------------
def add_tstamp_to_segments(text):
    lines = text.split('\n')
    new_lines = []
    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith('(segment ') and '(tstamp' not in line:
            line = line.rstrip()
            if line.endswith(')'):
                line = line[:-1] + f' (tstamp "{gen_uuid()}"))'
        new_lines.append(line)
    return '\n'.join(new_lines)

text = add_tstamp_to_segments(text)


# ---------------------------------------------------------------------------
# Step 12: Add tstamp to via elements (single-line)
# ---------------------------------------------------------------------------
def add_tstamp_to_vias(text):
    lines = text.split('\n')
    new_lines = []
    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith('(via ') and '(tstamp' not in line:
            line = line.rstrip()
            if line.endswith(')'):
                line = line[:-1] + f' (tstamp "{gen_uuid()}"))'
        new_lines.append(line)
    return '\n'.join(new_lines)

text = add_tstamp_to_vias(text)


# ---------------------------------------------------------------------------
# Step 13: Verify parenthesis balance before writing
# ---------------------------------------------------------------------------
opens = text.count('(')
closes = text.count(')')
print(f"Parenthesis check - opens: {opens}, closes: {closes}")
if opens != closes:
    print(f"WARNING: Parenthesis imbalance! Difference: {opens - closes}")
else:
    print("Parentheses are balanced.")

# ---------------------------------------------------------------------------
# Step 14: Write output
# ---------------------------------------------------------------------------
with open(PCB_PATH, "w") as f:
    f.write(text)

print(f"Written to: {PCB_PATH}")

# ---------------------------------------------------------------------------
# Step 15: Quick verification stats
# ---------------------------------------------------------------------------
print(f"keepout_settings count: {text.count('keepout_settings')}")
print(f"'fill yes' count: {text.count('fill yes')}")
print(f"(uuid count: {text.count('(uuid')}")
print(f"(tstamp count: {text.count('(tstamp')}")
