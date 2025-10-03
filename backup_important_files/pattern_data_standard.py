"""
Unified Pattern Data Structure
==============================

This module defines the standardized pattern data structure used across all pattern
detection modules to ensure compatibility and eliminate data structure inconsistencies.

All pattern detection functions should return patterns in this standardized format.
"""

from typing import Dict, List, Optional, Union, Tuple
from dataclasses import dataclass
import pandas as pd


@dataclass
class PatternPoint:
    """Standardized pattern point with both timestamp and index"""
    timestamp: Union[pd.Timestamp, str]
    price: float
    index: int  # Bar index in the DataFrame


@dataclass
class StandardPattern:
    """Unified pattern data structure for all harmonic patterns"""

    # Basic identification
    name: str                    # Pattern name (e.g., "Gartley1_bull")
    pattern_type: str           # "ABCD" or "XABCD"
    formation_status: str       # "unformed" or "formed"
    direction: str              # "bullish" or "bearish"

    # Pattern points (all patterns have A, B, C)
    x_point: Optional[PatternPoint] = None  # Only for XABCD patterns
    a_point: PatternPoint = None
    b_point: PatternPoint = None
    c_point: PatternPoint = None
    d_point: Optional[PatternPoint] = None  # Only for formed patterns

    # PRZ information
    prz_zones: List[Tuple[float, float]] = None  # List of (min, max) zones
    d_lines: List[float] = None                  # Individual D line projections

    # Pattern ratios and validation
    ratios: Dict = None          # Pattern-specific ratios
    validation_type: str = "strict_containment"
    pattern_hash: Optional[str] = None

    def __post_init__(self):
        """Initialize default values and validate structure"""
        if self.prz_zones is None:
            self.prz_zones = []
        if self.d_lines is None:
            self.d_lines = []
        if self.ratios is None:
            self.ratios = {}

        # Auto-generate pattern hash if not provided
        if self.pattern_hash is None:
            self.pattern_hash = self._generate_hash()

    def _generate_hash(self) -> str:
        """
        Generate unique pattern hash based on structural points (X, A, B, C) AND pattern name.

        Uses indices plus pattern name to ensure different pattern definitions with the
        same structure get unique IDs. This allows tracking multiple patterns (e.g.,
        Gartley, Butterfly) that share the same X, A, B, C points but have different
        D projections and PRZ zones.

        This matches the logic in pattern_tracker.generate_pattern_id() for consistency.
        """
        import hashlib

        # Build key string from structural points only (X, A, B, C - NOT D)
        point_indices = []
        if self.x_point:
            point_indices.append(f"X:{self.x_point.index}")
        if self.a_point:
            point_indices.append(f"A:{self.a_point.index}")
        if self.b_point:
            point_indices.append(f"B:{self.b_point.index}")
        if self.c_point:
            point_indices.append(f"C:{self.c_point.index}")

        # Include pattern name in the key to differentiate patterns with same structure
        indices_string = '_'.join(point_indices) if point_indices else "unknown"
        key_string = f"{self.name}_{indices_string}"

        # Generate MD5 hash for consistency with pattern_tracker
        pattern_hash = hashlib.md5(str(key_string).encode()).hexdigest()[:16]

        return f"{self.pattern_type}_{pattern_hash}"

    def to_legacy_dict(self) -> Dict:
        """Convert to legacy dictionary format for backward compatibility"""
        pattern_dict = {
            'name': self.name,
            'pattern_type': self.pattern_type,
            'formation': self.formation_status,
            'type': self.direction,
            'points': {},
            'indices': {},
            'ratios': self.ratios.copy() if self.ratios else {},
            'validation': self.validation_type,
            'pattern_hash': self.pattern_hash
        }

        # Add points and indices
        if self.x_point:
            pattern_dict['points']['X'] = {
                'time': self.x_point.timestamp,
                'price': self.x_point.price,
                'index': self.x_point.index
            }
            pattern_dict['indices']['X'] = self.x_point.index

        if self.a_point:
            pattern_dict['points']['A'] = {
                'time': self.a_point.timestamp,
                'price': self.a_point.price,
                'index': self.a_point.index
            }
            pattern_dict['indices']['A'] = self.a_point.index

        if self.b_point:
            pattern_dict['points']['B'] = {
                'time': self.b_point.timestamp,
                'price': self.b_point.price,
                'index': self.b_point.index
            }
            pattern_dict['indices']['B'] = self.b_point.index

        if self.c_point:
            pattern_dict['points']['C'] = {
                'time': self.c_point.timestamp,
                'price': self.c_point.price,
                'index': self.c_point.index
            }
            pattern_dict['indices']['C'] = self.c_point.index

        if self.d_point:
            pattern_dict['points']['D'] = {
                'time': self.d_point.timestamp,
                'price': self.d_point.price,
                'index': self.d_point.index
            }
            pattern_dict['indices']['D'] = self.d_point.index

        # Add PRZ information
        if self.formation_status == 'unformed':
            if self.d_lines or self.prz_zones:
                # Initialize D_projected dict if either d_lines or prz_zones exist
                pattern_dict['points']['D_projected'] = {}
                if self.d_lines:
                    pattern_dict['points']['D_projected']['d_lines'] = self.d_lines
                if self.prz_zones:
                    pattern_dict['points']['D_projected']['prz_zones'] = self.prz_zones
        elif self.formation_status == 'formed':
            # For formed patterns, add PRZ zones from ratios if available
            if self.ratios and 'prz_zones' in self.ratios:
                pattern_dict['prz_zones'] = self.ratios['prz_zones']

        return pattern_dict

    @classmethod
    def from_legacy_dict(cls, pattern_dict: Dict) -> 'StandardPattern':
        """Create StandardPattern from legacy dictionary format"""
        points = pattern_dict.get('points', {})
        indices = pattern_dict.get('indices', {})

        # Extract basic info
        name = pattern_dict.get('name', '')
        pattern_type = pattern_dict.get('pattern_type', 'ABCD')
        formation_status = pattern_dict.get('formation', pattern_dict.get('formation_status', 'unformed'))
        direction = pattern_dict.get('type', 'bullish')

        # Create pattern points
        def create_point(point_key: str) -> Optional[PatternPoint]:
            if point_key in points:
                point_data = points[point_key]
                index = indices.get(point_key, point_data.get('index', -1))
                return PatternPoint(
                    timestamp=point_data.get('time', ''),
                    price=point_data.get('price', 0.0),
                    index=index
                )
            return None

        x_point = create_point('X') if pattern_type == 'XABCD' else None
        a_point = create_point('A')
        b_point = create_point('B')
        c_point = create_point('C')
        d_point = create_point('D')

        # Extract PRZ information
        d_lines = []
        prz_zones = []
        if 'D_projected' in points:
            d_proj = points['D_projected']
            if isinstance(d_proj, dict):
                d_lines = d_proj.get('d_lines', [])
                prz_zones = d_proj.get('prz_zones', [])

        return cls(
            name=name,
            pattern_type=pattern_type,
            formation_status=formation_status,
            direction=direction,
            x_point=x_point,
            a_point=a_point,
            b_point=b_point,
            c_point=c_point,
            d_point=d_point,
            prz_zones=prz_zones,
            d_lines=d_lines,
            ratios=pattern_dict.get('ratios', {}),
            validation_type=pattern_dict.get('validation', 'strict_containment'),
            pattern_hash=pattern_dict.get('pattern_hash')
        )


