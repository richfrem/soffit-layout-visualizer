import json
import math
import os

# Scale Constants
UNITS_PER_INCH = 1.3
INCHES_PER_FOOT = 12

def units_to_imperial(units):
    total_inches = units / UNITS_PER_INCH
    feet = int(total_inches // INCHES_PER_FOOT)
    inches = round(total_inches % INCHES_PER_FOOT, 1)
    return f"{feet}' {inches}\""

base_dir = os.path.dirname(os.path.abspath(__file__))
if os.path.basename(base_dir) == 'scripts':
    base_dir = os.path.dirname(base_dir)
json_in = os.path.join(base_dir, "perimeter_lights.json")

try:
    with open(json_in, 'r') as f:
        zones = json.load(f)
except Exception as e:
    print(f"Error loading {json_in}: {e}")
    exit(1)

print("="*60)
print("ARCHITECTURAL LIGHTING SPACING REPORT")
print(f"Scale Factor: {UNITS_PER_INCH} canvas units = 1 logical inch")
print("="*60)

for zone_name, lights in zones.items():
    print(f"\n--- Zone: {zone_name} ---")
    if not lights:
        print("  No lights defined.")
        continue
    
    print(f"  Light 1: Anchor point at (X:{lights[0]['x']}, Y:{lights[0]['y']})")
    
    # Calculate spacing between consecutive lights
    for i in range(1, len(lights)):
        dx = lights[i]['x'] - lights[i-1]['x']
        dy = lights[i]['y'] - lights[i-1]['y']
        distance_units = math.sqrt(dx**2 + dy**2)
        imperial_dist = units_to_imperial(distance_units)
        
        print(f"  Gap {i} to {i+1}: {imperial_dist}   | raw units: {distance_units:.1f}")

    # Calculate overall span of the zone
    if len(lights) > 1:
        total_dx = lights[-1]['x'] - lights[0]['x']
        total_dy = lights[-1]['y'] - lights[0]['y']
        total_units = math.sqrt(total_dx**2 + total_dy**2)
        total_imperial = units_to_imperial(total_units)
        print(f"  => Total Span (First to Last): {total_imperial}")

print("\n" + "="*60)
