"""
Enhanced Excel Export with Comprehensive Trading Data
This module provides enhanced Excel export functionality with:
- Pattern Details with D points and Fibonacci levels
- Fibonacci Analysis sheet
- Pattern Performance by type
- Trades sheet (when available)
- Enhanced Summary with performance metrics
"""

import pandas as pd
import numpy as np
from datetime import datetime
import os


def safe_value(value, default=''):
    """Safely convert value to Excel-compatible format"""
    if value is None:
        return default
    if isinstance(value, (int, float, np.integer, np.floating)):
        if np.isnan(value) or np.isinf(value):
            return default
        return value
    return value


def create_enhanced_pattern_details(tracker, test_data, fibonacci_trackers=None):
    """Create enhanced pattern details with D points and Fibonacci levels"""
    patterns_data = []

    for pattern_id, pattern in tracker.tracked_patterns.items():
        pattern_info = {
            'Pattern_ID': pattern_id[:20] + '...' if len(pattern_id) > 20 else pattern_id,
            'Type': pattern.pattern_type,
            'Subtype': pattern.subtype,
            'Status': pattern.status,
            'First_Seen_Bar': pattern.first_seen_bar
        }

        # X Point (XABCD only)
        if pattern.x_point:
            pattern_info['X_Bar'] = int(pattern.x_point[0]) if pattern.x_point[0] is not None else 'N/A'
            pattern_info['X_Price'] = round(float(pattern.x_point[1]), 2) if pattern.x_point[1] is not None else 'N/A'
            if pattern.x_point[0] is not None and pattern.x_point[0] < len(test_data):
                pattern_info['X_Date'] = test_data.index[pattern.x_point[0]].strftime('%Y-%m-%d')

        # A Point
        if pattern.a_point:
            pattern_info['A_Bar'] = int(pattern.a_point[0]) if pattern.a_point[0] is not None else 'N/A'
            pattern_info['A_Price'] = round(float(pattern.a_point[1]), 2) if pattern.a_point[1] is not None else 'N/A'
            if pattern.a_point[0] is not None and pattern.a_point[0] < len(test_data):
                pattern_info['A_Date'] = test_data.index[pattern.a_point[0]].strftime('%Y-%m-%d')

        # B Point
        if pattern.b_point:
            pattern_info['B_Bar'] = int(pattern.b_point[0]) if pattern.b_point[0] is not None else 'N/A'
            pattern_info['B_Price'] = round(float(pattern.b_point[1]), 2) if pattern.b_point[1] is not None else 'N/A'
            if pattern.b_point[0] is not None and pattern.b_point[0] < len(test_data):
                pattern_info['B_Date'] = test_data.index[pattern.b_point[0]].strftime('%Y-%m-%d')

        # C Point
        if pattern.c_point:
            pattern_info['C_Bar'] = int(pattern.c_point[0]) if pattern.c_point[0] is not None else 'N/A'
            pattern_info['C_Price'] = round(float(pattern.c_point[1]), 2) if pattern.c_point[1] is not None else 'N/A'
            if pattern.c_point[0] is not None and pattern.c_point[0] < len(test_data):
                pattern_info['C_Date'] = test_data.index[pattern.c_point[0]].strftime('%Y-%m-%d')

            # C updates tracking
            if hasattr(pattern, 'completion_details') and pattern.completion_details and pattern.completion_details.get('c_updated'):
                pattern_info['C_Updated'] = 'Yes'
                c_update_bar = pattern.completion_details.get('c_update_bar', None)
                pattern_info['C_Update_Bar'] = int(c_update_bar) if c_update_bar is not None else 'N/A'

                # Add updated C price and date
                if c_update_bar is not None and pattern.c_point:
                    # Current C point is the updated one
                    pattern_info['C_Update_Price'] = round(float(pattern.c_point[1]), 2) if pattern.c_point[1] is not None else 'N/A'
                    if c_update_bar < len(test_data):
                        pattern_info['C_Update_Date'] = test_data.index[c_update_bar].strftime('%Y-%m-%d')

        # D Point (if formed)
        if pattern.d_point:
            pattern_info['D_Bar'] = int(pattern.d_point[0]) if pattern.d_point[0] is not None else 'N/A'
            pattern_info['D_Price'] = round(float(pattern.d_point[1]), 2) if pattern.d_point[1] is not None else 'N/A'
            if pattern.d_point[0] is not None and pattern.d_point[0] < len(test_data):
                pattern_info['D_Date'] = test_data.index[pattern.d_point[0]].strftime('%Y-%m-%d')

        # PRZ/Zone Entry
        if pattern.zone_reached:
            pattern_info['PRZ_Entry_Bar'] = int(pattern.zone_entry_bar) if pattern.zone_entry_bar is not None else 'N/A'
            pattern_info['PRZ_Entry_Price'] = round(float(pattern.zone_entry_price), 2) if pattern.zone_entry_price is not None else 'N/A'
            if pattern.zone_entry_bar is not None and pattern.zone_entry_bar < len(test_data):
                pattern_info['PRZ_Entry_Date'] = test_data.index[pattern.zone_entry_bar].strftime('%Y-%m-%d')

        # PRZ Zone - Single consolidated format
        if pattern.prz_zones:
            # Use first/primary zone
            first_zone = pattern.prz_zones[0]
            prz_min = first_zone.get('min', 0)
            prz_max = first_zone.get('max', 0)
            pattern_source = first_zone.get('pattern_source', 'Zone')

            pattern_info['PRZ_Zone'] = f"{round(prz_min, 2)} - {round(prz_max, 2)}"
            pattern_info['PRZ_Source'] = pattern_source

            # Calculate PRZ width
            if prz_min and prz_max:
                prz_width = ((prz_max - prz_min) / prz_min) * 100
                pattern_info['PRZ_Width_%'] = round(prz_width, 2)
        elif pattern.prz_min and pattern.prz_max:
            pattern_info['PRZ_Zone'] = f"{round(pattern.prz_min, 2)} - {round(pattern.prz_max, 2)}"
            prz_width = ((pattern.prz_max - pattern.prz_min) / pattern.prz_min) * 100
            pattern_info['PRZ_Width_%'] = round(prz_width, 2)
        elif pattern.d_lines:
            pattern_info['PRZ_Zone'] = ', '.join([str(round(d, 2)) for d in pattern.d_lines[:3]])

        # Fibonacci levels from tracker (if available)
        if fibonacci_trackers and pattern_id in fibonacci_trackers:
            fib_tracker = fibonacci_trackers[pattern_id]

            # Add key Fibonacci levels
            if hasattr(fib_tracker, 'fib_levels'):
                for level_name, level_price in fib_tracker.fib_levels.items():
                    # Only add major levels to pattern details
                    if any(key in level_name for key in ['38.2', '50.0', '61.8', '78.6', '127', '161']):
                        pattern_info[f'Fib_{level_name}'] = round(level_price, 2)

        # Dismissal reason
        if pattern.status == 'dismissed' and hasattr(pattern, 'completion_details'):
            pattern_info['Dismissal_Reason'] = pattern.completion_details.get('dismissal_reason', 'Unknown')

        # Pattern quality metrics
        if hasattr(pattern, 'price_accuracy') and pattern.price_accuracy:
            pattern_info['Price_Accuracy_%'] = round(pattern.price_accuracy * 100, 2)

        patterns_data.append(pattern_info)

    patterns_df = pd.DataFrame(patterns_data)
    if not patterns_df.empty:
        patterns_df = patterns_df.sort_values(['First_Seen_Bar', 'Status'], ascending=[True, True])
        # Replace None and NaN with empty string for Excel compatibility
        patterns_df = patterns_df.fillna('')

    return patterns_df


