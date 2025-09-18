#identifies:-
#   * AB=CD harmonic pattern (tested against Trading View formulation, works perfect)
#   * AB=CD added 14 patterns & ratios (7 bull / 7 bearish)
#   * graph plots each individually
#   * XABCD also implemented (bruteforce, not most effecient, O(N^5))
#   * added 3 XABCD patterns: bat,maxbat,antibat
#  TODO: make it O(N^3)
#  in future, to replace local maxima/minima with swign high/low (Trend, subjective, to formulate)

import pandas as pd
import mplfinance as mpf
import matplotlib.pyplot as plt
from matplotlib.widgets import Button, TextBox, CheckButtons
from matplotlib.backends.backend_tkagg import NavigationToolbar2Tk
from matplotlib.widgets import Cursor
import matplotlib.dates as mdates
from pattern_ratios_2_Final import ABCD_PATTERN_RATIOS, XABCD_PATTERN_RATIOS, PATTERN_COLORS, PRZ_PROJECTION_PAIRS
import time
import numpy as np
import tkinter as tk
from tkinter import filedialog
from datetime import datetime
import json

def pivot_high(high: pd.Series, length: int) -> pd.Series:
    """
    Return a Series whose values equal the pivot-high price on the bar
    that is strictly higher than the `length` bars before *and* after it.
    Everywhere else the Series is NaN – identical to Pine's ta.pivothigh(len,len).

    Parameters
    ----------
    high   : pd.Series
        High-price column, indexed in chronological order.
    length : int
        Number of bars to look back AND look ahead (symmetric window).

    Returns
    -------
    pd.Series
        Same index as `high`, NaN except on confirmed pivot-high bars.
    """
    n = len(high)
    out = np.full(n, np.nan)
    h = high.values  # NumPy array for speed

    for i in range(length, n - length):
        window_left  = h[i - length:i]          # preceding highs
        window_right = h[i + 1:i + length + 1]  # future highs
        candidate = h[i]

        # strictly higher than every other high in the window
        if (candidate > window_left).all() and (candidate > window_right).all():
            out[i] = candidate          # mark only the pivot bar

    return pd.Series(out, index=high.index, name="pivot_high")

def pivot_low(low: pd.Series, length: int) -> pd.Series:
    """
    Mirror of `pivot_high` for lows (strictly lower than neighbours).
    """
    n = len(low)
    out = np.full(n, np.nan)
    l = low.values

    for i in range(length, n - length):
        window_left  = l[i - length:i]
        window_right = l[i + 1:i + length + 1]
        candidate = l[i]

        if (candidate < window_left).all() and (candidate < window_right).all():
            out[i] = candidate

    return pd.Series(out, index=low.index, name="pivot_low")

class InteractiveGraphBase:
    """Base class for interactive graph functionality with enhanced features."""
    
    def __init__(self):
        self.cursor_text = None
        self.date_text = None
        self.price_text = None
        self.help_text = None
        self.pan_mode = False
        self.zoom_x_only = False
        self.zoom_y_only = False
        self.start_pan = None
        self.original_xlim = None
        self.original_ylim = None
        
        # Axis drag zoom variables
        self.x_axis_drag = False
        self.y_axis_drag = False
        self.drag_start_x = None
        self.drag_start_y = None
        self.drag_start_xlim = None
        self.drag_start_ylim = None
        
    def setup_interactive_features(self, fig, ax, data):
        """Setup panning, zooming, and hover text for the graph."""
        # Store original limits
        self.original_xlim = ax.get_xlim()
        self.original_ylim = ax.get_ylim()
        
        # Setup cursor for crosshair
        cursor = Cursor(ax, useblit=True, color='gray', linewidth=0.5, linestyle='--')
        
        # Create text objects for displaying hover information
        self.date_text = fig.text(0.5, 0.02, '', ha='center', va='bottom', 
                                 bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
        self.price_text = fig.text(0.98, 0.5, '', ha='right', va='center', rotation=90,
                                  bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.8))
        
        # Add help text
        help_str = ("Controls:\n"
                   "Mouse: Hover for date/price | Wheel: Zoom | Right-click+drag: Pan\n"
                   "Left-click+drag on axis areas: Axis-specific zoom\n"
                   "Keys: 'h'-help | 'r'-reset | 'x'-X-zoom | 'y'-Y-zoom | 'z'-both zoom")
        self.help_text = fig.text(0.02, 0.98, help_str, ha='left', va='top', fontsize=8,
                                 bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.7))
        
        # Connect all interactive events
        fig.canvas.mpl_connect('motion_notify_event', 
                              lambda event: self.on_mouse_move(event, ax, data))
        fig.canvas.mpl_connect('key_press_event', 
                              lambda event: self.on_key_press_zoom(event, ax))
        fig.canvas.mpl_connect('button_press_event',
                              lambda event: self.on_button_press(event, ax))
        fig.canvas.mpl_connect('button_release_event',
                              lambda event: self.on_button_release(event, ax))
        fig.canvas.mpl_connect('scroll_event',
                              lambda event: self.on_scroll(event, ax))
        
        return cursor

    def is_on_x_axis(self, event, ax):
        """Check if mouse is on the X-axis area (bottom 10% of chart)."""
        if event.inaxes != ax or event.ydata is None:
            return False
        ylim = ax.get_ylim()
        y_range = ylim[1] - ylim[0]
        return event.ydata < (ylim[0] + y_range * 0.1)

    def is_on_y_axis(self, event, ax):
        """Check if mouse is on the Y-axis area (left 10% of chart)."""
        if event.inaxes != ax or event.xdata is None:
            return False
        xlim = ax.get_xlim()
        x_range = xlim[1] - xlim[0]
        return event.xdata < (xlim[0] + x_range * 0.1)
    
    def on_mouse_move(self, event, ax, data):
        """Handle mouse movement for hover text and axis dragging."""
        if event.inaxes != ax and not self.x_axis_drag and not self.y_axis_drag:
            self.date_text.set_text('')
            self.price_text.set_text('')
            return
        
        # Handle X-axis drag zooming
        if self.x_axis_drag and self.drag_start_x is not None:
            if event.xdata is not None:
                drag_distance = event.xdata - self.drag_start_x
                xlim = self.drag_start_xlim
                x_range = xlim[1] - xlim[0]
                
                # Linear zoom based on drag distance relative to current range
                zoom_factor = 1.0 + (drag_distance / (x_range * 0.5))  # More consistent sensitivity
                
                if zoom_factor > 0.1:  # Prevent negative zoom
                    x_center = (xlim[0] + xlim[1]) / 2
                    new_x_range = x_range / zoom_factor
                    
                    new_xlim = (x_center - new_x_range/2, x_center + new_x_range/2)
                    ax.set_xlim(new_xlim)
                    event.canvas.draw_idle()
            return
        
        # Handle Y-axis drag zooming
        if self.y_axis_drag and self.drag_start_y is not None:
            if event.ydata is not None:
                drag_distance = event.ydata - self.drag_start_y
                ylim = self.drag_start_ylim
                y_range = ylim[1] - ylim[0]
                
                # Linear zoom based on drag distance relative to current range
                zoom_factor = 1.0 + (drag_distance / (y_range * 0.5))  # More consistent sensitivity
                
                if zoom_factor > 0.1:  # Prevent negative zoom
                    y_center = (ylim[0] + ylim[1]) / 2
                    new_y_range = y_range / zoom_factor
                    
                    new_ylim = (y_center - new_y_range/2, y_center + new_y_range/2)
                    ax.set_ylim(new_ylim)
                    event.canvas.draw_idle()
            return
            
        # Handle regular panning
        if self.pan_mode and self.start_pan and event.button == 3:
            if event.xdata is not None and event.ydata is not None:
                dx = event.xdata - self.start_pan[0]
                dy = event.ydata - self.start_pan[1]
                
                xlim = ax.get_xlim()
                ylim = ax.get_ylim()
                
                ax.set_xlim(xlim[0] - dx, xlim[1] - dx)
                ax.set_ylim(ylim[0] - dy, ylim[1] - dy)
                
                event.canvas.draw_idle()
            return
        
        # Show visual feedback for axis areas and hover info
        if event.inaxes == ax:
            x, y = event.xdata, event.ydata
            if x is None or y is None:
                return
                
            # Visual feedback for axis areas
            if self.is_on_x_axis(event, ax):
                ax.set_xlabel('Time Index (DRAG HERE TO ZOOM TIME AXIS)', 
                             fontweight='bold', color='red')
            elif self.is_on_y_axis(event, ax):
                ax.set_ylabel('Price (DRAG HERE TO ZOOM PRICE AXIS)', 
                             fontweight='bold', color='red')
            else:
                ax.set_xlabel('Time Index', fontweight='normal', color='black')
                ax.set_ylabel('Price', fontweight='normal', color='black')
                
            # Show hover information
            try:
                x_idx = int(round(x))
                if 0 <= x_idx < len(data):
                    timestamp = data.index[x_idx]
                    date_str = timestamp.strftime('%Y-%m-%d %H:%M:%S')
                    
                    self.date_text.set_text(f'Date: {date_str}')
                    self.price_text.set_text(f'Price: {y:.4f}')
                    
                    event.canvas.draw_idle()
            except (IndexError, ValueError):
                pass
    
    def on_button_press(self, event, ax):
        """Handle mouse button press for panning and axis zooming."""
        if event.button == 1:  # Left mouse button
            if self.is_on_x_axis(event, ax):
                self.x_axis_drag = True
                self.drag_start_x = event.xdata if event.xdata else 0
                self.drag_start_xlim = ax.get_xlim()
                print("X-axis drag zoom started - drag right to zoom in, left to zoom out")
                return
            elif self.is_on_y_axis(event, ax):
                self.y_axis_drag = True
                self.drag_start_y = event.ydata if event.ydata else 0
                self.drag_start_ylim = ax.get_ylim()
                print("Y-axis drag zoom started - drag up to zoom in, down to zoom out")
                return
                
        elif event.button == 3:  # Right mouse button
            if event.inaxes == ax:
                self.pan_mode = True
                self.start_pan = (event.xdata, event.ydata)
                print("Pan mode started - drag to pan around")
    
    def on_button_release(self, event, ax):
        """Handle mouse button release."""
        if event.button == 1:  # Left mouse button
            if self.x_axis_drag:
                self.x_axis_drag = False
                self.drag_start_x = None
                self.drag_start_xlim = None
                print("X-axis drag zoom ended")
            elif self.y_axis_drag:
                self.y_axis_drag = False
                self.drag_start_y = None
                self.drag_start_ylim = None
                print("Y-axis drag zoom ended")
                
        elif event.button == 3:  # Right mouse button
            self.pan_mode = False
            self.start_pan = None
            print("Pan mode ended")
    
    def on_scroll(self, event, ax):
        """Handle mouse wheel scrolling for zooming with linear zoom speed."""
        if event.inaxes != ax:
            return
            
        # Get current axis limits
        xlim = ax.get_xlim()
        ylim = ax.get_ylim()
        
        # Linear zoom: use fixed amount based on current range
        # This makes zoom speed feel consistent regardless of zoom level
        zoom_speed = 0.1  # 10% of current range per scroll
        
        # Get mouse position in data coordinates
        x_mouse = event.xdata
        y_mouse = event.ydata
        
        # Determine zoom direction (in = negative step, out = positive step)
        zoom_in = event.step < 0
        
        if self.zoom_x_only:
            # Zoom X-axis only with linear speed
            x_range = xlim[1] - xlim[0]
            zoom_amount = x_range * zoom_speed
            
            if zoom_in:
                zoom_amount = -zoom_amount  # Zoom in (reduce range)
            
            x_center = x_mouse if x_mouse else (xlim[0] + xlim[1]) / 2
            new_x_range = x_range + zoom_amount
            
            # Prevent zooming in too much
            if new_x_range > 0.1:  # Minimum range
                new_xlim = (x_center - new_x_range/2, x_center + new_x_range/2)
                ax.set_xlim(new_xlim)
            
        elif self.zoom_y_only:
            # Zoom Y-axis only with linear speed
            y_range = ylim[1] - ylim[0]
            zoom_amount = y_range * zoom_speed
            
            if zoom_in:
                zoom_amount = -zoom_amount  # Zoom in (reduce range)
            
            y_center = y_mouse if y_mouse else (ylim[0] + ylim[1]) / 2
            new_y_range = y_range + zoom_amount
            
            # Prevent zooming in too much
            if new_y_range > 0.001:  # Minimum range for price
                new_ylim = (y_center - new_y_range/2, y_center + new_y_range/2)
                ax.set_ylim(new_ylim)
            
        else:
            # Zoom both axes with linear speed
            x_range = xlim[1] - xlim[0]
            y_range = ylim[1] - ylim[0]
            
            x_zoom_amount = x_range * zoom_speed
            y_zoom_amount = y_range * zoom_speed
            
            if zoom_in:
                x_zoom_amount = -x_zoom_amount
                y_zoom_amount = -y_zoom_amount
            
            x_center = x_mouse if x_mouse else (xlim[0] + xlim[1]) / 2
            y_center = y_mouse if y_mouse else (ylim[0] + ylim[1]) / 2
            
            new_x_range = x_range + x_zoom_amount
            new_y_range = y_range + y_zoom_amount
            
            # Prevent zooming in too much
            if new_x_range > 0.1 and new_y_range > 0.001:
                new_xlim = (x_center - new_x_range/2, x_center + new_x_range/2)
                new_ylim = (y_center - new_y_range/2, y_center + new_y_range/2)
                
                ax.set_xlim(new_xlim)
                ax.set_ylim(new_ylim)
        
        event.canvas.draw_idle()

    def on_key_press_zoom(self, event, ax):
        """Handle keyboard shortcuts for axis-specific zooming."""
        if event.key == 'h':
            # Toggle help text visibility
            if self.help_text:
                self.help_text.set_visible(not self.help_text.get_visible())
                event.canvas.draw_idle()
        elif event.key == 'r':
            # Reset zoom
            if self.original_xlim and self.original_ylim:
                ax.set_xlim(self.original_xlim)
                ax.set_ylim(self.original_ylim)
                self.zoom_x_only = False
                self.zoom_y_only = False
                event.canvas.draw_idle()
                print("Zoom reset to original view")
        elif event.key == 'x':
            # Toggle X-axis only zoom mode
            self.zoom_x_only = not self.zoom_x_only
            self.zoom_y_only = False
            mode = "X-axis only" if self.zoom_x_only else "both axes"
            print(f"Zoom mode: {mode}")
        elif event.key == 'y':
            # Toggle Y-axis only zoom mode
            self.zoom_y_only = not self.zoom_y_only
            self.zoom_x_only = False
            mode = "Y-axis only" if self.zoom_y_only else "both axes"
            print(f"Zoom mode: {mode}")
        elif event.key == 'z':
            # Reset to both axes zoom
            self.zoom_x_only = False
            self.zoom_y_only = False
            print("Zoom mode: both axes")

