"""
Pattern Tracking Utilities for Harmonic Pattern Backtesting

This module tracks the lifecycle of patterns from unformed (potential) to formed (completed),
enabling analysis of pattern completion rates, accuracy, and success metrics.
"""

import hashlib
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from datetime import datetime
import numpy as np
import pandas as pd


@dataclass
class TrackedPattern:
    """Represents a tracked pattern through its lifecycle"""
    pattern_id: str
    pattern_type: str  # ABCD or XABCD
    subtype: str  # Gartley, Butterfly, etc.
    first_seen_bar: int  # When pattern was first detected

    # Pattern points with timestamps and prices
    x_point: Tuple[int, float]  # (bar_index, price)
    a_point: Tuple[int, float]
    b_point: Tuple[int, float]
    c_point: Tuple[int, float]
    d_point: Optional[Tuple[int, float]] = None  # D point when pattern becomes formed

    # Projected D zone (PRZ for ABCD, d_lines for XABCD)
    prz_min: Optional[float] = None  # For ABCD patterns (deprecated - use prz_zones)
    prz_max: Optional[float] = None  # For ABCD patterns (deprecated - use prz_zones)
    prz_zones: List[Dict] = field(default_factory=list)  # Separate PRZ zones for each pattern
    d_lines: List[float] = field(default_factory=list)  # For XABCD patterns
    projected_d_time: int = 0  # Estimated time for D

    # Pattern timestamps for time tracking
    a_timestamp: Optional[datetime] = None
    b_timestamp: Optional[datetime] = None
    c_timestamp: Optional[datetime] = None
    detection_timestamp: Optional[datetime] = None

    # Completion tracking
    status: str = 'pending'  # pending, success, failed, dismissed
    zone_reached: bool = False
    zone_entry_bar: Optional[int] = None
    zone_entry_price: Optional[float] = None
    zone_entry_timestamp: Optional[datetime] = None
    zone_exit_bar: Optional[int] = None  # For tracking zone violation
    zone_exit_price: Optional[float] = None
    reversal_confirmed: bool = False  # Track if price reversed after zone entry
    reversal_bar: Optional[int] = None
    reversal_price: Optional[float] = None

    # Actual completion details
    actual_d_price: Optional[float] = None
    actual_d_bar: Optional[int] = None
    actual_d_timestamp: Optional[datetime] = None
    formed_pattern_name: Optional[str] = None  # What pattern actually formed

    # Timing metrics
    bars_from_c_to_zone: Optional[int] = None  # Bars from C to zone entry
    bars_from_a_to_d: Optional[int] = None  # Total pattern duration
    bars_from_detection_to_completion: Optional[int] = None

    # Accuracy metrics
    price_accuracy: Optional[float] = None
    pattern_match_accuracy: Optional[float] = None  # Did it form the expected pattern?

    # Additional details
    completion_details: Dict = field(default_factory=dict)


