import subprocess, sys, uuid

def gen_uuid():
    return str(uuid.uuid4())

def q(s): return f'"{s}"'

# nets
nets = [
    ("GND", 0), ("3V3", 1), ("BAT+", 2), ("SDA", 3), ("SCL", 4),
    ("VBAT_DIV", 5), ("GPIO1", 6), ("GPIO10", 7), ("BAT_IN", 8),
    ("LOAD+", 9), ("TEMP_DQ", 10), ("RTC_VBAT", 11), ("VIN+", 12),
    ("VIN-", 13),
]
net_by_name = {n: i for n, i in nets}

lines = []
def emit(s, indent=0): lines.append(('\t' * (indent + 1)) + s)

# First line is special - no indent
def emit_top(s):
    lines.append(s)

emit('(kicad_pcb')
emit('(version 20260206)')
emit('(generator "opencode")')
emit('(general')
emit('(thickness 1.6)', 1)
emit('(legacy_teardrops no)', 1)
emit(')')
emit('(paper "A4")')
emit('(title_block')
emit('(title "Battery Failure Predictor - Sensor Shield")', 1)
emit('(date "2026-07-21")', 1)
emit('(rev "1.0")', 1)
emit('(company "Multi-Horizon Battery Framework")', 1)
emit(')')

# layers
emit('(layers')
layers = [
    (0, "F.Cu", "signal"), (2, "B.Cu", "signal"),
    (9, "F.Adhes", "user", "F.Adhesive"), (11, "B.Adhes", "user", "B.Adhesive"),
    (13, "F.Paste", "user"), (15, "B.Paste", "user"),
    (5, "F.SilkS", "user", "F.Silkscreen"), (7, "B.SilkS", "user", "B.Silkscreen"),
    (1, "F.Mask", "user"), (3, "B.Mask", "user"),
    (17, "Dwgs.User", "user", "User.Drawings"), (19, "Cmts.User", "user", "User.Comments"),
    (21, "Eco1.User", "user", "User.Eco1"), (23, "Eco2.User", "user", "User.Eco2"),
    (25, "Edge.Cuts", "user"), (27, "Margin", "user"),
    (31, "F.CrtYd", "user", "F.Courtyard"), (29, "B.CrtYd", "user", "B.Courtyard"),
    (35, "F.Fab", "user"), (33, "B.Fab", "user"),
]
for l in layers:
    if len(l) == 3:
        emit(f'({l[0]} {q(l[1])} {l[2]})', 1)
    else:
        emit(f'({l[0]} {q(l[1])} {l[2]} {q(l[3])})', 1)
emit(')')

# setup
emit('(setup')
emit('(pad_to_mask_clearance 0)', 1)
emit('(allow_soldermask_bridges_in_footprints no)', 1)
emit('(tenting (front yes) (back yes))', 1)
emit('(covering (front no) (back no))', 1)
emit('(plugging (front no) (back no))', 1)
emit('(capping no)', 1)
emit('(filling no)', 1)
emit('(pcbplotparams', 1)
emit('(layerselection 0x00000000_00000000_55555555_5755f5ff)', 2)
emit('(disableapertmacros no)', 2)
emit('(usegerberextensions no)', 2)
emit('(usegerberattributes yes)', 2)
emit('(usegerberadvancedattributes yes)', 2)
emit('(creategerberjobfile yes)', 2)
emit('(dashed_line_dash_ratio 12)', 2)
emit('(dashed_line_gap_ratio 3)', 2)
emit('(svgprecision 4)', 2)
emit('(plotframeref no)', 2)
emit('(mode 1)', 2)
emit('(useauxorigin no)', 2)
emit('(png_front_fp_property_popups yes)', 2)
emit('(png_back_fp_property_popups yes)', 2)
emit('(svg_metadata yes)', 2)
emit('(plot_black_and_white yes)', 2)
emit('(sketchpadsonfab no)', 2)
emit('(plotpadnumbers no)', 2)
emit('(hidednponfab no)', 2)
emit('(sketchdnponfab yes)', 2)
emit('(crossoutdnponfab yes)', 2)
emit('(subtractmaskfromsilk no)', 2)
emit('(outputformat 1)', 2)
emit('(mirror no)', 2)
emit('(drillshape 1)', 2)
emit('(scaleselection 1)', 2)
emit('(outputdirectory "gerber/")', 2)
emit(')', 1)
emit(')')