class PatternDetector:
    def __init__(self, data, extremum_points=None, length=1):
        self.data = data
        self.extremum_points = extremum_points  # List of (index, price, is_min) tuples
        self.length = length
        
        # Precompute pivot highs and lows if not using predefined extremum points
        if self.extremum_points is None:
            self.pivot_highs = pivot_high(self.data['high'], self.length)
            self.pivot_lows = pivot_low(self.data['low'], self.length)

    def is_local_extremum(self, index, is_min=True):
        """Check if a point is a local extremum."""
        if self.extremum_points is not None:
            # Convert index to timestamp for comparison
            if isinstance(index, int):
                if index < 0 or index >= len(self.data):
                    return False
                timestamp = self.data.index[index]
            else:
                timestamp = index
            
            # Check if the point exists in our predefined extremum points
            return any(idx == timestamp and is_max == (not is_min) 
                      for idx, _, is_max in self.extremum_points)
        
        # Use precomputed pivot highs/lows
        if is_min:
            return not pd.isna(self.pivot_lows.iloc[index])
        else:
            return not pd.isna(self.pivot_highs.iloc[index])

    def find_abcd_patterns(self):
        """Find AB=CD patterns in the data."""
        patterns = []
        
        def find_pattern(pattern_name, ratios):
            is_bear_pattern = (ratios['type'] == 1)
            
            # If using predefined extremum points, only iterate over those
            if self.extremum_points is not None:
                # Convert extremum points to a lookup for faster access
                extremum_lookup = {}
                for timestamp, price, is_max in self.extremum_points:
                    extremum_lookup[timestamp] = (price, is_max)
                
                # Get timestamps in chronological order
                timestamps = sorted([idx for idx, _, _ in self.extremum_points])
                
                # Use the same logic as original but with predefined extremum points
                # Need to maintain proper spacing constraints like the original algorithm
                for i in range(len(timestamps)):
                    a_time = timestamps[i]
                    a_idx = self.data.index.get_loc(a_time)
                    
                    # Skip if A is too close to start/end (like original: range(1, len-3))
                    if a_idx < 1 or a_idx >= len(self.data) - 3:
                        continue
                        
                    if not self.is_local_extremum(a_time, is_min=not is_bear_pattern):
                        continue
                        
                    # Find B points with proper spacing (equivalent to j + 2 spacing)
                    for j in range(i + 1, len(timestamps)):
                        b_time = timestamps[j]
                        b_idx = self.data.index.get_loc(b_time)
                        
                        # Ensure proper spacing: B must be at least 2 positions after A
                        if b_idx < a_idx + 2 or b_idx >= len(self.data) - 2:
                            continue
                            
                        if not self.is_local_extremum(b_time, is_min=is_bear_pattern):
                            continue
                            
                        # Validate AB move direction
                        if is_bear_pattern:
                            if not (self.data.loc[a_time, 'high'] > self.data.loc[b_time, 'low']):
                                continue
                            ab_move = self.data.loc[a_time, 'high'] - self.data.loc[b_time, 'low']
                        else:
                            if not (self.data.loc[a_time, 'low'] < self.data.loc[b_time, 'high']):
                                continue
                            ab_move = self.data.loc[b_time, 'high'] - self.data.loc[a_time, 'low']

                        # Safety check for division by zero
                        if ab_move == 0:
                            continue

                        # Find C points with proper spacing
                        for k in range(j + 1, len(timestamps)):
                            c_time = timestamps[k]
                            c_idx = self.data.index.get_loc(c_time)
                            
                            # Ensure proper spacing: C must be at least 2 positions after B
                            if c_idx < b_idx + 2 or c_idx >= len(self.data) - 1:
                                continue
                                
                            if not self.is_local_extremum(c_time, is_min=not is_bear_pattern):
                                continue
                                
                            # Validate BC move direction
                            if is_bear_pattern:
                                if not (self.data.loc[b_time, 'low'] < self.data.loc[c_time, 'high']):
                                    continue
                                bc_move = self.data.loc[c_time, 'high'] - self.data.loc[b_time, 'low']
                            else:
                                if not (self.data.loc[b_time, 'high'] > self.data.loc[c_time, 'low']):
                                    continue
                                bc_move = self.data.loc[c_time, 'low'] - self.data.loc[b_time, 'high']

                            # Safety check for division by zero
                            if bc_move == 0:
                                continue

                            bc_retracement = abs(bc_move / ab_move) * 100
                            if ratios['retr'][0] <= bc_retracement <= ratios['retr'][1]:
                                # Find D points with proper spacing
                                for l in range(k + 1, len(timestamps)):
                                    d_time = timestamps[l]
                                    d_idx = self.data.index.get_loc(d_time)
                                    
                                    # Ensure proper spacing: D must be at least 2 positions after C
                                    if d_idx < c_idx + 2:
                                        continue
                                        
                                    if not self.is_local_extremum(d_time, is_min=is_bear_pattern):
                                        continue
                                        
                                    # Validate CD move direction
                                    if is_bear_pattern:
                                        if not (self.data.loc[c_time, 'high'] > self.data.loc[d_time, 'low']):
                                            continue
                                        cd_move = self.data.loc[d_time, 'low'] - self.data.loc[c_time, 'high']
                                    else:
                                        if not (self.data.loc[c_time, 'low'] < self.data.loc[d_time, 'high']):
                                            continue
                                        cd_move = self.data.loc[d_time, 'high'] - self.data.loc[c_time, 'low']

                                    cd_projection = abs(cd_move / bc_move) * 100
                                    if ratios['proj'][0] <= cd_projection <= ratios['proj'][1]:
                                        patterns.append((a_time, b_time, c_time, d_time, 
                                                      bc_retracement, cd_projection, pattern_name))
                                        break  # Only first valid D for this ABC - CRITICAL!
            else:
                # Original pattern detection logic for automatic extremum detection
                for i in range(1, len(self.data) - 3):
                    for j in range(i + 2, len(self.data) - 2):
                        if not self.is_local_extremum(i, is_min=not is_bear_pattern) or \
                           not self.is_local_extremum(j, is_min=is_bear_pattern):
                            continue
                            
                        ab_start, ab_end = self.data.index[i], self.data.index[j]
                        if is_bear_pattern:
                            if not (self.data.loc[ab_start, 'high'] > self.data.loc[ab_end, 'low']):
                                continue
                            ab_move = self.data.loc[ab_start, 'high'] - self.data.loc[ab_end, 'low']
                        else:
                            if not (self.data.loc[ab_start, 'low'] < self.data.loc[ab_end, 'high']):
                                continue
                            ab_move = self.data.loc[ab_end, 'high'] - self.data.loc[ab_start, 'low']

                        # Safety check for division by zero
                        if ab_move == 0:
                            continue

                        for k in range(j + 2, len(self.data) - 1):
                            if not self.is_local_extremum(k, is_min=not is_bear_pattern):
                                continue
                                
                            bc_end = self.data.index[k]
                            if is_bear_pattern:
                                if not (self.data.loc[ab_end, 'low'] < self.data.loc[bc_end, 'high']):
                                    continue
                                bc_move = self.data.loc[bc_end, 'high'] - self.data.loc[ab_end, 'low']
                            else:
                                if not (self.data.loc[ab_end, 'high'] > self.data.loc[bc_end, 'low']):
                                    continue
                                bc_move = self.data.loc[bc_end, 'low'] - self.data.loc[ab_end, 'high']

                            # Safety check for division by zero
                            if bc_move == 0:
                                continue

                            bc_retracement = abs(bc_move / ab_move) * 100
                            if ratios['retr'][0] <= bc_retracement <= ratios['retr'][1]:
                                for l in range(k + 2, len(self.data)):
                                    if not self.is_local_extremum(l, is_min=is_bear_pattern):
                                        continue
                                        
                                    cd_end = self.data.index[l]
                                    if is_bear_pattern:
                                        if not (self.data.loc[bc_end, 'high'] > self.data.loc[cd_end, 'low']):
                                            continue
                                        cd_move = self.data.loc[cd_end, 'low'] - self.data.loc[bc_end, 'high']
                                    else:
                                        if not (self.data.loc[bc_end, 'low'] < self.data.loc[cd_end, 'high']):
                                            continue
                                        cd_move = self.data.loc[cd_end, 'high'] - self.data.loc[bc_end, 'low']

                                    cd_projection = abs(cd_move / bc_move) * 100
                                    if ratios['proj'][0] <= cd_projection <= ratios['proj'][1]:
                                        patterns.append((ab_start, ab_end, bc_end, cd_end, 
                                                      bc_retracement, cd_projection, pattern_name))
                                        break

        for pattern_name, ratios in ABCD_PATTERN_RATIOS.items():
            find_pattern(pattern_name, ratios)
        return patterns

    def find_xabcd_patterns(self):
        """Find XABCD patterns in the data using a fast, candidate-pruned approach (no window for X)."""
        patterns = []
        n = len(self.data)
        # Precompute extrema types for all indices
        is_min = [self.is_local_extremum(i, is_min=True) for i in range(n)]
        is_max = [self.is_local_extremum(i, is_min=False) for i in range(n)]
        for pattern_name, ratios in XABCD_PATTERN_RATIOS.items():
            is_bear_pattern = (ratios['type'] == 1)
            # Assign candidate lists based on pattern type
            if is_bear_pattern:
                a_candidates = [i for i in range(n) if is_min[i]]
                x_candidates_all = [i for i in range(n) if is_max[i]]
                b_candidates = [i for i in range(n) if is_max[i]]
                c_candidates = [i for i in range(n) if is_min[i]]
                d_candidates = [i for i in range(n) if is_max[i]]
            else:
                a_candidates = [i for i in range(n) if is_max[i]]
                x_candidates_all = [i for i in range(n) if is_min[i]]
                b_candidates = [i for i in range(n) if is_min[i]]
                c_candidates = [i for i in range(n) if is_max[i]]
                d_candidates = [i for i in range(n) if is_min[i]]
            for ai in a_candidates:
                # For X, consider all X < A (no window)
                x_candidates = [xi for xi in x_candidates_all if xi < ai]
                for xi in x_candidates:
                    # XA move
                    if is_bear_pattern:
                        if not (self.data.iloc[xi]['high'] > self.data.iloc[ai]['low']):
                            continue
                        xa_move = self.data.iloc[xi]['high'] - self.data.iloc[ai]['low']
                    else:
                        if not (self.data.iloc[xi]['low'] < self.data.iloc[ai]['high']):
                            continue
                        xa_move = self.data.iloc[ai]['high'] - self.data.iloc[xi]['low']
                    for bi in b_candidates:
                        if bi <= ai:
                            continue
                        # AB move
                        if is_bear_pattern:
                            if not (self.data.iloc[bi]['high'] > self.data.iloc[ai]['low']):
                                continue
                            ab_move = self.data.iloc[bi]['high'] - self.data.iloc[ai]['low']
                        else:
                            if not (self.data.iloc[bi]['low'] < self.data.iloc[ai]['high']):
                                continue
                            ab_move = self.data.iloc[ai]['high'] - self.data.iloc[bi]['low']
                        ab_xa_ratio = (ab_move / xa_move) * 100 if xa_move != 0 else 0
                        if not (ratios['ab_xa'][0] <= ab_xa_ratio <= ratios['ab_xa'][1]):
                            continue
                        for ci in c_candidates:
                            if ci <= bi:
                                continue
                            # BC move
                            if is_bear_pattern:
                                if not (self.data.iloc[bi]['high'] > self.data.iloc[ci]['low']):
                                    continue
                                bc_move = self.data.iloc[bi]['high'] - self.data.iloc[ci]['low']
                            else:
                                if not (self.data.iloc[bi]['low'] < self.data.iloc[ci]['high']):
                                    continue
                                bc_move = self.data.iloc[ci]['high'] - self.data.iloc[bi]['low']
                            bc_ab_ratio = (bc_move / ab_move) * 100 if ab_move != 0 else 0
                            if not (ratios['bc_ab'][0] <= bc_ab_ratio <= ratios['bc_ab'][1]):
                                continue
                            for di in d_candidates:
                                if di <= ci:
                                    continue
                                # CD and AD moves
                                if is_bear_pattern:
                                    if not (self.data.iloc[ci]['low'] < self.data.iloc[di]['high']):
                                        continue
                                    cd_move = self.data.iloc[di]['high'] - self.data.iloc[ci]['low']
                                    ad_move = self.data.iloc[di]['high'] - self.data.iloc[ai]['low']
                                else:
                                    if not (self.data.iloc[ci]['high'] > self.data.iloc[di]['low']):
                                        continue
                                    cd_move = self.data.iloc[ci]['high'] - self.data.iloc[di]['low']
                                    ad_move = self.data.iloc[ai]['high'] - self.data.iloc[di]['low']
                                cd_bc_ratio = (cd_move / bc_move) * 100 if bc_move != 0 else 0
                                ad_xa_ratio = (ad_move / xa_move) * 100 if xa_move != 0 else 0
                                if (ratios['cd_bc'][0] <= cd_bc_ratio <= ratios['cd_bc'][1] and
                                    ratios['ad_xa'][0] <= ad_xa_ratio <= ratios['ad_xa'][1]):
                                    x_point = self.data.index[xi]
                                    a_point = self.data.index[ai]
                                    b_point = self.data.index[bi]
                                    c_point = self.data.index[ci]
                                    d_point = self.data.index[di]
                                    patterns.append((x_point, a_point, b_point, c_point, d_point,
                                                    ab_xa_ratio, bc_ab_ratio, cd_bc_ratio, ad_xa_ratio,
                                                    pattern_name))
                                    break  # Only first valid D for this XABC
        return patterns

    def find_unformed_patterns(self):
        """Find potential (unformed) AB=CD patterns."""
        patterns = []
        def find_pattern(pattern_name, ratios):
            for i in range(1, len(self.data) - 2):
                for j in range(i + 2, len(self.data) - 1):
                    is_bear_pattern = (ratios['type'] == 1)
                    if not self.is_local_extremum(i, is_min=not is_bear_pattern) or \
                       not self.is_local_extremum(j, is_min=is_bear_pattern):
                        continue
                    ab_start, ab_end = self.data.index[i], self.data.index[j]
                    if is_bear_pattern:
                        if not (self.data.loc[ab_start, 'high'] > self.data.loc[ab_end, 'low']):
                            continue
                        ab_move = self.data.loc[ab_start, 'high'] - self.data.loc[ab_end, 'low']
                    else:
                        if not (self.data.loc[ab_start, 'low'] < self.data.loc[ab_end, 'high']):
                            continue
                        ab_move = self.data.loc[ab_end, 'high'] - self.data.loc[ab_start, 'low']
                    if ab_move == 0:
                        continue
                    for k in range(j + 2, len(self.data)):
                        if not self.is_local_extremum(k, is_min=not is_bear_pattern):
                            continue
                        bc_end = self.data.index[k]
                        if is_bear_pattern:
                            if not (self.data.loc[ab_end, 'low'] < self.data.loc[bc_end, 'high']):
                                continue
                            bc_move = self.data.loc[bc_end, 'high'] - self.data.loc[ab_end, 'low']
                        else:
                            if not (self.data.loc[ab_end, 'high'] > self.data.loc[bc_end, 'low']):
                                continue
                            bc_move = self.data.loc[bc_end, 'low'] - self.data.loc[ab_end, 'high']
                        if bc_move == 0:
                            continue
                        bc_retracement = abs(bc_move / ab_move) * 100
                        if ratios['retr'][0] <= bc_retracement <= ratios['retr'][1]:
                            if is_bear_pattern:
                                potential_d_price_min = self.data.loc[bc_end, 'high'] - (bc_move * ratios['proj'][1] / 100)
                                potential_d_price_max = self.data.loc[bc_end, 'high'] - (bc_move * ratios['proj'][0] / 100)
                            else:
                                potential_d_price_min = self.data.loc[bc_end, 'low'] + (bc_move * ratios['proj'][0] / 100)
                                potential_d_price_max = self.data.loc[bc_end, 'low'] + (bc_move * ratios['proj'][1] / 100)
                            patterns.append((ab_start, ab_end, bc_end, 
                                          bc_retracement, ratios['proj'][0], ratios['proj'][1],
                                          potential_d_price_min, potential_d_price_max,
                                          pattern_name))
                            break
        for pattern_name, ratios in ABCD_PATTERN_RATIOS.items():
            find_pattern(pattern_name, ratios)
        # --- Post-filter: remove patterns where D already formed ---
        print(f"[DEBUG] Unformed ABCD: {len(patterns)} patterns before D-range filter")
        first_filtered = []
        epsilon = 1e-8
        for idx, pat in enumerate(patterns):
            ab_start, ab_end, bc_end, bc_retr, cd_proj_min, cd_proj_max, d_price_min, d_price_max, pattern_name = pat
            is_bull = 'bull' in pattern_name.lower()
            c_idx = self.data.index.get_loc(bc_end)
            df_after_c = self.data.iloc[c_idx+1:]
            dmin = min(d_price_min, d_price_max) - epsilon
            dmax = max(d_price_min, d_price_max) + epsilon
            if idx < 3:
                # Print debug info for first 3 patterns
                print(f"[DEBUG] Pattern {idx}: {pattern_name}, C={bc_end}, D-range=({dmin:.6f}, {dmax:.6f})")
                if is_bull:
                    print(f"[DEBUG]   min(low) after C: {df_after_c['low'].min()}, max(low): {df_after_c['low'].max()}")
                else:
                    print(f"[DEBUG]   min(high) after C: {df_after_c['high'].min()}, max(high): {df_after_c['high'].max()}")
            if is_bull:
                if df_after_c['low'].between(dmin, dmax, inclusive='both').any():
                    continue
            else:
                if df_after_c['high'].between(dmin, dmax, inclusive='both').any():
                    continue
            first_filtered.append(pat)
        print(f"[DEBUG] Unformed ABCD: {len(first_filtered)} patterns after D-range filter")
        
        # --- PRZ containment filter: remove patterns where price entered PRZ zone ---
        filtered_patterns = []
        patterns_removed_by_prz = 0
        
        for pat in first_filtered:
            ab_start, ab_end, bc_end, bc_retr, cd_proj_min, cd_proj_max, d_price_min, d_price_max, pattern_name = pat
            is_bull = 'bull' in pattern_name.lower()
            
            # Get price points
            if is_bull:
                c_price = self.data.loc[bc_end, 'low']
                b_price = self.data.loc[ab_end, 'high']
            else:
                c_price = self.data.loc[bc_end, 'high']
                b_price = self.data.loc[ab_end, 'low']
            
            # Calculate BC move
            bc_move = abs(c_price - b_price)
            
            # Calculate average projection
            avg_projection = (cd_proj_min + cd_proj_max) / 2
            
            # Get price data after C
            c_idx = self.data.index.get_loc(bc_end)
            df_after_c = self.data.iloc[c_idx+1:]
            
            if len(df_after_c) == 0:
                filtered_patterns.append(pat)
                continue
            
            # Get highest high and lowest low after C
            max_high_after_c = df_after_c['high'].max()
            min_low_after_c = df_after_c['low'].min()
            
            # Check each applicable PRZ pair based on BC retracement
            pattern_valid = False
            for proj_low, proj_high in PRZ_PROJECTION_PAIRS:
                if proj_low <= bc_retr <= proj_high:
                    # This PRZ pair applies - compute PRZ boundaries
                    if is_bull:
                        prz_low = c_price + (bc_move * proj_low / 100)
                        prz_high = c_price + (bc_move * proj_high / 100)
                    else:
                        # For bearish patterns
                        prz_high = c_price - (bc_move * proj_low / 100)
                        prz_low = c_price - (bc_move * proj_high / 100)
                    
                    # Check if price stayed outside PRZ zone
                    # Pattern is valid if highest high is below PRZ_low OR lowest low is above PRZ_high
                    if max_high_after_c < prz_low or min_low_after_c > prz_high:
                        pattern_valid = True
                        break
            
            if pattern_valid:
                filtered_patterns.append(pat)
            else:
                patterns_removed_by_prz += 1
        
        print(f"[PRZ FILTER] {patterns_removed_by_prz} patterns removed - price entered PRZ zone")
        print(f"[DEBUG] Unformed ABCD: {len(filtered_patterns)} valid patterns remaining")
        
        # Report patterns with multiple PRZ pairs
        patterns_with_multiple_prz = []
        for idx, pat in enumerate(filtered_patterns):
            ab_start, ab_end, bc_end, bc_retr, cd_proj_min, cd_proj_max, d_price_min, d_price_max, pattern_name = pat
            is_bull = 'bull' in pattern_name.lower()
            
            # Get price points
            if is_bull:
                c_price = self.data.loc[bc_end, 'low']
                b_price = self.data.loc[ab_end, 'high']
            else:
                c_price = self.data.loc[bc_end, 'high']
                b_price = self.data.loc[ab_end, 'low']
            
            # Calculate BC move and average projection
            bc_move = abs(c_price - b_price)
            avg_projection = (cd_proj_min + cd_proj_max) / 2
            
            # Find all matching PRZ pairs based on BC retracement
            matching_prz = []
            for proj_low, proj_high in PRZ_PROJECTION_PAIRS:
                if proj_low <= bc_retr <= proj_high:
                    if is_bull:
                        prz_low = c_price + (bc_move * proj_low / 100)
                        prz_high = c_price + (bc_move * proj_high / 100)
                    else:
                        prz_high = c_price - (bc_move * proj_low / 100)
                        prz_low = c_price - (bc_move * proj_high / 100)
                    matching_prz.append({
                        'proj_pair': (proj_low, proj_high),
                        'prz_range': (prz_low, prz_high)
                    })
            
            if len(matching_prz) > 1:
                patterns_with_multiple_prz.append({
                    'index': idx + 1,  # 1-based index for user display
                    'pattern_name': pattern_name,
                    'bc_retracement': bc_retr,
                    'prz_zones': matching_prz
                })
        
        # Print patterns with multiple PRZ
        if patterns_with_multiple_prz:
            print(f"\n[MULTIPLE PRZ] Patterns with multiple PRZ zones detected:")
            for pat_info in patterns_with_multiple_prz:
                print(f"  Pattern #{pat_info['index']} ({pat_info['pattern_name']}) - BC Retracement: {pat_info['bc_retracement']:.2f}%")
                for prz in pat_info['prz_zones']:
                    print(f"    - Proj: {prz['proj_pair'][0]:.1f}%-{prz['proj_pair'][1]:.1f}% "
                          f"-> PRZ: {prz['prz_range'][0]:.4f} to {prz['prz_range'][1]:.4f}")
        
        return filtered_patterns

    def find_unformed_xabcd_patterns(self):
        """Find potential (unformed) XABCD patterns where D has not yet formed."""
        patterns = []
        n = len(self.data)
        is_min = [self.is_local_extremum(i, is_min=True) for i in range(n)]
        is_max = [self.is_local_extremum(i, is_min=False) for i in range(n)]
        for pattern_name, ratios in XABCD_PATTERN_RATIOS.items():
            is_bear_pattern = (ratios['type'] == 1)
            if is_bear_pattern:
                a_candidates = [i for i in range(n) if is_min[i]]
                x_candidates_all = [i for i in range(n) if is_max[i]]
                b_candidates = [i for i in range(n) if is_max[i]]
                c_candidates = [i for i in range(n) if is_min[i]]
            else:
                a_candidates = [i for i in range(n) if is_max[i]]
                x_candidates_all = [i for i in range(n) if is_min[i]]
                b_candidates = [i for i in range(n) if is_min[i]]
                c_candidates = [i for i in range(n) if is_max[i]]
            for ai in a_candidates:
                x_candidates = [xi for xi in x_candidates_all if xi < ai]
                for xi in x_candidates:
                    if is_bear_pattern:
                        if not (self.data.iloc[xi]['high'] > self.data.iloc[ai]['low']):
                            continue
                        xa_move = self.data.iloc[xi]['high'] - self.data.iloc[ai]['low']
                    else:
                        if not (self.data.iloc[xi]['low'] < self.data.iloc[ai]['high']):
                            continue
                        xa_move = self.data.iloc[ai]['high'] - self.data.iloc[xi]['low']
                    for bi in b_candidates:
                        if bi <= ai:
                            continue
                        if is_bear_pattern:
                            if not (self.data.iloc[bi]['high'] > self.data.iloc[ai]['low']):
                                continue
                            ab_move = self.data.iloc[bi]['high'] - self.data.iloc[ai]['low']
                        else:
                            if not (self.data.iloc[bi]['low'] < self.data.iloc[ai]['high']):
                                continue
                            ab_move = self.data.iloc[ai]['high'] - self.data.iloc[bi]['low']
                        ab_xa_ratio = (ab_move / xa_move) * 100 if xa_move != 0 else 0
                        if not (ratios['ab_xa'][0] <= ab_xa_ratio <= ratios['ab_xa'][1]):
                            continue
                        for ci in c_candidates:
                            if ci <= bi:
                                continue
                            if is_bear_pattern:
                                if not (self.data.iloc[bi]['high'] > self.data.iloc[ci]['low']):
                                    continue
                                bc_move = self.data.iloc[bi]['high'] - self.data.iloc[ci]['low']
                            else:
                                if not (self.data.iloc[bi]['low'] < self.data.iloc[ci]['high']):
                                    continue
                                bc_move = self.data.iloc[ci]['high'] - self.data.iloc[bi]['low']
                            bc_ab_ratio = (bc_move / ab_move) * 100 if ab_move != 0 else 0
                            if not (ratios['bc_ab'][0] <= bc_ab_ratio <= ratios['bc_ab'][1]):
                                continue
                            cd_ratio_min, cd_ratio_max = ratios['cd_bc']
                            cd_move_min = bc_move * cd_ratio_min / 100.0
                            cd_move_max = bc_move * cd_ratio_max / 100.0
                            ad_ratio_min, ad_ratio_max = ratios['ad_xa']
                            ad_move_min = xa_move * ad_ratio_min / 100.0
                            ad_move_max = xa_move * ad_ratio_max / 100.0
                            if is_bear_pattern:
                                c_price = self.data.iloc[ci]['low']
                                d_price_cd_min = c_price + cd_move_min
                                d_price_cd_max = c_price + cd_move_max
                            else:
                                c_price = self.data.iloc[ci]['high']
                                d_price_cd_min = c_price - cd_move_max
                                d_price_cd_max = c_price - cd_move_min
                            if is_bear_pattern:
                                a_price = self.data.iloc[ai]['low']
                                d_price_ad_min = a_price + ad_move_min
                                d_price_ad_max = a_price + ad_move_max
                            else:
                                a_price = self.data.iloc[ai]['high']
                                d_price_ad_min = a_price - ad_move_max
                                d_price_ad_max = a_price - ad_move_min
                            cd_lower, cd_upper = sorted([d_price_cd_min, d_price_cd_max])
                            ad_lower, ad_upper = sorted([d_price_ad_min, d_price_ad_max])
                            d_price_min = max(cd_lower, ad_lower)
                            d_price_max = min(cd_upper, ad_upper)
                            if d_price_min > d_price_max:
                                continue
                            x_point = self.data.index[xi]
                            a_point = self.data.index[ai]
                            b_point = self.data.index[bi]
                            c_point = self.data.index[ci]
                            patterns.append((x_point, a_point, b_point, c_point,
                                             ab_xa_ratio, bc_ab_ratio,
                                             cd_ratio_min, cd_ratio_max,
                                             d_price_min, d_price_max,
                                             pattern_name))
                            break
        print(f"[DEBUG] Unformed XABCD: {len(patterns)} patterns before D-range filter")
        filtered_patterns = []
        epsilon = 1e-8
        for idx, pat in enumerate(patterns):
            (x_point, a_point, b_point, c_point,
             ab_xa_ratio, bc_ab_ratio, cd_min, cd_max, d_price_min, d_price_max, pattern_name) = pat
            is_bull = 'bull' in pattern_name.lower()
            c_idx = self.data.index.get_loc(c_point)
            df_after_c = self.data.iloc[c_idx+1:]
            dmin = min(d_price_min, d_price_max) - epsilon
            dmax = max(d_price_min, d_price_max) + epsilon
            if idx < 3:
                print(f"[DEBUG] Pattern {idx}: {pattern_name}, C={c_point}, D-range=({dmin:.6f}, {dmax:.6f})")
                if is_bull:
                    print(f"[DEBUG]   min(low) after C: {df_after_c['low'].min()}, max(low): {df_after_c['low'].max()}")
                else:
                    print(f"[DEBUG]   min(high) after C: {df_after_c['high'].min()}, max(high): {df_after_c['high'].max()}")
            if is_bull:
                if df_after_c['low'].between(dmin, dmax, inclusive='both').any():
                    continue
            else:
                if df_after_c['high'].between(dmin, dmax, inclusive='both').any():
                    continue
            filtered_patterns.append(pat)
        print(f"[DEBUG] Unformed XABCD: {len(filtered_patterns)} patterns after D-range filter")
        return filtered_patterns

    def PRZ_computation_plotting(self, unformed_patterns, ax=None):
        """
        Compute and plot PRZ levels for unformed ABCD patterns.
        
        For each unformed pattern:
        1. Calculate D_real using average of pattern's projection range
        2. Find all PRZ pairs where D_real falls within
        3. Compute PRZ_low and PRZ_high for each matching pair
        4. Plot horizontal lines at PRZ levels
        
        Returns: List of PRZ computations for each pattern
        """
        prz_results = []
        
        for pattern in unformed_patterns:
            # Unpack pattern data
            if len(pattern) == 9:  # ABCD unformed pattern format
                (ab_start, ab_end, bc_end, bc_retracement, 
                 cd_proj_min, cd_proj_max, d_price_min, d_price_max, pattern_name) = pattern
                
                # Determine if bullish or bearish
                is_bull = 'bull' in pattern_name.lower()
                
                # Get price points
                if is_bull:
                    a_price = self.data.loc[ab_start, 'low']
                    b_price = self.data.loc[ab_end, 'high']
                    c_price = self.data.loc[bc_end, 'low']
                else:
                    a_price = self.data.loc[ab_start, 'high']
                    b_price = self.data.loc[ab_end, 'low']
                    c_price = self.data.loc[bc_end, 'high']
                
                # Calculate BC move
                bc_move = abs(c_price - b_price)
                
                # Calculate average projection and D_real
                avg_projection = (cd_proj_min + cd_proj_max) / 2
                
                if is_bull:
                    d_real = c_price + (bc_move * avg_projection / 100)
                else:
                    d_real = c_price - (bc_move * avg_projection / 100)
                
                # Find matching PRZ pairs and compute PRZ levels
                prz_levels = []
                for proj_low, proj_high in PRZ_PROJECTION_PAIRS:
                    # Check if BC retracement falls within this pair
                    if proj_low <= bc_retracement <= proj_high:
                        if is_bull:
                            prz_low = c_price + (bc_move * proj_low / 100)
                            prz_high = c_price + (bc_move * proj_high / 100)
                        else:
                            # For bearish, flip the calculation
                            prz_high = c_price - (bc_move * proj_low / 100)
                            prz_low = c_price - (bc_move * proj_high / 100)
                        
                        prz_levels.append({
                            'prz_low': prz_low,
                            'prz_high': prz_high,
                            'proj_pair': (proj_low, proj_high)
                        })
                        
                        # Plot horizontal lines if ax is provided
                        if ax:
                            # Get time range for the lines (from C to end of data)
                            c_idx = self.data.index.get_loc(bc_end)
                            x_start = c_idx
                            x_end = len(self.data) - 1
                            
                            # Plot PRZ low line
                            ax.hlines(prz_low, x_start, x_end, colors='green', 
                                    linestyles='dashed', alpha=0.7, linewidth=1,
                                    label=f'PRZ Low ({proj_low}%)')
                            
                            # Plot PRZ high line
                            ax.hlines(prz_high, x_start, x_end, colors='red', 
                                    linestyles='dashed', alpha=0.7, linewidth=1,
                                    label=f'PRZ High ({proj_high}%)')
                
                # Store results
                prz_results.append({
                    'pattern_name': pattern_name,
                    'pattern_points': (ab_start, ab_end, bc_end),
                    'd_real': d_real,
                    'avg_projection': avg_projection,
                    'prz_levels': prz_levels,
                    'is_bullish': is_bull
                })
                
                # Debug output
                if prz_levels:
                    print(f"\n[PRZ] Pattern: {pattern_name}")
                    print(f"  D_real: {d_real:.4f} (avg proj: {avg_projection:.1f}%)")
                    print(f"  Found {len(prz_levels)} PRZ zones:")
                    for prz in prz_levels:
                        print(f"    PRZ: {prz['prz_low']:.4f} - {prz['prz_high']:.4f} "
                              f"(from {prz['proj_pair'][0]}%-{prz['proj_pair'][1]}%)")
        
        return prz_results

