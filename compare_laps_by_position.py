"""
Position-Based Lap Comparison Tool

Compare multiple laps from telemetry data based on track position alignment.
This tool generates an interactive HTML visualization showing where time is
gained or lost around the track.

Usage:
    python compare_laps_by_position.py <telemetry_csv_file>

Example:
    python compare_laps_by_position.py data/output/telemetry_20251024_163152.csv

The CSV file must contain the following columns:
- lap_number: Integer lap number
- track_position: Float percentage (0-100) indicating position around track
- throttle, brake, steering: Telemetry inputs
- speed: Speed in km/h
- time, frame: Timing information
"""

import sys
import pandas as pd
from pathlib import Path
from src.interactive_visualizer import InteractiveTelemetryVisualizer


def validate_csv(df: pd.DataFrame) -> tuple[bool, str]:
    """
    Validate that the CSV has required columns and data for comparison.
    
    Args:
        df: Loaded DataFrame
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check required columns
    required_cols = ['lap_number', 'track_position', 'throttle', 'brake', 'steering', 'time', 'frame']
    missing_cols = [col for col in required_cols if col not in df.columns]
    
    if missing_cols:
        return False, f"Missing required columns: {', '.join(missing_cols)}"
    
    # Check for track_position data
    valid_positions = df[df['track_position'].notna()]
    if valid_positions.empty:
        return False, "No track_position data found. Run main.py with position tracking enabled."
    
    # Check for lap_number data
    valid_laps = df[df['lap_number'].notna()]
    if valid_laps.empty:
        return False, "No lap_number data found."
    
    # Check that we have at least 2 laps with position data
    laps_with_position = df[(df['lap_number'].notna()) & (df['track_position'].notna())]
    unique_laps = laps_with_position['lap_number'].unique()
    
    if len(unique_laps) < 2:
        return False, f"Need at least 2 laps with position data for comparison. Found {len(unique_laps)} lap(s)."
    
    return True, ""


def print_lap_summary(df: pd.DataFrame):
    """Print summary of available laps."""
    valid_df = df[(df['lap_number'].notna()) & (df['track_position'].notna())].copy()

    if valid_df.empty:
        return

    # Ensure track_position is numeric
    valid_df['track_position'] = pd.to_numeric(valid_df['track_position'], errors='coerce')

    print(f"\n📊 Lap Data Summary:")
    print(f"   {'Lap':<8} {'Frames':<10} {'Duration':<12} {'Position Coverage':<20}")
    print(f"   {'-'*60}")

    for lap_num in sorted(valid_df['lap_number'].unique()):
        lap_df = valid_df[valid_df['lap_number'] == lap_num]

        frames = len(lap_df)
        duration = lap_df['time'].iloc[-1] - lap_df['time'].iloc[0]
        min_pos = float(lap_df['track_position'].min())
        max_pos = float(lap_df['track_position'].max())
        position_range = f"{min_pos:.1f}% - {max_pos:.1f}%"

        print(f"   {int(lap_num):<8} {frames:<10} {duration:<12.2f}s {position_range:<20}")


def main():
    """Main entry point for position-based lap comparison."""
    
    print("=" * 70)
    print("ACC Position-Based Lap Comparison Tool")
    print("=" * 70)
    
    # Parse command line arguments
    if len(sys.argv) < 2:
        print("\n❌ Error: No CSV file provided")
        print("\nUsage:")
        print("   python compare_laps_by_position.py <telemetry_csv_file>")
        print("\nExample:")
        print("   python compare_laps_by_position.py data/output/telemetry_20251024_163152.csv")
        print("\nNote: The CSV must contain telemetry data with track position information.")
        print("      Run main.py to generate telemetry CSV with position tracking.")
        return 1
    
    csv_path = Path(sys.argv[1])
    
    # Validate file exists
    if not csv_path.exists():
        print(f"\n❌ Error: File not found: {csv_path}")
        return 1
    
    # Load CSV
    print(f"\n📁 Loading telemetry data from: {csv_path.name}")
    try:
        df = pd.read_csv(csv_path)
        print(f"   ✅ Loaded {len(df)} frames")

        # Clean track_position column (remove any malformed values with spaces)
        if 'track_position' in df.columns:
            df['track_position'] = pd.to_numeric(df['track_position'], errors='coerce')

    except Exception as e:
        print(f"\n❌ Error loading CSV: {e}")
        return 1
    
    # Validate CSV has required data
    is_valid, error_msg = validate_csv(df)
    if not is_valid:
        print(f"\n❌ Error: {error_msg}")
        print("\nTip: Make sure you run main.py with track position tracking enabled.")
        print("     The video must have the minimap visible and properly configured.")
        return 1
    
    # Print lap summary
    print_lap_summary(df)
    
    # Create visualizer
    print(f"\n🎨 Generating position-based comparison visualization...")
    visualizer = InteractiveTelemetryVisualizer()
    
    try:
        # Generate comparison HTML
        # Extract FPS from data if possible (estimate from time/frame)
        fps = 30.0  # Default
        if len(df) > 1 and 'frame' in df.columns and 'time' in df.columns:
            frame_diff = df['frame'].iloc[-1] - df['frame'].iloc[0]
            time_diff = df['time'].iloc[-1] - df['time'].iloc[0]
            if time_diff > 0:
                fps = frame_diff / time_diff
                print(f"   Detected FPS: {fps:.2f}")
        
        html_path = visualizer.plot_position_based_comparison(
            df=df,
            position_step=0.5,  # Sample every 0.5% around track
            fps=fps
        )
        
        print(f"\n   ✅ Comparison visualization saved: {html_path}")
        print(f"      💡 Open this HTML file in your browser to compare laps!")
        
        # Open in browser (macOS)
        import subprocess
        try:
            subprocess.run(['open', html_path], check=False)
            print(f"   🌐 Opening in browser...")
        except Exception:
            pass  # Silent fail if open command doesn't work
        
        print("\n" + "=" * 70)
        print("✅ Position-based comparison complete!")
        print("=" * 70)
        print("\nHow to use the visualization:")
        print("  • Use the dropdown menu to select which two laps to compare")
        print("  • The time delta plot shows where time is gained (negative) or lost (positive)")
        print("  • Hover over any plot to see detailed values at that track position")
        print("  • Zoom by clicking and dragging, pan by dragging while zoomed")
        print("  • Use the range slider at the bottom to navigate quickly")
        
        return 0
        
    except ValueError as e:
        print(f"\n❌ Error: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())

