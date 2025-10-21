"""
Lap Comparison Tool - Compare telemetry from multiple laps
Usage: python compare_laps.py lap1.csv lap2.csv lap3.csv
"""

import sys
import pandas as pd
from pathlib import Path
from src.interactive_visualizer import InteractiveTelemetryVisualizer


def main():
    """Compare multiple lap telemetry files."""
    
    if len(sys.argv) < 3:
        print("=" * 60)
        print("ACC Telemetry Lap Comparison")
        print("=" * 60)
        print("\n❌ Error: Need at least 2 CSV files to compare")
        print("\nUsage:")
        print("   python compare_laps.py lap1.csv lap2.csv [lap3.csv ...]")
        print("\nExample:")
        print("   python compare_laps.py data/output/telemetry_20251022_005324.csv data/output/telemetry_20251022_010355.csv")
        return
    
    csv_files = sys.argv[1:]
    
    print("=" * 60)
    print("ACC Telemetry Lap Comparison")
    print("=" * 60)
    
    # Load all CSV files
    dataframes = []
    labels = []
    
    for idx, csv_path in enumerate(csv_files):
        path = Path(csv_path)
        
        if not path.exists():
            print(f"\n❌ Error: File not found: {csv_path}")
            return
        
        print(f"\n📁 Loading lap {idx + 1}: {path.name}")
        df = pd.read_csv(path)
        
        # Display basic info
        duration = df['time'].iloc[-1] - df['time'].iloc[0]
        avg_throttle = df['throttle'].mean()
        avg_brake = df['brake'].mean()
        
        print(f"   Duration: {duration:.2f}s")
        print(f"   Avg Throttle: {avg_throttle:.1f}%")
        print(f"   Avg Brake: {avg_brake:.1f}%")
        
        dataframes.append(df)
        labels.append(f"Lap {idx + 1}")
    
    # Create comparison visualization
    print(f"\n📈 Generating comparison visualization...")
    visualizer = InteractiveTelemetryVisualizer()
    
    comparison_path = visualizer.plot_comparison(
        dataframes=dataframes,
        labels=labels
    )
    
    print(f"   ✅ Comparison graph saved: {comparison_path}")
    print(f"      💡 Open this HTML file in your browser to compare laps!")
    
    # Open in browser
    import subprocess
    subprocess.run(['open', comparison_path])
    
    print("\n" + "=" * 60)
    print("✅ Comparison complete!")
    print("=" * 60)


if __name__ == '__main__':
    main()

