import re

svg_path = "/Users/richardfremmerlid/Renos/2024Roof and Gutters/A_Evidence_and_Forensics/1517SanJuan-new-floorplan.svg"
out_path = "/Users/richardfremmerlid/Renos/2024Roof and Gutters/A_Evidence_and_Forensics/1517SanJuan-new-floorplan-ARROWS.svg"

with open(svg_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Add defs if not there, or just inject at the end before </svg>
injection = """
<defs>
  <marker id="arrow" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
    <path d="M 0 0 L 10 5 L 0 10 z" fill="#D90429" />
  </marker>
</defs>
<g transform="translate(350, 900)" font-family="Arial, sans-serif" font-size="12" fill="#D90429" stroke="#D90429">
    
    <!-- BACK WALL (100" horizontal) -->
    <text x="50" y="-8" text-anchor="middle" stroke="none">100" (Back Wall)</text>
    <line x1="0" y1="0" x2="100" y2="0" stroke-width="1.5" marker-start="url(#arrow)" marker-end="url(#arrow)" />
    <!-- Back wall soffit -->
    <text x="50" y="20" text-anchor="middle" font-size="10" stroke="none">24" Soffit</text>

    <!-- LEFT WALL (111" vertical) -->
    <text x="-8" y="55" text-anchor="end" stroke="none">111" (Left Wall)</text>
    <line x1="0" y1="0" x2="0" y2="111" stroke-width="1.5" marker-start="url(#arrow)" marker-end="url(#arrow)" />
    <!-- Left wall soffit -->
    <text x="15" y="55" font-size="10" stroke="none">24" Soffit</text>

    <!-- RIGHT WALL (76" vertical) -->
    <text x="108" y="38" text-anchor="start" stroke="none">(Right) 76"</text>
    <line x1="100" y1="0" x2="100" y2="76" stroke-width="1.5" marker-start="url(#arrow)" marker-end="url(#arrow)" />
    <!-- Right wall soffit -->
    <text x="55" y="38" text-anchor="end" font-size="10" stroke="none">24" Soffit</text>

</g>
</svg>
"""

# if there was already an arrow injection, we want to replace it
if '<marker id="arrow"' in content:
    # replace everything from <defs>\n  <marker id="arrow" to </svg>
    content = re.sub(r'<defs>\s*<marker id="arrow".*?</svg>', injection, content, flags=re.DOTALL)
else:
    content = content.replace("</svg>", injection)


with open(out_path, 'w', encoding='utf-8') as f:
    f.write(content)

print(f"Updated {out_path}")