# net classes
emit('(net_class "Default"')
emit('(clearance 0.2)', 1)
emit('(trace_width 0.5)', 1)
emit('(via_dia 1.0)', 1)
emit('(via_drill 0.6)', 1)
emit('(uvia_dia 0.3)', 1)
emit('(uvia_drill 0.1)', 1)
emit(')')

# nets - KiCad 10 requires explicit (nets) section
emit(f'(nets')
for n, idx in nets:
    emit(f'(net {idx} {q(n)})', 1)
emit(')')

# embedded fonts
emit('(embedded_fonts no)')

# board outline
outline_pts = [(0,0),(95,0),(95,75),(0,75)]
for i in range(4):
    x1,y1 = outline_pts[i]
    x2,y2 = outline_pts[(i+1)%4]
    emit(f'(gr_line (start {x1} {y1}) (end {x2} {y2}) (layer "Edge.Cuts") (stroke (width 0.15) (type default)))')

# Mounting holes
m3_positions = [(3.5,3.5),(91.5,3.5),(3.5,71.5),(91.5,71.5)]
for x,y in m3_positions:
    uid = gen_uuid()
    emit(f'(footprint "MountingHole:M3" (layer "F.Cu")')
    emit(f'(at {x} {y} 0)', 1)
    emit('(attr smd)', 1)
    emit('(fp_circle (center 0 0) (end 1.6 0) (layer "Edge.Cuts") (stroke (width 0.15) (type default)) (fill none))', 1)
    emit(f'(pad "" np_thru_hole circle (at 0 0) (size 3.2 3.2) (drill 3.2) (layers "*.Cu" "*.Mask"))', 1)
    emit(')')

# 2x19 Female Header J1 at (15.24, 77.47) in schematic coords
# In PCB: placed near left edge. J1 (connector) is a single footprint with 38 pins
# Use a custom footprint definition or approximate as 2 rows of 19
uid_j1 = gen_uuid()
emit(f'(footprint "Connector_PinHeader_2.54mm:PinHeader_2x19_P2.54mm_Vertical" (layer "F.Cu")')
emit('(tedit 0)', 1)
emit(f'(at 10 37.5 0)', 1)
emit('(descr "2x19 pin header")', 1)
emit(f'(uuid {uid_j1})', 1)
emit('(property "Reference" "J1" (at 0 0 0) (effects (font (size 1 1)) hide))', 1)
emit('(property "Value" "ESP32-S3-DevKitC-1" (at 0 0 0) (effects (font (size 1 1)) hide))', 1)
emit('(pad "1" thru_hole rect (at 0 0) (size 2 2) (drill 1) (layers "*.Cu" "*.Mask") (net 1 "3V3"))', 1)
for i in range(2, 20):
    emit(f'(pad {q(str(i))} thru_hole circle (at 0 {(i-1)*2.54}) (size 2 2) (drill 1) (layers "*.Cu" "*.Mask"))', 1)
for i in range(20, 39):
    emit(f'(pad {q(str(i))} thru_hole circle (at 22.86 {(i-20)*2.54}) (size 2 2) (drill 1) (layers "*.Cu" "*.Mask"))', 1)
emit(')')

