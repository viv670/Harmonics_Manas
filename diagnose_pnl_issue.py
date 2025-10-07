"""
Diagnostic script to understand Enhanced PnL issue
This will help us see what's happening with the patterns
"""

import pandas as pd
import json

# Check if we have recent backtest results
import os
backtest_files = [f for f in os.listdir('backtest_results') if f.endswith('.xlsx')]
if backtest_files:
    latest = sorted(backtest_files)[-1]
    print(f"Latest backtest: {latest}")

    # Try to read the Excel file to see pattern data
    try:
        df = pd.read_excel(f'backtest_results/{latest}', sheet_name='Pattern Details')
        print(f"\nTotal patterns in backtest: {len(df)}")
        print(f"Columns: {df.columns.tolist()}")

        # Check successful patterns
        if 'Status' in df.columns:
            successful = df[df['Status'] == 'success']
            print(f"\nSuccessful patterns: {len(successful)}")

            if len(successful) > 0:
                print("\nFirst successful pattern details:")
                pattern = successful.iloc[0]
                print(f"  Pattern: {pattern.get('Pattern Name', 'N/A')}")
                print(f"  Formation Bar: {pattern.get('Formation Bar', 'N/A')}")
                print(f"  Status: {pattern.get('Status', 'N/A')}")

                # Check if D point info exists
                d_cols = [col for col in df.columns if 'D' in col or 'd_' in col.lower()]
                print(f"\n  D-point related columns: {d_cols}")

                for col in d_cols[:5]:  # Show first 5 D-related columns
                    print(f"    {col}: {pattern.get(col, 'N/A')}")
    except Exception as e:
        print(f"Error reading Excel: {e}")
else:
    print("No backtest results found!")

print("\n" + "="*80)
print("DIAGNOSIS:")
print("="*80)

print("""
The Enhanced PnL calculation needs:
1. D point price (entry price)
2. D point bar index (to slice data after D)
3. Future candles after D point (to check if TPs were hit)

Common causes of 'no_tp_hits':
A. D point bar index is at the END of data (no future candles)
B. D point price is missing or incorrect
C. TP candidates are all filtered out (none above/below entry)
D. Future candles don't reach any TP levels (SL hit first or pattern failed)

Check the console output when you run Enhanced PnL - it will show:
  - Entry price
  - Direction
  - TP Candidates list
  - Number of candles after D
  - Price range after D
""")
