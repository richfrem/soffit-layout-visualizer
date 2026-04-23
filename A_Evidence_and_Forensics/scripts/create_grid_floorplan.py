import sys

infile = "/Users/richardfremmerlid/Renos/2024Roof and Gutters/A_Evidence_and_Forensics/1517SanJuan-new-floorplan.svg"
outfile = "/Users/richardfremmerlid/Renos/2024Roof and Gutters/A_Evidence_and_Forensics/1517SanJuan-new-floorplan-GRID.svg"

with open(infile, 'r') as f:
    text = f.read()

# 1. Expand the viewBox and canvas dimensions
text = text.replace('width="708.15997"\n   height="1056"\n   viewBox="0 0 708.15997 1056"', 'width="2000"\n   height="2500"\n   viewBox="-500 -500 2000 2500"')

# 2. Inject the bg_canvas right inside the main group
# We find:
#   <g
#      id="g1"
#      inkscape:groupmode="layer"
#      inkscape:label="1">
g1_start = '  <g\n     id="g1"\n     inkscape:groupmode="layer"\n     inkscape:label="1">'
bg_canvas = '\n<rect id="bg_canvas" x="-1000" y="-1000" width="4000" height="4000" fill="#ffffff" />'
text = text.replace(g1_start, g1_start + bg_canvas)

# 3. Add the debug grid at the end before </svg>
grid_svg = ['<!-- DEBUG GRID -->', '<g id="debug_grid" stroke="#0000FF" stroke-width="1" opacity="0.4" font-family="monospace" font-size="16" fill="#0000FF">']

# Spanning from -200 to 1200 dynamically to match the newly expanded viewBox visually.
for x in range(-200, 1200, 50):
    grid_svg.append(f'  <line x1="{x}" y1="-200" x2="{x}" y2="1300" />')
    if x % 100 == 0:
        grid_svg.append(f'  <text x="{x + 2}" y="-100">X={x}</text>')
        grid_svg.append(f'  <text x="{x + 2}" y="1200">X={x}</text>')

for y in range(-200, 1300, 50):
    grid_svg.append(f'  <line x1="-200" y1="{y}" x2="1000" y2="{y}" />')
    if y % 100 == 0:
        grid_svg.append(f'  <text x="-150" y="{y - 5}">Y={y}</text>')
        grid_svg.append(f'  <text x="850" y="{y - 5}">Y={y}</text>')

grid_svg.append('</g>')

text = text.replace('</svg>', '\n'.join(grid_svg) + '\n</svg>')

with open(outfile, 'w') as f:
    f.write(text)

print(f"Created {outfile} successfully")