def create_fibonacci_analysis_sheet(fibonacci_trackers):
    """Create comprehensive Fibonacci analysis sheet"""
    fib_data = []

    if not fibonacci_trackers:
        return pd.DataFrame()

    for pattern_id, fib_tracker in fibonacci_trackers.items():
        # Base pattern info
        base_info = {
            'Pattern_ID': pattern_id[:30],
            'Pattern_Type': fib_tracker.pattern_type,
            'Pattern_Name': fib_tracker.pattern_name,
            'Direction': fib_tracker.direction,
            'Detection_Bar': fib_tracker.detection_bar,
            'D_Price': round(fib_tracker.d_price, 2),
            'PRZ_Min': round(fib_tracker.prz_min, 2),
            'PRZ_Max': round(fib_tracker.prz_max, 2),
            'PRZ_Broken': 'Yes' if fib_tracker.prz_broken_bar else 'No',
            'Bars_Tracked': fib_tracker.total_bars_tracked
        }

        # Add Fibonacci retracement levels
        fib_retrace_levels = ['23.6%', '38.2%', '50.0%', '61.8%', '78.6%']
        fib_extension_levels = ['127.2%', '141.4%', '161.8%', '200.0%', '261.8%']

        # Combine all levels
        all_fib_levels = {}
        if hasattr(fib_tracker, 'fib_levels'):
            all_fib_levels.update(fib_tracker.fib_levels)
        if hasattr(fib_tracker, 'harmonic_levels'):
            all_fib_levels.update(fib_tracker.harmonic_levels)

        # Count touches per level
        touches_by_level = {}
        if hasattr(fib_tracker, 'touches'):
            for touch in fib_tracker.touches:
                level = touch.level_name
                if level not in touches_by_level:
                    touches_by_level[level] = []
                touches_by_level[level].append(touch)

        # Add each Fibonacci level and harmonic structure level as a separate row
        for level_name, level_price in sorted(all_fib_levels.items()):
            # Include Fibonacci percentages AND harmonic structure levels (X, A, B, C)
            is_fib_level = any(key in level_name for key in ['23.6', '38.2', '50.0', '61.8', '78.6', '127', '141', '161', '200', '261'])
            is_harmonic_level = any(key in level_name for key in ['X_Level', 'A_Level', 'B_Level', 'C_Level'])

            if is_fib_level or is_harmonic_level:
                row = base_info.copy()
                row['Level_Name'] = level_name
                row['Level_Price'] = round(level_price, 2)

                # Touch information
                level_touches = touches_by_level.get(level_name, [])
                row['Touch_Count'] = len(level_touches)
                row['Hit'] = 'Yes' if level_touches else 'No'

                if level_touches:
                    first_touch = level_touches[0]
                    # Use getattr with defaults to handle missing attributes
                    abs_bar = getattr(first_touch, 'absolute_bar', None)
                    inc_bar = getattr(first_touch, 'incremental_bar', None)
                    touch_type = getattr(first_touch, 'touch_type', 'unknown')

                    row['First_Touch_Bar'] = int(abs_bar) if abs_bar is not None else ''
                    row['First_Touch_Type'] = touch_type if touch_type else ''
                    row['Bars_To_Hit'] = int(inc_bar) if inc_bar is not None else ''

                fib_data.append(row)

    fib_df = pd.DataFrame(fib_data)
    if not fib_df.empty:
        # Create a sorting key for Fibonacci levels
        def fib_sort_key(level_name):
            """Extract numeric value from Fibonacci level name for sorting"""
            import re
            match = re.search(r'(\d+\.?\d*)', level_name)
            if match:
                return float(match.group(1))
            return 999  # Put unknown formats at end

        # Sort by Pattern_ID first, then by Fibonacci level ascending
        fib_df['_sort_key'] = fib_df['Level_Name'].apply(fib_sort_key)
        fib_df = fib_df.sort_values(['Pattern_ID', '_sort_key'], ascending=[True, True])
        fib_df = fib_df.drop(columns=['_sort_key'])

        # Replace None and NaN with empty string for Excel compatibility
        fib_df = fib_df.fillna('')

    return fib_df


