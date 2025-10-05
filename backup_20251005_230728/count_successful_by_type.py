"""
Count ABCD vs XABCD in the 87 successful patterns
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

print(f"SUCCESSFUL PATTERNS BREAKDOWN")
print("="*80)

# Count by Type
type_counts = successful['Type'].value_counts()

print(f"\nTotal Successful Patterns: {len(successful)}")
print(f"\nBy Pattern Type:")
for ptype, count in type_counts.items():
    percentage = (count / len(successful)) * 100
    print(f"  {ptype}: {count} patterns ({percentage:.1f}%)")

# Also show breakdown by specific pattern names
print(f"\n" + "="*80)
print(f"DETAILED BREAKDOWN BY PATTERN NAME:")
print("="*80)

name_counts = successful['Subtype'].value_counts()
print(f"\nTop 10 Most Successful Pattern Types:")
for i, (name, count) in enumerate(name_counts.head(10).items(), 1):
    print(f"  {i}. {name}: {count} times")

print(f"\n" + "="*80)
print(f"SUMMARY:")
print("="*80)
if 'ABCD' in type_counts and 'XABCD' in type_counts:
    abcd_count = type_counts['ABCD']
    xabcd_count = type_counts['XABCD']
    print(f"✅ ABCD patterns: {abcd_count}/{len(successful)} ({abcd_count/len(successful)*100:.1f}%)")
    print(f"✅ XABCD patterns: {xabcd_count}/{len(successful)} ({xabcd_count/len(successful)*100:.1f}%)")
    print(f"\nRatio: ABCD:XABCD = {abcd_count}:{xabcd_count}")
elif 'ABCD' in type_counts:
    print(f"✅ Only ABCD patterns: {type_counts['ABCD']}")
elif 'XABCD' in type_counts:
    print(f"✅ Only XABCD patterns: {type_counts['XABCD']}")
else:
    print("❌ No Type column found or unexpected values")
