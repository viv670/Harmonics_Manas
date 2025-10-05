"""
Debug why bar 252 is detected as BOTH high and low with extremum=1
"""

import pandas as pd
import numpy as np

# Load ENAUSDT data
df = pd.read_csv('enausdt_1d.csv')
df.columns = [col.capitalize() if col.lower() in ['time', 'open', 'high', 'low', 'close', 'volume'] else col for col in df.columns]

print("Inspecting bar 252 and surroundings:\n")
print(f"{'Bar':<5} {'High':<10} {'Low':<10} {'Open':<10} {'Close':<10}")
print("-" * 50)
for i in range(250, 256):
    row = df.iloc[i]
    marker = " <<<" if i == 252 else ""
    print(f"{i:<5} {row['High']:<10.4f} {row['Low']:<10.4f} {row['Open']:<10.4f} {row['Close']:<10.4f}{marker}")

# Check with length=1
print("\n" + "="*60)
print("CHECK WITH LENGTH=1")
print("="*60)
bar_252 = df.iloc[252]
length = 1

# High pivot check
left_highs = df['High'].iloc[251:252].values  # bar 251
right_highs = df['High'].iloc[253:254].values  # bar 253
is_high_pivot = (bar_252['High'] >= np.max(left_highs) and
                 bar_252['High'] >= np.max(right_highs))

print(f"\nHIGH pivot check for bar 252:")
print(f"  Left high (bar 251): {left_highs}")
print(f"  Current high (bar 252): {bar_252['High']:.4f}")
print(f"  Right high (bar 253): {right_highs}")
print(f"  Is HIGH pivot? {is_high_pivot}")
print(f"  Condition: {bar_252['High']:.4f} >= {np.max(left_highs):.4f} AND {bar_252['High']:.4f} >= {np.max(right_highs):.4f}")

# Low pivot check
left_lows = df['Low'].iloc[251:252].values  # bar 251
right_lows = df['Low'].iloc[253:254].values  # bar 253
is_low_pivot = (bar_252['Low'] <= np.min(left_lows) and
                bar_252['Low'] <= np.min(right_lows))

print(f"\nLOW pivot check for bar 252:")
print(f"  Left low (bar 251): {left_lows}")
print(f"  Current low (bar 252): {bar_252['Low']:.4f}")
print(f"  Right low (bar 253): {right_lows}")
print(f"  Is LOW pivot? {is_low_pivot}")
print(f"  Condition: {bar_252['Low']:.4f} <= {np.min(left_lows):.4f} AND {bar_252['Low']:.4f} <= {np.min(right_lows):.4f}")

# Check with length=2
print("\n" + "="*60)
print("CHECK WITH LENGTH=2")
print("="*60)
length = 2

# High pivot check
left_highs_2 = df['High'].iloc[250:252].values  # bars 250, 251
right_highs_2 = df['High'].iloc[253:255].values  # bars 253, 254
is_high_pivot_2 = (bar_252['High'] >= np.max(left_highs_2) and
                   bar_252['High'] >= np.max(right_highs_2))

print(f"\nHIGH pivot check for bar 252:")
print(f"  Left highs (bars 250,251): {left_highs_2}")
print(f"  Current high (bar 252): {bar_252['High']:.4f}")
print(f"  Right highs (bars 253,254): {right_highs_2}")
print(f"  Is HIGH pivot? {is_high_pivot_2}")

# Low pivot check
left_lows_2 = df['Low'].iloc[250:252].values  # bars 250, 251
right_lows_2 = df['Low'].iloc[253:255].values  # bars 253, 254
is_low_pivot_2 = (bar_252['Low'] <= np.min(left_lows_2) and
                  bar_252['Low'] <= np.min(right_lows_2))

print(f"\nLOW pivot check for bar 252:")
print(f"  Left lows (bars 250,251): {left_lows_2}")
print(f"  Current low (bar 252): {bar_252['Low']:.4f}")
print(f"  Right lows (bars 253,254): {right_lows_2}")
print(f"  Is LOW pivot? {is_low_pivot_2}")

print("\n" + "="*60)
print("CONCLUSION")
print("="*60)
if is_high_pivot and is_low_pivot:
    print("⚠️  Bar 252 is BOTH a high and low pivot with length=1!")
    print("   This creates duplicate entries with different prices.")
    print("   The high price and low price are being treated as separate extremums.")
elif is_high_pivot:
    print("⚠️  Bar 252 is ONLY a high pivot with length=1 (WRONG!)")
elif is_low_pivot:
    print("✓ Bar 252 is ONLY a low pivot with length=1 (CORRECT!)")
else:
    print("❌ Bar 252 is NOT a pivot with length=1 (ERROR!)")
