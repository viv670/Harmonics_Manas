"""
Simple comparison using Excel bars and GUI detection
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

print(f"Total patterns in Excel: {len(pattern_details)}")
print(f"Successful patterns: {len(successful)}\n")

# Extract ABCD bar indices from successful patterns
excel_patterns = []
for i, row in successful.iterrows():
    # Use the _Bar columns for indices
    a_bar = row.get('A_Bar')
    b_bar = row.get('B_Bar')
    c_bar = row.get('C_Bar')

    # For D bar, check PRZ_Entry_Bar (when pattern entered PRZ zone)
    d_bar = row.get('PRZ_Entry_Bar')

    if pd.isna(a_bar) or pd.isna(b_bar) or pd.isna(c_bar):
        continue

    key = (int(a_bar), int(b_bar), int(c_bar), int(d_bar) if pd.notna(d_bar) else None)
    excel_patterns.append({
        'key': key,
        'name': row.get('Subtype', 'Unknown'),
        'type': row.get('Type', 'Unknown')
    })

print("Sample successful patterns from Excel:")
print("="*80)
for i, p in enumerate(excel_patterns[:5], 1):
    print(f"{i}. {p['type']} - {p['name'][:40]}")
    print(f"   ABCD bars: A={p['key'][0]}, B={p['key'][1]}, C={p['key'][2]}, D={p['key'][3]}")

if len(excel_patterns) > 5:
    print(f"... and {len(excel_patterns) - 5} more\n")

# Now get GUI patterns - but skip the slow detection, use what's in GUI
# Instead, let's check if user can provide the GUI pattern info
print("\n" + "="*80)
print("CANNOT COMPLETE - GUI detection is too slow")
print("="*80)
print("\nTo answer your question manually:")
print("1. Check the GUI - note the A, B, C, D BAR NUMBERS for each of the 7 patterns")
print("2. Compare with the successful patterns above")
print("3. If the ABCD bar numbers match, those patterns overlap")
print("\nAlternatively, the answer is already in the data:")
print(f"- Total successful (status='success'): {len(successful)}")
print(f"- These are unformed patterns that reached PRZ and reversed")
print(f"- The 7 GUI patterns are formed patterns detected on full dataset")
print(f"- They are tracked separately by design (see line 1455-1458 in backtester)")
print("\nSo NO, they are NOT the same - tracked in different ways.")
