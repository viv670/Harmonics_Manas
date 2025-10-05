"""
Quick comparison using existing backtest Excel results
"""

import pandas as pd
import os

# Find the most recent backtest Excel file
results_dir = 'backtest_results'
excel_files = [f for f in os.listdir(results_dir) if f.endswith('.xlsx') and not f.startswith('~$')]
excel_files.sort(reverse=True)  # Most recent first

if not excel_files:
    print("No backtest results found!")
    exit(1)

latest_file = os.path.join(results_dir, excel_files[0])
print(f"Reading: {latest_file}")
print("="*80)

# Read the Pattern Details sheet
try:
    pattern_details = pd.read_excel(latest_file, sheet_name='Pattern Details')
    print(f"\nFound {len(pattern_details)} patterns in Excel")
    print("\nColumns:", list(pattern_details.columns))
except Exception as e:
    print(f"Error reading Excel: {e}")
    exit(1)

# Filter successful patterns
successful = pattern_details[pattern_details['Status'] == 'success'].copy()
print(f"\nSuccessful patterns: {len(successful)}")

# Show first few successful patterns with their ABCD points
print("\n" + "="*80)
print("SUCCESSFUL PATTERNS (from Excel):")
print("="*80)

for i, row in successful.head(10).iterrows():
    print(f"\n{i+1}. {row.get('Pattern Type', '?')} - {row.get('Pattern Name', 'Unknown')[:40]}")
    print(f"   A: idx={row.get('A_Index', '?')}, price={row.get('A_Price', '?')}")
    print(f"   B: idx={row.get('B_Index', '?')}, price={row.get('B_Price', '?')}")
    print(f"   C: idx={row.get('C_Index', '?')}, price={row.get('C_Price', '?')}")
    print(f"   D: idx={row.get('D_Index', '?')}, price={row.get('D_Price', '?')}")
    print(f"   Status: {row.get('Status', '?')}")

if len(successful) > 10:
    print(f"\n... and {len(successful) - 10} more successful patterns")

# Now detect GUI patterns
print("\n" + "="*80)
print("Detecting GUI patterns...")
print("="*80)

# Load data
data = pd.read_csv('btcusdt_1d.csv')
data.rename(columns={
    'time': 'Date',
    'open': 'Open',
    'high': 'High',
    'low': 'Low',
    'close': 'Close',
    'volume': 'Volume'
}, inplace=True)
data['Date'] = pd.to_datetime(data['Date'])
data.set_index('Date', inplace=True)

from gui_compatible_detection import detect_all_gui_patterns
from extremum import detect_extremum_points as find_extremum_points

extremums = find_extremum_points(data, length=1)
data_with_date = data.reset_index()

all_abcd_full, all_xabcd_full = detect_all_gui_patterns(
    extremums,
    data_with_date,
    max_patterns=200,
    validate_d_crossing=False
)

# Get formed patterns
gui_formed = [p for p in all_abcd_full + all_xabcd_full if 'points' in p and 'D' in p['points']]

print(f"\nGUI formed patterns: {len(gui_formed)}")

# Extract ABCD keys from GUI patterns
gui_abcd_keys = []
for pattern in gui_formed:
    indices = pattern.get('indices', {})
    key = (
        indices.get('A'),
        indices.get('B'),
        indices.get('C'),
        indices.get('D')
    )
    gui_abcd_keys.append({
        'key': key,
        'name': pattern.get('name', 'Unknown'),
        'type': pattern.get('pattern_type', 'ABCD')
    })

print("\nGUI FORMED PATTERNS:")
print("="*80)
for i, p in enumerate(gui_abcd_keys, 1):
    print(f"{i}. {p['type']} - {p['name'][:40]}")
    print(f"   ABCD: A={p['key'][0]}, B={p['key'][1]}, C={p['key'][2]}, D={p['key'][3]}")

# Extract ABCD keys from successful Excel patterns
excel_abcd_keys = []
for i, row in successful.iterrows():
    key = (
        int(row.get('A_Index', -1)) if pd.notna(row.get('A_Index')) else None,
        int(row.get('B_Index', -1)) if pd.notna(row.get('B_Index')) else None,
        int(row.get('C_Index', -1)) if pd.notna(row.get('C_Index')) else None,
        int(row.get('D_Index', -1)) if pd.notna(row.get('D_Index')) else None
    )
    excel_abcd_keys.append({
        'key': key,
        'name': row.get('Pattern Name', 'Unknown'),
        'type': row.get('Pattern Type', 'Unknown')
    })

# Compare
print("\n" + "="*80)
print("COMPARISON:")
print("="*80)

gui_keys_set = set(p['key'] for p in gui_abcd_keys)
excel_keys_set = set(p['key'] for p in excel_abcd_keys)

overlaps = gui_keys_set.intersection(excel_keys_set)

print(f"\nGUI formed patterns: {len(gui_keys_set)}")
print(f"Successful tracked patterns: {len(excel_keys_set)}")
print(f"Overlapping (same ABCD points): {len(overlaps)}")

if overlaps:
    print(f"\n✅ YES! {len(overlaps)} of the {len(gui_keys_set)} GUI patterns ARE among the {len(excel_keys_set)} successful patterns!")
    print("\nOverlapping patterns:")
    for key in overlaps:
        gui_p = next(p for p in gui_abcd_keys if p['key'] == key)
        excel_p = next(p for p in excel_abcd_keys if p['key'] == key)
        print(f"\n  ABCD: A={key[0]}, B={key[1]}, C={key[2]}, D={key[3]}")
        print(f"    GUI: {gui_p['type']} - {gui_p['name'][:30]}")
        print(f"    Excel: {excel_p['type']} - {excel_p['name'][:30]}")
else:
    print(f"\n❌ NO! The {len(gui_keys_set)} GUI patterns are NOT in the {len(excel_keys_set)} successful patterns")

# Show unique to GUI
gui_only = gui_keys_set - excel_keys_set
if gui_only:
    print(f"\n{len(gui_only)} GUI patterns NOT in successful patterns:")
    for key in list(gui_only):
        gui_p = next(p for p in gui_abcd_keys if p['key'] == key)
        print(f"  - {gui_p['name'][:40]}: A={key[0]}, B={key[1]}, C={key[2]}, D={key[3]}")

# Show unique to successful
excel_only = excel_keys_set - gui_keys_set
if excel_only:
    print(f"\n{len(excel_only)} Successful patterns NOT in GUI:")
    for key in list(excel_only)[:10]:
        excel_p = next(p for p in excel_abcd_keys if p['key'] == key)
        print(f"  - {excel_p['name'][:40]}: A={key[0]}, B={key[1]}, C={key[2]}, D={key[3]}")
    if len(excel_only) > 10:
        print(f"  ... and {len(excel_only) - 10} more")

print("\n" + "="*80)
