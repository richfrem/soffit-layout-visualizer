import re

svg_path = "/Users/richardfremmerlid/Renos/2024Roof and Gutters/A_Evidence_and_Forensics/1517SanJuan-new-floorplan.svg"
out_path = "/Users/richardfremmerlid/Renos/2024Roof and Gutters/A_Evidence_and_Forensics/1517SanJuan-new-floorplan-ARROWS.svg"

with open(svg_path, 'r', encoding='utf-8') as f:
    content = f.read()

injection = """
<defs>
  <marker id="arrow" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
    <path d="M 0 0 L 10 5 L 0 10 z" fill="#0077B6" />
  </marker>
</defs>

<!-- Translating to roughly where the entryway is. 
Since the text was overlapping rooms, we adjust the offsets so they render purely in the whitespace of the exterior Entryway -->
<g transform="translate(350, 850)" font-family="Arial, sans-serif" font-size="12" fill="#0077B6" stroke="#0077B6">
    
    <!-- BACK WALL (100" horizontal) 
         Shifted DOWN (+y) so it sits outside the house in the yard -->
    <line x1="0" y1="20" x2="100" y2="20" stroke-width="1.5" marker-start="url(#arrow)" marker-end="url(#arrow)" />
    <text x="50" y="15" text-anchor="middle" stroke="none">100"</text>
    <text x="50" y="32" text-anchor="middle" font-size="10" stroke="none">24" Soffit</text>

    <!-- LEFT WALL (111" vertical) 
         Shifted RIGHT (+x) so it sits outside the garage in the yard -->
    <line x1="20" y1="0" x2="20" y2="111" stroke-width="1.5" marker-start="url(#arrow)" marker-end="url(#arrow)" />
    <!-- Rotating text so it aligns with arrow -->
    <text x="25" y="55" text-anchor="start" stroke="none">111"</text>
    <text x="25" y="68" font-size="10" stroke="none">24" Soffit</text>

    <!-- RIGHT WALL (76" vertical) 
         Shifted LEFT (-x) so it sits outside the master bed in the yard -->
    <line x1="80" y1="0" x2="80" y2="76" stroke-width="1.5" marker-start="url(#arrow)" marker-end="url(#arrow)" />
    <text x="75" y="38" text-anchor="end" stroke="none">76"</text>
    <text x="75" y="51" text-anchor="end" font-size="10" stroke="none">24" Soffit</text>

</g>
</svg>
"""

# if there was already an arrow injection, we want to replace it
if '<marker id="arrow"' in content:
    content = re.sub(r'<defs>\s*<marker id="arrow".*?</svg>', injection, content, flags=re.DOTALL)
else:
    content = content.replace("</svg>", injection)


with open(out_path, 'w', encoding='utf-8') as f:
    f.write(content)

print(f"Updated {out_path}")