def create_pattern_performance_sheet(tracker):
    """Create pattern performance analysis by type"""
    performance_data = {}

    for pattern_id, pattern in tracker.tracked_patterns.items():
        subtype = pattern.subtype

        if subtype not in performance_data:
            performance_data[subtype] = {
                'Pattern_Name': subtype,
                'Total_Occurrences': 0,
                'Success_Count': 0,
                'Failed_Count': 0,
                'Dismissed_Count': 0,
                'Pending_Count': 0,
                'Zone_Reached_Count': 0
            }

        performance_data[subtype]['Total_Occurrences'] += 1

        if pattern.status == 'success':
            performance_data[subtype]['Success_Count'] += 1
        elif pattern.status == 'failed':
            performance_data[subtype]['Failed_Count'] += 1
        elif pattern.status == 'dismissed':
            performance_data[subtype]['Dismissed_Count'] += 1
        elif pattern.status == 'pending':
            performance_data[subtype]['Pending_Count'] += 1

        if pattern.zone_reached:
            performance_data[subtype]['Zone_Reached_Count'] += 1

    # Calculate rates
    perf_list = []
    for pattern_name, data in performance_data.items():
        total = data['Total_Occurrences']
        if total > 0:
            data['Zone_Reach_Rate_%'] = round((data['Zone_Reached_Count'] / total) * 100, 1)

            completed = data['Success_Count'] + data['Failed_Count']
            if completed > 0:
                data['Success_Rate_%'] = round((data['Success_Count'] / completed) * 100, 1)
            else:
                data['Success_Rate_%'] = 'N/A'

        perf_list.append(data)

    perf_df = pd.DataFrame(perf_list)
    if not perf_df.empty:
        perf_df = perf_df.sort_values('Total_Occurrences', ascending=False)
        # Replace None and NaN with empty string for Excel compatibility
        perf_df = perf_df.fillna('')

    return perf_df


