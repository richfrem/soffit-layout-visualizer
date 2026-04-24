"""
render_lights_to_grid.py
Reads perimeter_lights.json and stamps all red dot markers onto floorplan_grid.svg.
Run any time you edit the JSON to see updated placement.
"""
import json
import re
import os

base_dir = os.path.dirname(os.path.abspath(__file__))
if os.path.basename(base_dir) == 'scripts':
    base_dir = os.path.dirname(base_dir)

json_in  = os.path.join(base_dir, "perimeter_lights.json")
svg_grid = os.path.join(base_dir, "floorplan_grid.svg")

with open(json_in, 'r') as f:
    zones = json.load(f)

with open(svg_grid, 'r') as f:
    content = f.read()

# Remove any previously stamped lights
content = re.sub(r'<!-- PERIMETER LIGHTS -->.*?</g>\n?', '', content, flags=re.DOTALL)

svg_lines = [
    '<!-- PERIMETER LIGHTS -->',
    '<g id="perimeter_lights" fill="#FF0000" stroke="#FFFFFF" stroke-width="1.5">'
]
total = 0
for zone, lights in zones.items():
    svg_lines.append(f'  <!-- {zone} -->')
    for i, light in enumerate(lights):
        safe_id = re.sub(r'[^a-z0-9_]', '_', zone.lower())
        if zone == "Wall lights":
            # Render as square with bright blue fill
            svg_lines.append(
                f'  <rect id="light_{safe_id}_{i}" fill="#00D2FF" '
                f'x="{light["x"] - 5.5}" y="{light["y"] - 5.5}" width="11" height="11" />'
            )
        elif zone == "Security Cameras":
            # Render as orange star (Increased size)
            star_pts = "0,-10.5 3,-4 10.5,-4 5,1 6,8.5 0,4.5 -6,8.5 -5,1 -10.5,-4 -3,-4"
            svg_lines.append(
                f'  <polygon id="light_{safe_id}_{i}" fill="#FF8C00" '
                f'points="{star_pts}" transform="translate({light["x"]},{light["y"]})" />'
            )
        else:
            # Render as circle
            svg_lines.append(
                f'  <circle id="light_{safe_id}_{i}" '
                f'cx="{light["x"]}" cy="{light["y"]}" r="5.5" />'
            )
        total += 1
svg_lines.append('</g>')

# --- LEGEND ---
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

# Remove old legend if exists
content = re.sub(r'<!-- LEGEND -->.*?</g>\n?', '', content, flags=re.DOTALL)

if '<!-- DEBUG GRID -->' in content:
    content = content.replace('<!-- DEBUG GRID -->', '\n'.join(svg_lines) + '\n' + '\n'.join(legend_lines) + '\n<!-- DEBUG GRID -->')
else:
    content = content.replace('</svg>', '\n'.join(svg_lines) + '\n' + '\n'.join(legend_lines) + '\n</svg>')

with open(svg_grid, 'w') as f:
    f.write(content)

print(f"✓ Rendered {total} lights across {len(zones)} zones → {svg_grid}")