class PatternViewer(InteractiveGraphBase):
    def __init__(self, data, patterns, pattern_type='ABCD'):
        super().__init__()
        self.data = data
        self.patterns = patterns
        self.pattern_type = pattern_type
        self.current_idx = 0
        self.fig = plt.figure(figsize=(15, 8))
        plt.subplots_adjust(bottom=0.2)
        self.info_text_box = None  # For pattern info box
        self.setup_plot()
        
    def setup_plot(self):
        self.ax = self.fig.add_axes([0.1, 0.25, 0.8, 0.65])  # Adjusted to make room for hover text
        self.ax_prev = self.fig.add_axes([0.2, 0.05, 0.15, 0.075])
        self.ax_next = self.fig.add_axes([0.65, 0.05, 0.15, 0.075])
        self.btn_prev = Button(self.ax_prev, 'Previous')
        self.btn_next = Button(self.ax_next, 'Next')
        self.btn_prev.on_clicked(self.previous_pattern)
        self.btn_next.on_clicked(self.next_pattern)
        
        # Setup interactive features with custom help text
        plot_data = self.data.copy()
        plot_data.index = pd.to_datetime(plot_data.index)
        self.setup_interactive_features_with_navigation(self.fig, self.ax, plot_data)
        
        self.fig.canvas.mpl_connect('key_press_event', self.on_key_press)
        self.plot_current_pattern()
        
    def setup_interactive_features_with_navigation(self, fig, ax, data):
        """Setup interactive features with pattern navigation help."""
        # Call the base class setup method to get all enhanced features
        cursor = self.setup_interactive_features(fig, ax, data)
        
        # Update help text to include navigation controls
        help_str = ("Controls:\n"
                   "Mouse: Hover for date/price | Wheel: Zoom | Right-click+drag: Pan\n"
                   "Left-click+drag on axis areas: Axis-specific zoom\n"
                   "Keys: <-/-> arrows - navigate patterns | 'h' - toggle help | 'r' - reset zoom\n"
                   "'x'-X-zoom | 'y'-Y-zoom | 'z'-both zoom")
        self.help_text.set_text(help_str)
        
        return cursor
    
    def plot_current_pattern(self):
        if not self.patterns:
            self.ax.clear()
            self.ax.text(0.5, 0.5, 'No patterns found', ha='center', va='center')
            self.fig.canvas.draw_idle()
            return
        self.ax.clear()
        # Remove previous info box if it exists
        if self.info_text_box is not None:
            self.info_text_box.remove()
            self.info_text_box = None
        pattern = self.patterns[self.current_idx]
        plot_data = self.data.copy()
        plot_data.index = pd.to_datetime(plot_data.index)
        mpf.plot(plot_data, 
                 type='candle',
                 style='charles',
                 ax=self.ax,
                 volume=False,
                 datetime_format='%Y-%m-%d',
                 xrotation=45)
        if self.pattern_type == 'ABCD':
            self._plot_abcd_pattern(pattern)
        elif self.pattern_type == 'XABCD':
            self._plot_xabcd_pattern(pattern)
        elif self.pattern_type == 'UnformedXABCD':
            self._plot_unformed_xabcd_pattern(pattern)
        else:  # Unformed (ABCD)
            self._plot_unformed_pattern(pattern)
        self.fig.tight_layout()
        self.fig.canvas.draw_idle()
    
    def _plot_abcd_pattern(self, pattern):
        ab_start, ab_end, bc_end, cd_end, bc_retr, cd_proj, pattern_name = pattern
        color = self._get_color(pattern_name)
        is_bull = 'bull' in pattern_name
        points = []
        if is_bull:
            points = [
                (self.data.index.get_loc(ab_start), self.data.loc[ab_start, 'low']),
                (self.data.index.get_loc(ab_end), self.data.loc[ab_end, 'high']),
                (self.data.index.get_loc(bc_end), self.data.loc[bc_end, 'low']),
                (self.data.index.get_loc(cd_end), self.data.loc[cd_end, 'high'])
            ]
        else:
            points = [
                (self.data.index.get_loc(ab_start), self.data.loc[ab_start, 'high']),
                (self.data.index.get_loc(ab_end), self.data.loc[ab_end, 'low']),
                (self.data.index.get_loc(bc_end), self.data.loc[bc_end, 'high']),
                (self.data.index.get_loc(cd_end), self.data.loc[cd_end, 'low'])
            ]
        self._plot_points_and_lines(points, color, is_bull, ['A', 'B', 'C', 'D'])
        self.ax.set_title(f'Pattern {self.current_idx + 1}/{len(self.patterns)}: {pattern_name}\n'
                         f'BC Retracement: {bc_retr:.1f}%, CD Projection: {cd_proj:.1f}%')
        info = []
        for label, idx in zip(['A', 'B', 'C', 'D'], [ab_start, ab_end, bc_end, cd_end]):
            dt = str(idx)
            price = self.data.loc[idx, 'low'] if is_bull and label in ['A', 'C'] else self.data.loc[idx, 'high'] if is_bull else self.data.loc[idx, 'high'] if label in ['A', 'C'] else self.data.loc[idx, 'low']
            info.append(f"{label}: {dt}\n    Price: {price:.4f}")
        info.append(f"BC/AB: {bc_retr:.2f}%\nCD/BC: {cd_proj:.2f}%")
        self._show_info_box(info)
    
    def _plot_xabcd_pattern(self, pattern):
        x_point, a_point, b_point, c_point, d_point, ab_xa, bc_ab, cd_bc, ad_xa, pattern_name = pattern
        color = self._get_color(pattern_name)
        is_bull = 'bull' in pattern_name
        points = []
        if is_bull:
            points = [
                (self.data.index.get_loc(x_point), self.data.loc[x_point, 'low']),
                (self.data.index.get_loc(a_point), self.data.loc[a_point, 'high']),
                (self.data.index.get_loc(b_point), self.data.loc[b_point, 'low']),
                (self.data.index.get_loc(c_point), self.data.loc[c_point, 'high']),
                (self.data.index.get_loc(d_point), self.data.loc[d_point, 'low'])
            ]
        else:
            points = [
                (self.data.index.get_loc(x_point), self.data.loc[x_point, 'high']),
                (self.data.index.get_loc(a_point), self.data.loc[a_point, 'low']),
                (self.data.index.get_loc(b_point), self.data.loc[b_point, 'high']),
                (self.data.index.get_loc(c_point), self.data.loc[c_point, 'low']),
                (self.data.index.get_loc(d_point), self.data.loc[d_point, 'high'])
            ]
        self._plot_points_and_lines(points, color, is_bull, ['X', 'A', 'B', 'C', 'D'])
        self.ax.set_title(f'Pattern {self.current_idx + 1}/{len(self.patterns)}: {pattern_name}\n'
                         f'AB/XA: {ab_xa:.1f}%, BC/AB: {bc_ab:.1f}%\n'
                         f'CD/BC: {cd_bc:.1f}%, AD/XA: {ad_xa:.1f}%')
        info = []
        for label, idx in zip(['X', 'A', 'B', 'C', 'D'], [x_point, a_point, b_point, c_point, d_point]):
            dt = str(idx)
            if is_bull:
                price = self.data.loc[idx, 'low'] if label in ['X', 'B', 'D'] else self.data.loc[idx, 'high']
            else:
                price = self.data.loc[idx, 'high'] if label in ['X', 'B', 'D'] else self.data.loc[idx, 'low']
            info.append(f"{label}: {dt}\n    Price: {price:.4f}")
        info.append(f"AB/XA: {ab_xa:.2f}%\nBC/AB: {bc_ab:.2f}%\nCD/BC: {cd_bc:.2f}%\nAD/XA: {ad_xa:.2f}%")
        self._show_info_box(info)
    
    def _plot_unformed_pattern(self, pattern):
        ab_start, ab_end, bc_end, bc_retr, cd_proj_min, cd_proj_max, d_price_min, d_price_max, pattern_name = pattern
        color = self._get_color(pattern_name)
        is_bull = 'bull' in pattern_name
        points = []
        if is_bull:
            points = [
                (self.data.index.get_loc(ab_start), self.data.loc[ab_start, 'low']),
                (self.data.index.get_loc(ab_end), self.data.loc[ab_end, 'high']),
                (self.data.index.get_loc(bc_end), self.data.loc[bc_end, 'low'])
            ]
        else:
            points = [
                (self.data.index.get_loc(ab_start), self.data.loc[ab_start, 'high']),
                (self.data.index.get_loc(ab_end), self.data.loc[ab_end, 'low']),
                (self.data.index.get_loc(bc_end), self.data.loc[bc_end, 'high'])
            ]
        self._plot_points_and_lines(points, color, is_bull, ['A', 'B', 'C'])
        last_date_idx = len(self.data) - 1
        self.ax.plot([points[-1][0], last_date_idx],
                    [points[-1][1], d_price_min],
                    color=color, linestyle=':', alpha=0.5)
        self.ax.plot([points[-1][0], last_date_idx],
                    [points[-1][1], d_price_max],
                    color=color, linestyle=':', alpha=0.5)
        self.ax.annotate('D (min)',
                        (last_date_idx, d_price_min),
                        xytext=(10, 10), textcoords='offset points',
                        color=color, fontweight='bold')
        self.ax.annotate('D (max)',
                        (last_date_idx, d_price_max),
                        xytext=(10, -10), textcoords='offset points',
                        color=color, fontweight='bold')
        
        # Compute and plot PRZ levels
        detector = PatternDetector(self.data)
        prz_results = detector.PRZ_computation_plotting([pattern], ax=self.ax)
        
        # Calculate D_real and PRZ levels for info box
        d_real = None
        prz_info_lines = []
        if prz_results and prz_results[0]['prz_levels']:
            d_real = prz_results[0]['d_real']
            # Format PRZ levels for display
            for i, prz in enumerate(prz_results[0]['prz_levels'], 1):
                prz_info_lines.append(f"PRZ{i}: {prz['prz_low']:.4f} - {prz['prz_high']:.4f} ({prz['proj_pair'][0]:.1f}%-{prz['proj_pair'][1]:.1f}%)")
        
        self.ax.set_title(f'Unformed Pattern {self.current_idx + 1}/{len(self.patterns)}: {pattern_name}\n'
                         f'BC Retracement: {bc_retr:.1f}%\n'
                         f'CD Projection Range: {cd_proj_min:.1f}% - {cd_proj_max:.1f}%')
        info = []
        for label, idx in zip(['A', 'B', 'C'], [ab_start, ab_end, bc_end]):
            dt = str(idx)
            price = self.data.loc[idx, 'low'] if is_bull and label in ['A', 'C'] else self.data.loc[idx, 'high'] if is_bull else self.data.loc[idx, 'high'] if label in ['A', 'C'] else self.data.loc[idx, 'low']
            info.append(f"{label}: {dt}\n    Price: {price:.4f}")
        
        # Add D_real and PRZ levels to info box
        d_real_str = f"D_real: {d_real:.4f}" if d_real else "D_real: N/A"
        prz_str = "\n".join(prz_info_lines) if prz_info_lines else "No PRZ zones"
        info.append(f"BC/AB: {bc_retr:.2f}%\nCD/BC: {cd_proj_min:.2f}% - {cd_proj_max:.2f}%\nD range: {d_price_min:.4f} - {d_price_max:.4f}\n{d_real_str}\n{prz_str}")
        self._show_info_box(info)
    
    def _plot_unformed_xabcd_pattern(self, pattern):
        (x_point, a_point, b_point, c_point,
         ab_xa, bc_ab, cd_min, cd_max,
         d_price_min, d_price_max,
         pattern_name) = pattern
        color = self._get_color(pattern_name)
        is_bull = 'bull' in pattern_name
        if is_bull:
            points = [
                (self.data.index.get_loc(x_point), self.data.loc[x_point, 'low']),
                (self.data.index.get_loc(a_point), self.data.loc[a_point, 'high']),
                (self.data.index.get_loc(b_point), self.data.loc[b_point, 'low']),
                (self.data.index.get_loc(c_point), self.data.loc[c_point, 'high'])
            ]
        else:
            points = [
                (self.data.index.get_loc(x_point), self.data.loc[x_point, 'high']),
                (self.data.index.get_loc(a_point), self.data.loc[a_point, 'low']),
                (self.data.index.get_loc(b_point), self.data.loc[b_point, 'high']),
                (self.data.index.get_loc(c_point), self.data.loc[c_point, 'low'])
            ]
        self._plot_points_and_lines(points, color, is_bull, ['X', 'A', 'B', 'C'])
        last_date_idx = len(self.data) - 1
        self.ax.plot([points[-1][0], last_date_idx],
                     [points[-1][1], d_price_min],
                     color=color, linestyle=':', alpha=0.5)
        self.ax.plot([points[-1][0], last_date_idx],
                     [points[-1][1], d_price_max],
                     color=color, linestyle=':', alpha=0.5)
        self.ax.annotate('D (min)',
                         (last_date_idx, d_price_min),
                         xytext=(10, 10), textcoords='offset points',
                         color=color, fontweight='bold')
        self.ax.annotate('D (max)',
                         (last_date_idx, d_price_max),
                         xytext=(10, -10), textcoords='offset points',
                         color=color, fontweight='bold')
        self.ax.set_title(f'Unformed XABCD {self.current_idx + 1}/{len(self.patterns)}: {pattern_name}\n'
                          f'AB/XA: {ab_xa:.1f}%, BC/AB: {bc_ab:.1f}%\n'
                          f'CD/BC Range: {cd_min:.1f}% - {cd_max:.1f}%')
        info = []
        for label, idx in zip(['X', 'A', 'B', 'C'], [x_point, a_point, b_point, c_point]):
            dt = str(idx)
            if is_bull:
                price = self.data.loc[idx, 'low'] if label in ['X', 'B'] else self.data.loc[idx, 'high']
            else:
                price = self.data.loc[idx, 'high'] if label in ['X', 'B'] else self.data.loc[idx, 'low']
            info.append(f"{label}: {dt}\n    Price: {price:.4f}")
        info.append(f"AB/XA: {ab_xa:.2f}%\nBC/AB: {bc_ab:.2f}%\nCD/BC: {cd_min:.2f}% - {cd_max:.2f}%\nD range: {d_price_min:.4f} - {d_price_max:.4f}")
        self._show_info_box(info)
    
    def _plot_points_and_lines(self, points, color, is_bull, labels):
        for i in range(len(points)-1):
            self.ax.plot([points[i][0], points[i+1][0]], 
                        [points[i][1], points[i+1][1]], 
                        color=color, 
                        linewidth=2 if is_bull else 1,
                        linestyle='-' if is_bull else '--')
            
            self.ax.scatter(points[i][0], points[i][1], 
                           color=color, s=100, zorder=5)
        
        self.ax.scatter(points[-1][0], points[-1][1], 
                       color=color, s=100, zorder=5)
        
        for point, label in zip(points, labels):
            self.ax.annotate(label, 
                            (point[0], point[1]),
                            xytext=(10, 10),
                            textcoords='offset points',
                            color=color,
                            fontweight='bold')
    
    def next_pattern(self, event):
        if self.patterns:
            self.current_idx = (self.current_idx + 1) % len(self.patterns)
            self.plot_current_pattern()
    
    def previous_pattern(self, event):
        if self.patterns:
            self.current_idx = (self.current_idx - 1) % len(self.patterns)
            self.plot_current_pattern()
    
    def on_key_press(self, event):
        if event.key == 'right':
            self.next_pattern(event)
        elif event.key == 'left':
            self.previous_pattern(event)
        else:
            # Call the base class zoom functionality for other keys
            self.on_key_press_zoom(event, self.ax)

    def _get_color(self, pattern_name):
        """Return a color for the given pattern name, defaulting to black if not defined."""
        return PATTERN_COLORS.get(pattern_name, '#000000')

    def save_config(self, event):
        import tkinter as tk
        from tkinter import filedialog
        manual_extremums_serializable = [
            (timestamp.isoformat(), price, is_max) 
            for timestamp, price, is_max in self.manual_extremums
        ]
        removed_extremums_serializable = [
            (timestamp.isoformat(), price, is_max) 
            for timestamp, price, is_max in self.removed_extremums
        ]
        action_history_serializable = [
            (action, (timestamp.isoformat(), price, is_max)) 
            for action, (timestamp, price, is_max) in self.action_history
        ]
        config_data = {
            'manual_extremums': manual_extremums_serializable,
            'removed_extremums': removed_extremums_serializable,
            'action_history': action_history_serializable
        }
        # Use file dialog to ask for save location
        root = tk.Tk()
        root.withdraw()
        file_path = filedialog.asksaveasfilename(
            title="Save Extremum Config",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        root.destroy()
        if file_path:
            with open(file_path, 'w') as f:
                import json
                json.dump(config_data, f, indent=2)
            print(f"[OK] Manual extremums saved to '{file_path}'")
        else:
            print("Save cancelled.")

    def _show_info_box(self, info_lines):
        if self.info_text_box is not None:
            self.info_text_box.remove()
        self.info_text_box = self.fig.text(0.98, 0.98, '\n'.join(info_lines), ha='right', va='top', fontsize=9, bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

def save_patterns_to_csv(patterns, filename, data, pattern_type='ABCD'):
    """Save detected patterns to a CSV file."""
    if pattern_type == 'ABCD':
        df = pd.DataFrame([
            {
                'Pattern_Name': pattern_name,
                'Pattern_Type': 'Bullish' if 'bull' in pattern_name else 'Bearish',
                'Start_Date': ab_start,
                'Peak_Date': ab_end,
                'Trough_Date': bc_end,
                'End_Date': cd_end,
                'Retracement_Percentage': bc_retr,
                'Projection_Percentage': cd_proj,
                'Start_Price': data.loc[ab_start, 'low' if 'bull' in pattern_name else 'high'],
                'Peak_Price': data.loc[ab_end, 'high' if 'bull' in pattern_name else 'low'],
                'Trough_Price': data.loc[bc_end, 'low' if 'bull' in pattern_name else 'high'],
                'End_Price': data.loc[cd_end, 'high' if 'bull' in pattern_name else 'low']
            }
            for ab_start, ab_end, bc_end, cd_end, bc_retr, cd_proj, pattern_name in patterns
        ])
    elif pattern_type == 'XABCD':
        df = pd.DataFrame([
            {
                'Pattern_Name': pattern_name,
                'Pattern_Type': 'Bullish' if 'bull' in pattern_name else 'Bearish',
                'X_Date': x_point,
                'A_Date': a_point,
                'B_Date': b_point,
                'C_Date': c_point,
                'D_Date': d_point,
                'AB_XA_Ratio': ab_xa,
                'BC_AB_Ratio': bc_ab,
                'CD_BC_Ratio': cd_bc,
                'AD_XA_Ratio': ad_xa,
                'X_Price': data.loc[x_point, 'low' if 'bull' in pattern_name else 'high'],
                'A_Price': data.loc[a_point, 'high' if 'bull' in pattern_name else 'low'],
                'B_Price': data.loc[b_point, 'low' if 'bull' in pattern_name else 'high'],
                'C_Price': data.loc[c_point, 'high' if 'bull' in pattern_name else 'low'],
                'D_Price': data.loc[d_point, 'low' if 'bull' in pattern_name else 'high']
            }
            for x_point, a_point, b_point, c_point, d_point, ab_xa, bc_ab, cd_bc, ad_xa, pattern_name in patterns
        ])
    elif pattern_type == 'UnformedXABCD':
        df = pd.DataFrame([
            {
                'Pattern_Name': pattern_name,
                'Pattern_Type': 'Bullish' if 'bull' in pattern_name else 'Bearish',
                'X_Date': x_point,
                'A_Date': a_point,
                'B_Date': b_point,
                'C_Date': c_point,
                'AB_XA_Ratio': ab_xa,
                'BC_AB_Ratio': bc_ab,
                'CD_BC_Ratio_Min': cd_min,
                'CD_BC_Ratio_Max': cd_max,
                'Projected_D_Price_Min': d_price_min,
                'Projected_D_Price_Max': d_price_max,
                'X_Price': data.loc[x_point, 'low' if 'bull' in pattern_name else 'high'],
                'A_Price': data.loc[a_point, 'high' if 'bull' in pattern_name else 'low'],
                'B_Price': data.loc[b_point, 'low' if 'bull' in pattern_name else 'high'],
                'C_Price': data.loc[c_point, 'high' if 'bull' in pattern_name else 'low']
            }
            for x_point, a_point, b_point, c_point, ab_xa, bc_ab, cd_min, cd_max, d_price_min, d_price_max, pattern_name in patterns
        ])
    else:  # Unformed (ABCD)
        df = pd.DataFrame([
            {
                'Pattern_Name': pattern_name,
                'Pattern_Type': 'Bullish' if 'bull' in pattern_name else 'Bearish',
                'Start_Date': ab_start,
                'Peak_Date': ab_end,
                'Trough_Date': bc_end,
                'BC_Retracement': bc_retr,
                'CD_Projection_Min': cd_proj_min,
                'CD_Projection_Max': cd_proj_max,
                'Potential_D_Price_Min': d_price_min,
                'Potential_D_Price_Max': d_price_max,
                'Start_Price': data.loc[ab_start, 'low' if 'bull' in pattern_name else 'high'],
                'Peak_Price': data.loc[ab_end, 'high' if 'bull' in pattern_name else 'low'],
                'Trough_Price': data.loc[bc_end, 'low' if 'bull' in pattern_name else 'high']
            }
            for ab_start, ab_end, bc_end, bc_retr, cd_proj_min, cd_proj_max, d_price_min, d_price_max, pattern_name in patterns
        ])
    
    df.to_csv(filename, index=False)
    print(f"Patterns saved to '{filename}'")

class ExtremumDetectionPhase(InteractiveGraphBase):
    """Phase I: Load data, detect extremums, and visualize them."""
    
    def __init__(self):
        super().__init__()
        self.data = None
        self.filtered_data = None
        self.length = 1
        self.pivot_highs = None
        self.pivot_lows = None
        self.extremum_points = None
        self.fig = None
        self.ax = None
        self.stats_text = None
        
        # Date clipping controls
        self.start_date_input = None
        self.end_date_input = None
        
        # Pattern detection checkboxes
        self.pattern_checkboxes = None
        self.pattern_options = ['ABCD', 'XABCD', 'Unformed ABCD', 'Unformed XABCD']
        self.pattern_states = [True, True, True, True]  # All enabled by default
        
        # Default file path
        #self.default_file = 'grtusdt_1h.csv'
        self.default_file = 'btcusdt_1d.csv'
        self.current_file = None
        
        # Manual extremum editing
        self.manual_extremums = []  # List of manually added extremums (timestamp, price, is_max)
        self.removed_extremums = []  # List of removed extremums (timestamp, price, is_max)
        self.action_history = []  # History for undo functionality: ('add'/'remove', extremum_data)
        self.editing_mode = False  # Whether manual editing is enabled
        
        # Modifier key tracking for manual editing
        self.ctrl_pressed = False
        self.alt_pressed = False
        
    def setup_gui(self):
        """Setup the Phase I GUI with all controls organized on the right side."""
        self.fig = plt.figure(figsize=(16, 9))  # Reduced from 18x10 to fit monitors better
        plt.subplots_adjust(bottom=0.08, right=0.78, left=0.05, top=0.92)
        # Main chart area (takes up most of the screen)
        self.ax = self.fig.add_axes([0.05, 0.12, 0.70, 0.78])
        # === RIGHT SIDE CONTROL PANEL ===
        right_x = 0.79
        panel_width = 0.19
        # File Loading Section
        y_pos = 0.82
        self.fig.text(right_x, y_pos + 0.02, 'FILE', fontweight='bold', fontsize=10)
        self.ax_file = self.fig.add_axes([right_x, y_pos, panel_width, 0.035])
        self.btn_file = Button(self.ax_file, 'Load CSV')
        # Date Range Section
        y_pos = 0.72
        self.fig.text(right_x, y_pos + 0.04, 'DATE RANGE', fontweight='bold', fontsize=10)
        self.ax_start_date = self.fig.add_axes([right_x, y_pos + 0.01, panel_width * 0.47, 0.025])
        self.ax_end_date = self.fig.add_axes([right_x + panel_width * 0.53, y_pos + 0.01, panel_width * 0.47, 0.025])
        self.ax_clip_data = self.fig.add_axes([right_x, y_pos - 0.025, panel_width, 0.03])
        self.start_date_input = TextBox(self.ax_start_date, '', initial='2025-01-01')
        self.end_date_input = TextBox(self.ax_end_date, '', initial='2025-05-18')
        self.btn_clip_data = Button(self.ax_clip_data, 'Clip Data')
        # Extremum Detection Section
        y_pos = 0.60
        self.fig.text(right_x, y_pos + 0.04, 'EXTREMUMS', fontweight='bold', fontsize=10)
        self.ax_length = self.fig.add_axes([right_x, y_pos + 0.01, panel_width * 0.47, 0.025])
        self.ax_detect = self.fig.add_axes([right_x + panel_width * 0.53, y_pos + 0.01, panel_width * 0.47, 0.025])
        self.length_input = TextBox(self.ax_length, '', initial='1')
        self.btn_detect = Button(self.ax_detect, 'Detect')
        # Pattern Selection Section
        y_pos = 0.42
        self.fig.text(right_x, y_pos + 0.06, '☑️ PATTERNS', fontweight='bold', fontsize=10)
        self.ax_checkboxes = self.fig.add_axes([right_x, y_pos, panel_width, 0.12])
        self.pattern_checkboxes = CheckButtons(self.ax_checkboxes, self.pattern_options, self.pattern_states)
        for text in self.ax_checkboxes.texts:
            text.set_fontsize(8)
        # Start Detection Button
        y_pos = 0.32
        self.ax_proceed = self.fig.add_axes([right_x, y_pos, panel_width, 0.04])
        self.btn_proceed = Button(self.ax_proceed, 'Start Detection')
        # Manual Editing Section
        y_pos = 0.24
        self.fig.text(right_x, y_pos + 0.04, '✏️ MANUAL EDIT', fontweight='bold', fontsize=10)
        self.ax_add_mode = self.fig.add_axes([right_x, y_pos + 0.01, panel_width * 0.47, 0.025])
        self.ax_remove_mode = self.fig.add_axes([right_x + panel_width * 0.53, y_pos + 0.01, panel_width * 0.47, 0.025])
        self.btn_add_mode = Button(self.ax_add_mode, 'Add Extremum', color='lightgray')
        self.btn_remove_mode = Button(self.ax_remove_mode, 'Remove Extremum', color='lightgray')
        self.add_mode = False
        self.remove_mode = False
        self.btn_add_mode.on_clicked(self.toggle_add_mode)
        self.btn_remove_mode.on_clicked(self.toggle_remove_mode)
        # Undo/Reset buttons
        y_pos = 0.18
        self.ax_undo = self.fig.add_axes([right_x, y_pos + 0.01, panel_width * 0.47, 0.025])
        self.ax_reset_manual = self.fig.add_axes([right_x + panel_width * 0.53, y_pos + 0.01, panel_width * 0.47, 0.025])
        self.btn_undo = Button(self.ax_undo, 'Undo')
        self.btn_reset_manual = Button(self.ax_reset_manual, 'Reset')
        # Save/Load Extremums buttons
        y_pos = 0.13
        self.ax_save_extremums = self.fig.add_axes([right_x, y_pos + 0.01, panel_width * 0.47, 0.025])
        self.ax_load_extremums = self.fig.add_axes([right_x + panel_width * 0.53, y_pos + 0.01, panel_width * 0.47, 0.025])
        self.btn_save_extremums = Button(self.ax_save_extremums, 'Save Extremums')
        self.btn_load_extremums = Button(self.ax_load_extremums, 'Load Extremums')
        # Statistics Display (more compact)
        y_pos = 0.26
        self.fig.text(right_x, y_pos + 0.01, 'STATS', fontweight='bold', fontsize=10)
        self.stats_text = self.fig.text(right_x, y_pos - 0.01, '', ha='left', va='top', fontsize=7,
                                       bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.8))
        # Instructions (more compact)
        instructions = """CONTROLS:\n- Wheel: Zoom | Right+drag: Pan\n- Left+drag on axes: Axis zoom\n- Keys: h=help, r=reset, x/y/z=zoom"""
        self.fig.text(right_x, 0.08, instructions, ha='left', va='top', fontsize=7,
                     bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.7))
        # Connect button events
        self.btn_file.on_clicked(self.load_file)
        self.btn_clip_data.on_clicked(self.clip_data)
        self.btn_detect.on_clicked(self.detect_extremums)
        self.btn_proceed.on_clicked(self.proceed_to_phase2)
        self.btn_undo.on_clicked(self.undo_action)
        self.btn_reset_manual.on_clicked(self.reset_manual_data)
        self.btn_save_extremums.on_clicked(self.save_extremums_to_csv)
        self.btn_load_extremums.on_clicked(self.load_extremums_from_csv)
        # Initially disable buttons (progressive workflow)
        self.btn_clip_data.ax.set_visible(False)
        self.btn_detect.ax.set_visible(False)
        self.btn_proceed.ax.set_visible(False)
        plt.suptitle('Phase I: Data Loading, Clipping, and Extremum Detection', fontsize=12, fontweight='bold')
    
    def update_statistics(self):
        """Update the statistics display."""
        if self.filtered_data is None:
            self.stats_text.set_text("No data loaded")
            return
            
        # Calculate data reduction
        original_count = len(self.data) if self.data is not None else 0
        filtered_count = len(self.filtered_data)
        reduction_pct = ((original_count - filtered_count) / original_count * 100) if original_count > 0 else 0
        
        if self.extremum_points is None:
            stats_str = f"""File: {self.current_file.split('/')[-1] if self.current_file else 'None'}

Data: {original_count:,} -> {filtered_count:,} ({reduction_pct:.1f}% reduction)

Range: {self.filtered_data.index.min().strftime('%m/%d')} to {self.filtered_data.index.max().strftime('%m/%d')}

Status: Ready for extremum detection"""
        else:
            # Count automatic extremums (excluding removed ones)
            auto_extremums = [e for e in self.extremum_points if e not in self.removed_extremums]
            auto_high_count = sum(1 for _, _, is_max in auto_extremums if is_max)
            auto_low_count = sum(1 for _, _, is_max in auto_extremums if not is_max)
            
            # Count manual extremums
            manual_high_count = sum(1 for _, _, is_max in self.manual_extremums if is_max)
            manual_low_count = sum(1 for _, _, is_max in self.manual_extremums if not is_max)
            
            # Count removed extremums
            removed_high_count = sum(1 for _, _, is_max in self.removed_extremums if is_max)
            removed_low_count = sum(1 for _, _, is_max in self.removed_extremums if not is_max)
            
            # Total counts (final extremums for detection)
            total_high = auto_high_count + manual_high_count
            total_low = auto_low_count + manual_low_count
            total_count = total_high + total_low
            
            # Get selected pattern types (shortened names)
            selected_patterns = []
            checkbox_states = self.pattern_checkboxes.get_status()
            if checkbox_states[0]: selected_patterns.append('ABCD')
            if checkbox_states[1]: selected_patterns.append('XABCD')
            if checkbox_states[2]: selected_patterns.append('Unf-ABCD')
            if checkbox_states[3]: selected_patterns.append('Unf-XABCD')
            
            # Manual editing status
            manual_status = ""
            if self.manual_extremums or self.removed_extremums:
                manual_status = f"\n📝 Manual: +{len(self.manual_extremums)} -{len(self.removed_extremums)}"
                if self.action_history:
                    manual_status += f" | Undo: {len(self.action_history)}"
            
            stats_str = f"""File: {self.current_file.split('/')[-1] if self.current_file else 'None'}

Data: {original_count:,} -> {filtered_count:,} ({reduction_pct:.1f}% reduction)

Final Extremums (L={self.length}): {total_count} total
  Highs: {total_high} | Lows: {total_low}

Breakdown:
  Auto: {auto_high_count}H {auto_low_count}L | Manual: {manual_high_count}H {manual_low_count}L
  Removed: {removed_high_count}H {removed_low_count}L{manual_status}

Patterns: {', '.join(selected_patterns)}

Status: Ready for pattern detection"""
        
        self.stats_text.set_text(stats_str)
    
    def load_file(self, event):
        """Load CSV file with file selection dialog."""
        try:
            # Create a temporary root window for the file dialog
            root = tk.Tk()
            root.withdraw()  # Hide the root window
            
            # Show file dialog with default file pre-selected
            file_path = filedialog.askopenfilename(
                title="Select CSV file",
                initialfile=self.default_file,
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
            )
            
            root.destroy()  # Clean up the root window
            
            # If no file selected, use default
            if not file_path:
                file_path = self.default_file
                print(f"No file selected, using default: {file_path}")
            
            self.current_file = file_path
            
            # Load the data
            self.data = pd.read_csv(file_path)
            self.data['time'] = pd.to_datetime(self.data['time'])
            self.data.set_index('time', inplace=True)
            
            # Ensure timezone-naive for consistent comparison
            if self.data.index.tz is not None:
                self.data.index = self.data.index.tz_localize(None)
            
            print(f"Loaded data from: {file_path}")
            print(f"Total rows: {len(self.data)}")
            print(f"Date range: {self.data.index.min()} to {self.data.index.max()}")
            
            # Show full dataset initially
            self.filtered_data = self.data.copy()
            self.plot_basic_chart()
            self.update_statistics()
            
            # Enable clip data button
            self.btn_clip_data.ax.set_visible(True)
            self.fig.canvas.draw()
            
        except Exception as e:
            print(f"Error loading file: {str(e)}")
            # Try to load default file as fallback
            try:
                self.current_file = self.default_file
                self.data = pd.read_csv(self.default_file)
                self.data['time'] = pd.to_datetime(self.data['time'])
                self.data.set_index('time', inplace=True)
                
                # Ensure timezone-naive
                if self.data.index.tz is not None:
                    self.data.index = self.data.index.tz_localize(None)
                    
                print(f"Loaded default file: {self.default_file}")
                self.filtered_data = self.data.copy()
                self.plot_basic_chart()
                self.update_statistics()
                self.btn_clip_data.ax.set_visible(True)
                self.fig.canvas.draw()
            except Exception as e2:
                print(f"Error loading default file: {str(e2)}")
    
    def clip_data(self, event):
        """Clip data based on date range inputs."""
        if self.data is None:
            print("No data loaded!")
            return
            
        try:
            start_date = self.start_date_input.text.strip()
            end_date = self.end_date_input.text.strip()
            
            print(f"Clipping data from '{start_date}' to '{end_date}'")
            
            # Parse dates and ensure they are timezone-naive
            if start_date:
                start_dt = pd.to_datetime(start_date)
                if start_dt.tz is not None:
                    start_dt = start_dt.tz_localize(None)
            else:
                start_dt = self.data.index.min()
                
            if end_date:
                end_dt = pd.to_datetime(end_date)
                if end_dt.tz is not None:
                    end_dt = end_dt.tz_localize(None)
            else:
                end_dt = self.data.index.max()
            
            # Ensure start is before end
            if start_dt >= end_dt:
                print("Error: Start date must be before end date!")
                return
            
            # Clip the data
            print(f"Filtering data between {start_dt} and {end_dt}")
            self.filtered_data = self.data.loc[start_dt:end_dt].copy()
            
            if len(self.filtered_data) == 0:
                print("Warning: No data in the specified date range!")
                print(f"Available data range: {self.data.index.min()} to {self.data.index.max()}")
                return
            
            print(f"[OK] Data clipped successfully!")
            print(f"  Rows: {len(self.data)} -> {len(self.filtered_data)}")
            print(f"  Date range: {self.filtered_data.index.min()} to {self.filtered_data.index.max()}")
            
            # Update the chart with clipped data
            self.plot_basic_chart()
            self.update_statistics()
            
            # Reset extremum detection (since data changed)
            self.extremum_points = None
            self.btn_proceed.ax.set_visible(False)
            
            # Enable detect button
            self.btn_detect.ax.set_visible(True)
            self.fig.canvas.draw()
            
        except Exception as e:
            print(f"Error clipping data: {str(e)}")
            print("Please check your date format (YYYY-MM-DD)")
            import traceback
            traceback.print_exc()
        
    def detect_extremums(self, event):
        """Detect extremums based on current length setting."""
        if self.filtered_data is None:
            print("No data loaded!")
            return
            
        try:
            # Get length from input
            length_str = self.length_input.text.strip()
            self.length = int(length_str) if length_str else 1
            if self.length < 1:
                self.length = 1
                
            print(f"Detecting extremums with length={self.length}")
            
            # Compute pivot points
            self.pivot_highs = pivot_high(self.filtered_data['high'], self.length)
            self.pivot_lows = pivot_low(self.filtered_data['low'], self.length)
            
            # Create extremum points list for Phase II
            self.extremum_points = []
            
            # Add pivot highs
            for idx, price in self.pivot_highs.dropna().items():
                self.extremum_points.append((idx, price, True))  # True = is_maximum
                
            # Add pivot lows  
            for idx, price in self.pivot_lows.dropna().items():
                self.extremum_points.append((idx, price, False))  # False = is_minimum
            
            # Sort by timestamp
            self.extremum_points.sort(key=lambda x: x[0])
            
            print(f"[OK] Found {len(self.extremum_points)} extremum points")
            
            # Plot chart with extremums
            self.plot_chart_with_extremums()
            
            # Update statistics
            self.update_statistics()
            
            # Enable proceed button
            self.btn_proceed.ax.set_visible(True)
            self.fig.canvas.draw()
            
        except ValueError:
            print("Invalid length value! Please enter a positive integer.")
        except Exception as e:
            print(f"Error detecting extremums: {str(e)}")
    
    def plot_basic_chart(self):
        """Plot basic candlestick chart."""
        self.ax.clear()
        
        # Setup interactive features
        self.setup_interactive_features(self.fig, self.ax, self.filtered_data)
        
        # Plot candlesticks using mplfinance
        plot_data = self.filtered_data.copy()
        plot_data.index = pd.to_datetime(plot_data.index)
        
        mpf.plot(plot_data, 
                 type='candle',
                 style='charles',
                 ax=self.ax,
                 volume=False,
                 datetime_format='%Y-%m-%d',
                 xrotation=45)
        
        # Fix x-axis limits to match the clipped data range
        self.ax.set_xlim(-0.5, len(self.filtered_data) - 0.5)
        
        # Update the original limits for interactive features
        self.original_xlim = self.ax.get_xlim()
        self.original_ylim = self.ax.get_ylim()
        
        self.ax.set_title(f'Data: {len(self.filtered_data)} candles | '
                         f'{self.filtered_data.index.min().strftime("%Y-%m-%d")} to {self.filtered_data.index.max().strftime("%Y-%m-%d")}',
                         fontsize=12, pad=10)
        self.fig.canvas.draw()
    
    def plot_chart_with_extremums(self):
        """Plot candlestick chart with detected extremums."""
        self.ax.clear()
        
        # Setup interactive features
        self.setup_interactive_features(self.fig, self.ax, self.filtered_data)
        
        # Plot candlesticks
        plot_data = self.filtered_data.copy()
        plot_data.index = pd.to_datetime(plot_data.index)
        
        mpf.plot(plot_data, 
                 type='candle',
                 style='charles',
                 ax=self.ax,
                 volume=False,
                 datetime_format='%Y-%m-%d',
                 xrotation=45)
        
        # Fix x-axis limits to match the clipped data range
        self.ax.set_xlim(-0.5, len(self.filtered_data) - 0.5)
        
        # Combine automatic and manual extremums, excluding removed ones
        all_extremums = []
        if self.extremum_points:
            for extremum in self.extremum_points:
                if extremum not in self.removed_extremums:
                    all_extremums.append(extremum)
        all_extremums.extend(self.manual_extremums)
        
        # Plot extremums
        high_count = 0
        low_count = 0
        manual_high_count = 0
        manual_low_count = 0
        
        for timestamp, price, is_max in all_extremums:
            try:
                # Only plot if timestamp is in filtered_data.index
                if timestamp not in self.filtered_data.index:
                    continue
                x_pos = self.filtered_data.index.get_loc(timestamp)
                is_manual = (timestamp, price, is_max) in self.manual_extremums
                if is_max:
                    color = 'orange' if is_manual else 'red'
                    marker = '^'
                    size = 80 if is_manual else 60
                    if is_manual:
                        manual_high_count += 1
                    else:
                        high_count += 1
                else:
                    color = 'blue' if is_manual else 'green'
                    marker = 'v'
                    size = 80 if is_manual else 60
                    if is_manual:
                        manual_low_count += 1
                    else:
                        low_count += 1
                self.ax.scatter(x_pos, price, color=color, marker=marker, s=size, zorder=5, alpha=0.8)
            except Exception:
                continue
        
        # Update the original limits for interactive features
        self.original_xlim = self.ax.get_xlim()
        self.original_ylim = self.ax.get_ylim()
        
        # Create title with counts
        title_parts = []
        if high_count > 0 or low_count > 0:
            title_parts.append(f'Auto: {high_count}H, {low_count}L')
        if manual_high_count > 0 or manual_low_count > 0:
            title_parts.append(f'Manual: {manual_high_count}H, {manual_low_count}L')
        title_joined = ' | '.join(title_parts)
        title = f'Extremums (L={self.length}) - {title_joined} | {self.filtered_data.index.min().strftime("%Y-%m-%d")} to {self.filtered_data.index.max().strftime("%Y-%m-%d")}'
        self.ax.set_title(title, fontsize=11, pad=10)
        
        # Connect mouse/key events for manual editing
        self.fig.canvas.mpl_connect('button_press_event', self.on_manual_edit_click)
        self.fig.canvas.mpl_connect('key_press_event', self.on_key_press_manual)
        self.fig.canvas.mpl_connect('key_release_event', self.on_key_release_manual)
        
        # Add text to inform user about manual editing
        mode_str = 'Add Mode: Click to add extremum' if self.add_mode else ('Remove Mode: Click to remove extremum' if self.remove_mode else 'Manual Edit: Select a mode')
        self.ax.text(0.02, 0.98, mode_str, 
                    transform=self.ax.transAxes, fontsize=8, 
                    bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.7),
                    verticalalignment='top')
        
        print("[OK] Manual editing enabled: Ctrl+Click to add, Alt+Click to remove extremums")
        self.fig.canvas.draw()
    
    def proceed_to_phase2(self, event):
        """Close Phase I and proceed to Phase II."""
        if self.extremum_points is None:
            print("No extremums detected!")
            return
        # Combine automatic and manual extremums, excluding removed ones
        final_extremums = []
        if self.extremum_points:
            for extremum in self.extremum_points:
                if extremum not in self.removed_extremums:
                    final_extremums.append(extremum)
        final_extremums.extend(self.manual_extremums)
        final_extremums.sort(key=lambda x: x[0])
        if not final_extremums:
            print("No extremums available for pattern detection!")
            return
        # Get selected pattern types
        selected_patterns = {}
        checkbox_states = self.pattern_checkboxes.get_status()
        selected_patterns['abcd'] = checkbox_states[0]
        selected_patterns['xabcd'] = checkbox_states[1]
        selected_patterns['unformed_abcd'] = checkbox_states[2]
        selected_patterns['unformed_xabcd'] = checkbox_states[3]
        if not any(selected_patterns.values()):
            print("No pattern types selected!")
            return
        print(f"Proceeding to Phase II with {len(final_extremums)} extremums")
        print(f"  Automatic: {len([e for e in self.extremum_points if e not in self.removed_extremums])}")
        print(f"  Manual: {len(self.manual_extremums)}")
        print(f"  Removed: {len(self.removed_extremums)}")
        print(f"Selected patterns: {[k for k, v in selected_patterns.items() if v]}")
        plt.close(self.fig)
        # Launch Phase II with combined extremums
        phase2 = PatternDetectionPhase(self.filtered_data, final_extremums, selected_patterns)
        phase2.run_detection()

    def on_manual_edit_click(self, event):
        """Handle manual editing click events."""
        if event.inaxes != self.ax:
            return
        x, y = event.xdata, event.ydata
        if x is None or y is None:
            return
        x_idx = int(round(x))
        if x_idx < 0 or x_idx >= len(self.filtered_data):
            return
        timestamp = self.filtered_data.index[x_idx]
        if event.button == 1:  # Left mouse button
            if self.add_mode:
                # Add extremum (auto high/low)
                high_price = self.filtered_data.iloc[x_idx]['high']
                low_price = self.filtered_data.iloc[x_idx]['low']
                is_high = abs(y - high_price) < abs(y - low_price)
                actual_price = high_price if is_high else low_price
                self._add_manual_extremum(timestamp, actual_price, is_high)
            elif self.remove_mode:
                # Remove closest extremum
                self._remove_closest_extremum(x, y)

    def on_key_press_manual(self, event):
        if event.key == 'ctrl':
            self.ctrl_pressed = True
        elif event.key == 'alt':
            self.alt_pressed = True
    def on_key_release_manual(self, event):
        if event.key == 'ctrl':
            self.ctrl_pressed = False
        elif event.key == 'alt':
            self.alt_pressed = False
    def undo_action(self, event):
        self._undo_last_action()
    def reset_manual_data(self, event):
        self._reset_manual_edits()
    def toggle_add_mode(self, event):
        self.add_mode = not self.add_mode
        self.btn_add_mode.color = 'lightgreen' if self.add_mode else 'lightgray'
    def toggle_remove_mode(self, event):
        self.remove_mode = not self.remove_mode
        self.btn_remove_mode.color = 'lightgreen' if self.remove_mode else 'lightgray'

    def _add_manual_extremum(self, timestamp, price, is_high):
        new_extremum = (timestamp, price, is_high)
        if new_extremum not in self.manual_extremums and new_extremum not in self.extremum_points:
            self.manual_extremums.append(new_extremum)
            self.action_history.append(('add', new_extremum))
            print(f"[OK] Added {'high' if is_high else 'low'} extremum at {timestamp.strftime('%Y-%m-%d %H:%M')} = {price:.4f}")
            self.plot_chart_with_extremums()
            self.update_statistics()
        else:
            print(f"⚠ Extremum already exists at {timestamp.strftime('%Y-%m-%d %H:%M')}")
    def _remove_closest_extremum(self, x, y):
        closest_extremum = None
        min_distance = float('inf')
        all_extremums = [e for e in self.extremum_points if e not in self.removed_extremums] + self.manual_extremums
        for extremum in all_extremums:
            ext_timestamp, ext_price, ext_is_max = extremum
            try:
                ext_x = self.filtered_data.index.get_loc(ext_timestamp)
                distance = ((x - ext_x) ** 2 + ((y - ext_price) / ext_price * 100) ** 2) ** 0.5
                if distance < min_distance:
                    min_distance = distance
                    closest_extremum = extremum
            except KeyError:
                continue
        if closest_extremum and min_distance < 5:
            ext_timestamp, ext_price, ext_is_max = closest_extremum
            if closest_extremum in self.manual_extremums:
                self.manual_extremums.remove(closest_extremum)
                self.action_history.append(('remove_manual', closest_extremum))
                print(f"[OK] Removed manual {'high' if ext_is_max else 'low'} extremum at {ext_timestamp.strftime('%Y-%m-%d %H:%M')}")
            elif closest_extremum in self.extremum_points:
                self.removed_extremums.append(closest_extremum)
                self.action_history.append(('remove_auto', closest_extremum))
                print(f"[OK] Removed automatic {'high' if ext_is_max else 'low'} extremum at {ext_timestamp.strftime('%Y-%m-%d %H:%M')}")
            self.plot_chart_with_extremums()
            self.update_statistics()
        else:
            print("⚠ No extremum found near click location")
    def _undo_last_action(self):
        if not self.action_history:
            print("⚠ No actions to undo")
            return
        action, data = self.action_history.pop()
        if action == 'add':
            if data in self.manual_extremums:
                self.manual_extremums.remove(data)
                print(f"[OK] Undid manual addition of {'high' if data[2] else 'low'} extremum")
        elif action == 'remove_manual':
            self.manual_extremums.append(data)
            print(f"[OK] Undid removal of manual {'high' if data[2] else 'low'} extremum")
        elif action == 'remove_auto':
            if data in self.removed_extremums:
                self.removed_extremums.remove(data)
                print(f"[OK] Undid removal of automatic {'high' if data[2] else 'low'} extremum")
        self.plot_chart_with_extremums()
        self.update_statistics()
    def _reset_manual_edits(self):
        self.manual_extremums = []
        self.removed_extremums = []
        self.action_history = []
        self.editing_mode = False
        print("[OK] Reset all manual edits - back to automatic extremums only")
        self.plot_chart_with_extremums()
        self.update_statistics()

    def save_extremums_to_csv(self, event):
        """Save current extremum points (auto+manual, minus removed) to a CSV file."""
        import tkinter as tk
        from tkinter import filedialog
        import pandas as pd
        # Combine extremums (auto + manual, minus removed)
        all_extremums = [e for e in (self.extremum_points or []) if e not in self.removed_extremums]
        all_extremums.extend(self.manual_extremums)
        if not all_extremums:
            print("No extremums to save!")
            return
        # Prepare DataFrame
        df = pd.DataFrame([
            {'timestamp': ts.isoformat(), 'price': price, 'is_max': is_max}
            for ts, price, is_max in all_extremums
        ])
        # File dialog
        root = tk.Tk()
        root.withdraw()
        file_path = filedialog.asksaveasfilename(
            title="Save Extremums CSV",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        root.destroy()
        if file_path:
            df.to_csv(file_path, index=False)
            print(f"[OK] Extremums saved to '{file_path}'")
        else:
            print("Save cancelled.")

    def load_extremums_from_csv(self, event):
        """Load extremum points from a CSV file and use as current extremums."""
        import tkinter as tk
        from tkinter import filedialog
        import pandas as pd
        import numpy as np
        root = tk.Tk()
        root.withdraw()
        file_path = filedialog.askopenfilename(
            title="Load Extremums CSV",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        root.destroy()
        if not file_path:
            print("Load cancelled.")
            return
        try:
            df = pd.read_csv(file_path)
            # Parse and validate
            extremums = []
            for _, row in df.iterrows():
                try:
                    ts = pd.to_datetime(row['timestamp'])
                    price = float(row['price'])
                    is_max = bool(row['is_max'])
                    extremums.append((ts, price, is_max))
                except Exception as e:
                    print(f"Skipping row due to error: {e}")
            if not extremums:
                print("No valid extremums loaded from file!")
                return
            # Replace current extremums
            self.manual_extremums = []
            self.removed_extremums = []
            self.action_history = []
            self.extremum_points = extremums.copy()
            print(f"[OK] Loaded {len(extremums)} extremums from '{file_path}'")
            self.plot_chart_with_extremums()
            self.update_statistics()
            self.fig.canvas.draw()
        except Exception as e:
            print(f"Error loading extremums: {e}")

class PatternDetectionPhase:
    """Phase II: Run pattern detection using extremums from Phase I."""
    
    def __init__(self, data, extremum_points, selected_patterns=None):
        self.data = data
        self.extremum_points = extremum_points
        self.detector = None
        
        # Default to all patterns if none specified
        if selected_patterns is None:
            selected_patterns = {
                'abcd': True,
                'xabcd': True,
                'unformed_abcd': True,
                'unformed_xabcd': True
            }
        self.selected_patterns = selected_patterns
        
    def run_detection(self):
        """Run selected pattern detection algorithms and display results."""
        print("\n" + "="*50)
        print("PHASE II: PATTERN DETECTION")
        print("="*50)
        
        # Initialize pattern detector with extremum points
        self.detector = PatternDetector(self.data, self.extremum_points)
        
        # Initialize pattern containers
        abcd_patterns = []
        xabcd_patterns = []
        unformed_patterns = []
        unformed_xabcd_patterns = []
        
        # Find patterns with timing measurements
        print("\nTiming Pattern Detection:")
        print("-" * 30)
        
        # Time AB=CD patterns
        if self.selected_patterns['abcd']:
            start_time = time.time()
            abcd_patterns = self.detector.find_abcd_patterns()
            abcd_time = time.time() - start_time
            print(f"AB=CD patterns: {len(abcd_patterns)} patterns found in {abcd_time:.2f} seconds")
        else:
            print("AB=CD patterns: SKIPPED")
        
        # Time XABCD patterns
        if self.selected_patterns['xabcd']:
            start_time = time.time()
            xabcd_patterns = self.detector.find_xabcd_patterns()
            xabcd_time = time.time() - start_time
            print(f"XABCD patterns: {len(xabcd_patterns)} patterns found in {xabcd_time:.2f} seconds")
        else:
            print("XABCD patterns: SKIPPED")
        
        # Time unformed patterns
        if self.selected_patterns['unformed_abcd']:
            start_time = time.time()
            unformed_patterns = self.detector.find_unformed_patterns()
            unformed_time = time.time() - start_time
            print(f"Unformed patterns: {len(unformed_patterns)} patterns found in {unformed_time:.2f} seconds")
        else:
            print("Unformed patterns: SKIPPED")

        # Time unformed XABCD patterns
        if self.selected_patterns['unformed_xabcd']:
            start_time = time.time()
            unformed_xabcd_patterns = self.detector.find_unformed_xabcd_patterns()
            unformed_xabcd_time = time.time() - start_time
            print(f"Unformed XABCD patterns: {len(unformed_xabcd_patterns)} patterns found in {unformed_xabcd_time:.2f} seconds")
        else:
            print("Unformed XABCD patterns: SKIPPED")
        
        print("-" * 30)
        total_time = sum([
            abcd_time if self.selected_patterns['abcd'] else 0,
            xabcd_time if self.selected_patterns['xabcd'] else 0,
            unformed_time if self.selected_patterns['unformed_abcd'] else 0,
            unformed_xabcd_time if self.selected_patterns['unformed_xabcd'] else 0
        ])
        print(f"Total detection time: {total_time:.2f} seconds")
        print("-" * 30)
        
        # Save patterns to CSV (only for selected pattern types)
        if self.selected_patterns['abcd'] and abcd_patterns:
            save_patterns_to_csv(abcd_patterns, 'detected_patterns.csv', self.data, 'ABCD')
        if self.selected_patterns['xabcd'] and xabcd_patterns:
            save_patterns_to_csv(xabcd_patterns, 'detected_xabcd_patterns.csv', self.data, 'XABCD')
        if self.selected_patterns['unformed_abcd'] and unformed_patterns:
            save_patterns_to_csv(unformed_patterns, 'unformed_patterns.csv', self.data, 'Unformed')
        if self.selected_patterns['unformed_xabcd'] and unformed_xabcd_patterns:
            save_patterns_to_csv(unformed_xabcd_patterns, 'unformed_xabcd_patterns.csv', self.data, 'UnformedXABCD')
        
        # Create and show pattern viewers
        self.show_pattern_viewers(abcd_patterns, xabcd_patterns, unformed_patterns, unformed_xabcd_patterns)
    
    def show_pattern_viewers(self, abcd_patterns, xabcd_patterns, unformed_patterns, unformed_xabcd_patterns):
        """Display all pattern viewers sequentially."""
        if self.selected_patterns['abcd']:
            print("\nDisplaying AB=CD patterns...")
            if abcd_patterns:
                abcd_viewer = PatternViewer(self.data, abcd_patterns, 'ABCD')
                plt.show()
            else:
                print("No AB=CD patterns found.")
        
        if self.selected_patterns['xabcd']:
            print("\nDisplaying XABCD patterns...")
            if xabcd_patterns:
                xabcd_viewer = PatternViewer(self.data, xabcd_patterns, 'XABCD')
                plt.show()
            else:
                print("No XABCD patterns found.")
        
        if self.selected_patterns['unformed_abcd']:
            print("\nDisplaying unformed patterns...")
            if unformed_patterns:
                unformed_viewer = PatternViewer(self.data, unformed_patterns, 'Unformed')
                plt.show()
            else:
                print("No unformed patterns found.")

        if self.selected_patterns['unformed_xabcd']:
            print("\nDisplaying unformed XABCD patterns...")
            patterns_to_view = unformed_xabcd_patterns[:100] if len(unformed_xabcd_patterns) > 100 else unformed_xabcd_patterns
            if patterns_to_view:
                unformed_xabcd_viewer = PatternViewer(self.data, patterns_to_view, 'UnformedXABCD')
                plt.show()
            else:
                print("No unformed XABCD patterns found.")

        # Display extremum statistics
        high_count = sum(1 for _, _, is_max in self.extremum_points if is_max)
        low_count = sum(1 for _, _, is_max in self.extremum_points if not is_max)
        total_count = len(self.extremum_points)
        print(f"\n[INFO] Using {total_count} extremums for pattern detection:")
        print(f"   Highs: {high_count}")
        print(f"   Lows: {low_count}")
        print(f"   Date range: {self.extremum_points[0][0].strftime('%Y-%m-%d')} to {self.extremum_points[-1][0].strftime('%Y-%m-%d')}")

def main():
    """Main function - Launch Phase I for extremum detection."""
    print("="*60)
    print("HARMONIC PATTERN DETECTION SYSTEM")
    print("="*60)
    print("Phase I: Load data and detect extremums")
    print("Phase II: Detect harmonic patterns")
    print("="*60)
    
    # Launch Phase I
    phase1 = ExtremumDetectionPhase()
    phase1.setup_gui()
    plt.show()

if __name__ == "__main__":
    main()

#final