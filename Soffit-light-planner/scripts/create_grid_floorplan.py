"""
create_grid_floorplan.py
Generates floorplan_grid.svg from the annotated baseline SVG.

Grid improvements vs old version:
- Labels in FEET (not raw canvas units)  →  e.g. "0ft", "5ft", "10ft", …
- Labelled every 5 ft; thicker lines at every 5-ft boundary
- Softer blue grid so it does not fight the black structural walls
- Proper scale derivation: 1.3 canvas-units per inch, 15.6 per foot
"""
import json
import os
import re

# ── Scale constants ──────────────────────────────────────────────────────────
UNITS_PER_INCH = 1.3
UNITS_PER_FOOT = UNITS_PER_INCH * 12      # 15.6 canvas-units per foot

# ── Paths ────────────────────────────────────────────────────────────────────
base_dir = os.path.dirname(os.path.abspath(__file__))
if os.path.basename(base_dir) == 'scripts':
    base_dir = os.path.dirname(base_dir)

infile   = os.path.join(base_dir, "floorplan_annotated.svg")   # ← rich source
outfile  = os.path.join(base_dir, "floorplan_grid.svg")
json_in  = os.path.join(base_dir, "perimeter_lights.json")

# ── Load SVG ─────────────────────────────────────────────────────────────────
with open(infile, 'r') as f:
    text = f.read()

# 1. Strip any old DEBUG GRID and PERIMETER LIGHTS blocks so we can re-inject
text = re.sub(r'<!-- DEBUG GRID -->.*?</g>\n?', '', text, flags=re.DOTALL)
text = re.sub(r'<!-- PERIMETER LIGHTS -->.*?</g>\n?', '', text, flags=re.DOTALL)

# 2. Build the improved grid (every 1 ft, labelled every 5 ft) ──────────────
#    Canvas runs roughly from x=-100 to x=900, y=-100 to y=1250
x_start, x_end, y_start, y_end = -100, 900, -100, 1250

grid_lines = [
    '<!-- DEBUG GRID -->',
    '<g id="debug_grid" stroke="#8bafd4" stroke-width="0.5" opacity="0.65" '
    'font-family="Arial,Helvetica,sans-serif" font-size="9" fill="#1a4a8a">',
]

# Vertical lines
x = x_start
while x <= x_end + 0.01:
    xr = round(x, 1)
    ft = (xr) / UNITS_PER_FOOT          # canvas-origin = 0 ft
    ft_int = round(ft)
    is_5ft = abs(ft_int % 5) == 0 and abs(ft - ft_int) < 0.05

    sw = '1.0' if is_5ft else '0.4'
    grid_lines.append(
        f'  <line x1="{xr}" y1="{y_start}" x2="{xr}" y2="{y_end}" '
        f'stroke-width="{sw}" />'
    )
    if is_5ft:
        label = f"{ft_int:.0f}ft"
        grid_lines.append(
            f'  <text x="{xr+1}" y="{y_start + 11}" font-size="9">{label}</text>'
        )
        grid_lines.append(
            f'  <text x="{xr+1}" y="{y_end - 3}" font-size="9">{label}</text>'
        )
    x += UNITS_PER_FOOT

# Horizontal lines
y = y_start
while y <= y_end + 0.01:
    yr = round(y, 1)
    ft = (yr) / UNITS_PER_FOOT
    ft_int = round(ft)
    is_5ft = abs(ft_int % 5) == 0 and abs(ft - ft_int) < 0.05

    sw = '1.0' if is_5ft else '0.4'
    grid_lines.append(
        f'  <line x1="{x_start}" y1="{yr}" x2="{x_end}" y2="{yr}" '
        f'stroke-width="{sw}" />'
    )
    if is_5ft:
        label = f"{ft_int:.0f}ft"
        grid_lines.append(
            f'  <text x="{x_start + 2}" y="{yr - 2}" font-size="9">{label}</text>'
        )
        grid_lines.append(
            f'  <text x="{x_end - 30}" y="{yr - 2}" font-size="9">{label}</text>'
        )
    y += UNITS_PER_FOOT

grid_lines.append('</g>')

# 3. Re-stamp perimeter lights from JSON ─────────────────────────────────────
with open(json_in, 'r') as f:
    zones = json.load(f)

light_lines = ['<!-- PERIMETER LIGHTS -->',
               '<g id="perimeter_lights" fill="#FF0000" stroke="#FFFFFF" stroke-width="1.5">']
