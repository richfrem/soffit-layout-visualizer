"""
render_dimensions.py
Reads dimension_lines.json and stamps architectural dimension arrows
onto floorplan_grid.svg.

Each arrow:
  • double-headed architectural style (← label →)
  • label shows real-world distance in  ft' in"
  • computed automatically from XY coordinate distance
  • scale: UNITS_PER_INCH = 1.3  (i.e. 1.3 canvas-units per inch)

Run this after   render_lights_to_grid.py   to layer dimensions on top.
Or run as a standalone to toggle them independently.

Usage:
  python3 scripts/render_dimensions.py
"""
import json
import math
import os
import re

# ── Scale ────────────────────────────────────────────────────────────────────
UNITS_PER_INCH = 1.3

# ── Paths ────────────────────────────────────────────────────────────────────
base_dir = os.path.dirname(os.path.abspath(__file__))
if os.path.basename(base_dir) == 'scripts':
    base_dir = os.path.dirname(base_dir)

dim_json = os.path.join(base_dir, "dimension_lines.json")
svg_path = os.path.join(base_dir, "floorplan_grid.svg")

# ── Helpers ──────────────────────────────────────────────────────────────────

def units_to_imperial(units: float) -> str:
    """Convert canvas units to  ft' in\"  string."""
    total_inches = units / UNITS_PER_INCH
    feet = int(total_inches // 12)
    inches = total_inches % 12
    # Round inches to nearest ¼"
    inches_q = round(inches * 4) / 4
    if inches_q == 12:
        feet += 1
        inches_q = 0
    if inches_q == int(inches_q):
        return f"{feet}'{int(inches_q)}\""
    return f"{feet}'{inches_q}\""


def arrow_svg(x1, y1, x2, y2, label, offset, color, arrow_id):
    """
    Build SVG for a double-headed architectural dimension arrow.
    Works for horizontal OR vertical lines; offset is perpendicular shift.
    """
    dx = x2 - x1
    dy = y2 - y1
    length = math.hypot(dx, dy)
    if length == 0:
        return ""

    # Unit vector along the line, and perpendicular (for offset)
    ux, uy = dx / length, dy / length
    px, py = -uy, ux          # perpendicular unit vector

    # Shift both endpoints by offset in the perpendicular direction
    ax1 = round(x1 + px * offset, 2)
    ay1 = round(y1 + py * offset, 2)
    ax2 = round(x2 + px * offset, 2)
    ay2 = round(y2 + py * offset, 2)

    # Mid-point for the label
    mx = round((ax1 + ax2) / 2, 2)
    my = round((ay1 + ay2) / 2, 2)

    # Text rotation angle (keep text upright: flip if arrow goes right-to-left or bottom-to-top)
    angle = math.degrees(math.atan2(dy, dx))
    if angle > 90 or angle < -90:
        angle += 180

    # Arrowhead half-size
    head = 6
    marker_id = f"arrowhead_{arrow_id}"

    svg = f"""
  <!-- Dimension: {arrow_id} -->
  <defs>
    <marker id="{marker_id}" markerWidth="6" markerHeight="4"
            refX="6" refY="2" orient="auto">
      <polygon points="0 0, 6 2, 0 4" fill="{color}" />
    </marker>
  </defs>
  <line x1="{ax1}" y1="{ay1}" x2="{ax2}" y2="{ay2}"
        stroke="{color}" stroke-width="1.5"
        marker-start="url(#{marker_id})"
        marker-end="url(#{marker_id})" />
  <text x="{mx}" y="{my}"
        transform="rotate({angle:.1f},{mx},{my})"
        text-anchor="middle"
        dominant-baseline="text-after-edge"
        font-family="Arial,Helvetica,sans-serif"
        font-size="11" font-weight="bold" fill="{color}"
        stroke="white" stroke-width="2.5" paint-order="stroke"
        >{label}</text>"""
    return svg


# ── Main ─────────────────────────────────────────────────────────────────────
with open(dim_json, 'r') as f:
    config = json.load(f)

with open(svg_path, 'r') as f:
    svg_text = f.read()

# Remove any previously stamped dimension block
svg_text = re.sub(r'<!-- DIMENSION ARROWS -->.*?<!-- /DIMENSION ARROWS -->',
                  '', svg_text, flags=re.DOTALL)

if not config.get("enabled", True):
    print("Dimension arrows disabled in dimension_lines.json (enabled=false). SVG unchanged.")
else:
    parts = ['<!-- DIMENSION ARROWS -->']
    count = 0
    for dim in config.get("dimensions", []):
        if not dim.get("visible", True):
            continue
        x1, y1 = dim["x1"], dim["y1"]
        x2, y2 = dim["x2"], dim["y2"]
        
        # Use manual label if provided, else auto-calculate
        if "label" in dim and dim["label"]:
            label = dim["label"]
        else:
            length = math.hypot(x2 - x1, y2 - y1)
            label = units_to_imperial(length)
            
        offset = dim.get("label_offset", -20)
        color = dim.get("color", "#0055cc")
        arrow_id = dim.get("id", f"dim_{count}")
        parts.append(arrow_svg(x1, y1, x2, y2, label, offset, color, arrow_id))
        count += 1
    parts.append('<!-- /DIMENSION ARROWS -->')

    injection = '\n'.join(parts) + '\n'
    svg_text = svg_text.replace('</svg>', injection + '</svg>')

    with open(svg_path, 'w') as f:
        f.write(svg_text)
    print(f"✓ Stamped {count} dimension arrows onto {svg_path}")

print()
print("To HIDE all arrows:  set  \"enabled\": false  in dimension_lines.json  then re-run.")
print("To hide one arrow:   set  \"visible\": false  on that entry  then re-run.")