def create_enhanced_summary(stats, tracker, test_data, backtester):
    """Create enhanced summary with performance metrics"""

    # Calculate additional metrics
    success_count = sum(1 for p in tracker.tracked_patterns.values() if p.status == 'success')
    failed_count = sum(1 for p in tracker.tracked_patterns.values() if p.status == 'failed')
    dismissed_count = sum(1 for p in tracker.tracked_patterns.values() if p.status == 'dismissed')
    pending_count = sum(1 for p in tracker.tracked_patterns.values() if p.status == 'pending')
    zone_reached_count = sum(1 for p in tracker.tracked_patterns.values() if p.zone_reached)

    total_completed = success_count + failed_count
    success_rate = (success_count / total_completed * 100) if total_completed > 0 else 0
    zone_reach_rate = (zone_reached_count / len(tracker.tracked_patterns) * 100) if tracker.tracked_patterns else 0

    summary_data = {
        'Metric': [
            '--- BACKTEST INFO ---',
            'Date Range',
            'Total Bars',
            'Extremum Length',
            'Detection Interval',
            '',
            '--- PATTERN COUNTS ---',
            'Total Unformed Detected',
            'Total Formed Detected',
            '  - Formed ABCD',
            '  - Formed XABCD',
            'Unique Patterns Tracked',
            '',
            '--- PATTERN OUTCOMES ---',
            'Success',
            'Failed',
            'Dismissed',
            'Pending',
            'Zone Reached',
            '',
            '--- PERFORMANCE METRICS ---',
            'Success Rate (%)',
            'Zone Reach Rate (%)',
            'Average Bars to Zone',
            'Average Price Accuracy (%)',
            '',
            '--- EXTREMUM POINTS ---',
            'Total Extremums',
            '  - Highs',
            '  - Lows',
            '',
            '--- PROCESSING ---',
            'Time Taken (seconds)',
        ],
        'Value': [
            '',
            f"{test_data.index[0].strftime('%Y-%m-%d')} to {test_data.index[-1].strftime('%Y-%m-%d')}",
            len(test_data),
            backtester.extremum_length,
            backtester.detection_interval,
            '',
            '',
            stats.get('total_unformed_patterns', 0),
            stats.get('total_formed_patterns', 0),
            stats.get('formed_abcd_count', 0),
            stats.get('formed_xabcd_count', 0),
            stats.get('patterns_tracked', 0),
            '',
            '',
            success_count,
            failed_count,
            dismissed_count,
            pending_count,
            zone_reached_count,
            '',
            '',
            round(success_rate, 2),
            round(zone_reach_rate, 2),
            round(np.mean([p.bars_from_c_to_zone for p in tracker.tracked_patterns.values() if p.bars_from_c_to_zone]), 1) if any(p.bars_from_c_to_zone for p in tracker.tracked_patterns.values()) else 'N/A',
            round(np.mean([p.price_accuracy * 100 for p in tracker.tracked_patterns.values() if p.price_accuracy]), 1) if any(p.price_accuracy for p in tracker.tracked_patterns.values()) else 'N/A',
            '',
            '',
            stats.get('total_extremum_points', 0),
            stats.get('high_extremum_points', 0),
            stats.get('low_extremum_points', 0),
            '',
            '',
            round(stats.get('time_taken', 0), 2),
        ]
    }

    summary_df = pd.DataFrame(summary_data)
    # Replace None and NaN with empty string for Excel compatibility
    summary_df = summary_df.fillna('')

    return summary_df
