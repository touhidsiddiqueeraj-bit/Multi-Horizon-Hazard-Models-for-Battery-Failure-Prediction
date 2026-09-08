import subprocess, uuid

def gen_uuid():
    return str(uuid.uuid4())

nets = [
    ('GND', 0), ('3V3', 1), ('BAT+', 2), ('SDA', 3), ('SCL', 4),
    ('VBAT_DIV', 5), ('GPIO1', 6), ('GPIO10', 7), ('BAT_IN', 8),
    ('LOAD+', 9), ('TEMP_DQ', 10),     ('RTC_VBAT', 11), ('VIN+', 12),
    ('VIN-', 13), ('LED_AN', 14),
]
net_by_name = {n: i for n, i in nets}

# collect absolute pad positions for routing
net_pads = {n: [] for n, _ in nets}

import math

def add_pad(net_name, x, y):
    if net_name and net_name in net_pads:
        net_pads[net_name].append((round(x, 2), round(y, 2)))

def rot_pt(px, py, angle):
    """Rotate point (px,py) by angle degrees clockwise (KiCad convention)"""
    r = math.radians(angle)
    c, s = math.cos(r), math.sin(r)
    return px * c + py * s, -px * s + py * c

lines = []
def L(s, indent=1):
    lines.append('\t' * indent + s)

# Minimal working header (verified with kicad-cli 10.0.4)
L('(kicad_pcb', 0)
L('(version 20260206)')
L('(generator "opencode")')
L('(general (thickness 1.6))')
L('(paper "A4")')
L('(layers')
L('(0 "F.Cu" signal)', 2)
L('(2 "B.Cu" signal)', 2)
L('(25 "Edge.Cuts" user)', 2)
L(')')
L('(setup')
L('(pad_to_mask_clearance 0)', 2)
L('(solder_mask_min_width 0)', 2)
L(')')
L('(embedded_fonts no)')
L('(net_class "Default" ""')
L('(clearance 0.2)', 2)
L(')')

for n, idx in nets:
    L(f'(net {idx} "{n}")')

for i in range(4):
    x1,y1 = [(0,0),(95,0),(95,75),(0,75)][i]
    x2,y2 = [(95,0),(95,75),(0,75),(0,0)][i]
    L(f'(gr_line (start {x1} {y1}) (end {x2} {y2}) (layer "Edge.Cuts") (stroke (width 0.15) (type default)))')

for x,y in [(3.5,3.5),(91.5,3.5),(3.5,71.5),(91.5,71.5)]:
    uid = gen_uuid()
    L(f'(footprint "MountingHole:M3" (layer "F.Cu")')
    L(f'(at {x} {y} 0)', 2)
    L('(attr smd)', 2)
    L(f'(uuid {uid})', 2)
    L('(property "Reference" "#H" (at 0 0 0) (effects (font (size 1 1)) hide))', 2)
    L('(property "Value" "M3" (at 0 0 0) (effects (font (size 1 1)) hide))', 2)
    L('(fp_circle (center 0 0) (end 1.6 0) (layer "Edge.Cuts") (stroke (width 0.15) (type default)) (fill none))', 2)
    L('(pad "" np_thru_hole circle (at 0 0) (size 3.2 3.2) (drill 3.2) (layers "*.Cu" "*.Mask"))', 2)
    L(')')

j1_pin_nets = {
    1: '3V3', 14: 'SDA', 15: 'SCL', 19: 'GND', 21: '3V3', 38: 'GND',
}
uid = gen_uuid()
L(f'(footprint "Connector_PinHeader_2.54mm:PinHeader_2x19_P2.54mm_Vertical" (layer "F.Cu")')
L(f'(at 10 14.5 0)', 2)
L(f'(uuid {uid})', 2)
L('(property "Reference" "J1" (at 0 0 0) (effects (font (size 1 1)) hide))', 2)
L('(property "Value" "ESP32-S3-DevKitC-1" (at 0 0 0) (effects (font (size 1 1)) hide))', 2)
for i in range(1, 20):
    py = (i-1)*2.54
    net_name = j1_pin_nets.get(i)
    ax, ay = 10 + 0, 14.5 + py
    shape = 'rect' if i == 1 else 'circle'
    if net_name:
        ni = net_by_name[net_name]
        L(f'(pad "{i}" thru_hole {shape} (at 0 {py}) (size 1.8 1.8) (drill 1) (layers "*.Cu" "*.Mask") (net {ni} "{net_name}"))', 2)
    else:
        L(f'(pad "{i}" thru_hole circle (at 0 {py}) (size 1.8 1.8) (drill 1) (layers "*.Cu" "*.Mask"))', 2)
    add_pad(net_name, ax, ay)
