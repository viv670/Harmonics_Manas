"""
Unified Pattern Validation Module
Consolidates all price containment validation logic in one place

This eliminates ~600 lines of duplicate code across:
- formed_abcd.py
- unformed_abcd.py
- unformed_xabcd.py

Benefits:
- Single source of truth for validation rules
- Consistent validation across all pattern types
- Easier maintenance and bug fixes
- Reduced codebase size
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class PriceContainmentValidator:
    """
    Unified price containment validation for all harmonic patterns.

    Validates that price action between pattern points follows strict rules:
    - No breakouts beyond key levels
    - Clean pattern formation
    - Proper price sequencing
    """

    @staticmethod
    def validate_bullish_abcd(df: pd.DataFrame,
                              a_idx: int, b_idx: int, c_idx: int, d_idx: Optional[int],
                              a_price: float, b_price: float, c_price: float,
                              d_price: Optional[float] = None,
                              check_post_c: bool = False) -> bool:
        """
        Validate price containment for bullish ABCD patterns.

        Bullish: A(High) -> B(Low) -> C(High) -> D(Low)

        Rules:
        1. A->B: No candle has high exceeding A
        2. B->C: No candle has low breaking B
        3. C->D (if D exists): No candle has high exceeding C
        4. C->D (if D exists): No candle has low breaking D

        Args:
            df: OHLC DataFrame
            a_idx, b_idx, c_idx, d_idx: Bar indices for pattern points
            a_price, b_price, c_price, d_price: Pattern point prices
            check_post_c: Whether to validate price after C (for unformed patterns)

        Returns:
            True if validation passes, False otherwise
        """
        # Validate inputs
        assert df is not None and not df.empty, "DataFrame required"
        assert 0 <= a_idx < len(df), f"a_idx {a_idx} out of bounds"
        assert 0 <= b_idx < len(df), f"b_idx {b_idx} out of bounds"
        assert 0 <= c_idx < len(df), f"c_idx {c_idx} out of bounds"
        assert a_idx <= b_idx <= c_idx, f"Invalid order: A({a_idx}) <= B({b_idx}) <= C({c_idx})"

        if d_idx is not None:
            assert 0 <= d_idx < len(df), f"d_idx {d_idx} out of bounds"
            assert c_idx <= d_idx, f"C({c_idx}) must be <= D({d_idx})"

        try:
            high_col = 'High' if 'High' in df.columns else 'high'
            low_col = 'Low' if 'Low' in df.columns else 'low'

            # Rule 1: A to B - no high exceeds A
            if a_idx + 1 < b_idx:
                segment = df.iloc[a_idx+1:b_idx+1]
                if any(segment[high_col] > a_price):
                    return False

            # Rule 2: A to C - no low breaks B
            if a_idx + 1 < c_idx:
                segment = df.iloc[a_idx+1:c_idx+1]
                if any(segment[low_col] < b_price):
                    return False

            # Rule 3: B to C - no high exceeds C
            if b_idx < c_idx:
                segment = df.iloc[b_idx:c_idx]
                if any(segment[high_col] > c_price):
                    return False

            # Rules 4 & 5: Only if D point exists
            if d_idx is not None and d_price is not None:
                # B to D: no high exceeds C
                if b_idx < d_idx:
                    segment = df.iloc[b_idx:d_idx]
                    if any(segment[high_col] > c_price):
                        return False

                # C to D: no low breaks D
                if c_idx < d_idx:
                    segment = df.iloc[c_idx:d_idx]
                    if any(segment[low_col] < d_price):
                        return False

            # Optional: Check price after C (for unformed patterns)
            # This is NOT checked by default - pattern tracking handles invalidation
            if check_post_c and c_idx < len(df) - 1:
                max_high_after = df[high_col].iloc[c_idx+1:].max()
                if max_high_after > c_price:
                    return False

            return True

        except (KeyError, IndexError, TypeError, AttributeError) as e:
            logger.error(f"Validation error in validate_bullish_abcd: {e}")
            return False

    @staticmethod
    def validate_bearish_abcd(df: pd.DataFrame,
                             a_idx: int, b_idx: int, c_idx: int, d_idx: Optional[int],
                             a_price: float, b_price: float, c_price: float,
                             d_price: Optional[float] = None,
                             check_post_c: bool = False) -> bool:
        """
        Validate price containment for bearish ABCD patterns.

        Bearish: A(Low) -> B(High) -> C(Low) -> D(High)

        Rules:
        1. A->B: No candle has low breaking A
        2. B->C: No candle has high exceeding B
        3. C->D (if D exists): No candle has low breaking C
        4. C->D (if D exists): No candle has high exceeding D

        Args:
            df: OHLC DataFrame
            a_idx, b_idx, c_idx, d_idx: Bar indices
            a_price, b_price, c_price, d_price: Pattern point prices
            check_post_c: Whether to validate price after C

        Returns:
            True if validation passes, False otherwise
        """
        # Validate inputs
        assert df is not None and not df.empty, "DataFrame required"
        assert 0 <= a_idx < len(df), f"a_idx {a_idx} out of bounds"
        assert 0 <= b_idx < len(df), f"b_idx {b_idx} out of bounds"
        assert 0 <= c_idx < len(df), f"c_idx {c_idx} out of bounds"
        assert a_idx <= b_idx <= c_idx, f"Invalid order: A({a_idx}) <= B({b_idx}) <= C({c_idx})"

        if d_idx is not None:
            assert 0 <= d_idx < len(df), f"d_idx {d_idx} out of bounds"
            assert c_idx <= d_idx, f"C({c_idx}) must be <= D({d_idx})"

        try:
            high_col = 'High' if 'High' in df.columns else 'high'
            low_col = 'Low' if 'Low' in df.columns else 'low'

            # Rule 1: A to B - no low breaks A
            if a_idx + 1 < b_idx:
                segment = df.iloc[a_idx+1:b_idx+1]
                if any(segment[low_col] < a_price):
                    return False

            # Rule 2: A to C - no high exceeds B
            if a_idx + 1 < c_idx:
                segment = df.iloc[a_idx+1:c_idx+1]
                if any(segment[high_col] > b_price):
                    return False

            # Rule 3: B to C - no low breaks C
            if b_idx < c_idx:
                segment = df.iloc[b_idx:c_idx]
                if any(segment[low_col] < c_price):
                    return False

            # Rules 4 & 5: Only if D point exists
            if d_idx is not None and d_price is not None:
                # B to D: no low breaks C
                if b_idx < d_idx:
                    segment = df.iloc[b_idx:d_idx]
                    if any(segment[low_col] < c_price):
                        return False

                # C to D: no high exceeds D
                if c_idx < d_idx:
                    segment = df.iloc[c_idx:d_idx]
                    if any(segment[high_col] > d_price):
                        return False

            # Optional: Check price after C (for unformed patterns)
            if check_post_c and c_idx < len(df) - 1:
                min_low_after = df[low_col].iloc[c_idx+1:].min()
                if min_low_after < c_price:
                    return False

            return True

        except (KeyError, IndexError, TypeError, AttributeError) as e:
            logger.error(f"Validation error in validate_bearish_abcd: {e}")
            return False

    @staticmethod
    def validate_bullish_xabcd(df: pd.DataFrame,
                               x_idx: int, a_idx: int, b_idx: int, c_idx: int,
                               x_price: float, a_price: float, b_price: float, c_price: float,
                               check_post_c: bool = False) -> bool:
        """
        Validate price containment for bullish XABCD patterns.

        Bullish: X(Low) -> A(High) -> B(Low) -> C(High)

        Rules:
        1. X should be the lowest between X-A
        2. A should be the highest between X-B
        3. B should be > X and lowest between A-C
        4. C should be highest between B-C

        Args:
            df: OHLC DataFrame
            x_idx, a_idx, b_idx, c_idx: Bar indices
            x_price, a_price, b_price, c_price: Pattern point prices
            check_post_c: Whether to validate price after C

        Returns:
            True if validation passes, False otherwise
        """
        assert df is not None and not df.empty, "DataFrame required"
        assert 0 <= x_idx < len(df), f"x_idx out of bounds"
        assert 0 <= a_idx < len(df), f"a_idx out of bounds"
        assert 0 <= b_idx < len(df), f"b_idx out of bounds"
        assert 0 <= c_idx < len(df), f"c_idx out of bounds"
        assert x_idx <= a_idx <= b_idx <= c_idx, "Invalid point order"

        try:
            high_col = 'High' if 'High' in df.columns else 'high'
            low_col = 'Low' if 'Low' in df.columns else 'low'

            # Rule 1: X should be lowest between X-A
            if x_idx + 1 < a_idx:
                segment = df.iloc[x_idx+1:a_idx+1]
                if any(segment[low_col] < x_price):
                    return False

            # Rule 2: A should be highest between X-B
            if x_idx < b_idx:
                segment = df.iloc[x_idx:b_idx]
                if any(segment[high_col] > a_price):
                    return False

            # Rule 3a: B should be greater than X
            if b_price <= x_price:
                return False

            # Rule 3b: B should be lowest between A-C
            if a_idx < c_idx:
                segment = df.iloc[a_idx:c_idx+1]
                if any(segment[low_col] < b_price):
                    return False

            # Rule 4: C should be highest between B-C
            if b_idx < c_idx:
                segment = df.iloc[b_idx:c_idx]
                if any(segment[high_col] > c_price):
                    return False

            # Optional: Check price after C
            if check_post_c and c_idx < len(df) - 1:
                max_high_after = df[high_col].iloc[c_idx+1:].max()
                if max_high_after > c_price:
                    return False

            return True

        except (KeyError, IndexError, TypeError, AttributeError) as e:
            logger.error(f"Validation error in validate_bullish_xabcd: {e}")
            return False

    @staticmethod
    def validate_bearish_xabcd(df: pd.DataFrame,
                              x_idx: int, a_idx: int, b_idx: int, c_idx: int,
                              x_price: float, a_price: float, b_price: float, c_price: float,
                              check_post_c: bool = False) -> bool:
        """
        Validate price containment for bearish XABCD patterns.

        Bearish: X(High) -> A(Low) -> B(High) -> C(Low)

        Rules:
        1. X should be the highest between X-A
        2. A should be the lowest between X-B
        3. B should be < X and highest between A-C
        4. C should be lowest between B-C

        Args:
            df: OHLC DataFrame
            x_idx, a_idx, b_idx, c_idx: Bar indices
            x_price, a_price, b_price, c_price: Pattern point prices
            check_post_c: Whether to validate price after C

        Returns:
            True if validation passes, False otherwise
        """
        assert df is not None and not df.empty, "DataFrame required"
        assert 0 <= x_idx < len(df), f"x_idx out of bounds"
        assert 0 <= a_idx < len(df), f"a_idx out of bounds"
        assert 0 <= b_idx < len(df), f"b_idx out of bounds"
        assert 0 <= c_idx < len(df), f"c_idx out of bounds"
        assert x_idx <= a_idx <= b_idx <= c_idx, "Invalid point order"

        try:
            high_col = 'High' if 'High' in df.columns else 'high'
            low_col = 'Low' if 'Low' in df.columns else 'low'

            # Rule 1: X should be highest between X-A
            if x_idx + 1 < a_idx:
                segment = df.iloc[x_idx+1:a_idx+1]
                if any(segment[high_col] > x_price):
                    return False

            # Rule 2: A should be lowest between X-B
            if x_idx < b_idx:
                segment = df.iloc[x_idx:b_idx]
                if any(segment[low_col] < a_price):
                    return False

            # Rule 3a: B should be less than X
            if b_price >= x_price:
                return False

            # Rule 3b: B should be highest between A-C
            if a_idx < c_idx:
                segment = df.iloc[a_idx:c_idx+1]
                if any(segment[high_col] > b_price):
                    return False

            # Rule 4: C should be lowest between B-C
            if b_idx < c_idx:
                segment = df.iloc[b_idx:c_idx]
                if any(segment[low_col] < c_price):
                    return False

            # Optional: Check price after C
            if check_post_c and c_idx < len(df) - 1:
                min_low_after = df[low_col].iloc[c_idx+1:].min()
                if min_low_after < c_price:
                    return False

            return True

        except (KeyError, IndexError, TypeError, AttributeError) as e:
            logger.error(f"Validation error in validate_bearish_xabcd: {e}")
            return False


# Convenience wrapper for automatic pattern type detection
def validate_pattern(pattern_type: str, direction: str, df: pd.DataFrame,
                    points_dict: Dict, check_post_c: bool = False) -> bool:
    """
    Validate any pattern type with automatic dispatcher.

    Args:
        pattern_type: 'ABCD' or 'XABCD'
        direction: 'bullish' or 'bearish'
        df: OHLC DataFrame
        points_dict: Dictionary with point indices and prices
            For ABCD: {'a_idx', 'a_price', 'b_idx', 'b_price', 'c_idx', 'c_price', 'd_idx', 'd_price'}
            For XABCD: {'x_idx', 'x_price', 'a_idx', 'a_price', 'b_idx', 'b_price', 'c_idx', 'c_price'}
        check_post_c: Whether to validate price after C point

    Returns:
        True if validation passes, False otherwise
    """
    validator = PriceContainmentValidator()

    if pattern_type == 'ABCD':
        if direction == 'bullish':
            return validator.validate_bullish_abcd(
                df,
                points_dict['a_idx'], points_dict['b_idx'], points_dict['c_idx'],
                points_dict.get('d_idx'),
                points_dict['a_price'], points_dict['b_price'], points_dict['c_price'],
                points_dict.get('d_price'),
                check_post_c
            )
        else:  # bearish
            return validator.validate_bearish_abcd(
                df,
                points_dict['a_idx'], points_dict['b_idx'], points_dict['c_idx'],
                points_dict.get('d_idx'),
                points_dict['a_price'], points_dict['b_price'], points_dict['c_price'],
                points_dict.get('d_price'),
                check_post_c
            )

    elif pattern_type == 'XABCD':
        if direction == 'bullish':
            return validator.validate_bullish_xabcd(
                df,
                points_dict['x_idx'], points_dict['a_idx'], points_dict['b_idx'], points_dict['c_idx'],
                points_dict['x_price'], points_dict['a_price'], points_dict['b_price'], points_dict['c_price'],
                check_post_c
            )
        else:  # bearish
            return validator.validate_bearish_xabcd(
                df,
                points_dict['x_idx'], points_dict['a_idx'], points_dict['b_idx'], points_dict['c_idx'],
                points_dict['x_price'], points_dict['a_price'], points_dict['b_price'], points_dict['c_price'],
                check_post_c
            )

    else:
        raise ValueError(f"Unknown pattern type: {pattern_type}")


if __name__ == "__main__":
    print("Testing Pattern Validators...")

    # Create test data
    test_df = pd.DataFrame({
        'High': [102, 98, 101, 97, 100, 96, 99],
        'Low': [100, 96, 99, 95, 98, 94, 97],
        'Open': [100, 98, 99, 97, 98, 96, 97],
        'Close': [101, 97, 100, 96, 99, 95, 98]
    })

    # Test bullish ABCD validation
    result = PriceContainmentValidator.validate_bullish_abcd(
        test_df,
        a_idx=0, b_idx=1, c_idx=2, d_idx=3,
        a_price=102, b_price=96, c_price=101, d_price=95
    )
    print(f"Bullish ABCD validation: {result}")

    # Test using convenience wrapper
    points = {
        'a_idx': 0, 'a_price': 102,
        'b_idx': 1, 'b_price': 96,
        'c_idx': 2, 'c_price': 101,
        'd_idx': 3, 'd_price': 95
    }
    result2 = validate_pattern('ABCD', 'bullish', test_df, points)
    print(f"Convenience wrapper validation: {result2}")

    print("\n✅ Pattern validators ready!")
