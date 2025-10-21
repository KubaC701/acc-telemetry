#!/usr/bin/env python3
"""
Generate detailed telemetry visualizations from existing CSV data.

This script creates multiple detailed analysis graphs:
1. Comprehensive overview with multiple detail levels
2. Zoomed sections of the lap
3. Braking zones analysis
4. Throttle application analysis
"""

import pandas as pd
from pathlib import Path
import sys
from src.detailed_visualizer import DetailedTelemetryVisualizer


def main():
    """Generate all detailed visualizations."""
    
    # Find the most recent telemetry CSV
    output_dir = Path('data/output')
    csv_files = sorted(output_dir.glob('telemetry_*.csv'), reverse=True)
    
    if not csv_files:
        print("❌ No telemetry CSV files found in data/output/")
        print("   Run main.py first to generate telemetry data.")
        sys.exit(1)
    
    # Use the most recent CSV
    csv_file = csv_files[0]
    print(f"📊 Loading telemetry data from: {csv_file.name}")
    
    # Load data
    df = pd.read_csv(csv_file)
    print(f"   ✓ Loaded {len(df)} frames ({df['time'].iloc[-1]:.2f} seconds)")
    
    # Initialize detailed visualizer
    visualizer = DetailedTelemetryVisualizer(output_dir='data/output')
    
    print("\n🎨 Generating detailed visualizations...")
    print("   (This may take a minute - high resolution outputs)\n")
    
    # 1. Detailed overview
    print("   1/4 Creating comprehensive overview...")
    overview_path = visualizer.plot_detailed_overview(df)
    print(f"       ✓ Saved: {Path(overview_path).name}")
    
    # 2. Zoomed sections (6 sections)
    print("   2/4 Creating zoomed sections (6 sections)...")
    sections_path = visualizer.plot_zoomed_sections(df, num_sections=6)
    print(f"       ✓ Saved: {Path(sections_path).name}")
    
    # 3. Braking zones analysis
    print("   3/4 Analyzing braking zones...")
    braking_path = visualizer.plot_braking_zones(df, brake_threshold=10.0)
    if braking_path:
        print(f"       ✓ Saved: {Path(braking_path).name}")
    else:
        print(f"       ⚠ No braking zones found")
    
    # 4. Throttle application analysis
    print("   4/4 Analyzing throttle application...")
    throttle_path = visualizer.plot_throttle_application(df)
    print(f"       ✓ Saved: {Path(throttle_path).name}")
    
    print("\n✅ All detailed visualizations generated successfully!")
    print(f"\n📁 View your results in: {output_dir}/")
    print("\n💡 Tips:")
    print("   - Open PNG files at 100% zoom to see all details")
    print("   - Braking zones show context before/after each brake application")
    print("   - Throttle gradient uses color to show how aggressive you apply throttle")
    print("   - Compare different laps by running this on multiple CSV files")


if __name__ == '__main__':
    main()

