import re

svg_path = "/Users/richardfremmerlid/Renos/2024Roof and Gutters/A_Evidence_and_Forensics/1517SanJuan-new-floorplan.svg"
out_path = "/Users/richardfremmerlid/Renos/2024Roof and Gutters/A_Evidence_and_Forensics/1517SanJuan-new-floorplan-DIMENSIONS.svg"

with open(svg_path, 'r', encoding='utf-8') as f:
    content = f.read()

injection = """
<g font-family="Arial, sans-serif" font-size="12" fill="#E63946" transform="translate(360, 750)">
    <rect x="-5" y="-15" width="130" height="85" fill="white" fill-opacity="0.8" stroke="#E63946" stroke-width="1.5" rx="4"/>
    <text x="0" y="0" font-weight="bold">NEW ENTRY DIMS</text>
    <text x="0" y="16">Back Wall: 100"</text>
    <text x="0" y="32">Left Wall: 111"</text>
    <text x="0" y="48">Right Wall: 76"</text>
    <text x="0" y="64">Soffit Width: 24"</text>
</g>
</svg>
"""

updated_content = content.replace("</svg>", injection)

with open(out_path, 'w', encoding='utf-8') as f:
    f.write(updated_content)

print(f"Created {out_path}")
