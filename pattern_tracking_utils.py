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
from typing import Optional


@dataclass
class ZoneEntry:
    """Represents a single entry into a PRZ or d-line zone"""
    entry_id: str  # Unique ID for this entry
    pattern_id: str  # Parent pattern ID
    zone_level: float  # Specific price level or zone midpoint
    zone_min: float  # Zone minimum
    zone_max: float  # Zone maximum
    entry_bar: int  # Bar where entry occurred
    entry_price: float  # Price at entry
    entry_timestamp: Optional[datetime] = None
    exit_bar: Optional[int] = None  # Bar where price exited zone
    exit_price: Optional[float] = None  # Price at exit
    status: str = 'active'  # active, success, invalid_prz
    reversal_confirmed: bool = False
    reversal_bar: Optional[int] = None
    reversal_price: Optional[float] = None
    pattern_type: str = ''  # ABCD or XABCD
    pattern_subtype: str = ''  # Gartley, Butterfly, etc.
    is_bullish: bool = True  # Direction expectation

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

    # Fields with defaults must come after required fields
    prz_instance: str = 'prz_1'  # NEW: Which PRZ instance this tracks (prz_1, prz_2, etc.)
    d_point: Optional[Tuple[int, float]] = None  # D point when pattern becomes formed

    # Projected D zone (PRZ for ABCD, d_lines for XABCD)
    prz_min: Optional[float] = None  # For ABCD patterns (deprecated - use prz_zones)
    prz_max: Optional[float] = None  # For ABCD patterns (deprecated - use prz_zones)
    prz_zones: List[Dict] = field(default_factory=list)  # Only THIS instance's PRZ for entry checking
    all_prz_zones: List[Dict] = field(default_factory=list)  # ALL PRZ zones for display purposes
    d_lines: List[float] = field(default_factory=list)  # For XABCD patterns
    projected_d_time: int = 0  # Estimated time for D

    # Pattern timestamps for time tracking
    a_timestamp: Optional[datetime] = None
    b_timestamp: Optional[datetime] = None
    c_timestamp: Optional[datetime] = None
    detection_timestamp: Optional[datetime] = None

    # Completion tracking
    status: str = 'pending'  # pending, success, invalid_prz, failed_prz, dismissed
    zone_reached: bool = False
    zone_entry_bar: Optional[int] = None
    zone_entry_price: Optional[float] = None
    zone_entry_timestamp: Optional[datetime] = None
    zone_exit_bar: Optional[int] = None  # For tracking zone violation
    zone_exit_price: Optional[float] = None
    reversal_confirmed: bool = False  # Track if price reversed after zone entry
    reversal_bar: Optional[int] = None
    reversal_price: Optional[float] = None

    # Invalid/Failed PRZ tracking
    invalid_bar: Optional[int] = None  # Bar number when pattern became invalid
    failed_bar: Optional[int] = None  # Bar number when invalid pattern became failed
    candles_to_failure: Optional[int] = None  # Bars between invalid and failed

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

    # Zone entry tracking
    zone_entries: List[str] = field(default_factory=list)  # List of ZoneEntry IDs


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

        # Zone entry tracking for accurate success rate calculation
        self.zone_entries: Dict[str, ZoneEntry] = {}  # All zone entries
        self.zone_entry_stats: Dict[str, Dict] = {}  # Stats by pattern type

    def generate_pattern_id(self, pattern: Dict) -> str:
        """
        Generate a unique ID for a pattern based on its key points AND pattern name.

        Uses the pattern's structural points (X, A, B, C) INDICES plus the pattern name
        to ensure different pattern definitions with the same structure get unique IDs.
        This allows tracking multiple patterns (e.g., Gartley, Butterfly) that share
        the same X, A, B, C points but have different D projections and PRZ zones.

        Args:
            pattern: Pattern dictionary with A, B, C points (and X for XABCD)

        Returns:
            Unique pattern ID string
        """
        # Create a string representation of the key points
        pattern_type = pattern.get('pattern_type', 'UNK')
        pattern_name = pattern.get('name', 'unknown')

        # Normalize pattern name: strip "_unformed" suffix for matching
        # This ensures unformed and formed versions of the same pattern get the same ID
        # Example: "Gartley1_bull_unformed" -> "Gartley1_bull"
        normalized_name = pattern_name.replace('_unformed', '')

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

        # Create key string from indices AND normalized pattern name
        # This ensures different patterns with same structure get unique IDs
        # Uses normalized_name (without "_unformed") so unformed and formed versions match
        key_string = f"{normalized_name}_{'_'.join(point_indices)}" if point_indices else f"unknown_{id(pattern)}"

        # Generate hash for unique ID based on pattern name + point indices
        pattern_hash = hashlib.md5(str(key_string).encode()).hexdigest()[:16]

        # Use pattern type prefix
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
        If pattern has multiple PRZ zones, creates separate TrackedPattern instance for each.

        Args:
            pattern: Unformed pattern dictionary
            current_bar: Current bar number in backtest
            current_timestamp: Current timestamp

        Returns:
            Base pattern ID (without prz_instance suffix)
        """
        self.current_bar = current_bar
        base_pattern_id = self.generate_pattern_id(pattern)

        # Note: We don't check for duplicates here anymore because we create
        # separate instances for each PRZ zone

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
                    # For XABCD, keep d_lines as-is, don't convert to PRZ zones
                    # d_lines will be used directly for entry detection

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

        # Extract timestamps from points if available
        a_timestamp = None
        b_timestamp = None
        c_timestamp = None

        if 'points' in pattern:
            points = pattern['points']
            # Try to get timestamps from the point data
            if 'A' in points and isinstance(points['A'], dict) and 'time' in points['A']:
                a_timestamp = points['A']['time']
            if 'B' in points and isinstance(points['B'], dict) and 'time' in points['B']:
                b_timestamp = points['B']['time']
            if 'C' in points and isinstance(points['C'], dict) and 'time' in points['C']:
                c_timestamp = points['C']['time']

        # XABCD patterns: Create single instance with d_lines (no PRZ splitting)
        # ABCD patterns: Create separate instance for each PRZ zone
        if pattern.get('pattern_type') == 'XABCD' and d_lines:
            # XABCD: Single instance with d_lines only
            pattern_id_with_prz = f"{base_pattern_id}_prz_1"

            # Check if already tracking
            if pattern_id_with_prz not in self.tracked_patterns:
                tracked = TrackedPattern(
                    pattern_id=pattern_id_with_prz,
                    pattern_type='XABCD',
                    subtype=clean_name,
                    first_seen_bar=current_bar,
                    prz_instance='prz_1',
                    x_point=x_point,
                    a_point=a_point,
                    b_point=b_point,
                    c_point=c_point,
                    a_timestamp=a_timestamp,
                    b_timestamp=b_timestamp,
                    c_timestamp=c_timestamp,
                    prz_min=None,  # XABCD doesn't use PRZ zones
                    prz_max=None,
                    prz_zones=[],  # Empty for XABCD
                    all_prz_zones=[],  # Empty for XABCD
                    d_lines=d_lines,  # All d_lines for XABCD
                    projected_d_time=projected_d_time,
                    detection_timestamp=current_timestamp,
                    status='pending'
                )

                self.tracked_patterns[pattern_id_with_prz] = tracked

                # Update stats
                pattern_key = f"XABCD_{clean_name}"
                if pattern_key not in self.pattern_type_stats:
                    self.pattern_type_stats[pattern_key] = {
                        'total_detected': 0,
                        'success': 0,
                        'invalid_prz': 0,
                        'failed_prz': 0,
                        'dismissed': 0,
                        'completed': 0,
                        'completion_rate': 0.0,
                        'success_rate': 0.0,
                        'avg_accuracy': 0.0,
                        'avg_bars_to_complete': 0.0,
                        'accuracies': [],
                        'completion_times': [],
                        'pattern_transformations': {}
                    }
                self.pattern_type_stats[pattern_key]['total_detected'] += 1
        else:
            # ABCD: Split into multiple PRZ instances
            prz_zones_to_track = prz_zones if prz_zones else [{'min': prz_min, 'max': prz_max, 'pattern_source': 'default'}]

            # Create one TrackedPattern instance per PRZ zone
            for prz_idx, single_prz_zone in enumerate(prz_zones_to_track, start=1):
                prz_instance_name = f"prz_{prz_idx}"
                pattern_id_with_prz = f"{base_pattern_id}_{prz_instance_name}"

                # Check if already tracking this specific PRZ instance
                if pattern_id_with_prz in self.tracked_patterns:
                    continue

                # Extract PRZ min/max for this specific zone
                if isinstance(single_prz_zone, dict):
                    zone_min = single_prz_zone.get('min', prz_min)
                    zone_max = single_prz_zone.get('max', prz_max)
                else:
                    zone_min = prz_min
                    zone_max = prz_max

                tracked = TrackedPattern(
                    pattern_id=pattern_id_with_prz,
                    pattern_type=pattern.get('pattern_type', 'Unknown'),
                    subtype=clean_name,
                    first_seen_bar=current_bar,
                    prz_instance=prz_instance_name,
                    x_point=x_point,
                    a_point=a_point,
                    b_point=b_point,
                    c_point=c_point,
                    a_timestamp=a_timestamp,
                    b_timestamp=b_timestamp,
                    c_timestamp=c_timestamp,
                    prz_min=zone_min,
                    prz_max=zone_max,
                    prz_zones=[single_prz_zone],
                    all_prz_zones=prz_zones_to_track,
                    d_lines=[],  # Empty for ABCD
                    projected_d_time=projected_d_time,
                    detection_timestamp=current_timestamp,
                    status='pending'
                )

                self.tracked_patterns[pattern_id_with_prz] = tracked

                # Update pattern type statistics
                pattern_key = f"{tracked.pattern_type}_{tracked.subtype}"
                if pattern_key not in self.pattern_type_stats:
                    self.pattern_type_stats[pattern_key] = {
                        'total_detected': 0,
                        'success': 0,
                        'invalid_prz': 0,
                        'failed_prz': 0,
                        'dismissed': 0,
                        'completed': 0,
                        'completion_rate': 0.0,
                        'success_rate': 0.0,
                        'avg_accuracy': 0.0,
                        'avg_bars_to_complete': 0.0,
                        'accuracies': [],
                        'completion_times': [],
                        'pattern_transformations': {}
                    }

                self.pattern_type_stats[pattern_key]['total_detected'] += 1

        return base_pattern_id

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
        Also dismisses pending XABCD patterns if price crosses their D-lines.
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
            # Debug output removed for cleaner console

        # First pass: Check if any pending XABCD patterns should be dismissed due to empty d_lines
        for pattern_id, tracked in list(self.tracked_patterns.items()):
            if tracked.status == 'pending' and tracked.pattern_type == 'XABCD':
                # Dismiss if d_lines is empty or None (pattern was invalidated)
                if not hasattr(tracked, 'd_lines') or not tracked.d_lines:
                    tracked.status = 'dismissed'
                    tracked.completion_details['dismissal_reason'] = 'No valid D-lines (invalidated after detection)'
                    tracked.completion_details['dismissal_bar'] = current_bar

                    # Update statistics
                    pattern_key = f"{tracked.pattern_type}_{tracked.subtype}"
                    if pattern_key in self.pattern_type_stats:
                        self.pattern_type_stats[pattern_key]['dismissed'] = \
                            self.pattern_type_stats[pattern_key].get('dismissed', 0) + 1

        # Second pass: Check zone entry for pending and in_zone patterns
        for pattern_id, tracked in self.tracked_patterns.items():
            # Skip if pattern already concluded (success/failed/dismissed)
            if tracked.status not in ['pending', 'in_zone']:
                continue

            # Check if price enters any of the pattern's D zones
            zones_to_check = []

            if tracked.pattern_type == 'ABCD':
                # Check each PRZ zone separately if available
                if tracked.prz_zones:
                    for zone in tracked.prz_zones:
                        zone_min = float(zone.get('min', 0))
                        zone_max = float(zone.get('max', 0))
                        if zone_min and zone_max:
                            if price_low <= zone_max and price_high >= zone_min:
                                # DEBUG: Print entry detection details
                                bar_open = data_for_detection.iloc[current_bar]['Open'] if data_for_detection is not None and current_bar < len(data_for_detection) else 0
                                bar_close = data_for_detection.iloc[current_bar]['Close'] if data_for_detection is not None and current_bar < len(data_for_detection) else 0

                                print(f"\n[ENTRY DETECTION] Pattern {tracked.pattern_id} at bar {current_bar}")
                                print(f"  Bar OHLC: O={bar_open:.2f} H={price_high:.2f} L={price_low:.2f} C={bar_close:.2f}")
                                print(f"  PRZ Range: {zone_min:.2f} - {zone_max:.2f}")
                                print(f"  Condition: price_low({price_low:.2f}) <= zone_max({zone_max:.2f}) AND price_high({price_high:.2f}) >= zone_min({zone_min:.2f})")

                                # Calculate entry price for this zone
                                if price_low >= zone_min and price_low <= zone_max:
                                    entry_price = price_low
                                    print(f"  Entry Price = Low: {entry_price:.2f} (low is within PRZ)")
                                elif price_high >= zone_min and price_high <= zone_max:
                                    entry_price = price_high
                                    print(f"  Entry Price = High: {entry_price:.2f} (high is within PRZ)")
                                else:
                                    entry_price = (zone_min + zone_max) / 2
                                    print(f"  Entry Price = Midpoint: {entry_price:.2f} (bar crosses entire PRZ)")

                                zones_to_check.append({
                                    'zone_min': zone_min,
                                    'zone_max': zone_max,
                                    'entry_price': entry_price,
                                    'pattern_source': zone.get('pattern_source', 'unknown')
                                })
                    # Process all entered zones (removed break to allow multiple entries)
                # Fallback to old method if no zones
                elif tracked.prz_min is not None and tracked.prz_max is not None:
                    if price_low <= tracked.prz_max and price_high >= tracked.prz_min:
                        # Record the price that entered the zone
                        if price_low >= tracked.prz_min and price_low <= tracked.prz_max:
                            entry_price = price_low
                        elif price_high >= tracked.prz_min and price_high <= tracked.prz_max:
                            entry_price = price_high
                        else:
                            entry_price = (tracked.prz_min + tracked.prz_max) / 2

                        zones_to_check.append({
                            'zone_min': tracked.prz_min,
                            'zone_max': tracked.prz_max,
                            'entry_price': entry_price,
                            'pattern_source': 'legacy_prz'
                        })

            elif tracked.pattern_type == 'XABCD' and tracked.d_lines:
                # Check each d_line individually for XABCD patterns
                # Convert to regular floats to avoid numpy comparison issues
                d_values = [float(d) for d in tracked.d_lines]

                for i, d_line in enumerate(d_values, 1):
                    if price_low <= d_line <= price_high:
                        # Price touched this d_line
                        zones_to_check.append({
                            'zone_min': d_line,
                            'zone_max': d_line,
                            'entry_price': d_line,
                            'pattern_source': f'xabcd_d_line_{i}'
                        })

            # Process all zone entries found
            for zone_info in zones_to_check:
                zone_min = zone_info['zone_min']
                zone_max = zone_info['zone_max']
                entry_price = zone_info['entry_price']
                pattern_source = zone_info['pattern_source']

                # Create unique entry ID including pattern source to allow multiple zone entries
                entry_id = f"{pattern_id}_{pattern_source}_{current_bar}_{entry_price:.2f}"

                # Skip if this exact zone entry already exists (avoid duplicates on same bar)
                if entry_id in self.zone_entries:
                    continue

                # Create a zone entry record for accurate success rate tracking
                is_bullish = tracked.a_point[1] > tracked.b_point[1]

                # Record this zone entry
                zone_entry = ZoneEntry(
                    entry_id=entry_id,
                    pattern_id=pattern_id,
                    zone_level=(zone_min + zone_max) / 2,
                    zone_min=zone_min,
                    zone_max=zone_max,
                    entry_bar=current_bar,
                    entry_price=entry_price,
                    entry_timestamp=current_timestamp,
                    pattern_type=tracked.pattern_type,
                    pattern_subtype=tracked.subtype,
                    is_bullish=is_bullish
                )

                self.zone_entries[entry_id] = zone_entry
                tracked.zone_entries.append(entry_id)

                # Store which specific zone was entered (for the last zone entered)
                tracked.completion_details['entered_zone'] = pattern_source

                # Update pattern status only on FIRST zone entry (when status is 'pending')
                if tracked.status == 'pending':
                    # Proceed with zone entry logic for first entry
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

                    # Also write to file for debugging
                    with open('pattern_debug.log', 'a') as f:
                        f.write(f"Pattern {pattern_id[:30]}... entered zone {pattern_source} at price {entry_price:.2f}, status: in_zone\n")
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
                else:
                    # Pattern already in_zone - this is a subsequent zone entry
                    # Just record the zone entry, don't update pattern status
                    with open('pattern_debug.log', 'a') as f:
                        f.write(f"Pattern {pattern_id[:30]}... entered additional zone {pattern_source} at price {entry_price:.2f} (already in_zone)\n")

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

        # Extract indices and prices from points FIRST
        a_point = points.get('A')
        b_point = points.get('B')
        c_point = points.get('C')

        if not a_point or not b_point or not c_point:
            return None

        a_idx = a_point[0] if isinstance(a_point, (list, tuple)) and len(a_point) > 0 else a_point.get('index', 0) if isinstance(a_point, dict) else 0
        b_idx = b_point[0] if isinstance(b_point, (list, tuple)) and len(b_point) > 0 else b_point.get('index', 0) if isinstance(b_point, dict) else 0
        c_idx = c_point[0] if isinstance(c_point, (list, tuple)) and len(c_point) > 0 else c_point.get('index', 0) if isinstance(c_point, dict) else 0

        a_price = a_point[1] if isinstance(a_point, (list, tuple)) and len(a_point) > 1 else a_point.get('price', 0) if isinstance(a_point, dict) else 0
        b_price = b_point[1] if isinstance(b_point, (list, tuple)) and len(b_point) > 1 else b_point.get('price', 0) if isinstance(b_point, dict) else 0
        c_price = c_point[1] if isinstance(c_point, (list, tuple)) and len(c_point) > 1 else c_point.get('price', 0) if isinstance(c_point, dict) else 0

        x_idx = None
        x_price = None
        if 'X' in points and pattern_type == 'XABCD':
            x_point = points['X']
            x_idx = x_point[0] if isinstance(x_point, (list, tuple)) and len(x_point) > 0 else x_point.get('index', 0) if isinstance(x_point, dict) else 0
            x_price = x_point[1] if isinstance(x_point, (list, tuple)) and len(x_point) > 1 else x_point.get('price', 0) if isinstance(x_point, dict) else 0

        # Determine pattern direction AFTER extracting prices
        if pattern_type == 'ABCD':
            is_bullish = a_price > b_price  # A > B for bullish
        else:  # XABCD
            if x_price is None:
                return None
            is_bullish = a_price > x_price  # A > X for bullish

        tracked = TrackedPattern(
            pattern_id=pattern_id,
            pattern_type=pattern_type,
            subtype=subtype,
            a_point=(a_idx, a_price),
            b_point=(b_idx, b_price),
            c_point=(c_idx, c_price),
            x_point=(x_idx, x_price) if x_idx is not None else None,
            first_seen_bar=current_bar,
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
            tracked.status = 'invalid_prz'  # Combining failed with invalid_prz
            tracked.completion_details = {'invalid_reason': 'Price continued past D without reversal'}
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
                'invalid_prz': 0,
                'failed_prz': 0,
                'inconclusive': 0
            }

        self.pattern_type_stats[pattern_key]['total'] += 1
        if success:
            self.pattern_type_stats[pattern_key]['success'] += 1
        elif failure:
            self.pattern_type_stats[pattern_key]['invalid_prz'] += 1
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

            # Get B point price (critical structure level)
            b_price = tracked.b_point[1]

            # Check for TRUE structure break
            should_dismiss = False
            reason = ""

            # Determine if pattern is bullish or bearish based on points
            # Bullish: A (high) > B (low), Bearish: A (low) < B (high)
            is_bullish = tracked.a_point[1] > tracked.b_point[1]  # A higher than B

            if is_bullish:
                # For bullish patterns (B is low), dismiss if price breaks below B
                # C can be updated to new highs - this is normal pattern behavior
                if price_low < b_price:  # Structure break below B
                    should_dismiss = True
                    reason = "Structure broken - price below B"
            else:
                # For bearish patterns (B is high), dismiss if price breaks above B
                # C can be updated to new lows - this is normal pattern behavior
                if price_high > b_price:  # Structure break above B
                    should_dismiss = True
                    reason = "Structure broken - price above B"

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

    def _recalculate_prz(self, tracked: 'TrackedPattern') -> bool:
        """
        Recalculate PRZ (d_lines) for a pattern with updated C point.

        Args:
            tracked: The tracked pattern to recalculate

        Returns:
            True if recalculation successful, False otherwise
        """
        try:
            from pattern_ratios_2_Final import XABCD_PATTERN_RATIOS, ABCD_PATTERN_RATIOS

            # Get pattern ratios from tracked pattern
            pattern_ratios = tracked.ratios if hasattr(tracked, 'ratios') and tracked.ratios else {}
            matching_patterns = pattern_ratios.get('matching_patterns', [])

            if not matching_patterns:
                return False

            # Get first matching pattern name
            first_pattern_name = matching_patterns[0]

            # Get prices
            x_price = tracked.x_point[1] if tracked.x_point else None
            a_price = tracked.a_point[1]
            b_price = tracked.b_point[1]
            c_price = tracked.c_point[1]  # Updated C price

            is_bullish = a_price > b_price

            if tracked.pattern_type == 'XABCD' and x_price is not None:
                # Get pattern definition
                pattern_def = XABCD_PATTERN_RATIOS.get(first_pattern_name)
                if not pattern_def:
                    return False

                # Calculate moves
                xa_move = abs(a_price - x_price)
                bc_move = abs(c_price - b_price)  # Uses NEW C price

                if xa_move == 0 or bc_move == 0:
                    return False

                # Get AD and CD ranges
                ad_min, ad_max = pattern_def.get('ad_xa', [0, 0])
                cd_min, cd_max = pattern_def.get('cd_bc', [0, 0])

                if ad_min == 0 and ad_max == 0:
                    return False

                # Calculate d_lines using same logic as unformed_xabcd.py
                d_lines = []
                ad_avg = (ad_min + ad_max) / 2
                cd_avg = (cd_min + cd_max) / 2

                # Method 1: Fix AD ratios
                for ad_ratio in [ad_avg, ad_max, ad_min]:
                    projected_ad = xa_move * (ad_ratio / 100)
                    d_from_ad = a_price - projected_ad if is_bullish else a_price + projected_ad

                    cd_move_implied = abs(d_from_ad - c_price)
                    if bc_move > 0:
                        cd_ratio_implied = (cd_move_implied / bc_move) * 100
                        cd_ratio_clamped = max(cd_min, min(cd_max, cd_ratio_implied))
                        projected_cd_clamped = bc_move * (cd_ratio_clamped / 100)
                        d_final = c_price - projected_cd_clamped if is_bullish else c_price + projected_cd_clamped
                    else:
                        d_final = d_from_ad
                    d_lines.append(d_final)

                # Method 2: Fix CD ratios
                for cd_ratio in [cd_avg, cd_max, cd_min]:
                    projected_cd = bc_move * (cd_ratio / 100)
                    d_from_cd = c_price - projected_cd if is_bullish else c_price + projected_cd

                    ad_move_implied = abs(a_price - d_from_cd)
                    if xa_move > 0:
                        ad_ratio_implied = (ad_move_implied / xa_move) * 100
                        ad_ratio_clamped = max(ad_min, min(ad_max, ad_ratio_implied))
                        projected_ad_clamped = xa_move * (ad_ratio_clamped / 100)
                        d_final = a_price - projected_ad_clamped if is_bullish else a_price + projected_ad_clamped
                    else:
                        d_final = d_from_cd
                    d_lines.append(d_final)

                # Remove duplicates
                unique_d_lines = []
                for d_price in d_lines:
                    is_duplicate = any(abs(d_price - existing) < 0.1 for existing in unique_d_lines)
                    if not is_duplicate:
                        unique_d_lines.append(d_price)

                # CRITICAL: Validate d_lines against candlestick crossing
                # Same validation as initial detection in unformed_xabcd.py
                if unique_d_lines and hasattr(self, 'current_data') and self.current_data is not None:
                    c_bar = tracked.c_point[0]  # C point bar index

                    # Validate using same logic as unformed_xabcd.py
                    valid_d_lines = self._validate_d_lines_crossing(
                        self.current_data, c_bar, unique_d_lines
                    )

                    if not valid_d_lines:
                        # All d_lines cross candlesticks - pattern is invalid
                        # Return False to signal that recalculation failed
                        return False

                    # Use only valid d_lines
                    unique_d_lines = valid_d_lines

                # Update tracked pattern with validated d_lines
                tracked.d_lines = unique_d_lines

            elif tracked.pattern_type == 'ABCD':
                # Get pattern definition
                pattern_def = ABCD_PATTERN_RATIOS.get(first_pattern_name)
                if not pattern_def:
                    return False

                # Calculate BC move with new C
                ab_move = abs(b_price - a_price)
                bc_move = abs(c_price - b_price)  # Uses NEW C price

                if ab_move == 0 or bc_move == 0:
                    return False

                # Get projection range
                proj_min, proj_max = pattern_def.get('proj', [0, 0])
                if proj_min == 0 and proj_max == 0:
                    return False

                # Recalculate PRZ zone
                if is_bullish:
                    prz_min_new = c_price - (bc_move * proj_max / 100)
                    prz_max_new = c_price - (bc_move * proj_min / 100)
                else:
                    prz_min_new = c_price + (bc_move * proj_min / 100)
                    prz_max_new = c_price + (bc_move * proj_max / 100)

                # Update PRZ zones
                if tracked.prz_zones:
                    for zone in tracked.prz_zones:
                        zone['min'] = prz_min_new
                        zone['max'] = prz_max_new
                else:
                    tracked.prz_zones = [{
                        'min': prz_min_new,
                        'max': prz_max_new,
                        'proj_min': proj_min,
                        'proj_max': proj_max
                    }]

            return True

        except Exception as e:
            import logging
            logging.error(f"Error recalculating PRZ: {e}")
            return False

    def _validate_d_lines_crossing(self, df: pd.DataFrame, c_idx: int, d_lines: List[float]) -> List[float]:
        """
        Validate that horizontal D projection lines don't cross any candlesticks after point C.
        Same logic as validate_d_lines_no_candlestick_crossing() in unformed_xabcd.py

        Args:
            df: DataFrame with OHLC data
            c_idx: Index of point C in the DataFrame
            d_lines: List of projected D price levels

        Returns:
            List of valid D lines that don't cross candlesticks
        """
        if not d_lines or c_idx >= len(df) - 1:
            return d_lines

        try:
            import numpy as np

            MAX_FUTURE_CANDLES = 100  # Same as unformed_xabcd.py

            high_col = 'High' if 'High' in df.columns else 'high'
            low_col = 'Low' if 'Low' in df.columns else 'low'

            # Get candles after point C (limited to MAX_FUTURE_CANDLES)
            end_idx = min(c_idx + 1 + MAX_FUTURE_CANDLES, len(df))
            candles_after_c = df.iloc[c_idx + 1:end_idx]

            # Extract arrays for vectorized operations
            highs = candles_after_c[high_col].values
            lows = candles_after_c[low_col].values

            valid_d_lines = []

            for d_price in d_lines:
                # Vectorized check if d_price crosses any candlestick
                crosses_candle = np.any((lows <= d_price) & (d_price <= highs))

                if not crosses_candle:
                    valid_d_lines.append(d_price)

            return valid_d_lines

        except (KeyError, IndexError, TypeError) as e:
            import logging
            logging.error(f"D line validation failed in pattern tracking: {e}")
            # Return empty list on error - no D lines are valid if validation fails
            return []

    def update_c_points(self, extremum_points: List[Tuple], current_bar: int) -> List[str]:
        """
        Update C points for pending patterns when a new extremum exceeds the current C.

        Args:
            extremum_points: List of extremum points (timestamp, price, is_high, bar_index)
            current_bar: Current bar index

        Returns:
            List of updated pattern IDs
        """
        updated_patterns = []

        # Performance optimization: pre-filter extremums by bar index
        # Only consider extremums that are recent enough to potentially update any pattern
        # c_point is (bar_index, price) so use [0] for bar index
        min_c_bar = min((tracked.c_point[0] for tracked in self.tracked_patterns.values()
                        if tracked.status == 'pending' and not tracked.zone_reached),
                       default=current_bar)

        # Filter extremums to only those after the earliest C point
        recent_extremums = [ext for ext in extremum_points if len(ext) == 4 and ext[3] > min_c_bar]

        if not recent_extremums:
            # No new extremums to check
            return updated_patterns

        for pattern_id, tracked in list(self.tracked_patterns.items()):
            # Only update pending patterns (not yet in zone)
            if tracked.status != 'pending' or tracked.zone_reached:
                continue

            # Get current C point - it's a 2-tuple (bar_index, price)
            c_idx, c_price = tracked.c_point

            # Determine if pattern is bullish or bearish
            # Bullish: A (high) > B (low), Bearish: A (low) < B (high)
            is_bullish = tracked.a_point[1] > tracked.b_point[1]

            # Find newer extremums that could update C (using pre-filtered list)
            for ext in recent_extremums:
                ext_idx, ext_price, is_high, ext_bar = ext

                # Only consider extremums after current C
                if ext_bar <= c_idx:
                    continue

                # Check if this extremum should become the new C
                should_update = False

                if is_bullish:
                    # For bullish patterns, C is a high - update if new extremum is higher
                    if is_high and ext_price > c_price:
                        should_update = True
                else:
                    # For bearish patterns, C is a low - update if new extremum is lower
                    if not is_high and ext_price < c_price:
                        should_update = True

                if should_update:
                    # Validate structure before updating C
                    b_price = tracked.b_point[1]

                    # Check that new C maintains valid structure relative to B
                    structure_valid = False
                    if is_bullish:
                        # For bullish: new C (high) must be > B (low)
                        if ext_price > b_price:
                            structure_valid = True
                    else:
                        # For bearish: new C (low) must be < B (high)
                        if ext_price < b_price:
                            structure_valid = True

                    if not structure_valid:
                        # New C would violate structure, skip this update
                        continue

                    # Check BC/AB ratio still produces valid harmonic patterns
                    # If new C creates invalid ratios, skip update
                    a_price = tracked.a_point[1]
                    ab_move = abs(b_price - a_price)
                    new_bc_move = abs(ext_price - b_price)

                    if ab_move > 0:
                        new_bc_ab_ratio = (new_bc_move / ab_move) * 100
                        # BC/AB ratio should be reasonable (10% to 500% typical for harmonic patterns)
                        if new_bc_ab_ratio < 10 or new_bc_ab_ratio > 500:
                            # New C creates extreme ratio, skip update
                            continue

                    # Structure is valid, proceed with update
                    # c_point is (bar_index, price) - use ext_bar as bar_index
                    tracked.c_point = (ext_bar, ext_price)

                    # Recalculate PRZ with new C
                    prz_recalculated = self._recalculate_prz(tracked)

                    if not prz_recalculated:
                        # PRZ recalculation failed - all d_lines cross candlesticks
                        # Dismiss this pattern
                        tracked.status = 'dismissed'
                        tracked.completion_details['dismissal_reason'] = 'All D-lines cross candlesticks after C update'
                        tracked.completion_details['dismissal_bar'] = current_bar

                        # Update statistics
                        pattern_key = f"{tracked.pattern_type}_{tracked.subtype}"
                        if pattern_key in self.pattern_type_stats:
                            self.pattern_type_stats[pattern_key]['dismissed'] = \
                                self.pattern_type_stats[pattern_key].get('dismissed', 0) + 1

                        # Skip adding to updated_patterns since it's now dismissed
                        continue

                    # Mark that C was updated
                    tracked.completion_details['c_updated'] = True
                    tracked.completion_details['c_update_bar'] = current_bar
                    tracked.completion_details['prz_recalculated'] = prz_recalculated

                    updated_patterns.append(pattern_id)

                    # Update to the latest valid C (not multiple updates per pattern)
                    c_price = ext_price
                    c_idx = ext_bar

        return updated_patterns

    def check_zone_violation(self, price_high: float, price_low: float, current_bar: int) -> List[str]:
        """
        Check if any patterns that entered their zone have now violated it (invalid PRZ).

        Args:
            price_high: Current bar high
            price_low: Current bar low
            current_bar: Current bar index

        Returns:
            List of invalid PRZ pattern IDs
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

                # Get PRZ boundaries based on pattern type
                if tracked.pattern_type == 'XABCD' and tracked.d_lines:
                    # For XABCD patterns, use d_lines range
                    prz_min = min(tracked.d_lines)
                    prz_max = max(tracked.d_lines)
                else:
                    # For ABCD patterns, use prz_min/prz_max
                    prz_min = tracked.prz_min
                    prz_max = tracked.prz_max

                # Skip if PRZ boundaries not set
                if prz_min is None or prz_max is None:
                    continue

                if is_bullish:
                    # Bullish pattern: price falls TO the PRZ, then should reverse UP
                    # Success: price rises and exits above the PRZ (reversal upward)
                    if price_high > prz_max:
                        reversal_confirmed = True
                    # Failure: price breaks below the PRZ (violation)
                    elif price_low < prz_min:
                        zone_violated = True
                else:
                    # Bearish pattern: price rises TO the PRZ, then should reverse DOWN
                    # Success: price falls and exits below the PRZ (reversal downward)
                    if price_low < prz_min:
                        reversal_confirmed = True
                    # Failure: price breaks above the PRZ (violation)
                    elif price_high > prz_max:
                        zone_violated = True

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
                # CHECK FOR INVALID PRZ: Single candle crosses entire PRZ zone
                # For bullish: candle low below PRZ AND candle high above PRZ (crosses completely through)
                # For bearish: candle low below PRZ AND candle high above PRZ (crosses completely through)
                just_entered_this_bar = (tracked.zone_entry_bar == current_bar)

                # Get PRZ boundaries for this pattern
                if tracked.prz_zones and tracked.completion_details.get('entered_zone'):
                    for zone in tracked.prz_zones:
                        if zone.get('pattern_source') == tracked.completion_details['entered_zone']:
                            prz_min_check = float(zone.get('min', 0))
                            prz_max_check = float(zone.get('max', 0))
                            break
                    else:
                        prz_min_check = tracked.prz_min
                        prz_max_check = tracked.prz_max
                elif tracked.prz_min and tracked.prz_max:
                    prz_min_check = tracked.prz_min
                    prz_max_check = tracked.prz_max
                elif tracked.pattern_type == 'XABCD' and tracked.d_lines:
                    prz_min_check = min(tracked.d_lines)
                    prz_max_check = max(tracked.d_lines)
                else:
                    prz_min_check = None
                    prz_max_check = None

                # Check if single candle completely crossed the PRZ
                candle_crosses_entire_prz = False
                if prz_min_check and prz_max_check and just_entered_this_bar:
                    # Single candle crosses entire zone if its range contains the entire PRZ
                    candle_crosses_entire_prz = (price_low < prz_min_check and price_high > prz_max_check)

                if candle_crosses_entire_prz:
                    # Invalid PRZ - price crossed entire zone (keep tracking for potential failed_prz)
                    tracked.status = 'invalid_prz'
                    tracked.invalid_bar = current_bar  # Store when it became invalid
                    tracked.completion_details['invalid_reason'] = 'Price crossed PRZ completely'
                    tracked.completion_details['invalid_bar'] = current_bar
                    failed_patterns.append(pattern_id)  # Track as invalid for statistics

                    # Update zone entries
                    for entry_id in tracked.zone_entries:
                        if entry_id in self.zone_entries and self.zone_entries[entry_id].status == 'active':
                            self.zone_entries[entry_id].status = 'invalid_prz'
                            self.zone_entries[entry_id].exit_bar = current_bar
                            self.zone_entries[entry_id].exit_price = price_high if is_bullish else price_low

                    # Update statistics
                    pattern_key = f"{tracked.pattern_type}_{tracked.subtype}"
                    if pattern_key in self.pattern_type_stats:
                        self.pattern_type_stats[pattern_key]['invalid_prz'] = \
                            self.pattern_type_stats[pattern_key].get('invalid_prz', 0) + 1
                        self.pattern_type_stats[pattern_key]['in_zone'] = max(0,
                            self.pattern_type_stats[pattern_key].get('in_zone', 0) - 1)

                    # Continue tracking this pattern - don't dismiss it yet!

                elif reversal_confirmed:
                    # Pattern succeeded - price left PRZ in expected direction
                    tracked.status = 'success'
                    tracked.reversal_confirmed = True
                    tracked.reversal_bar = current_bar
                    # For bullish, reversal price is when it went above PRZ max
                    # For bearish, reversal price is when it went below PRZ min
                    tracked.reversal_price = price_high if is_bullish else price_low
                    successful_patterns.append(pattern_id)

                    # Update zone entries for this pattern
                    for entry_id in tracked.zone_entries:
                        if entry_id in self.zone_entries and self.zone_entries[entry_id].status == 'active':
                            self.zone_entries[entry_id].status = 'success'
                            self.zone_entries[entry_id].reversal_confirmed = True
                            self.zone_entries[entry_id].reversal_bar = current_bar
                            self.zone_entries[entry_id].reversal_price = tracked.reversal_price
                            self.zone_entries[entry_id].exit_bar = current_bar
                            self.zone_entries[entry_id].exit_price = tracked.reversal_price

                    # Update statistics
                    pattern_key = f"{tracked.pattern_type}_{tracked.subtype}"
                    if pattern_key in self.pattern_type_stats:
                        self.pattern_type_stats[pattern_key]['success'] = \
                            self.pattern_type_stats[pattern_key].get('success', 0) + 1
                        self.pattern_type_stats[pattern_key]['in_zone'] = max(0,
                            self.pattern_type_stats[pattern_key].get('in_zone', 0) - 1)

                        # Recalculate success rate based on zone entries
                        self._update_zone_entry_stats(pattern_key)

                elif zone_violated:
                    # Pattern invalid - price violated PRZ boundaries (keep tracking for potential failed_prz)
                    tracked.status = 'invalid_prz'
                    tracked.invalid_bar = current_bar  # Store when it became invalid
                    tracked.zone_exit_bar = current_bar
                    tracked.zone_exit_price = price_low if is_bullish else price_high
                    tracked.completion_details['invalid_reason'] = "PRZ violated without reversal"
                    failed_patterns.append(pattern_id)

                    # Update zone entries for this pattern
                    for entry_id in tracked.zone_entries:
                        if entry_id in self.zone_entries and self.zone_entries[entry_id].status == 'active':
                            self.zone_entries[entry_id].status = 'invalid_prz'
                            self.zone_entries[entry_id].exit_bar = current_bar
                            self.zone_entries[entry_id].exit_price = tracked.zone_exit_price

                    # Update statistics
                    pattern_key = f"{tracked.pattern_type}_{tracked.subtype}"
                    if pattern_key in self.pattern_type_stats:
                        self.pattern_type_stats[pattern_key]['invalid_prz'] = \
                            self.pattern_type_stats[pattern_key].get('invalid_prz', 0) + 1
                        self.pattern_type_stats[pattern_key]['in_zone'] = max(0,
                            self.pattern_type_stats[pattern_key].get('in_zone', 0) - 1)

                        # Recalculate success rate based on zone entries
                        self._update_zone_entry_stats(pattern_key)

                    # Continue tracking this pattern - don't dismiss it yet!
                # else: Pattern stays in_zone - neither success nor failure yet

            # Once a pattern is successful, it stays successful - no stop-loss logic
            # Only patterns that are in_zone can transition to success or invalid/failed

            # Check if invalid_prz patterns cross back to become failed_prz
            elif tracked.status == 'invalid_prz':
                # Get PRZ boundaries
                if tracked.pattern_type == 'XABCD' and tracked.d_lines:
                    prz_min = min(tracked.d_lines)
                    prz_max = max(tracked.d_lines)
                else:
                    prz_min = tracked.prz_min
                    prz_max = tracked.prz_max

                if prz_min is None or prz_max is None:
                    continue

                # Check if price crossed back from the other side
                # Pattern is invalid if it crossed through PRZ
                # It becomes failed_prz if it crosses back through PRZ from the opposite direction

                # Determine which side price initially crossed to (from zone_exit_price or current position)
                if is_bullish:
                    # Bullish: price initially went below PRZ (zone_exit_price < prz_min)
                    # Failed if price now goes above PRZ
                    if price_high > prz_max:
                        tracked.status = 'failed_prz'
                        tracked.failed_bar = current_bar
                        tracked.candles_to_failure = current_bar - tracked.invalid_bar if tracked.invalid_bar else 0
                        tracked.completion_details['failed_reason'] = 'Price crossed back through PRZ from other side'
                        tracked.completion_details['failed_bar'] = current_bar
                        tracked.completion_details['candles_to_failure'] = tracked.candles_to_failure

                        # Update statistics
                        pattern_key = f"{tracked.pattern_type}_{tracked.subtype}"
                        if pattern_key in self.pattern_type_stats:
                            # Move from invalid to failed
                            self.pattern_type_stats[pattern_key]['invalid_prz'] = max(0,
                                self.pattern_type_stats[pattern_key].get('invalid_prz', 0) - 1)
                            self.pattern_type_stats[pattern_key]['failed_prz'] = \
                                self.pattern_type_stats[pattern_key].get('failed_prz', 0) + 1
                else:
                    # Bearish: price initially went above PRZ (zone_exit_price > prz_max)
                    # Failed if price now goes below PRZ
                    if price_low < prz_min:
                        tracked.status = 'failed_prz'
                        tracked.failed_bar = current_bar
                        tracked.candles_to_failure = current_bar - tracked.invalid_bar if tracked.invalid_bar else 0
                        tracked.completion_details['failed_reason'] = 'Price crossed back through PRZ from other side'
                        tracked.completion_details['failed_bar'] = current_bar
                        tracked.completion_details['candles_to_failure'] = tracked.candles_to_failure

                        # Update statistics
                        pattern_key = f"{tracked.pattern_type}_{tracked.subtype}"
                        if pattern_key in self.pattern_type_stats:
                            # Move from invalid to failed
                            self.pattern_type_stats[pattern_key]['invalid_prz'] = max(0,
                                self.pattern_type_stats[pattern_key].get('invalid_prz', 0) - 1)
                            self.pattern_type_stats[pattern_key]['failed_prz'] = \
                                self.pattern_type_stats[pattern_key].get('failed_prz', 0) + 1

        # Add both successful and invalid patterns to completion history
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
        invalid_prz = sum(1 for p in self.tracked_patterns.values() if p.status == 'invalid_prz')
        failed_prz = sum(1 for p in self.tracked_patterns.values() if p.status == 'failed_prz')
        dismissed = sum(1 for p in self.tracked_patterns.values() if p.status == 'dismissed')
        pending = sum(1 for p in self.tracked_patterns.values() if p.status == 'pending')
        in_zone = sum(1 for p in self.tracked_patterns.values() if p.status == 'in_zone')
        inconclusive = sum(1 for p in self.tracked_patterns.values() if p.status == 'inconclusive')
        evaluating = sum(1 for p in self.tracked_patterns.values() if p.status == 'evaluating')

        # OLD METHOD: Calculate success rate for patterns that reached a conclusion
        concluded = success + invalid_prz + failed_prz
        old_success_rate = success / concluded if concluded > 0 else 0

        # NEW METHOD: Calculate success rate based on zone entries
        total_success_entries = sum(1 for e in self.zone_entries.values() if e.status == 'success')
        total_invalid_entries = sum(1 for e in self.zone_entries.values() if e.status == 'invalid_prz')
        total_active_entries = sum(1 for e in self.zone_entries.values() if e.status == 'active')
        total_concluded_entries = total_success_entries + total_invalid_entries

        # Zone-based success rate (the correct trading metric)
        zone_success_rate = total_success_entries / total_concluded_entries if total_concluded_entries > 0 else 0

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

        # Calculate zone activation rate
        total_projected_zones = 0
        for pattern in self.tracked_patterns.values():
            if pattern.pattern_type == 'XABCD' and pattern.d_lines:
                total_projected_zones += len(pattern.d_lines)
            elif pattern.pattern_type == 'ABCD':
                if pattern.prz_zones:
                    total_projected_zones += len(pattern.prz_zones)
                elif pattern.prz_min and pattern.prz_max:
                    total_projected_zones += 1

        zone_activation_rate = len(self.zone_entries) / total_projected_zones if total_projected_zones > 0 else 0

        return {
            'total_tracked': total_patterns,
            'success': success,
            'invalid_prz': invalid_prz,
            'failed_prz': failed_prz,
            'dismissed': dismissed,
            'pending': pending,
            'in_zone': in_zone,
            'inconclusive': inconclusive,
            'evaluating': evaluating,
            'concluded': concluded,
            'pattern_success_rate': old_success_rate,  # Old method for reference
            'zone_success_rate': zone_success_rate,  # NEW: Correct trading metric
            'total_zone_entries': len(self.zone_entries),  # NEW
            'successful_zone_entries': total_success_entries,  # NEW
            'invalid_zone_entries': total_invalid_entries,  # NEW
            'active_zone_entries': total_active_entries,  # NEW
            'zone_activation_rate': zone_activation_rate,  # NEW
            'zone_entry_stats': self.zone_entry_stats,  # NEW: Stats by pattern type
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

    def _update_zone_entry_stats(self, pattern_key: str):
        """Update zone entry statistics for a specific pattern type."""
        # Count zone entries for this pattern type
        pattern_type, subtype = pattern_key.split('_', 1) if '_' in pattern_key else (pattern_key, '')

        success_entries = 0
        failed_entries = 0
        active_entries = 0

        for entry in self.zone_entries.values():
            if entry.pattern_type == pattern_type and (not subtype or entry.pattern_subtype == subtype):
                if entry.status == 'success':
                    success_entries += 1
                elif entry.status == 'invalid_prz':
                    failed_entries += 1
                elif entry.status == 'active':
                    active_entries += 1

        # Update zone entry stats
        if pattern_key not in self.zone_entry_stats:
            self.zone_entry_stats[pattern_key] = {}

        self.zone_entry_stats[pattern_key]['success_entries'] = success_entries
        self.zone_entry_stats[pattern_key]['failed_entries'] = failed_entries
        self.zone_entry_stats[pattern_key]['active_entries'] = active_entries
        self.zone_entry_stats[pattern_key]['total_entries'] = success_entries + failed_entries + active_entries

        # Calculate zone-based success rate
        concluded_entries = success_entries + failed_entries
        if concluded_entries > 0:
            self.zone_entry_stats[pattern_key]['zone_success_rate'] = success_entries / concluded_entries
        else:
            self.zone_entry_stats[pattern_key]['zone_success_rate'] = 0

    def reset(self):
        """Reset the tracker for a new backtest run."""
        self.tracked_patterns.clear()
        self.completion_history.clear()
        self.pattern_type_stats.clear()
        self.zone_entries.clear()
        self.zone_entry_stats.clear()
        self.current_bar = 0
        self.current_data = None