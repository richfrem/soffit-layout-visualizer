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
        safe_id = zone.replace(" ", "_").replace("(", "").replace(")", "").lower()
        svg_lines.append(
            f'  <circle id="light_{safe_id}_{i}" cx="{light["x"]}" cy="{light["y"]}" r="5.5" />'
        )
        total += 1
svg_lines.append('</g>')

if '<!-- DEBUG GRID -->' in content:
    content = content.replace('<!-- DEBUG GRID -->', '\n'.join(svg_lines) + '\n<!-- DEBUG GRID -->')
else:
    content = content.replace('</svg>', '\n'.join(svg_lines) + '\n</svg>')

with open(svg_grid, 'w') as f:
    f.write(content)

print(f"✓ Rendered {total} lights across {len(zones)} zones → {svg_grid}")
