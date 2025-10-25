# Red Dot Position Detection - Diagnostic Report
**Generated:** diagnostic_report.md
**Issue:** 1-pixel Y-coordinate difference causes different track_path index matching

## Executive Summary

This report analyzes why a 1-pixel difference in red dot Y-coordinate detection (Y=27 vs Y=26) causes the position tracker to match different track_path indices (index 25 vs index 15), leading to incorrect lap position percentages.

## Frame Analysis

### Red Dot Detection Comparison

| Frame | Lap | Red Dot (x,y) | Closest Index | Distance (px) | Position % |
|-------|-----|---------------|---------------|---------------|------------|
| 3064 | 1 | (15, 27) | 25 | 1.00 | 3.871% |
| 9430 | 3 | (15, 26) | 15 | 1.41 | 2.151% |
| 12431 | 4 | (15, 27) | 25 | 1.00 | 3.871% |

### Detailed Frame Analysis

#### Frame 3064 (Lap 1)

**Red Dot Detection:**
- Position: (15, 27)
- BGR value: [0, 0, 217]
- HSV value: H=0° S=100.0% V=85.1%
- Contours detected: 1
- Largest contour area: 67.0px²
- Total red pixels: 85

**Track Path Matching:**
- Closest index: 25
- Distance: 1.00 pixels
- Track point: (14, 27)

**Top 5 Nearest Track Points:**
1. Index 25: distance=1.00px, position=(14, 27)
2. Index 26: distance=1.41px, position=(14, 28)
3. Index 15: distance=2.24px, position=(14, 25)
4. Index 16: distance=2.24px, position=(13, 26)
5. Index 24: distance=2.24px, position=(13, 26)

#### Frame 9430 (Lap 3)

**Red Dot Detection:**
- Position: (15, 26)
- BGR value: [15, 0, 204]
- HSV value: H=178° S=100.0% V=80.0%
- Contours detected: 1
- Largest contour area: 51.5px²
- Total red pixels: 73

**Track Path Matching:**
- Closest index: 15
- Distance: 1.41 pixels
- Track point: (14, 25)

**Top 5 Nearest Track Points:**
1. Index 15: distance=1.41px, position=(14, 25)
2. Index 25: distance=1.41px, position=(14, 27)
3. Index 14: distance=2.00px, position=(15, 24)
4. Index 16: distance=2.00px, position=(13, 26)
5. Index 24: distance=2.00px, position=(13, 26)

#### Frame 12431 (Lap 4)

**Red Dot Detection:**
- Position: (15, 27)
- BGR value: [5, 0, 219]
- HSV value: H=179° S=100.0% V=85.9%
- Contours detected: 2
- Largest contour area: 61.0px²
- Total red pixels: 79

**Track Path Matching:**
- Closest index: 25
- Distance: 1.00 pixels
- Track point: (14, 27)

**Top 5 Nearest Track Points:**
1. Index 25: distance=1.00px, position=(14, 27)
2. Index 26: distance=1.41px, position=(14, 28)
3. Index 15: distance=2.24px, position=(14, 25)
4. Index 16: distance=2.24px, position=(13, 26)
5. Index 24: distance=2.24px, position=(13, 26)

## Root Cause Analysis

**Key Observation:**
- Lap 1 dot: (15, 27) → matched to index 25
- Lap 3 dot: (15, 26) → matched to index 15
- Y-coordinate difference: 1 pixel(s)
- Index difference: 10 indices

**Why does 1 pixel matter?**

The track path near the start/finish line is tightly spaced. A single pixel difference in Y-coordinate can be enough to make the dot closer to a different track_path point. This is especially problematic when:

1. The track path has multiple points within 1-2 pixels of each other
2. The red dot detection varies slightly between frames (sub-pixel centroid shifts)
3. The closest-point matching uses Euclidean distance without tolerance

## Recommendations

### 1. Use Search Window Instead of Single Closest Point

Instead of matching to the single closest point, find all track_path points within a radius (e.g., 3 pixels) and use the one with the smallest arc length deviation from expected position.

```python
# Find all points within tolerance radius
tolerance_radius = 3.0  # pixels
candidates = []
for i, (px, py) in enumerate(track_path):
    distance = sqrt((dot_x - px)**2 + (dot_y - py)**2)
    if distance <= tolerance_radius:
        candidates.append((i, distance))

# Among candidates, pick the one closest to expected position
# (based on last known position + velocity)
```

### 2. Lock Start Position on First Lap Detection

The current implementation sets `start_position = track_path[0]` during path extraction. This is correct. However, we should ALSO capture the actual red dot pixel position on the first lap start and use that for sub-pixel refinement.

### 3. Use Sub-Pixel Interpolation

Instead of using integer pixel coordinates, interpolate between track_path points to get sub-pixel precision. This reduces sensitivity to 1-pixel variations.

### 4. Add Temporal Consistency Check

At lap start, the position should be very close to 0%. If the matched index gives a position >5%, reject it and search for a better match closer to the start line.

### 5. Visualize Track Path Geometry Near Start

Examine the track_path points near index 0, 15, and 25 to understand their spacing. If they're extremely close together, consider resampling the track path to have more uniform point spacing.

## Validation Test Plan

After implementing fixes:

1. **Consistency Test**: Extract position at lap start for laps 1-5. All should show <1% variation.
2. **Robustness Test**: Manually shift red dot detection by ±1 pixel. Position change should be <0.5%.
3. **Arc Length Test**: Verify arc length from index 0 to indices 15 and 25. Compare to expected position.
4. **Visual Inspection**: Overlay detected positions on track map. Start positions should align.

