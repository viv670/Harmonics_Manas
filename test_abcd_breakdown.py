"""
Quick test to verify ABCD/XABCD breakdown tracking
"""

# Simulate the output format
print("PATTERN COMPLETION ANALYSIS:")
print("  Completed Successfully: 87")
print("    - ABCD: 38")
print("    - XABCD: 49")
print("  Failed (PRZ Violated): 45")
print("    - ABCD: 20")
print("    - XABCD: 25")
print("  In PRZ Zone (Active): 12")
print("    - ABCD: 5")
print("    - XABCD: 7")
print("  Dismissed (Structure Break): 10")
print("  Still Pending: 89")
print()
print("  Success Rate: 65.9% (87/132 patterns that reached PRZ)")
print("  Total Tracked: 243")
