# Structure Break Conditions for ABCD and XABCD Patterns

## Current Implementation in Code

### Location: `pattern_tracking_utils.py:1035-1090`

```python
def check_pattern_dismissal(self, price_high: float, price_low: float, current_bar: int):
    """Check if any pending patterns should be dismissed due to structure break."""

    for pattern_id, tracked in list(self.tracked_patterns.items()):
        # Only check pending patterns
        if tracked.status != 'pending':
            continue

        b_price = tracked.b_point[1]
        is_bullish = tracked.a_point[1] > tracked.b_point[1]

        if is_bullish:
            # For bullish patterns (B is low), dismiss if price breaks below B
            if price_low < b_price:
                should_dismiss = True
                reason = "Structure broken - price below B"
        else:
            # For bearish patterns (B is high), dismiss if price breaks above B
            if price_high > b_price:
                should_dismiss = True
                reason = "Structure broken - price above B"
```

---

## ABCD Pattern Structure

### Bullish ABCD Pattern
**Structure:** A(High) → B(Low) → C(High) → D(Low)

**Price Containment Rules (from unformed_abcd.py:95-144):**
1. **A→B segment:** No candle between A and B has a high that exceeds A
2. **A→C segment:** No candle between A and C has a low that breaks below B
3. **B→C segment:** No candle between B and C has a high that exceeds C
4. **Post-C:** Price can move above C before reaching D (handled by tracking, not detection)

**Current Structure Break Condition:**
- ❌ Dismiss if: `price_low < B_price`

### Bearish ABCD Pattern
**Structure:** A(Low) → B(High) → C(Low) → D(High)

**Price Containment Rules (from unformed_abcd.py:147-189):**
1. **A→B segment:** No candle between A and B has a low that breaks below A
2. **A→C segment:** No candle between A and C has a high that exceeds B
3. **B→C segment:** No candle between B and C has a low that breaks below C
4. **Post-C:** Price can move below C before reaching D (handled by tracking, not detection)

**Current Structure Break Condition:**
- ❌ Dismiss if: `price_high > B_price`

---

## XABCD Pattern Structure

### Bullish XABCD Pattern
**Structure:** X(Low) → A(High) → B(Low) → C(High) → D(Low)

**Price Containment Rules (from unformed_xabcd.py:105-162):**
1. **X should be the lowest point between X and A**
2. **A should be the highest point between X and B**
3. **B should be > X and the lowest point between A and C**
4. **C should be the highest point between B and C**
5. **Post-C:** Price can move above C before reaching D (comment: "this is normal pattern behavior")

**Note from code (line 111):**
> "Structure breaks (price below B) are handled by check_pattern_dismissal()."

**Current Structure Break Condition:**
- ❌ Dismiss if: `price_low < B_price`

### Bearish XABCD Pattern
**Structure:** X(High) → A(Low) → B(High) → C(Low) → D(High)

**Price Containment Rules (from unformed_xabcd.py:165-224):**
1. **X should be the highest point between X and A**
2. **A should be the lowest point between X and B**
3. **B should be < X and the highest point between A and C**
4. **C should be the lowest point between B and C**
5. **Post-C:** Price can move below C before reaching D (comment: "this is normal pattern behavior")

**Note from code (line 181):**
> "Structure breaks (price above B) are handled by check_pattern_dismissal()."

**Current Structure Break Condition:**
- ❌ Dismiss if: `price_high > B_price`

---

## Summary Table

| Pattern Type | Direction | A Point | B Point | C Point | Expected D | Current Break Condition |
|--------------|-----------|---------|---------|---------|------------|------------------------|
| ABCD | Bullish | HIGH | LOW | HIGH | LOW | price_low < B |
| ABCD | Bearish | LOW | HIGH | LOW | HIGH | price_high > B |
| XABCD | Bullish | HIGH | LOW | HIGH | LOW | price_low < B |
| XABCD | Bearish | LOW | HIGH | LOW | HIGH | price_high > B |

---

## Key Observations

1. **Both ABCD and XABCD use the SAME structure break condition** (checked at point B)

2. **For Bullish patterns (both ABCD & XABCD):**
   - Pattern: A(high) → B(low) → C(high) → D(low)
   - D is expected to be a LOW (below C)
   - Structure break: When price goes BELOW B

3. **For Bearish patterns (both ABCD & XABCD):**
   - Pattern: A(low) → B(high) → C(low) → D(high)
   - D is expected to be a HIGH (above C)
   - Structure break: When price goes ABOVE B

4. **Important notes from code:**
   - "C can be updated to new highs/lows - this is normal pattern behavior"
   - "Price can move above/below C before reaching D - handled by tracking"
   - "Post-C validation REMOVED: Pattern invalidation is handled by tracking system"

---

## Questions for Clarification

### Question 1: XABCD D Point Location
You stated: "In XABCD pattern, pt D will always be below pt B"

But looking at the structure:
- **Bullish XABCD:** X(low) → A(high) → B(low) → C(high) → D(low)
  - Is D always below B? Or can D be between B and C?

- **Bearish XABCD:** X(high) → A(low) → B(high) → C(low) → D(high)
  - Is D always above B? Or can D be between C and B?

### Question 2: When is Structure Truly Broken?
Current logic dismisses when:
- Bullish: price goes below B
- Bearish: price goes above B

But if D can be below B (bullish) or above B (bearish), then this condition seems INCORRECT.

**Should structure break be:**
- Bullish: price goes below X? Or below some other level?
- Bearish: price goes above X? Or above some other level?

### Question 3: ABCD vs XABCD
Is there a difference in structure break conditions between:
- ABCD patterns (3 points + projected D)
- XABCD patterns (4 points + projected D)

Or should they both use the same rules?