def standardize_pattern_name(raw_name: str, formation_status: str, direction: str) -> str:
    """
    Standardize pattern names for consistent matching between unformed and formed.

    Args:
        raw_name: Original pattern name from detection
        formation_status: "unformed" or "formed"
        direction: "bullish" or "bearish"

    Returns:
        Standardized pattern name
    """
    # Remove existing status and direction indicators
    clean_name = raw_name

    # Remove common suffixes
    suffixes_to_remove = ['_unformed', '_formed', '_strict', '_bull', '_bear', '_bullish', '_bearish']
    for suffix in suffixes_to_remove:
        clean_name = clean_name.replace(suffix, '')

    # Add standardized direction suffix
    direction_suffix = '_bull' if direction.lower() in ['bullish', 'bull'] else '_bear'

    # Add formation status
    status_suffix = f'_{formation_status}' if formation_status == 'unformed' else ''

    return f"{clean_name}{direction_suffix}{status_suffix}"


def fix_unicode_issues(text: str) -> str:
    """Fix Unicode issues in pattern names and output"""
    if not isinstance(text, str):
        return str(text)

    # Replace problematic Unicode characters with ASCII equivalents
    replacements = {
        '✓': '[OK]',
        '✗': '[FAIL]',
        '→': '->',
        '←': '<-',
        '↑': '^',
        '↓': 'v',
        '⚠': '[WARNING]',
        '•': '*',
        '▶': '>',
        '◀': '<'
    }

    result = text
    for unicode_char, ascii_replacement in replacements.items():
        result = result.replace(unicode_char, ascii_replacement)

    # Ensure text is properly encoded as ASCII
    try:
        result = result.encode('ascii', 'replace').decode('ascii')
    except (UnicodeEncodeError, UnicodeDecodeError):
        # Fallback: remove non-ASCII characters
        result = ''.join(char for char in result if ord(char) < 128)

    return result