for i in range(20, 39):
    py = (i-20)*2.54
    net_name = j1_pin_nets.get(i)
    ax, ay = 10 + 22.86, 14.5 + py
    if net_name:
        ni = net_by_name[net_name]
        L(f'(pad "{i}" thru_hole circle (at 22.86 {py}) (size 1.8 1.8) (drill 1) (layers "*.Cu" "*.Mask") (net {ni} "{net_name}"))', 2)
    else:
        L(f'(pad "{i}" thru_hole circle (at 22.86 {py}) (size 1.8 1.8) (drill 1) (layers "*.Cu" "*.Mask"))', 2)
    add_pad(net_name, ax, ay)
L(')')

def fp_tht(name, ref, value, x, y, pins, rot=0):
    uid = gen_uuid()
    L(f'(footprint "{name}" (layer "F.Cu")')
    L(f'(at {x} {y} {rot})', 2)
    L(f'(uuid {uid})', 2)
    L(f'(property "Reference" "{ref}" (at 0 3 0) (effects (font (size 1 1))))', 2)
    L(f'(property "Value" "{value}" (at 0 -3 0) (effects (font (size 1 1))))', 2)
    for pn, px, py, net_name in pins:
        net_idx = net_by_name.get(net_name) if net_name else None
        if net_idx is not None:
            L(f'(pad "{pn}" thru_hole circle (at {px} {py}) (size 1.8 1.8) (drill 0.8) (layers "*.Cu" "*.Mask") (net {net_idx} "{net_name}"))', 2)
        else:
            L(f'(pad "{pn}" thru_hole circle (at {px} {py}) (size 1.8 1.8) (drill 0.8) (layers "*.Cu" "*.Mask"))', 2)
        rpx, rpy = rot_pt(px, py, rot)
        add_pad(net_name, x + rpx, y + rpy)
    L(')')

def fp_smt(name, ref, value, x, y, pins, rot=0):
    uid = gen_uuid()
    L(f'(footprint "{name}" (layer "F.Cu")')
    L(f'(at {x} {y} {rot})', 2)
    L(f'(uuid {uid})', 2)
    L(f'(property "Reference" "{ref}" (at 0 3 0) (effects (font (size 1 1))))', 2)
    L(f'(property "Value" "{value}" (at 0 -3 0) (effects (font (size 1 1))))', 2)
    for pn, px, py, net_name in pins:
        net_idx = net_by_name.get(net_name) if net_name else None
        if net_idx is not None:
            L(f'(pad "{pn}" smd rect (at {px} {py}) (size 1.5 0.6) (layers "F.Cu" "F.Paste" "F.Mask") (net {net_idx} "{net_name}"))', 2)
        else:
            L(f'(pad "{pn}" smd rect (at {px} {py}) (size 1.5 0.6) (layers "F.Cu" "F.Paste" "F.Mask"))', 2)
        rpx, rpy = rot_pt(px, py, rot)
        add_pad(net_name, x + rpx, y + rpy)
    L(')')

