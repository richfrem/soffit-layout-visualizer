import json
import re
import os

# Go up one level from the scripts directory since this script runs from within 'scripts' or from evidence dir.
base_dir = os.path.dirname(os.path.abspath(__file__))
if os.path.basename(base_dir) == 'scripts':
    base_dir = os.path.dirname(base_dir)

json_in = os.path.join(base_dir, "perimeter_lights.json")
svg_grid = os.path.join(base_dir, "1517SanJuan-new-floorplan-GRID.svg")

with open(json_in, "r") as f:
    zones = json.load(f)

# Inject into the GRID SVG
with open(svg_grid, "r") as f:
    grid_content = f.read()

grid_content = re.sub(r'<!-- PERIMETER LIGHTS -->.*?</g>\n', '', grid_content, flags=re.DOTALL)

svg_injection = ['<!-- PERIMETER LIGHTS -->', '<g id="perimeter_lights" fill="#FF0000" stroke="#FFFFFF" stroke-width="1.5">']

for zone, lights in zones.items():
    svg_injection.append(f'  <!-- {zone} -->')
    for i, light in enumerate(lights):
        svg_injection.append(f'  <circle id="light_{zone.replace(" ", "_").lower()}_{i}" cx="{light["x"]}" cy="{light["y"]}" r="5.5" />')
svg_injection.append('</g>')

# Inject before debug grid, or before </svg> if no debug grid
if '<!-- DEBUG GRID -->' in grid_content:
    grid_content = grid_content.replace('<!-- DEBUG GRID -->', '\n'.join(svg_injection) + '\n<!-- DEBUG GRID -->')
else:
    grid_content = grid_content.replace('</svg>', '\n'.join(svg_injection) + '\n</svg>')

with open(svg_grid, "w") as f:
    f.write(grid_content)

print(f"Rendered {sum(len(l) for l in zones.values())} lights from JSON onto the GRID svg!")
