import re

svg_in = "/Users/richardfremmerlid/Renos/2024Roof and Gutters/A_Evidence_and_Forensics/1517SanJuan-new-floorplan-ARROWS.svg"

with open(svg_in, 'r') as f:
    content = f.read()

# Expand viewBox
content = re.sub(
    r'width="[^"]+"(\s*)height="[^"]+"(\s*)viewBox="[^"]+"',
    r'width="1108"\1height="1456"\2viewBox="-200 -200 1108 1456"',
    content
)

# Coordinates configuration
scale = 1.3
soffit_offset = 15
dot_radius = 5.5

# House corners roughly mapped to absolute coordinates
# Front Garage: x=30 to x=340, y=1099
# Front Master: x=455 to x=684, y=1053
# West Wall: x=30, y=1099 back to y=150
# East Wall: x=684, y=1053 back to y=150
# North Wall: x=30 to x=684, y=150

lights_svg = ['<!-- PERIMETER LIGHTS -->', '<g id="perimeter_lights" fill="#FF0000" stroke="#FFFFFF" stroke-width="1.5">']

def add_line_of_lights(x1, y1, x2, y2, n_lights, offset_x, offset_y, label):
    global lights_svg
    lights_svg.append(f"  <!-- {label} -->")
    # Linear interpolation
    for i in range(n_lights):
        fraction = i / max(1, (n_lights - 1))
        # Nudge slightly fully off the edge so we don't put a light on the exact corner
        fraction = 0.05 + 0.9 * fraction
        
        lx = x1 + (x2 - x1) * fraction + offset_x
        ly = y1 + (y2 - y1) * fraction + offset_y
        lights_svg.append(f'  <circle cx="{lx:.1f}" cy="{ly:.1f}" r="{dot_radius}" />')

# Front Garage (South): 4 lights. Y offset +15
add_line_of_lights(30, 1099, 340, 1099, 4, 0, 15, "Front Garage")

# Front Master (South): 3 lights. Y offset +15
add_line_of_lights(455, 1053, 684, 1053, 3, 0, 15, "Front Master")

# West Wall: length 949. Spacing ~7-8ft => 8 or 9 lights. X offset -15
add_line_of_lights(30, 1099, 30, 150, 9, -15, 0, "West Wall")

# East Wall: length 903. 9 lights. X offset +15
add_line_of_lights(684, 1053, 684, 150, 9, 15, 0, "East Wall")

# North Wall: length 654. 7 lights. Y offset -15
add_line_of_lights(30, 150, 684, 150, 8, 0, -15, "North Wall")

lights_svg.append('</g>')

# Inject before closing svg
content = content.replace('</svg>', '\n'.join(lights_svg) + '\n</svg>')

with open(svg_in, 'w') as f:
    f.write(content)

print("Injected!")
