#!/usr/bin/env python3
"""
Compare lap detection quality between two CSV files.
Shows side-by-side statistics.
"""

import csv
import sys

def analyze_csv(csv_path):
    """Extract lap transition statistics from CSV."""
    transitions = []
    prev_lap = None
    oscillations = 0
    
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            lap = row['lap_number']
            if lap and lap != prev_lap:
                if prev_lap and float(lap) < float(prev_lap):
                    oscillations += 1
                transitions.append(lap)
                prev_lap = lap
    
    return {
        'total_transitions': len(transitions),
        'oscillations': oscillations,
        'unique_laps': len(set(transitions))
    }

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python compare_lap_detections.py <old.csv> <new.csv>")
        sys.exit(1)
    
    old_path = sys.argv[1]
    new_path = sys.argv[2]
    
    print("=" * 60)
    print("Lap Detection Quality Comparison")
    print("=" * 60)
    
    old_stats = analyze_csv(old_path)
    new_stats = analyze_csv(new_path)
    
    print(f"\n{'Metric':<30} {'Before':<15} {'After':<15}")
    print("-" * 60)
    print(f"{'Total Transitions':<30} {old_stats['total_transitions']:<15} {new_stats['total_transitions']:<15}")
    print(f"{'Oscillations (backward jumps)':<30} {old_stats['oscillations']:<15} {new_stats['oscillations']:<15}")
    print(f"{'Unique Laps':<30} {old_stats['unique_laps']:<15} {new_stats['unique_laps']:<15}")
    
    improvement = old_stats['oscillations'] - new_stats['oscillations']
    print("\n" + "=" * 60)
    if improvement > 0:
        print(f"✅ Improvement: {improvement} oscillations eliminated!")
    elif improvement == 0 and old_stats['oscillations'] == 0:
        print(f"✅ Both files have clean lap detection!")
    else:
        print(f"❌ New file has MORE oscillations!")
    print("=" * 60)
