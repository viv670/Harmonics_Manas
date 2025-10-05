"""
Visualize Harmonic Patterns from Excel Backtest Results
Creates visual charts showing pattern structure and Fibonacci levels
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import Rectangle
import numpy as np
import sys
import os


def visualize_pattern_with_fibonacci(pattern_details_row, fibonacci_rows, test_data):
    """
    Create a visual representation of a single pattern with Fibonacci levels

    Args:
        pattern_details_row: Row from Pattern Details sheet
        fibonacci_rows: All rows from Fibonacci Analysis for this pattern
        test_data: Original OHLC data
    """
    fig, ax = plt.subplots(figsize=(14, 8))

    # Extract pattern info
    pattern_id = pattern_details_row.get('Pattern_ID', 'Unknown')
    pattern_type = pattern_details_row.get('Type', 'Unknown')
    pattern_subtype = pattern_details_row.get('Subtype', 'Unknown')
    status = pattern_details_row.get('Status', 'Unknown')

    # Title
    title = f"{pattern_type} - {pattern_subtype} (ID: {pattern_id})\nStatus: {status}"
    ax.set_title(title, fontsize=14, fontweight='bold')

    # Extract points
    points = {}
    point_labels = ['X', 'A', 'B', 'C', 'D']

    for point_label in point_labels:
        bar_col = f'{point_label}_Bar'
        price_col = f'{point_label}_Price'

        if bar_col in pattern_details_row and price_col in pattern_details_row:
            bar = pattern_details_row[bar_col]
            price = pattern_details_row[price_col]

            # Check if values exist and are not 'N/A'
            if bar != '' and bar != 'N/A' and price != '' and price != 'N/A':
                try:
                    points[point_label] = (int(bar), float(price))
                except:
                    pass

    if not points:
        print(f"No valid points found for pattern {pattern_id}")
        plt.close()
        return None

    # Get bar range for chart
    all_bars = [p[0] for p in points.values()]
    min_bar = min(all_bars) - 10
    max_bar = max(all_bars) + 50  # Extra space for Fib levels

    # Plot price data
    chart_data = test_data.iloc[min_bar:max_bar]
    bars = range(len(chart_data))
    bar_indices = list(range(min_bar, max_bar))

    # Plot candlestick-style price action
    for i, (idx, row) in enumerate(chart_data.iterrows()):
        color = 'green' if row['Close'] >= row['Open'] else 'red'
        ax.plot([i, i], [row['Low'], row['High']], color='gray', linewidth=0.5, alpha=0.5)
        ax.plot([i, i], [row['Open'], row['Close']], color=color, linewidth=2, alpha=0.7)

    # Plot pattern structure (connecting lines)
    point_order = []
    if 'X' in points:
        point_order = ['X', 'A', 'B', 'C']
    else:
        point_order = ['A', 'B', 'C']

    if 'D' in points:
        point_order.append('D')

    for i in range(len(point_order) - 1):
        p1_label = point_order[i]
        p2_label = point_order[i + 1]

        if p1_label in points and p2_label in points:
            p1_bar, p1_price = points[p1_label]
            p2_bar, p2_price = points[p2_label]

            # Convert to chart coordinates
            x1 = p1_bar - min_bar
            x2 = p2_bar - min_bar

            ax.plot([x1, x2], [p1_price, p2_price], 'b-', linewidth=2, alpha=0.7)

    # Plot pattern points
    colors = {'X': 'purple', 'A': 'red', 'B': 'blue', 'C': 'green', 'D': 'orange'}
    for label, (bar, price) in points.items():
        x = bar - min_bar
        ax.scatter(x, price, s=200, c=colors.get(label, 'black'),
                  marker='o', edgecolors='black', linewidths=2, zorder=5)
        ax.text(x, price, f'  {label}', fontsize=12, fontweight='bold',
               verticalalignment='center')

    # Plot PRZ Zone
    prz_zone = pattern_details_row.get('PRZ_Zone', '')
    if prz_zone and prz_zone != '':
        try:
            prz_parts = prz_zone.split(' - ')
            if len(prz_parts) == 2:
                prz_min = float(prz_parts[0])
                prz_max = float(prz_parts[1])

                # Draw PRZ rectangle
                rect = Rectangle((0, prz_min), len(bars)-1, prz_max - prz_min,
                               alpha=0.2, facecolor='yellow', edgecolor='orange',
                               linewidth=2, linestyle='--', label='PRZ Zone')
                ax.add_patch(rect)
        except:
            pass

    # Plot Fibonacci Levels
    if fibonacci_rows is not None and len(fibonacci_rows) > 0:
        # Sort by level value for better visualization
        fib_sorted = sorted(fibonacci_rows,
                          key=lambda x: float(x.get('Level_Price', 0)))

        for fib_row in fib_sorted:
            level_name = fib_row.get('Level_Name', '')
            level_price = fib_row.get('Level_Price', '')
            touch_count = fib_row.get('Touch_Count', 0)
            first_touch_bar = fib_row.get('First_Touch_Bar', '')

            if level_price and level_price != '':
                try:
                    price = float(level_price)

                    # Determine line style based on touch count
                    if touch_count > 0:
                        linestyle = '-'
                        linewidth = 1.5
                        alpha = 0.8
                        color = 'darkgreen'
                    else:
                        linestyle = '--'
                        linewidth = 1
                        alpha = 0.4
                        color = 'gray'

                    # Draw Fibonacci level line
                    ax.axhline(y=price, color=color, linestyle=linestyle,
                             linewidth=linewidth, alpha=alpha)

                    # Add label
                    label_text = f"{level_name} ({price:.2f})"
                    if touch_count > 0:
                        label_text += f" [{touch_count}x]"

                    ax.text(len(bars) - 1, price, f"  {label_text}",
                           fontsize=8, verticalalignment='center',
                           bbox=dict(boxstyle='round,pad=0.3', facecolor='white',
                                   edgecolor=color, alpha=0.7))

                    # Mark first touch point if available
                    if first_touch_bar and first_touch_bar != '':
                        try:
                            touch_bar = int(first_touch_bar)
                            touch_x = touch_bar - min_bar
                            if 0 <= touch_x < len(bars):
                                ax.scatter(touch_x, price, s=100, c='red',
                                         marker='x', linewidths=3, zorder=6,
                                         label='Touch' if 'Touch' not in [h.get_label() for h in ax.get_children()] else '')
                        except:
                            pass

                except Exception as e:
                    print(f"Error plotting Fib level {level_name}: {e}")

    # Formatting
    ax.set_xlabel('Bar Index', fontsize=11)
    ax.set_ylabel('Price', fontsize=11)
    ax.grid(True, alpha=0.3)
    ax.legend(loc='upper left')

    # Set x-axis labels to actual bar indices
    num_ticks = min(10, len(bars))
    tick_positions = np.linspace(0, len(bars)-1, num_ticks, dtype=int)
    tick_labels = [str(min_bar + int(pos)) for pos in tick_positions]
    ax.set_xticks(tick_positions)
    ax.set_xticklabels(tick_labels, rotation=45)

    plt.tight_layout()

    return fig


def visualize_excel_patterns(excel_file):
    """
    Load Excel backtest results and create visualizations for all patterns

    Args:
        excel_file: Path to backtest results Excel file
    """
    print(f"Loading Excel file: {excel_file}")

    # Load sheets
    try:
        pattern_details = pd.read_excel(excel_file, sheet_name='Pattern Details')
        print(f"✅ Loaded {len(pattern_details)} patterns from Pattern Details")
    except Exception as e:
        print(f"❌ Could not load Pattern Details: {e}")
        return

    try:
        fib_analysis = pd.read_excel(excel_file, sheet_name='Fibonacci Analysis')
        print(f"✅ Loaded {len(fib_analysis)} Fibonacci level records")
    except Exception as e:
        print(f"⚠️ No Fibonacci Analysis sheet: {e}")
        fib_analysis = None

    # Load original data
    data_files = ['btcusdt_1d.csv', 'ethusdt_1d.csv']
    test_data = None
    for data_file in data_files:
        if os.path.exists(data_file):
            test_data = pd.read_csv(data_file)
            # Handle different column name formats
            if 'time' in test_data.columns:
                test_data['Date'] = pd.to_datetime(test_data['time'])
            elif 'Date' in test_data.columns:
                test_data['Date'] = pd.to_datetime(test_data['Date'])

            # Rename columns to standard format
            test_data.columns = [col.capitalize() for col in test_data.columns]
            test_data.set_index('Date', inplace=True)
            print(f"✅ Loaded data from {data_file}")
            break

    if test_data is None:
        print("❌ Could not find data file (btcusdt_1d.csv or ethusdt_1d.csv)")
        return

    # Create visualizations
    output_dir = os.path.join(os.path.dirname(excel_file), 'pattern_charts')
    os.makedirs(output_dir, exist_ok=True)

    print(f"\nGenerating pattern visualizations for SUCCESSFUL patterns only...")

    # Filter for successful patterns only
    successful_patterns = pattern_details[pattern_details['Status'] == 'success']
    print(f"Found {len(successful_patterns)} successful patterns out of {len(pattern_details)} total")

    if len(successful_patterns) == 0:
        print("⚠️ No successful patterns found - no charts to generate")
        return

    for idx, pattern_row in successful_patterns.iterrows():
        pattern_id = pattern_row.get('Pattern_ID', f'Pattern_{idx}')

        # Get Fibonacci data for this pattern
        fib_rows = []
        if fib_analysis is not None:
            fib_rows = fib_analysis[fib_analysis['Pattern_ID'] == pattern_id].to_dict('records')

        print(f"  Creating chart for {pattern_id}...")

        try:
            fig = visualize_pattern_with_fibonacci(pattern_row, fib_rows, test_data)

            if fig:
                # Save chart
                safe_id = pattern_id.replace('/', '_').replace('\\', '_').replace(':', '_')
                chart_file = os.path.join(output_dir, f'{safe_id}.png')
                fig.savefig(chart_file, dpi=150, bbox_inches='tight')
                plt.close(fig)
                print(f"    ✅ Saved: {chart_file}")
        except Exception as e:
            print(f"    ❌ Error creating chart: {e}")
            import traceback
            traceback.print_exc()

    print(f"\n✅ All charts saved to: {output_dir}")
    print(f"   Open the PNG files to see visual representations!")


if __name__ == "__main__":
    # Get most recent backtest result
    results_dir = 'backtest_results'

    if len(sys.argv) > 1:
        excel_file = sys.argv[1]
    else:
        # Find most recent Excel file
        excel_files = [f for f in os.listdir(results_dir)
                      if f.endswith('.xlsx') and not f.startswith('~$')]

        if not excel_files:
            print("No Excel files found in backtest_results/")
            sys.exit(1)

        excel_files.sort(reverse=True)
        excel_file = os.path.join(results_dir, excel_files[0])

    print(f"Visualizing patterns from: {excel_file}\n")
    visualize_excel_patterns(excel_file)