total = 0
for zone, lights in zones.items():
    light_lines.append(f'  <!-- {zone} -->')
    for i, light in enumerate(lights):
        safe_id = re.sub(r'[^a-z0-9_]', '_', zone.lower())
        if zone == "Wall lights":
            # Render as square with bright blue fill
            light_lines.append(
                f'  <rect id="light_{safe_id}_{i}" fill="#00D2FF" '
                f'x="{light["x"] - 5.5}" y="{light["y"] - 5.5}" width="11" height="11" />'
            )
        elif zone == "Security Cameras":
            # Render as orange star (Increased size)
            star_pts = "0,-10.5 3,-4 10.5,-4 5,1 6,8.5 0,4.5 -6,8.5 -5,1 -10.5,-4 -3,-4"
            light_lines.append(
                f'  <polygon id="light_{safe_id}_{i}" fill="#FF8C00" '
                f'points="{star_pts}" transform="translate({light["x"]},{light["y"]})" />'
            )
        else:
            # Render as circle
            light_lines.append(
                f'  <circle id="light_{safe_id}_{i}" '
                f'cx="{light["x"]}" cy="{light["y"]}" r="5.5" />'
            )
        total += 1
light_lines.append('</g>')

# 3c. Add Legend ─────────────────────────────────────────────────────────────
legend_star_pts = "0,-10.5 3,-4 10.5,-4 5,1 6,8.5 0,4.5 -6,8.5 -5,1 -10.5,-4 -3,-4"
legend_lines = [
    '<!-- LEGEND -->',
    '<g id="legend" font-family="Arial,Helvetica,sans-serif" font-size="10" fill="#333333">',
    '  <rect x="495" y="1100" width="180" height="70" fill="#FFFFFF" fill-opacity="0.8" stroke="#0055cc" stroke-width="1" rx="5" />',
    '  <circle cx="515" cy="1115" r="5.5" fill="#FF0000" stroke="#FFFFFF" stroke-width="1" />',
    '  <text x="530" y="1119">Soffit Light</text>',
    '  <rect x="509.5" y="1130.5" width="11" height="11" fill="#00D2FF" stroke="#FFFFFF" stroke-width="1" />',
    '  <text x="530" y="1139">Wall Light</text>',
    f'  <polygon points="{legend_star_pts}" fill="#FF8C00" stroke="#FFFFFF" stroke-width="1" transform="translate(515,1156)" />',
    '  <text x="530" y="1160">Security Camera</text>',
    '</g>'
]

# 3b. Raw-unit coordinate labels every 50 units — top row and right column ──
#     These match exactly what you type in perimeter_lights.json.
coord_lines = [
    '<!-- RAW COORD LABELS -->',
    '<g id="raw_coords" font-family="Arial,Helvetica,sans-serif" font-size="9" '
    'fill="#b85c00" opacity="0.85">',
]

# Top edge: X labels every 50 units
x = x_start
while x <= x_end + 0.01:
    xr = round(x)
    if xr % 50 == 0:
        coord_lines.append(
            f'  <text x="{xr + 1}" y="{y_start - 3}" font-size="9" '
            f'font-weight="bold">X={xr}</text>'
        )
        coord_lines.append(
            f'  <text x="{xr + 1}" y="{y_end + 10}" font-size="9" '
            f'font-weight="bold">X={xr}</text>'
        )
    x += 1 # Increment by 1 unit to check every integer
    if x > x_end + 0.01: break

# Right edge: Y labels every 50 units
y = y_start
while y <= y_end + 0.01:
    yr = round(y)
    if yr % 50 == 0:
        coord_lines.append(
            f'  <text x="{x_start - 35}" y="{yr + 3}" font-size="9" '
            f'font-weight="bold">Y={yr}</text>'
        )
        coord_lines.append(
            f'  <text x="{x_end + 2}" y="{yr + 3}" font-size="9" '
            f'font-weight="bold">Y={yr}</text>'
        )
    y += 1 # Increment by 1 unit to check every integer
    if y > y_end + 0.01: break

coord_lines.append('</g>')

# 4. Inject both blocks before </svg> ─────────────────────────────────────────
injection = '\n'.join(light_lines) + '\n' + '\n'.join(grid_lines) + '\n' + '\n'.join(coord_lines) + '\n' + '\n'.join(legend_lines) + '\n'
text = text.replace('</svg>', injection + '</svg>')


# 5. Surgical Crop: Adjust viewBox and dimensions to remove whitespace
# Original viewBox was "-500 -500 2000 2500"
# We'll crop to roughly encompass our grid and lights: [-150, -150, 1100, 1400]
text = re.sub(r'viewBox="-500 -500 2000 2500"', 'viewBox="-150 -150 1100 1400"', text, flags=re.IGNORECASE)
text = re.sub(r'\bwidth="2000"', 'width="1100"', text, count=1, flags=re.IGNORECASE)
text = re.sub(r'\bheight="2500"', 'height="1400"', text, count=1, flags=re.IGNORECASE)

# 6. Write output ─────────────────────────────────────────────────────────────

with open(outfile, 'w') as f:
    f.write(text)

print(f"Grid SVG written → {outfile}")
print(f"  Source : floorplan_annotated.svg")
print(f"  Scale  : {UNITS_PER_FOOT:.1f} canvas-units / foot")
print(f"  Lights : {total} dots re-stamped")
