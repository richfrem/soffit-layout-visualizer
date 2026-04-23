import re

svg_in = "/Users/richardfremmerlid/Renos/2024Roof and Gutters/A_Evidence_and_Forensics/1517SanJuan-new-floorplan-ARROWS.svg"

with open(svg_in, 'r') as f:
    content = f.read()

# Make the canvas enormous with tons of padding
content = re.sub(
    r'width="[^"]+"(\s*)height="[^"]+"(\s*)viewBox="[^"]+"',
    r'width="2000"\1height="2500"\2viewBox="-500 -500 2000 2500"',
    content
)

# Insert a solid white background right after <defs> so the padding isn't transparent
if '<rect id="bg_canvas"' not in content:
    bg_rect = '\n<rect id="bg_canvas" x="-1000" y="-1000" width="4000" height="4000" fill="#ffffff" />\n'
    content = content.replace('</defs>', '</defs>' + bg_rect)

with open(svg_in, 'w') as f:
    f.write(content)

print("Canvas widened and background whitened")