class PatternTracker:
    """
    Tracks patterns from unformed to formed state, calculating completion rates
    and success metrics for backtesting analysis.
    """

    def __init__(self):
        """Initialize the pattern tracker without expiry mechanism."""
        self.tracked_patterns: Dict[str, TrackedPattern] = {}
        self.completion_history: List[TrackedPattern] = []
        self.pattern_type_stats: Dict[str, Dict] = {}
        self.current_bar: int = 0
        self.current_data = None  # Store current price data

    def generate_pattern_id(self, pattern: Dict) -> str:
        """
        Generate a unique ID for a pattern based on its key points.

        Uses only the pattern's structural points (X, A, B, C) INDICES to ensure
        the same pattern always gets the same ID regardless of when it's detected.

        Args:
            pattern: Pattern dictionary with A, B, C points (and X for XABCD)

        Returns:
            Unique pattern ID string
        """
        # Create a string representation of the key points
        pattern_type = pattern.get('pattern_type', 'UNK')

        # Extract ONLY the indices for unique identification (not prices)
        point_indices = []

        # Handle different pattern structures
        if 'indices' in pattern:
            # Direct indices available
            indices = pattern['indices']
            for point_name in ['X', 'A', 'B', 'C']:
                if point_name in indices:
                    point_indices.append(f"{point_name}:{indices[point_name]}")
        elif 'points' in pattern:
            # Extract indices from points structure
            points = pattern['points']
            for point_name in ['X', 'A', 'B', 'C']:
                if point_name in points:
                    point_data = points[point_name]
                    if isinstance(point_data, dict):
                        # Try to get index or timestamp
                        idx = point_data.get('index', point_data.get('time', point_data.get('timestamp', '')))
                        # If idx is a timestamp/datetime, try to extract just the bar index
                        if isinstance(idx, (int, float)):
                            point_indices.append(f"{point_name}:{int(idx)}")
                        else:
                            # Use the full timestamp if we can't get an index
                            point_indices.append(f"{point_name}:{idx}")
                    else:
                        # Assume it's an index
                        point_indices.append(f"{point_name}:{point_data}")
        else:
            # Fallback: try to extract from direct keys
            for point_name in ['X', 'A', 'B', 'C']:
                if point_name in pattern:
                    val = pattern[point_name]
                    # Try to extract index from tuple/list
                    if isinstance(val, (tuple, list)) and len(val) >= 1:
                        point_indices.append(f"{point_name}:{val[0]}")
                    else:
                        point_indices.append(f"{point_name}:{val}")

        # Create key string from indices only (no prices, no detection bar)
        key_string = '_'.join(point_indices) if point_indices else f"unknown_{id(pattern)}"

        # Generate hash for unique ID based ONLY on point indices
        pattern_hash = hashlib.md5(str(key_string).encode()).hexdigest()[:16]

        # Use only pattern type prefix
        return f"{pattern_type}_{pattern_hash}"

    def _extract_point(self, point_data) -> Tuple[int, float]:
        """
        Extract point information from various formats.

        Args:
            point_data: Point data in various formats

        Returns:
            Tuple of (time_index, price)
        """
        if isinstance(point_data, dict):
            # Handle dict with 'time' and 'price' keys
            time_val = point_data.get('time', 0)
            price_val = point_data.get('price', 0)

            # Convert numpy types if needed
            if hasattr(time_val, 'item'):
                time_val = time_val.item()
            if hasattr(price_val, 'item'):
                price_val = float(price_val.item())
            else:
                price_val = float(price_val) if price_val else 0

            # If time is a datetime, convert to index (simplified)
            if isinstance(time_val, (np.datetime64, datetime)):
                time_val = 0  # Will be handled later if needed

            return (time_val, price_val)
        elif isinstance(point_data, (tuple, list)) and len(point_data) >= 2:
            return (point_data[0], float(point_data[1]))
        else:
            return (0, 0)

    def track_unformed_pattern(self, pattern: Dict, current_bar: int, current_timestamp: datetime = None) -> str:
        """
        Track a newly detected unformed pattern.

        Args:
            pattern: Unformed pattern dictionary
            current_bar: Current bar number in backtest
            current_timestamp: Current timestamp

        Returns:
            Pattern ID of the tracked pattern
        """
        self.current_bar = current_bar
        pattern_id = self.generate_pattern_id(pattern)

        # Check if we're already tracking this pattern
        if pattern_id in self.tracked_patterns:
            # Already tracking this pattern, don't create duplicate
            return pattern_id

        # Extract point data based on pattern structure
        if 'points' in pattern:
            # New structure from comprehensive patterns
            points = pattern['points']

            # Get indices if available (more reliable than timestamps)
            indices = pattern.get('indices', {})

            # For X, A, B, C points, prefer indices over timestamps
            if indices:
                x_idx = indices.get('X', 0)
                a_idx = indices.get('A', 0)
                b_idx = indices.get('B', 0)
                c_idx = indices.get('C', 0)

                # Get prices from points
                x_price = points.get('X', {}).get('price', 0) if 'X' in points else 0
                a_price = points.get('A', {}).get('price', 0)
                b_price = points.get('B', {}).get('price', 0)
                c_price = points.get('C', {}).get('price', 0)

                x_point = (x_idx, x_price)
                a_point = (a_idx, a_price)
                b_point = (b_idx, b_price)
                c_point = (c_idx, c_price)
            else:
                # Fallback to original extraction method
                x_point = (0, 0) if 'X' not in points else self._extract_point(points['X'])
                a_point = self._extract_point(points.get('A', {}))
                b_point = self._extract_point(points.get('B', {}))
                c_point = self._extract_point(points.get('C', {}))

            # Extract projected D zone with better error handling
            d_proj = points.get('D_projected', {})
            prz_min = None
            prz_max = None
            prz_zones = []  # Initialize prz_zones list
            d_lines = []

            if isinstance(d_proj, dict):
                # Extract d_lines if available
                if 'd_lines' in d_proj:
                    d_lines = d_proj['d_lines'] if isinstance(d_proj['d_lines'], list) else []
                    # If we have d_lines, calculate PRZ from them
                    if d_lines and not prz_min:
                        valid_d_lines = [float(d) for d in d_lines if d is not None and str(d).replace('.','').replace('-','').isdigit()]
                        if valid_d_lines:
                            prz_min = min(valid_d_lines)  # No tolerance - exact PRZ boundaries
                            prz_max = max(valid_d_lines)  # No tolerance - exact PRZ boundaries

                # Handle prz_zones structure from comprehensive_abcd_patterns
                if 'prz_zones' in d_proj and isinstance(d_proj['prz_zones'], list) and len(d_proj['prz_zones']) > 0:
                    # Store each zone separately for accurate tracking
                    prz_zones = d_proj['prz_zones']
                    # For backward compatibility, also set overall min/max
                    all_mins = [float(zone['min']) for zone in d_proj['prz_zones'] if 'min' in zone]
                    all_maxs = [float(zone['max']) for zone in d_proj['prz_zones'] if 'max' in zone]
                    if all_mins and all_maxs:
                        prz_min = min(all_mins)
                        prz_max = max(all_maxs)
                elif 'prz' in d_proj and isinstance(d_proj['prz'], (tuple, list)) and len(d_proj['prz']) >= 2:
                    prz_min = float(d_proj['prz'][0])
                    prz_max = float(d_proj['prz'][1])

            projected_d_time = current_bar + 10  # Estimate
        else:
            # Old structure with direct keys (fallback)
            x_point = pattern.get('X', (0, 0))
            a_point = pattern.get('A', (0, 0))
            b_point = pattern.get('B', (0, 0))
            c_point = pattern.get('C', (0, 0))

            # Check for D_projections (another format)
            d_proj = pattern.get('D_projections', {})
            prz_min = None
            prz_max = None
            prz_zones = []

            if d_proj:
                prz_min = d_proj.get('prz_min')
                prz_max = d_proj.get('prz_max')
                d_lines = d_proj.get('d_lines', [])
            else:
                # Extract PRZ or d_lines from top level
                prz = pattern.get('prz', pattern.get('PRZ', []))
                if prz and len(prz) >= 2:
                    prz_min = float(min(prz))
                    prz_max = float(max(prz))
                d_lines = pattern.get('d_lines', [])
            projected_d_time = pattern.get('D_time', current_bar + 10)

        # Create new tracked pattern with Unicode fixes
        from pattern_data_standard import fix_unicode_issues
        raw_name = pattern.get('subtype', pattern.get('name', ''))
        clean_name = fix_unicode_issues(raw_name)

        tracked = TrackedPattern(
            pattern_id=pattern_id,
            pattern_type=pattern.get('pattern_type', 'Unknown'),
            subtype=clean_name,
            first_seen_bar=current_bar,
            x_point=x_point,
            a_point=a_point,
            b_point=b_point,
            c_point=c_point,
            prz_min=prz_min,
            prz_max=prz_max,
            prz_zones=prz_zones if 'prz_zones' in locals() else [],
            d_lines=d_lines,
            projected_d_time=projected_d_time,
            detection_timestamp=current_timestamp,
            status='pending'
        )

        self.tracked_patterns[pattern_id] = tracked

        # Update pattern type statistics
        pattern_key = f"{tracked.pattern_type}_{tracked.subtype}"
        if pattern_key not in self.pattern_type_stats:
            self.pattern_type_stats[pattern_key] = {
                'total_detected': 0,
                'success': 0,  # Zone reached + reversal
                'failed': 0,   # Zone reached + violated
                'dismissed': 0,  # Structure broken before zone
                'completed': 0,  # Legacy - kept for compatibility
                'completion_rate': 0.0,
                'success_rate': 0.0,
                'avg_accuracy': 0.0,
                'avg_bars_to_complete': 0.0,
                'accuracies': [],
                'completion_times': [],
                'pattern_transformations': {}  # Track what patterns actually form
            }

        self.pattern_type_stats[pattern_key]['total_detected'] += 1

        return pattern_id

    def update_unformed_to_formed(self, formed_pattern: Dict, current_bar: int) -> Optional[str]:
        """
        Check if a formed pattern matches an existing unformed pattern and update it.

        Args:
            formed_pattern: Formed pattern dictionary with all points including D
            current_bar: Current bar index

        Returns:
            Pattern ID if matched and updated, None otherwise
        """
        # Extract points from formed pattern
        points = formed_pattern.get('points', {})
        if 'D' not in points:
            return None

        # Get formed pattern type and name
        pattern_type = formed_pattern.get('pattern_type', 'ABCD')
        formed_name = formed_pattern.get('name', '')

        # Extract key points for matching
        a_point = points.get('A')
        b_point = points.get('B')
        c_point = points.get('C')
        x_point = points.get('X') if pattern_type == 'XABCD' else None
        d_point = points.get('D')

        if not all([a_point, b_point, c_point, d_point]):
            return None

        # Get indices - they might be in a separate 'indices' dict or in the points themselves
        indices = formed_pattern.get('indices', {})

        # Look for matching unformed pattern
        for pattern_id, tracked in self.tracked_patterns.items():
            # Skip if not pending or already has D point
            if tracked.status != 'pending' or tracked.actual_d_price:
                continue

            # Check pattern type matches
            if tracked.pattern_type != pattern_type:
                continue

            # Check if pattern names are compatible using standardized naming
            from pattern_data_standard import standardize_pattern_name, fix_unicode_issues

            # Get base names by removing status and direction indicators
            unformed_base = tracked.subtype
            # Remove common suffixes for comparison
            for suffix in ['_unformed', '_formed', '_strict', '_bull', '_bear']:
                unformed_base = unformed_base.replace(suffix, '')

            formed_base = formed_name
            for suffix in ['_unformed', '_formed', '_strict', '_bull', '_bear']:
                formed_base = formed_base.replace(suffix, '')

            # Check if base names match
            if not (unformed_base == formed_base or unformed_base in formed_base or formed_base in unformed_base):
                continue

            # Check if key points match (using indices for exact matching)
            # Try to get indices from the 'indices' dict first, then from points
            a_idx = indices.get('A', a_point.get('index', -1)) if indices else a_point.get('index', -1)
            b_idx = indices.get('B', b_point.get('index', -1)) if indices else b_point.get('index', -1)
            c_idx = indices.get('C', c_point.get('index', -1)) if indices else c_point.get('index', -1)

            if (tracked.a_point[0] == a_idx and
                tracked.b_point[0] == b_idx and
                tracked.c_point[0] == c_idx):

                # For XABCD, also check X point
                if pattern_type == 'XABCD':
                    x_idx = indices.get('X', x_point.get('index', -1)) if indices and x_point else -1
                    if tracked.x_point and tracked.x_point[0] != x_idx:
                        continue

                # This is a match! Update the tracked pattern with D point
                d_idx = indices.get('D', d_point.get('index', -1)) if indices else d_point.get('index', -1)
                d_price = d_point.get('price', 0)

                tracked.d_point = (d_idx, d_price)  # Set the D point
                tracked.actual_d_price = d_price
                tracked.actual_d_bar = d_idx
                tracked.formed_pattern_name = formed_name
                tracked.bars_from_c_to_zone = d_idx - tracked.c_point[0]
                tracked.bars_from_a_to_d = d_idx - tracked.a_point[0]

                print(f"Pattern {pattern_id[:8]}... transitioned from unformed to formed at bar {current_bar}")
                print(f"  Type: {pattern_type}, Name: {fix_unicode_issues(formed_name)}")
                print(f"  D point: bar {d_idx}, price {d_price:.2f}")

                return pattern_id

        return None

    def validate_pattern_ratios(self, tracked: 'TrackedPattern', d_price: float) -> bool:
        """
        Validate if pattern ratios are still valid when D point is reached.
        Uses exact ratios from pattern_ratios_2_Final.py

        Args:
            tracked: The tracked pattern
            d_price: The price at potential D point

        Returns:
            True if ratios are valid, False otherwise
        """
        # Import pattern ratios
        try:
            from pattern_ratios_2_Final import ABCD_PATTERN_RATIOS, XABCD_PATTERN_RATIOS
        except ImportError:
            # Fallback to generic validation if import fails
            return self._generic_ratio_validation(tracked, d_price)

        # Calculate current ratios with the D price
        x_price = tracked.x_point[1] if tracked.x_point else 0
        a_price = tracked.a_point[1]
        b_price = tracked.b_point[1]
        c_price = tracked.c_point[1]

        # For ABCD patterns
        if tracked.pattern_type == 'ABCD':
            ab_move = abs(b_price - a_price)
            bc_move = abs(c_price - b_price)
            cd_move = abs(d_price - c_price)

            if ab_move > 0 and bc_move > 0:
                bc_retracement = (bc_move / ab_move) * 100
                cd_projection = (cd_move / bc_move) * 100

                # Determine if pattern is bullish or bearish
                # For bullish ABCD: A (high) > B (low), expects bullish reversal at D
                # For bearish ABCD: A (low) < B (high), expects bearish reversal at D
                is_bullish = a_price > b_price

                # Check against all ABCD pattern configurations
                for pattern_name, ratios in ABCD_PATTERN_RATIOS.items():
                    # Match pattern type (bull/bear)
                    if is_bullish and '_bear' in pattern_name:
                        continue
                    if not is_bullish and '_bull' in pattern_name:
                        continue

                    # Check if ratios match
                    retr_min, retr_max = ratios['retr']
                    proj_min, proj_max = ratios['proj']

                    if (retr_min <= bc_retracement <= retr_max and
                        proj_min <= cd_projection <= proj_max):
                        return True

                # No matching pattern found
                return False

        # For XABCD patterns
        elif tracked.pattern_type == 'XABCD' and x_price > 0:
            xa_move = abs(a_price - x_price)
            ab_move = abs(b_price - a_price)
            bc_move = abs(c_price - b_price)
            cd_move = abs(d_price - c_price)
            xd_move = abs(d_price - x_price)

            if xa_move > 0 and ab_move > 0 and bc_move > 0:
                ab_xa_ratio = (ab_move / xa_move) * 100
                bc_ab_ratio = (bc_move / ab_move) * 100
                cd_bc_ratio = (cd_move / bc_move) * 100
                ad_xa_ratio = (xd_move / xa_move) * 100

                # Determine if pattern is bullish or bearish
                is_bullish = a_price > x_price

                # Check against all XABCD pattern configurations
                for pattern_name, ratios in XABCD_PATTERN_RATIOS.items():
                    # Match pattern type (bull/bear)
                    if is_bullish and '_bear' in pattern_name:
                        continue
                    if not is_bullish and '_bull' in pattern_name:
                        continue

                    # Check all ratio requirements
                    ratios_match = True
                    if 'ab_xa' in ratios:
                        if not (ratios['ab_xa'][0] <= ab_xa_ratio <= ratios['ab_xa'][1]):
                            ratios_match = False
                    if 'bc_ab' in ratios and ratios_match:
                        if not (ratios['bc_ab'][0] <= bc_ab_ratio <= ratios['bc_ab'][1]):
                            ratios_match = False
                    if 'cd_bc' in ratios and ratios_match:
                        if not (ratios['cd_bc'][0] <= cd_bc_ratio <= ratios['cd_bc'][1]):
                            ratios_match = False
                    if 'ad_xa' in ratios and ratios_match:
                        if not (ratios['ad_xa'][0] <= ad_xa_ratio <= ratios['ad_xa'][1]):
                            ratios_match = False

                    if ratios_match:
                        return True

                # No matching pattern found
                return False

        return True

    def _generic_ratio_validation(self, tracked: 'TrackedPattern', d_price: float) -> bool:
        """Fallback generic ratio validation using wider tolerances"""
        x_price = tracked.x_point[1] if tracked.x_point else 0
        a_price = tracked.a_point[1]
        b_price = tracked.b_point[1]
        c_price = tracked.c_point[1]

        if tracked.pattern_type == 'ABCD':
            ab_distance = abs(b_price - a_price)
            cd_distance = abs(d_price - c_price)
            if ab_distance > 0:
                ab_cd_ratio = cd_distance / ab_distance
                # Allow wider range for generic validation
                if ab_cd_ratio < 0.5 or ab_cd_ratio > 2.0:
                    return False
            bc_retracement = abs(c_price - b_price) / abs(b_price - a_price) if ab_distance > 0 else 0
            if bc_retracement < 0.3 or bc_retracement > 1.0:
                return False

        elif tracked.pattern_type == 'XABCD' and x_price > 0:
            xa_distance = abs(a_price - x_price)
            xb_retracement = abs(b_price - x_price) / xa_distance if xa_distance > 0 else 0
            xd_retracement = abs(d_price - x_price) / xa_distance if xa_distance > 0 else 0
            if xd_retracement < 0.4 or xd_retracement > 2.5:
                return False
            if xb_retracement < 0.2 or xb_retracement > 1.0:
                return False

        return True

    def check_price_in_zone(self, price_high: float, price_low: float, current_bar: int,
                            current_timestamp: datetime = None, data_for_detection = None) -> List[str]:
        """
        Check if current price enters any tracked pattern's D zone.
        Returns list of pattern IDs that completed.

        Args:
            price_high: Current bar's high price
            price_low: Current bar's low price
            current_bar: Current bar index
            current_timestamp: Current timestamp
            data_for_detection: Data to use for formed pattern detection

        Returns:
            List of pattern IDs that completed
        """
        self.current_bar = current_bar
        self.current_data = data_for_detection
        completed_patterns = []

        # Debug: Count patterns being checked
        pending_count = sum(1 for p in self.tracked_patterns.values() if p.status == 'pending')
        if pending_count > 0 and current_bar % 10 == 0:  # Print every 10 bars to avoid spam
            prz_count = sum(1 for p in self.tracked_patterns.values()
                          if p.status == 'pending' and p.prz_min and p.prz_max)
            print(f"DEBUG check_price_in_zone bar {current_bar}: {pending_count} pending, {prz_count} have PRZ, price H:{price_high:.2f} L:{price_low:.2f}")

        for pattern_id, tracked in self.tracked_patterns.items():
            # Skip if not pending
            if tracked.status != 'pending':
                continue

            # Check if price enters the pattern's D zone
            zone_entered = False
            entry_price = None

            if tracked.pattern_type == 'ABCD':
                # Check each PRZ zone separately if available
                if tracked.prz_zones:
                    for zone in tracked.prz_zones:
                        zone_min = float(zone.get('min', 0))
                        zone_max = float(zone.get('max', 0))
                        if zone_min and zone_max:
                            if price_low <= zone_max and price_high >= zone_min:
                                zone_entered = True
                                # Record the price that entered the zone
                                if price_low >= zone_min and price_low <= zone_max:
                                    entry_price = price_low
                                elif price_high >= zone_min and price_high <= zone_max:
                                    entry_price = price_high
                                else:
                                    entry_price = (zone_min + zone_max) / 2
                                # Store which specific zone was entered
                                tracked.completion_details['entered_zone'] = zone.get('pattern_source', 'unknown')
                                break  # Stop checking once we find a matching zone
                # Fallback to old method if no zones
                elif tracked.prz_min is not None and tracked.prz_max is not None:
                    if price_low <= tracked.prz_max and price_high >= tracked.prz_min:
                        zone_entered = True
                        # Record the price that entered the zone
                        if price_low >= tracked.prz_min and price_low <= tracked.prz_max:
                            entry_price = price_low
                        elif price_high >= tracked.prz_min and price_high <= tracked.prz_max:
                            entry_price = price_high
                        else:
                            entry_price = (tracked.prz_min + tracked.prz_max) / 2

            elif tracked.pattern_type == 'XABCD' and tracked.d_lines:
                # Check d_lines for XABCD patterns
                d_min = min(tracked.d_lines)
                d_max = max(tracked.d_lines)
                if price_low <= d_max and price_high >= d_min:
                    zone_entered = True
                    # Record the price that entered the zone
                    if price_low >= d_min and price_low <= d_max:
                        entry_price = price_low
                    elif price_high >= d_min and price_high <= d_max:
                        entry_price = price_high
                    else:
                        entry_price = (d_min + d_max) / 2

            if zone_entered:
                # Validate pattern ratios before marking as success
                if not self.validate_pattern_ratios(tracked, entry_price):
                    # Ratios are invalid - dismiss the pattern
                    tracked.status = 'dismissed'
                    tracked.completion_details['dismissal_reason'] = "Invalid ratios at D zone"
                    tracked.completion_details['dismissal_bar'] = current_bar

                    # Update statistics for dismissal
                    pattern_key = f"{tracked.pattern_type}_{tracked.subtype}"
                    if pattern_key in self.pattern_type_stats:
                        self.pattern_type_stats[pattern_key]['dismissed'] = \
                            self.pattern_type_stats[pattern_key].get('dismissed', 0) + 1

                    # Don't add to completed patterns - it's dismissed
                    continue

                # Ratios are valid - proceed with normal zone entry logic
                tracked.zone_reached = True
                tracked.zone_entry_bar = current_bar
                tracked.zone_entry_price = entry_price
                tracked.zone_entry_timestamp = current_timestamp

                # Calculate timing metrics
                tracked.bars_from_c_to_zone = current_bar - tracked.c_point[0]
                tracked.bars_from_a_to_d = current_bar - tracked.a_point[0]
                tracked.bars_from_detection_to_completion = current_bar - tracked.first_seen_bar

                # Initially mark as in_zone (will determine success/failure later)
                tracked.status = 'in_zone'
                print(f"DEBUG: Pattern {pattern_id[:30]}... entered zone at price {entry_price:.2f}, marked as in_zone")
                # Also write to file for debugging
                with open('pattern_debug.log', 'a') as f:
                    f.write(f"Pattern {pattern_id[:30]}... entered zone at price {entry_price:.2f}, status: in_zone\n")
                tracked.actual_d_price = entry_price
                tracked.actual_d_bar = current_bar
                tracked.actual_d_timestamp = current_timestamp

                completed_patterns.append(pattern_id)

                # Track that pattern entered zone but don't count as success yet
                pattern_key = f"{tracked.pattern_type}_{tracked.subtype}"
                stats = self.pattern_type_stats[pattern_key]
                # Add a new counter for patterns in zone
                if 'in_zone' not in stats:
                    stats['in_zone'] = 0
                stats['in_zone'] += 1
                stats['completion_times'].append(tracked.bars_from_detection_to_completion)

                # Calculate price accuracy
                if tracked.pattern_type == 'ABCD' and tracked.prz_min and tracked.prz_max:
                    # How well did price hit the middle of PRZ?
                    prz_center = (tracked.prz_min + tracked.prz_max) / 2
                    prz_width = tracked.prz_max - tracked.prz_min
                    if prz_width > 0:
                        tracked.price_accuracy = 1 - abs(entry_price - prz_center) / prz_width
                    else:
                        tracked.price_accuracy = 1.0
                elif tracked.pattern_type == 'XABCD' and tracked.d_lines:
                    # How well did price hit the middle of d_lines range?
                    d_center = np.mean(tracked.d_lines)
                    d_range = max(tracked.d_lines) - min(tracked.d_lines)
                    if d_range > 0:
                        tracked.price_accuracy = 1 - abs(entry_price - d_center) / d_range
                    else:
                        tracked.price_accuracy = 1.0

                stats['accuracies'].append(tracked.price_accuracy or 0)

                # Don't update success rate yet - pattern outcome undetermined
                stats['avg_accuracy'] = np.mean(stats['accuracies']) if stats['accuracies'] else 0
                stats['avg_bars_to_complete'] = np.mean(stats['completion_times']) if stats['completion_times'] else 0

        return completed_patterns

    def track_formed_pattern(self, pattern: Dict, current_bar: int, bars_data: pd.DataFrame) -> str:
        """
        Track a formed pattern (one that already has D point) and evaluate its success/failure.

        Args:
            pattern: Formed pattern dictionary with all points including D
            current_bar: Current bar index
            bars_data: DataFrame with OHLC data to evaluate post-D price action

        Returns:
            Pattern ID of the tracked pattern
        """
        pattern_id = self.generate_pattern_id(pattern)

        # Skip if already tracked
        if pattern_id in self.tracked_patterns:
            return pattern_id

        # Extract pattern points
        points = pattern.get('points', {})
        if 'D' not in points:
            # Not a formed pattern, skip
            return None

        # Create tracked pattern object for formed pattern
        pattern_type = pattern.get('pattern_type', 'ABCD')
        subtype = pattern.get('name', pattern.get('subtype', 'Unknown'))

        # Get point values
        d_point = points.get('D')
        if not d_point:
            return None

        # Determine pattern direction
        if pattern_type == 'ABCD':
            a_point = points.get('A')
            b_point = points.get('B')
            if not a_point or not b_point:
                return None
            is_bullish = a_point[1] > b_point[1]  # A > B for bullish
        else:  # XABCD
            x_point = points.get('X')
            a_point = points.get('A')
            if not x_point or not a_point:
                return None
            is_bullish = a_point[1] > x_point[1]  # A > X for bullish

        # Create tracked pattern for the formed pattern
        tracked = TrackedPattern(
            pattern_id=pattern_id,
            pattern_type=pattern_type,
            subtype=subtype,
            a_point=(0, a_point[1]) if 'A' in points else (0, 0),
            b_point=(0, points['B'][1]) if 'B' in points else (0, 0),
            c_point=(0, points['C'][1]) if 'C' in points else (0, 0),
            x_point=(0, points['X'][1]) if 'X' in points and pattern_type == 'XABCD' else None,
            detection_bar=current_bar,
            status='evaluating'  # New status for formed patterns being evaluated
        )

        # Get D point details
        d_bar = d_point[0] if isinstance(d_point, (list, tuple)) else current_bar
        d_price = d_point[1] if isinstance(d_point, (list, tuple)) else d_point

        # Look at bars after D to evaluate success/failure
        reversal_threshold = 0.02  # 2% reversal to confirm success
        max_bars_to_check = min(10, len(bars_data) - d_bar - 1)  # Check up to 10 bars after D

        if max_bars_to_check <= 0:
            # Not enough data after D to evaluate
            tracked.status = 'pending'
            self.tracked_patterns[pattern_id] = tracked
            return pattern_id

        # Check price action after D
        success = False
        failure = False

        for i in range(1, max_bars_to_check + 1):
            if d_bar + i >= len(bars_data):
                break

            bar = bars_data.iloc[d_bar + i]

            if is_bullish:
                # Bullish pattern: D is a low, should reverse up
                reversal_amount = (bar['High'] - d_price) / d_price
                if reversal_amount > reversal_threshold:
                    success = True
                    break
                # Check for failure: price goes significantly below D
                if bar['Low'] < d_price * 0.98:  # 2% below D
                    failure = True
                    break
            else:
                # Bearish pattern: D is a high, should reverse down
                reversal_amount = (d_price - bar['Low']) / d_price
                if reversal_amount > reversal_threshold:
                    success = True
                    break
                # Check for failure: price goes significantly above D
                if bar['High'] > d_price * 1.02:  # 2% above D
                    failure = True
                    break

        # Set final status
        if success:
            tracked.status = 'success'
            tracked.reversal_confirmed = True
            tracked.formed_pattern_name = subtype
        elif failure:
            tracked.status = 'failed'
            tracked.completion_details = {'failure_reason': 'Price continued past D without reversal'}
        else:
            tracked.status = 'inconclusive'  # Not enough movement to determine

        # Store the tracked pattern
        self.tracked_patterns[pattern_id] = tracked

        # Update statistics
        pattern_key = f"{pattern_type}_{subtype}"
        if pattern_key not in self.pattern_type_stats:
            self.pattern_type_stats[pattern_key] = {
                'total': 0,
                'success': 0,
                'failed': 0,
                'inconclusive': 0
            }

        self.pattern_type_stats[pattern_key]['total'] += 1
        if success:
            self.pattern_type_stats[pattern_key]['success'] += 1
        elif failure:
            self.pattern_type_stats[pattern_key]['failed'] += 1
        else:
            self.pattern_type_stats[pattern_key]['inconclusive'] += 1

        return pattern_id

    def update_formed_patterns(self, formed_patterns: List[Dict], current_bar: int):
        """
        Update tracked patterns with information about what patterns actually formed.

        Args:
            formed_patterns: List of formed patterns detected
            current_bar: Current bar index
        """
        # For each completed pattern that just entered its zone
        # Check what pattern(s) actually formed at this point
        for formed in formed_patterns:
            formed_name = formed.get('name', formed.get('subtype', 'Unknown'))
            formed_type = formed.get('pattern_type', 'Unknown')

            # Find recently completed patterns to update
            for pattern_id, tracked in self.tracked_patterns.items():
                if (tracked.status == 'completed' and
                    tracked.zone_entry_bar == current_bar and
                    tracked.formed_pattern_name is None):

                    # Record what pattern actually formed
                    tracked.formed_pattern_name = formed_name

                    # Update pattern transformation statistics
                    pattern_key = f"{tracked.pattern_type}_{tracked.subtype}"
                    stats = self.pattern_type_stats[pattern_key]
                    if 'pattern_transformations' not in stats:
                        stats['pattern_transformations'] = {}

                    if formed_name not in stats['pattern_transformations']:
                        stats['pattern_transformations'][formed_name] = 0
                    stats['pattern_transformations'][formed_name] += 1

                    # Calculate pattern match accuracy
                    if tracked.subtype.lower() == formed_name.lower():
                        tracked.pattern_match_accuracy = 1.0  # Perfect match
                    elif tracked.subtype.split('_')[0].lower() == formed_name.split('_')[0].lower():
                        tracked.pattern_match_accuracy = 0.5  # Same base pattern
                    else:
                        tracked.pattern_match_accuracy = 0.0  # Different pattern

    def check_pattern_dismissal(self, price_high: float, price_low: float, current_bar: int) -> List[str]:
        """
        Check if any pending patterns should be dismissed due to structure break.

        Args:
            price_high: Current bar high
            price_low: Current bar low
            current_bar: Current bar index

        Returns:
            List of dismissed pattern IDs
        """
        dismissed_patterns = []

        for pattern_id, tracked in list(self.tracked_patterns.items()):
            # Only check pending patterns
            if tracked.status != 'pending':
                continue

            # Get C point price
            c_price = tracked.c_point[1]

            # Check for structure break or zone overshoot
            should_dismiss = False
            reason = ""

            # Determine if pattern is bullish or bearish based on points
            is_bullish = tracked.b_point[1] > tracked.a_point[1]  # B higher than A

            if is_bullish:
                # For bullish patterns, dismiss if price breaks below C
                if price_low < c_price:  # Exact check - no tolerance
                    should_dismiss = True
                    reason = "Structure broken - price below C"
            else:
                # For bearish patterns, dismiss if price breaks above C
                if price_high > c_price:  # Exact check - no tolerance
                    should_dismiss = True
                    reason = "Structure broken - price above C"

            if should_dismiss:
                tracked.status = 'dismissed'
                tracked.completion_details['dismissal_reason'] = reason
                tracked.completion_details['dismissal_bar'] = current_bar
                dismissed_patterns.append(pattern_id)

                # Update statistics
                pattern_key = f"{tracked.pattern_type}_{tracked.subtype}"
                if pattern_key in self.pattern_type_stats:
                    self.pattern_type_stats[pattern_key]['dismissed'] = \
                        self.pattern_type_stats[pattern_key].get('dismissed', 0) + 1

        return dismissed_patterns

    def check_zone_violation(self, price_high: float, price_low: float, current_bar: int) -> List[str]:
        """
        Check if any patterns that entered their zone have now violated it (failed).

        Args:
            price_high: Current bar high
            price_low: Current bar low
            current_bar: Current bar index

        Returns:
            List of failed pattern IDs
        """
        failed_patterns = []
        successful_patterns = []

        for pattern_id, tracked in self.tracked_patterns.items():
            # Skip patterns that haven't entered zone yet
            if not tracked.zone_reached:
                continue

            # Determine if pattern is bullish or bearish
            # For bullish ABCD: A (high) > B (low), expects bullish reversal at D
            # For bearish ABCD: A (low) < B (high), expects bearish reversal at D
            is_bullish = tracked.a_point[1] > tracked.b_point[1]

            # Initialize variables for tracking zone status
            zone_violated = False
            reversal_confirmed = False

            # Handle patterns that are in_zone - check for success or failure
            if tracked.status == 'in_zone':

                # Get PRZ boundaries
                prz_min = tracked.prz_min
                prz_max = tracked.prz_max

                # Debug logging
                if pattern_id and 'ABCD' in pattern_id and tracked.zone_reached:
                    print(f"DEBUG in_zone check: {pattern_id[:20]}... PRZ:{prz_min:.2f}-{prz_max:.2f} H:{price_high:.2f} L:{price_low:.2f}")

                if is_bullish:
                    # Bullish pattern: price falls TO the PRZ, then should reverse UP
                    # Success: price rises and exits above the PRZ (reversal upward)
                    if price_high > prz_max:
                        reversal_confirmed = True
                        print(f"  -> SUCCESS: Bullish reversal confirmed (high {price_high:.2f} > PRZ max {prz_max:.2f})")
                    # Failure: price breaks below the PRZ (violation)
                    elif price_low < prz_min:
                        zone_violated = True
                        print(f"  -> FAILED: PRZ violated (low {price_low:.2f} < PRZ min {prz_min:.2f})")
                else:
                    # Bearish pattern: price rises TO the PRZ, then should reverse DOWN
                    # Success: price falls and exits below the PRZ (reversal downward)
                    if price_low < prz_min:
                        reversal_confirmed = True
                        print(f"  -> SUCCESS: Bearish reversal confirmed (low {price_low:.2f} < PRZ min {prz_min:.2f})")
                    # Failure: price breaks above the PRZ (violation)
                    elif price_high > prz_max:
                        zone_violated = True
                        print(f"  -> FAILED: PRZ violated (high {price_high:.2f} > PRZ max {prz_max:.2f})")

            # For patterns NOT in_zone, check for violations (for already successful patterns)
            if tracked.status != 'in_zone' and tracked.pattern_type == 'ABCD':
                # Check the appropriate PRZ based on whether we have zones or single values
                if tracked.prz_zones and tracked.completion_details.get('entered_zone'):
                    # Find the specific zone that was entered
                    entered_zone_name = tracked.completion_details['entered_zone']
                    for zone in tracked.prz_zones:
                        if zone.get('pattern_source') == entered_zone_name:
                            zone_min = float(zone.get('min', 0))
                            zone_max = float(zone.get('max', 0))
                            if is_bullish:
                                # For bullish ABCD, fail if price goes significantly below PRZ minimum
                                # Exact PRZ boundaries - any violation is failure
                                if price_low < zone_min:  # No tolerance
                                    zone_violated = True
                            else:
                                # For bearish ABCD, fail if price goes significantly above PRZ maximum
                                # Exact PRZ boundaries - any violation is failure
                                if price_high > zone_max:  # No tolerance
                                    zone_violated = True
                            break
                elif tracked.prz_min and tracked.prz_max:
                    if is_bullish:
                        # For bullish ABCD, fail if price goes significantly below PRZ minimum
                        # Exact PRZ boundaries - any violation is failure
                        if price_low < tracked.prz_min:  # No tolerance
                            zone_violated = True
                    else:
                        # For bearish ABCD, fail if price goes significantly above PRZ maximum
                        # Exact PRZ boundaries - any violation is failure
                        if price_high > tracked.prz_max:  # No tolerance
                            zone_violated = True

            elif tracked.status != 'in_zone' and tracked.pattern_type == 'XABCD' and tracked.d_lines:
                d_min = min(tracked.d_lines)
                d_max = max(tracked.d_lines)

                if is_bullish:
                    # For bullish XABCD, fail if price goes significantly below d_lines minimum
                    # Exact PRZ boundaries - any violation is failure
                    if price_low < d_min:  # No tolerance
                        zone_violated = True
                else:
                    # For bearish XABCD, fail if price goes significantly above d_lines maximum
                    # Exact PRZ boundaries - any violation is failure
                    if price_high > d_max:  # No tolerance
                        zone_violated = True

            # Now determine the outcome based on the pattern's status and price action
            if tracked.status == 'in_zone':
                # Pattern is in zone - check if it should transition to success or failure
                if 'reversal_confirmed' in locals() and reversal_confirmed:
                    # Pattern succeeded - price left PRZ in expected direction
                    tracked.status = 'success'
                    tracked.reversal_confirmed = True
                    tracked.reversal_bar = current_bar
                    # For bullish, reversal price is when it went above PRZ max
                    # For bearish, reversal price is when it went below PRZ min
                    tracked.reversal_price = price_high if is_bullish else price_low
                    successful_patterns.append(pattern_id)

                    # Update statistics
                    pattern_key = f"{tracked.pattern_type}_{tracked.subtype}"
                    if pattern_key in self.pattern_type_stats:
                        self.pattern_type_stats[pattern_key]['success'] = \
                            self.pattern_type_stats[pattern_key].get('success', 0) + 1
                        self.pattern_type_stats[pattern_key]['in_zone'] = max(0,
                            self.pattern_type_stats[pattern_key].get('in_zone', 0) - 1)

                        # Recalculate success rate
                        total_concluded = (self.pattern_type_stats[pattern_key].get('success', 0) +
                                         self.pattern_type_stats[pattern_key].get('failed', 0))
                        if total_concluded > 0:
                            self.pattern_type_stats[pattern_key]['success_rate'] = \
                                self.pattern_type_stats[pattern_key]['success'] / total_concluded

                elif zone_violated:
                    # Pattern failed - price violated PRZ boundaries
                    tracked.status = 'failed'
                    tracked.zone_exit_bar = current_bar
                    tracked.zone_exit_price = price_low if is_bullish else price_high
                    tracked.completion_details['failure_reason'] = "PRZ violated without reversal"
                    failed_patterns.append(pattern_id)

                    # Update statistics
                    pattern_key = f"{tracked.pattern_type}_{tracked.subtype}"
                    if pattern_key in self.pattern_type_stats:
                        self.pattern_type_stats[pattern_key]['failed'] = \
                            self.pattern_type_stats[pattern_key].get('failed', 0) + 1
                        self.pattern_type_stats[pattern_key]['in_zone'] = max(0,
                            self.pattern_type_stats[pattern_key].get('in_zone', 0) - 1)

                        # Recalculate success rate
                        total_concluded = (self.pattern_type_stats[pattern_key].get('success', 0) +
                                         self.pattern_type_stats[pattern_key].get('failed', 0))
                        if total_concluded > 0:
                            self.pattern_type_stats[pattern_key]['success_rate'] = \
                                self.pattern_type_stats[pattern_key]['success'] / total_concluded
                # else: Pattern stays in_zone - neither success nor failure yet

            # Once a pattern is successful, it stays successful - no stop-loss logic
            # Only patterns that are in_zone can transition to success or failed

        # Add both successful and failed patterns to completion history
        for pattern_id in successful_patterns:
            if pattern_id in self.tracked_patterns:
                self.completion_history.append(self.tracked_patterns[pattern_id])

        for pattern_id in failed_patterns:
            if pattern_id in self.tracked_patterns:
                self.completion_history.append(self.tracked_patterns[pattern_id])

        # Return both lists
        return failed_patterns  # Keeping same return for backward compatibility

    def get_completion_statistics(self) -> Dict:
        """
        Get comprehensive completion statistics for all tracked patterns.

        Returns:
            Dictionary containing completion statistics
        """
        total_patterns = len(self.tracked_patterns)
        success = sum(1 for p in self.tracked_patterns.values() if p.status == 'success')
        failed = sum(1 for p in self.tracked_patterns.values() if p.status == 'failed')
        dismissed = sum(1 for p in self.tracked_patterns.values() if p.status == 'dismissed')
        pending = sum(1 for p in self.tracked_patterns.values() if p.status == 'pending')
        in_zone = sum(1 for p in self.tracked_patterns.values() if p.status == 'in_zone')
        inconclusive = sum(1 for p in self.tracked_patterns.values() if p.status == 'inconclusive')
        evaluating = sum(1 for p in self.tracked_patterns.values() if p.status == 'evaluating')

        # Calculate success rate for patterns that reached a conclusion
        concluded = success + failed
        success_rate = success / concluded if concluded > 0 else 0

        # Calculate average accuracy for completed patterns
        accuracies = [p.price_accuracy for p in self.completion_history if p.price_accuracy]
        avg_accuracy = np.mean(accuracies) if accuracies else 0

        # Calculate average time to completion
        completion_times = [p.bars_from_detection_to_completion for p in self.completion_history
                          if p.bars_from_detection_to_completion]
        avg_completion_time = np.mean(completion_times) if completion_times else 0

        # Calculate pattern formation times (A to D)
        formation_times = [p.bars_from_a_to_d for p in self.completion_history if p.bars_from_a_to_d]
        avg_formation_time = np.mean(formation_times) if formation_times else 0

        # Get top performing pattern types
        top_patterns = []
        for pattern_key, stats in self.pattern_type_stats.items():
            if stats['total_detected'] >= 5:  # Minimum sample size
                top_patterns.append({
                    'type': pattern_key,
                    'completion_rate': stats['completion_rate'],
                    'avg_accuracy': stats['avg_accuracy'],
                    'total': stats['total_detected'],
                    'completed': stats['completed'],
                    'transformations': stats.get('pattern_transformations', {})
                })

        # Sort by completion rate
        top_patterns.sort(key=lambda x: x['completion_rate'], reverse=True)

        return {
            'total_tracked': total_patterns,
            'success': success,
            'failed': failed,
            'dismissed': dismissed,
            'pending': pending,
            'in_zone': in_zone,
            'inconclusive': inconclusive,
            'evaluating': evaluating,
            'concluded': concluded,
            'success_rate': success_rate,
            'avg_projection_accuracy': avg_accuracy,
            'avg_bars_to_complete': avg_completion_time,
            'avg_bars_formation': avg_formation_time,
            'pattern_type_stats': self.pattern_type_stats,
            'top_performing_patterns': top_patterns[:10],  # Top 10
            'completion_history': self.completion_history[-20:]  # Last 20 completions
        }

    def get_pattern_details(self, pattern_id: str) -> Optional[TrackedPattern]:
        """
        Get detailed information about a specific pattern.

        Args:
            pattern_id: ID of the pattern

        Returns:
            TrackedPattern object or None if not found
        """
        return self.tracked_patterns.get(pattern_id)

    def reset(self):
        """Reset the tracker for a new backtest run."""
        self.tracked_patterns.clear()
        self.completion_history.clear()
        self.pattern_type_stats.clear()
        self.current_bar = 0
        self.current_data = None