# Resistors - axial vertical
def resistor(ref, value, x, y, net1=None, net2=None):
    uid = gen_uuid()
    emit(f'(footprint "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P2.54mm_Vertical" (layer "F.Cu")')
    emit(f'(at {x} {y} 0)', 1)
    emit(f'(descr "Axial resistor vertical")', 1)
    emit(f'(uuid {uid})', 1)
    emit(f'(property "Reference" {q(ref)} (at 0 4 0) (effects (font (size 1 1))))', 1)
    emit(f'(property "Value" {q(value)} (at 0 -4 0) (effects (font (size 1 1))))', 1)
    emit(f'(pad "1" thru_hole circle (at -1.27 0) (size 2 2) (drill 0.8) (layers "*.Cu" "*.Mask"))', 1)
    emit(f'(pad "2" thru_hole circle (at 1.27 0) (size 2 2) (drill 0.8) (layers "*.Cu" "*.Mask"))', 1)
    emit(')')

# Capacitors - radial
def capacitor(ref, value, x, y):
    uid = gen_uuid()
    emit(f'(footprint "Capacitor_THT:C_Radial_D5.0mm_P2.5mm" (layer "F.Cu")')
    emit(f'(at {x} {y} 0)', 1)
    emit(f'(uuid {uid})', 1)
    emit(f'(property "Reference" {q(ref)} (at 0 4 0) (effects (font (size 1 1))))', 1)
    emit(f'(property "Value" {q(value)} (at 0 -4 0) (effects (font (size 1 1))))', 1)
    emit(f'(pad "1" thru_hole circle (at -1.25 0) (size 2 2) (drill 0.8) (layers "*.Cu" "*.Mask"))', 1)
    emit(f'(pad "2" thru_hole circle (at 1.25 0) (size 2 2) (drill 0.8) (layers "*.Cu" "*.Mask"))', 1)
    emit(')')

# LED
def led(ref, value, x, y):
    uid = gen_uuid()
    emit(f'(footprint "LED_THT:LED_D3.0mm" (layer "F.Cu")')
    emit(f'(at {x} {y} 0)', 1)
    emit(f'(uuid {uid})', 1)
    emit(f'(property "Reference" {q(ref)} (at 0 4 0) (effects (font (size 1 1))))', 1)
    emit(f'(property "Value" {q(value)} (at 0 -4 0) (effects (font (size 1 1))))', 1)
    emit(f'(pad "1" thru_hole circle (at -1.27 0) (size 2 2) (drill 0.8) (layers "*.Cu" "*.Mask"))', 1)
    emit(f'(pad "2" thru_hole circle (at 1.27 0) (size 2 2) (drill 0.8) (layers "*.Cu" "*.Mask"))', 1)
    emit(')')

# Screw terminal 2-pin
def screw2(ref, value, x, y):
    uid = gen_uuid()
    emit(f'(footprint "TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5-2-5.08_1x02_P5.08mm_Horizontal" (layer "F.Cu")')
    emit(f'(at {x} {y} 90)', 1)
    emit(f'(uuid {uid})', 1)
    emit(f'(property "Reference" {q(ref)} (at 0 4 0) (effects (font (size 1 1))))', 1)
    emit(f'(property "Value" {q(value)} (at 0 -4 0) (effects (font (size 1 1))))', 1)
    emit(f'(pad "1" thru_hole oval (at -2.54 0) (size 2.5 3) (drill 1.3) (layers "*.Cu" "*.Mask"))', 1)
    emit(f'(pad "2" thru_hole oval (at 2.54 0) (size 2.5 3) (drill 1.3) (layers "*.Cu" "*.Mask"))', 1)
    emit(')')

# Screw terminal 3-pin
def screw3(ref, value, x, y):
    uid = gen_uuid()
    emit(f'(footprint "TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5-3-5.08_1x03_P5.08mm_Horizontal" (layer "F.Cu")')
    emit(f'(at {x} {y} 90)', 1)
    emit(f'(uuid {uid})', 1)
    emit(f'(property "Reference" {q(ref)} (at 0 4 0) (effects (font (size 1 1))))', 1)
    emit(f'(property "Value" {q(value)} (at 0 -4 0) (effects (font (size 1 1))))', 1)
    emit(f'(pad "1" thru_hole oval (at -5.08 0) (size 2.5 3) (drill 1.3) (layers "*.Cu" "*.Mask"))', 1)
    emit(f'(pad "2" thru_hole oval (at 0 0) (size 2.5 3) (drill 1.3) (layers "*.Cu" "*.Mask"))', 1)
    emit(f'(pad "3" thru_hole oval (at 5.08 0) (size 2.5 3) (drill 1.3) (layers "*.Cu" "*.Mask"))', 1)
    emit(')')

