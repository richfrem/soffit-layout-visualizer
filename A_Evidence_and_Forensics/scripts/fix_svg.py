import re

svg_path = "/Users/richardfremmerlid/Renos/2024Roof and Gutters/A_Evidence_and_Forensics/1517SanJuan-new-floorplan-ARROWS.svg"

with open(svg_path, 'r', encoding='utf-8') as f:
    content = f.read()

injection = """<g transform="translate(350, 750)" font-family="Arial, sans-serif" font-size="12" fill="#D90429" stroke="#D90429">
    <!-- Back Wall Span -->
    <line x1="0" y1="-15" x2="100" y2="-15" stroke-width="1.5" marker-start="url(#arrow)" marker-end="url(#arrow)" />
    <text x="50" y="-20" text-anchor="middle" stroke="none">100"</text>
    <text x="50" y="-2" text-anchor="middle" font-size="10" stroke="none">24" Soffit</text>

    <!-- Left Wall Span -->
    <line x1="-15" y1="0" x2="-15" y2="111" stroke-width="1.5" marker-start="url(#arrow)" marker-end="url(#arrow)" />
    <text x="-20" y="55" text-anchor="end" stroke="none">111"</text>
    <text x="-20" y="68" text-anchor="end" font-size="10" stroke="none">24" Soffit</text>

    <!-- Right Wall Span -->
    <line x1="115" y1="0" x2="115" y2="76" stroke-width="1.5" marker-start="url(#arrow)" marker-end="url(#arrow)" />
    <text x="120" y="38" text-anchor="start" stroke="none">76"</text>
    <text x="120" y="51" text-anchor="start" font-size="10" stroke="none">24" Soffit</text>
</g>"""

# Using regex to replace the entire <g transform="translate(350, ..."> block
content = re.sub(r'<g transform="translate\(350, \d+\)".*?</g>', injection, content, flags=re.DOTALL)

with open(svg_path, 'w', encoding='utf-8') as f:
    f.write(content)
print("done")