L(f'(footprint "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm" (layer "F.Cu")')
L('(at 58 52 0)', 2)
L(f'(uuid {gen_uuid()})', 2)
L('(property "Reference" "U1" (at 0 0 0) (effects (font (size 1 1)) hide))', 2)
L('(property "Value" "INA219" (at 0 0 0) (effects (font (size 1 1)) hide))', 2)
ina_pads = [(-2.54, 1.905, '3V3'), (-2.54, 0.635, 'GND'), (2.54, 1.905, 'SDA'), (2.54, 0.635, 'SCL'), (2.54, -0.635, 'VIN-'), (2.54, -1.905, 'VIN+'), (-2.54, -0.635, ''), (-2.54, -1.905, '')]
for i, (px, py, n) in enumerate(ina_pads, 1):
    ni = net_by_name.get(n) if n else None
    if ni is not None:
        L(f'(pad "{i}" smd rect (at {px} {py}) (size 1.5 0.6) (layers "F.Cu" "F.Paste" "F.Mask") (net {ni} "{n}"))', 2)
    else:
        L(f'(pad "{i}" smd rect (at {px} {py}) (size 1.5 0.6) (layers "F.Cu" "F.Paste" "F.Mask"))', 2)
    add_pad(n, 58 + px, 52 + py)
L(')')

L(f'(footprint "Package_SO:SOIC-16W_7.5x10.3mm_P1.27mm" (layer "F.Cu")')
L('(at 75 52 0)', 2)
L(f'(uuid {gen_uuid()})', 2)
L('(property "Reference" "U2" (at 0 0 0) (effects (font (size 1 1)) hide))', 2)
L('(property "Value" "DS3231" (at 0 0 0) (effects (font (size 1 1)) hide))', 2)
ds_pads = [(-5.08, 4.445, ''), (-5.08, 3.175, '3V3'), (-5.08, 1.905, ''), (-5.08, 0.635, ''), (5.08, 4.445, 'SDA'), (5.08, 3.175, 'SCL'), (5.08, 1.905, ''), (5.08, 0.635, ''), (5.08, -0.635, ''), (5.08, -1.905, ''), (5.08, -3.175, ''), (5.08, -4.445, ''), (-5.08, -0.635, ''), (-5.08, -1.905, ''), (-5.08, -3.175, ''), (-5.08, -4.445, 'GND')]
for i, (px, py, n) in enumerate(ds_pads, 1):
    ni = net_by_name.get(n) if n else None
    if ni is not None:
        L(f'(pad "{i}" smd rect (at {px} {py}) (size 1.5 0.6) (layers "F.Cu" "F.Paste" "F.Mask") (net {ni} "{n}"))', 2)
    else:
        L(f'(pad "{i}" smd rect (at {px} {py}) (size 1.5 0.6) (layers "F.Cu" "F.Paste" "F.Mask"))', 2)
    add_pad(n, 75 + px, 52 + py)
L(')')

fp_tht('Package_TO_SOT_THT:TO-92_Inline', 'U3', 'DS18B20', 28, 18,
    [('1', -1.27, 0, 'GND'), ('2', 1.27, 0, 'TEMP_DQ'), ('3', 0, -2.54, '3V3')])

fp_tht('Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P2.54mm_Vertical', 'R1', '10k', 78, 25, [('1', -1.27, 0, '3V3'), ('2', 1.27, 0, 'VBAT_DIV')])
fp_tht('Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P2.54mm_Vertical', 'R2', '10k', 78, 30, [('1', -1.27, 0, 'VBAT_DIV'), ('2', 1.27, 0, 'GND')])
fp_tht('Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P2.54mm_Vertical', 'R3', '4.7k', 62, 48, [('1', -1.27, 0, '3V3'), ('2', 1.27, 0, 'SDA')])
fp_tht('Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P2.54mm_Vertical', 'R4', '4.7k', 67, 48, [('1', -1.27, 0, '3V3'), ('2', 1.27, 0, 'SCL')])
fp_tht('Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P2.54mm_Vertical', 'R5', '4.7k', 30, 10, [('1', -1.27, 0, '3V3'), ('2', 1.27, 0, 'TEMP_DQ')])
fp_tht('Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P2.54mm_Vertical', 'RS', '0.1 1W', 60, 58, [('1', -1.27, 0, 'VIN-'), ('2', 1.27, 0, 'VIN+')])
fp_tht('Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P2.54mm_Vertical', 'RLED', '1k', 44, 42, [('1', -1.27, 0, '3V3'), ('2', 1.27, 0, 'LED_AN')])

