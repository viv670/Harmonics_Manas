# Complete Structure and Validation Conditions for ABCD and XABCD Patterns

## ABCD PATTERN - BULLISH

**Structure:** A(High) → B(Low) → C(High) → D(Low)

### Price Containment Rules (Source: `unformed_abcd.py:87-144`)

**Rule 1 - A to B segment:**
```
No candle between A and B has a high that exceeds A
Code: if any(segment_ab[high_col] > a_price): return False
Meaning: A must be the highest point between A and B
```

**Rule 2 - A to C segment (B protection):**
```
No candle between A and C has a low that breaks below B
Code: if any(segment_ac[low_col] < b_price): return False
Meaning: B must be the LOWEST point between A and C
```

**Rule 3 - B to C segment:**
```
No candle between B and C has a high that exceeds C
Code: if any(segment_bc[high_col] > c_price): return False
Meaning: C must be the highest point between B and C
```

**Post-C Behavior:**
```
Price CAN move above C before reaching D zone
Comment: "Pattern invalidation is handled by the tracking system, not detection"
```

### Current Structure Break Condition (Source: `pattern_tracking_utils.py:1068-1070`)
```python
if is_bullish:
    if price_low < b_price:
        should_dismiss = True
        reason = "Structure broken - price below B"
```

---

## ABCD PATTERN - BEARISH

**Structure:** A(Low) → B(High) → C(Low) → D(High)

### Price Containment Rules (Source: `unformed_abcd.py:147-204`)

**Rule 1 - A to B segment:**
```
No candle between A and B has a low that breaks below A
Code: if any(segment_ab[low_col] < a_price): return False
Meaning: A must be the lowest point between A and B
```

**Rule 2 - A to C segment (B protection):**
```
No candle between A and C has a high that exceeds B
Code: if any(segment_ac[high_col] > b_price): return False
Meaning: B must be the HIGHEST point between A and C
```

**Rule 3 - B to C segment:**
```
No candle between B and C has a low that breaks below C
Code: if any(segment_bc[low_col] < c_price): return False
Meaning: C must be the lowest point between B and C
```

**Post-C Behavior:**
```
Price CAN move below C before reaching D zone
Comment: "Pattern invalidation is handled by the tracking system, not detection"
```

### Current Structure Break Condition (Source: `pattern_tracking_utils.py:1074-1076`)
```python
else:  # bearish
    if price_high > b_price:
        should_dismiss = True
        reason = "Structure broken - price above B"
```

---

## XABCD PATTERN - BULLISH

**Structure:** X(Low) → A(High) → B(Low) → C(High) → D(Low)

### Price Containment Rules (Source: `unformed_xabcd.py:95-162`)

**Rule 1 - X to A segment:**
```
X should be the lowest point between X and A (excluding X itself)
Code: if any(segment_xa[low_col] < x_price): return False
Meaning: No lower low than X between X and A
```

**Rule 2 - X to B segment:**
```
A should be the highest point between X and B (excluding A itself)
Code: if any(segment_xb[high_col] > a_price): return False
Meaning: No higher high than A between X and B
```

**Rule 3a - B vs X relationship:**
```
B should be greater than X
Code: if b_price <= x_price: return False
Meaning: B must be ABOVE X (B is a higher low than X)
```

**Rule 3b - A to C segment (B protection):**
```
B should be the lowest point between A and C
Code: if any(segment_ac[low_col] < b_price): return False
Meaning: No lower low than B between A and C
```

**Rule 4 - B to C segment:**
```
C should be the highest point between B and C (excluding C itself)
Code: if any(segment_bc[high_col] > c_price): return False
Meaning: No higher high than C between B and C
```

**Post-C Behavior:**
```
Price CAN move above C before reaching D zone
Comment: "this is normal pattern behavior"
Comment: "Pattern invalidation is handled by the tracking system, not detection"
```

### Current Structure Break Condition (Source: `pattern_tracking_utils.py:1068-1070`)
```python
if is_bullish:
    if price_low < b_price:
        should_dismiss = True
        reason = "Structure broken - price below B"
```