# INA219 SOIC-8
uid_u1 = gen_uuid()
emit(f'(footprint "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm" (layer "F.Cu")')
emit(f'(at 55 55 0)', 1)
emit(f'(uuid {uid_u1})', 1)
emit(f'(property "Reference" "U1" (at 0 4 0) (effects (font (size 1 1))))', 1)
emit(f'(property "Value" "INA219" (at 0 -4 0) (effects (font (size 1 1))))', 1)
for i in range(1, 9):
    emit(f'(pad {q(str(i))} smd rect (at {(-3.9/2 if i <= 4 else 3.9/2)} {(2.5 - (i-1)*1.27) if i <= 4 else (2.5 - (i-5)*1.27)}) (size 1.5 0.6) (layers "F.Cu" "F.Paste" "F.Mask"))', 1)
emit(')')

# DS3231 SOIC-16W
uid_u2 = gen_uuid()
emit(f'(footprint "Package_SO:SOIC-16W_7.5x10.3mm_P1.27mm" (layer "F.Cu")')
emit(f'(at 70 55 0)', 1)
emit(f'(uuid {uid_u2})', 1)
emit(f'(property "Reference" "U2" (at 0 4 0) (effects (font (size 1 1))))', 1)
emit(f'(property "Value" "DS3231" (at 0 -4 0) (effects (font (size 1 1))))', 1)
for i in range(1, 17):
    side = "left" if i <= 8 else "right"
    emit(f'(pad {q(str(i))} smd rect (at 0 0) (size 1.5 0.6) (layers "F.Cu" "F.Paste" "F.Mask"))', 1)
emit(')')

# DS18B20 TO-92
uid_u3 = gen_uuid()
emit(f'(footprint "Package_TO_SOT_THT:TO-92_Inline" (layer "F.Cu")')
emit(f'(at 30 20 0)', 1)
emit(f'(uuid {uid_u3})', 1)
emit(f'(property "Reference" "U3" (at 0 4 0) (effects (font (size 1 1))))', 1)
emit(f'(property "Value" "DS18B20" (at 0 -4 0) (effects (font (size 1 1))))', 1)
emit(f'(pad "1" thru_hole circle (at -1.27 0) (size 1.6 1.6) (drill 0.8) (layers "*.Cu" "*.Mask"))', 1)
emit(f'(pad "2" thru_hole circle (at 1.27 0) (size 1.6 1.6) (drill 0.8) (layers "*.Cu" "*.Mask"))', 1)
emit(f'(pad "3" thru_hole circle (at 0 -2.54) (size 1.6 1.6) (drill 0.8) (layers "*.Cu" "*.Mask"))', 1)
emit(')')

# Crystal Y1 32.768kHz
uid_y1 = gen_uuid()
emit(f'(footprint "Crystal:Crystal_SMD_3.2x1.5mm_HandSoldering" (layer "F.Cu")')
emit(f'(at 70 45 0)', 1)
emit(f'(uuid {uid_y1})', 1)
emit(f'(property "Reference" "Y1" (at 0 3 0) (effects (font (size 1 1))))', 1)
emit(f'(property "Value" "32.768kHz" (at 0 -3 0) (effects (font (size 1 1))))', 1)
emit(f'(pad "1" smd rect (at -1.6 0) (size 1.2 0.8) (layers "F.Cu" "F.Paste" "F.Mask"))', 1)
emit(f'(pad "2" smd rect (at 1.6 0) (size 1.2 0.8) (layers "F.Cu" "F.Paste" "F.Mask"))', 1)
emit(')')