fp_tht('Capacitor_THT:C_Radial_D5.0mm_P2.5mm', 'C1', '100nF', 38, 25, [('1', -1.25, 0, '3V3'), ('2', 1.25, 0, 'GND')])
fp_tht('Capacitor_THT:C_Radial_D5.0mm_P2.5mm', 'C2', '100uF', 38, 20, [('1', -1.25, 0, '3V3'), ('2', 1.25, 0, 'GND')])
fp_tht('Capacitor_THT:C_Radial_D5.0mm_P2.5mm', 'C3', '100nF', 72, 58, [('1', -1.25, 0, '3V3'), ('2', 1.25, 0, 'GND')])

fp_tht('LED_THT:LED_D3.0mm', 'D1', 'GREEN', 44, 37, [('1', -1.27, 0, 'GND'), ('2', 1.27, 0, 'LED_AN')])

fp_tht('TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5-2-5.08_1x02_P5.08mm_Horizontal', 'J2', 'BAT_IN', 85, 55, [('1', 0, 0, 'BAT_IN'), ('2', 5.08, 0, 'GND')], 90)
fp_tht('TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5-2-5.08_1x02_P5.08mm_Horizontal', 'J3', 'LOAD', 85, 62, [('1', 0, 0, ''), ('2', 5.08, 0, '')], 90)
fp_tht('TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5-3-5.08_1x03_P5.08mm_Horizontal', 'J4', 'TEMP_PROBE', 20, 15, [('1', 0, 0, 'GND'), ('2', 5.08, 0, 'TEMP_DQ'), ('3', 10.16, 0, '3V3')], 90)

fp_smt('Crystal:Crystal_SMD_3.2x1.5mm_HandSoldering', 'Y1', '32.768kHz', 75, 60,
    [('1', -1.6, 0, ''), ('2', 1.6, 0, '')])

L(f'(footprint "Battery:BatteryHolder_Keystone_3001_1xCR1220" (layer "F.Cu")')
L('(at 82 40 0)', 2)
L(f'(uuid {gen_uuid()})', 2)
L('(property "Reference" "BT1" (at 0 0 0) (effects (font (size 1 1)) hide))', 2)
L('(property "Value" "CR1220" (at 0 0 0) (effects (font (size 1 1)) hide))', 2)
L('(pad "1" smd rect (at 4.5 3.5) (size 3 4) (layers "F.Cu" "F.Paste" "F.Mask"))', 2)
L('(pad "2" smd rect (at -4.5 -3.5) (size 3 4) (layers "F.Cu" "F.Paste" "F.Mask"))', 2)
L(')')

fp_tht('Diode_THT:D_DO-35_SOD27_P7.62mm_Horizontal', 'D2', '1N4148', 55, 68,
    [('1', -3.81, 0, ''), ('2', 3.81, 0, '')])

for layer in ['F.Cu', 'B.Cu']:
    uid = gen_uuid()
    L(f'(zone (net {net_by_name["GND"]}) (net_name "GND") (layer "{layer}")')
    L(f'(uuid {uid})', 2)
    L('(polygon', 2)
    L('(pts (xy 0.5 0.5) (xy 94.5 0.5) (xy 94.5 74.5) (xy 0.5 74.5))', 3)
    L(')', 2)
    L('(fill yes)', 2)
    L(')')

# ponytail: no auto-routing — GND zones handle ground; user routes signals in KiCad GUI

L(')', 0)

content = '\n'.join(lines) + '\n'
with open('/home/touhid/multi-horizon-battery/hardware/battery-predictor.kicad_pcb', 'w') as f:
    f.write(content)
print(f'Written {len(content)} bytes, {len(lines)} lines')
print(f'Pad counts:')
for nn in ['3V3', 'SDA', 'SCL', 'TEMP_DQ', 'VBAT_DIV', 'GND']:
    print(f'  {nn}: {len(net_pads.get(nn, []))} pads: {net_pads.get(nn)}')

r = subprocess.run(['kicad-cli', 'pcb', 'export', 'gerbers',
    '/home/touhid/multi-horizon-battery/hardware/battery-predictor.kicad_pcb',
    '--output', '/tmp/gerbers3'], capture_output=True, text=True, timeout=30)
print(f'Validation: exit={r.returncode}')
if r.returncode != 0:
    print(f'Error: {r.stderr.strip()[:500]}')
