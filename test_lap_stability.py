#!/usr/bin/env python3
"""
Test script to verify lap detection stability.
Checks for oscillations in lap number detection.
"""

import csv
import sys

def test_lap_stability(csv_path):
    """
    Analyze lap number stability in telemetry CSV.
    
    Returns True if stable, False if oscillations detected.
    """
    print(f"Testing lap stability in: {csv_path}\n")
    
    lap_transitions = []
    prev_lap = None
    
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row_num, row in enumerate(reader, start=2):
            lap_num = row['lap_number']
            if lap_num and lap_num != prev_lap:
                lap_transitions.append({
                    'frame': int(row['frame']),
                    'from': prev_lap,
                    'to': lap_num
                })
                prev_lap = lap_num
    
    print(f"Total lap transitions detected: {len(lap_transitions)}\n")
    
    # Check for backward transitions (oscillations)
    oscillations = []
    for i in range(len(lap_transitions) - 1):
        curr = lap_transitions[i]
        next = lap_transitions[i + 1]
        
        if curr['from'] and curr['to']:
            curr_lap_float = float(curr['to'])
            next_lap_float = float(next['to'])
            
            # Backward transition = oscillation
            if next_lap_float < curr_lap_float:
                oscillations.append({
                    'frame': next['frame'],
                    'backward_jump': f"{curr['to']} → {next['to']}"
                })
    
    if oscillations:
        print(f"❌ FAILED: Detected {len(oscillations)} oscillations:")
        for osc in oscillations[:10]:  # Show first 10
            print(f"   Frame {osc['frame']}: {osc['backward_jump']}")
        if len(oscillations) > 10:
            print(f"   ... and {len(oscillations) - 10} more")
        return False
    else:
        print("✅ PASSED: No lap oscillations detected!")
        print(f"   All {len(lap_transitions)} transitions are forward progression.")
        return True

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python test_lap_stability.py <telemetry.csv>")
        sys.exit(1)
    
    csv_path = sys.argv[1]
    success = test_lap_stability(csv_path)
    sys.exit(0 if success else 1)
