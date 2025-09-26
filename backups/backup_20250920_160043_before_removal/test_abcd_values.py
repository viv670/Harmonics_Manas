"""
Test to verify ABCD pattern values match in console and viewer
"""
import pandas as pd
from extremum import detect_extremum_points
from formed_and_unformed_patterns import detect_abcd_patterns_fast

# Read and prepare data
df = pd.read_csv('btcusdt_1d.csv')
print(f"Total rows in CSV: {len(df)}")

# Capitalize column names
df.columns = [col.capitalize() for col in df.columns]

# Convert time column to datetime
df['Time'] = pd.to_datetime(df['Time'])
df.set_index('Time', inplace=True)

# Detect extremum points
print("\n=== Detecting Extremum Points ===")
extremum_points = detect_extremum_points(df, length=1)
print(f"Found {len(extremum_points)} extremum points")

# Show first 10 extremum points to verify D=74508.00 doesn't exist
print("\nFirst 20 extremum points:")
for i, (time, price, is_high) in enumerate(extremum_points[:20]):
    point_type = "High" if is_high else "Low"
    print(f"  [{i}] {time}: {price:.2f} ({point_type})")

# Detect ABCD patterns
print("\n=== Detecting ABCD Patterns ===")
patterns = detect_abcd_patterns_fast(extremum_points, log_details=True)

print(f"\n=== Total Patterns Found: {len(patterns)} ===")

# Show first pattern details
if patterns:
    pattern = patterns[0]
    print(f"\nFirst pattern details:")
    print(f"  Name: {pattern['name']}")
    print(f"  Type: {pattern['type']}")
    print(f"  Points:")
    for point_name, point_data in pattern['points'].items():
        print(f"    {point_name}: {point_data['price']:.2f} at {point_data['time']}")

    # Verify these points exist in extremum points
    print(f"\n  Verifying points exist in extremum data:")
    for point_name, point_data in pattern['points'].items():
        found = False
        for ep_time, ep_price, _ in extremum_points:
            if ep_time == point_data['time'] and abs(ep_price - point_data['price']) < 0.01:
                found = True
                break
        print(f"    {point_name} ({point_data['price']:.2f}): {'FOUND' if found else 'NOT FOUND'}")

# Check for the specific pattern mentioned in console
print("\n=== Looking for specific pattern from console ===")
target_values = {
    'A': 92810.64,
    'B': 81134.66,
    'C': 87453.67,
    'D': 74508.00
}

print(f"Console showed: A={target_values['A']}, B={target_values['B']}, C={target_values['C']}, D={target_values['D']}")

# Check if D=74508.00 exists in extremum points
d_found = False
for time, price, is_high in extremum_points:
    if abs(price - 74508.00) < 1.0:
        d_found = True
        print(f"\nD point 74508.00 found at {time} ({'High' if is_high else 'Low'})")
        break

if not d_found:
    print(f"\nD point 74508.00 NOT found in extremum points!")
    print("This suggests the console output may be showing a different value or calculated projection")

# Find patterns matching the console values
matching_patterns = []
for p in patterns:
    if (abs(p['points']['A']['price'] - target_values['A']) < 1.0 and
        abs(p['points']['B']['price'] - target_values['B']) < 1.0 and
        abs(p['points']['C']['price'] - target_values['C']) < 1.0):
        matching_patterns.append(p)
        print(f"\nFound pattern with matching A,B,C:")
        print(f"  A: {p['points']['A']['price']:.2f}")
        print(f"  B: {p['points']['B']['price']:.2f}")
        print(f"  C: {p['points']['C']['price']:.2f}")
        print(f"  D: {p['points']['D']['price']:.2f} (actual D in pattern)")

if not matching_patterns:
    print("\nNo patterns found matching the console A,B,C values")