# CR1220 Battery holder
uid_bt1 = gen_uuid()
emit(f'(footprint "Battery:BatteryHolder_Keystone_3001_1xCR1220" (layer "F.Cu")')
emit(f'(at 80 45 0)', 1)
emit(f'(uuid {uid_bt1})', 1)
emit(f'(property "Reference" "BT1" (at 0 3 0) (effects (font (size 1 1))))', 1)
emit(f'(property "Value" "CR1220" (at 0 -3 0) (effects (font (size 1 1))))', 1)
emit(f'(pad "1" smd rect (at 4.5 3.5 0) (size 3 4) (layers "F.Cu" "F.Paste" "F.Mask"))', 1)
emit(f'(pad "2" smd rect (at -4.5 -3.5 0) (size 3 4) (layers "F.Cu" "F.Paste" "F.Mask"))', 1)
emit(')')

# Diode DO-35 (for DS3231 backup isolation)
uid_d2 = gen_uuid()
emit(f'(footprint "Diode_THT:D_DO-35_SOD27_P7.62mm_Horizontal" (layer "F.Cu")')
emit(f'(at 60 45 0)', 1)
emit(f'(uuid {uid_d2})', 1)
emit(f'(property "Reference" "D2" (at 0 3 0) (effects (font (size 1 1))))', 1)
emit(f'(property "Value" "1N4148" (at 0 -3 0) (effects (font (size 1 1))))', 1)
emit(f'(pad "1" thru_hole circle (at -3.81 0) (size 2 2) (drill 0.8) (layers "*.Cu" "*.Mask"))', 1)
emit(f'(pad "2" thru_hole circle (at 3.81 0) (size 2 2) (drill 0.8) (layers "*.Cu" "*.Mask"))', 1)
emit(')')

# Place axial resistors
resistor("R1", "10k", 45, 30)
resistor("R2", "10k", 45, 35)
resistor("R3", "4.7k", 55, 45)
resistor("R4", "4.7k", 60, 45)
resistor("R5", "4.7k", 30, 25)
resistor("RS", "0.1 1W", 50, 60)
resistor("RLED", "1k", 10, 30)

# Place capacitors
capacitor("C1", "100nF", 10, 25)
capacitor("C2", "100uF", 10, 20)
capacitor("C3", "100nF", 55, 50)

# Place LED
led("D1", "GREEN", 10, 35)

# Place screw terminals
screw2("J2", "BAT_IN", 40, 65)
screw2("J3", "LOAD", 50, 65)
screw3("J4", "TEMP_PROBE", 30, 15)

# Zones - GND pour on both layers
for layer in ["F.Cu", "B.Cu"]:
    uid = gen_uuid()
    emit(f'(zone (net {net_by_name["GND"]}) (net_name "GND") (layer {q(layer)})')
    emit(f'(uuid {uid})', 1)
    emit(f'(polygon', 1)
    emit(f'(pts (xy 0.5 0.5) (xy 94.5 0.5) (xy 94.5 74.5) (xy 0.5 74.5))', 2)
    emit(f')', 1)
    emit(f'(fill (mode thermal) (clearance 0.3) (thermal_gap 0.2) (thermal_bridge_width 0.3))', 1)
    emit(')')

emit(')')  # close (kicad_pcb

content = '\n'.join(lines)
with open('/home/touhid/multi-horizon-battery/hardware/battery-predictor.kicad_pcb', 'w') as f:
    f.write(content + '\n')

print(f"Written {len(content)} bytes, {len(lines)} lines")
result = subprocess.run(['kicad-cli', 'pcb', 'export', 'gerbers',
    '/home/touhid/multi-horizon-battery/hardware/battery-predictor.kicad_pcb',
    '--output', '/tmp/gerbers2'], capture_output=True, text=True, timeout=30)
print(f"Validation: exit={result.returncode}")
print(result.stderr[:200] if result.stderr else "OK")
