"""
Extract all 87 successful patterns' ABCD points for manual comparison
"""

import pandas as pd
import os

# Find most recent Excel
results_dir = 'backtest_results'
excel_files = [f for f in os.listdir(results_dir) if f.endswith('.xlsx') and not f.startswith('~$')]
excel_files.sort(reverse=True)

latest_file = os.path.join(results_dir, excel_files[0])
print(f"Reading: {latest_file}\n")

# Read Pattern Details
pattern_details = pd.read_excel(latest_file, sheet_name='Pattern Details')

# Get successful patterns
successful = pattern_details[pattern_details['Status'] == 'success'].copy()

print(f"EXTRACTED ALL {len(successful)} SUCCESSFUL PATTERNS")
print("="*100)
print(f"{'#':<4} {'Type':<6} {'Pattern Name':<40} {'A':<6} {'B':<6} {'C':<6} {'D':<6}")
print("="*100)

all_patterns = []
for i, row in successful.iterrows():
    a_bar = row.get('A_Bar')
    b_bar = row.get('B_Bar')
    c_bar = row.get('C_Bar')
    d_bar = row.get('PRZ_Entry_Bar')

    if pd.isna(a_bar) or pd.isna(b_bar) or pd.isna(c_bar):
        continue

    a = int(a_bar)
    b = int(b_bar)
    c = int(c_bar)
    d = int(d_bar) if pd.notna(d_bar) else None

    ptype = str(row.get('Type', 'ABCD'))[:6]
    name = str(row.get('Subtype', 'Unknown'))[:40]

    all_patterns.append({
        'idx': i+1,
        'type': ptype,
        'name': name,
        'a': a,
        'b': b,
        'c': c,
        'd': d
    })

    print(f"{i+1:<4} {ptype:<6} {name:<40} {a:<6} {b:<6} {c:<6} {str(d) if d else 'None':<6}")

print("="*100)
print(f"\nTotal: {len(all_patterns)} successful patterns")
print("\n" + "="*100)
print("INSTRUCTIONS FOR MANUAL COMPARISON:")
print("="*100)
print("1. Open your GUI and find the 7 formed patterns")
print("2. For each GUI pattern, note down the bar numbers for points A, B, C, D")
print("3. Look in the table above to see if those exact ABCD bar numbers exist")
print("4. If they match, that GUI pattern is among the 87 successful patterns")
print("\nExample:")
print("  If GUI shows: A=23, B=30, C=32, D=40")
print("  Look for row with those exact values")
print("  Found in row #4 and #5 above!")
print("\nNote: Some patterns may have slightly different D values due to timing")
print("      of when the pattern 'entered PRZ' vs when it 'completed'")