**Note from code (line 111):**
> "Structure breaks (price below B) are handled by check_pattern_dismissal()."

---

## XABCD PATTERN - BEARISH

**Structure:** X(High) → A(Low) → B(High) → C(Low) → D(High)

### Price Containment Rules (Source: `unformed_xabcd.py:165-229`)

**Rule 1 - X to A segment:**
```
X should be the highest point between X and A (excluding X itself)
Code: if any(segment_xa[high_col] > x_price): return False
Meaning: No higher high than X between X and A
```

**Rule 2 - X to B segment:**
```
A should be the lowest point between X and B (excluding A itself)
Code: if any(segment_xb[low_col] < a_price): return False
Meaning: No lower low than A between X and B
```

**Rule 3a - B vs X relationship:**
```
B should be less than X
Code: if b_price >= x_price: return False
Meaning: B must be BELOW X (B is a lower high than X)
```

**Rule 3b - A to C segment (B protection):**
```
B should be the highest point between A and C
Code: if any(segment_ac[high_col] > b_price): return False
Meaning: No higher high than B between A and C
```

**Rule 4 - B to C segment:**
```
C should be the lowest point between B and C (excluding C itself)
Code: if any(segment_bc[low_col] < c_price): return False
Meaning: No lower low than C between B and C
```

**Post-C Behavior:**
```
Price CAN move below C before reaching D zone
Comment: "this is normal pattern behavior"
Comment: "Pattern invalidation is handled by the tracking system, not detection"
```

### Current Structure Break Condition (Source: `pattern_tracking_utils.py:1074-1076`)
```python
else:  # bearish
    if price_high > b_price:
        should_dismiss = True
        reason = "Structure broken - price above B"
```

**Note from code (line 181):**
> "Structure breaks (price above B) are handled by check_pattern_dismissal()."

---

## Summary of All Conditions

### ABCD Bullish: A(High) → B(Low) → C(High) → D(Low)
1. ✅ A is highest between A-B
2. ✅ **B is LOWEST between A-C** ← Key condition
3. ✅ C is highest between B-C
4. ✅ Price can move above C after C forms
5. ❌ **Structure break: price_low < B**

### ABCD Bearish: A(Low) → B(High) → C(Low) → D(High)
1. ✅ A is lowest between A-B
2. ✅ **B is HIGHEST between A-C** ← Key condition
3. ✅ C is lowest between B-C
4. ✅ Price can move below C after C forms
5. ❌ **Structure break: price_high > B**

### XABCD Bullish: X(Low) → A(High) → B(Low) → C(High) → D(Low)
1. ✅ X is lowest between X-A
2. ✅ A is highest between X-B
3. ✅ **B > X** (B is higher low than X)
4. ✅ **B is LOWEST between A-C** ← Key condition
5. ✅ C is highest between B-C
6. ✅ Price can move above C after C forms
7. ❌ **Structure break: price_low < B**

### XABCD Bearish: X(High) → A(Low) → B(High) → C(Low) → D(High)
1. ✅ X is highest between X-A
2. ✅ A is lowest between X-B
3. ✅ **B < X** (B is lower high than X)
4. ✅ **B is HIGHEST between A-C** ← Key condition
5. ✅ C is lowest between B-C
6. ✅ Price can move below C after C forms
7. ❌ **Structure break: price_high > B**

---

## Critical Observation

**The structure break condition (`price crosses B`) CONTRADICTS the validation rules!**

- For **bullish** patterns: Rule says "B is LOWEST between A-C", but structure break dismisses when price goes below B
- For **bearish** patterns: Rule says "B is HIGHEST between A-C", but structure break dismisses when price goes above B

**This means:**
- If price violates B while forming the pattern (between A and C), the pattern is INVALID during detection
- But if pattern is already detected and THEN price crosses B (after C), it gets dismissed
- This dismissal happens BEFORE point D can form
- **Point D is expected to be in the PRZ zone, which could be beyond B!**
