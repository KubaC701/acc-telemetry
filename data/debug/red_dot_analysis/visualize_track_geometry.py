"""
Track Path Geometry Analysis

Creates detailed visualization of track_path geometry near indices 0, 15, and 25
to understand why 1-pixel variation causes different index matching.

Author: ACC Telemetry Debugging Specialist
"""

import cv2
import numpy as np
import yaml
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, '/Users/jakub.cieply/Personal/acc-telemetry')
from src.position_tracker_v2 import PositionTrackerV2


def visualize_track_geometry():
    """Create detailed visualization of track path near start line."""

    print("="*80)
    print("TRACK PATH GEOMETRY ANALYSIS")
    print("="*80)

    # Configuration
    video_path = '/Users/jakub.cieply/Personal/acc-telemetry/panorama.mp4'
    config_path = '/Users/jakub.cieply/Personal/acc-telemetry/config/roi_config.yaml'
    output_dir = '/Users/jakub.cieply/Personal/acc-telemetry/data/debug/red_dot_analysis'

    # Load ROI config
    with open(config_path, 'r') as f:
        roi_config = yaml.safe_load(f)

    # Extract track path
    print("\nExtracting track path...")
    cap = cv2.VideoCapture(video_path)

    sample_frames = [0, 50, 100, 150, 200, 250, 500, 750, 1000, 1250, 1500]
    map_rois = []

    for frame_num in sample_frames:
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
        ret, frame = cap.read()
        if ret:
            roi = roi_config['track_map']
            x, y, w, h = roi['x'], roi['y'], roi['width'], roi['height']
            map_roi = frame[y:y+h, x:x+w]
            map_rois.append(map_roi)

    cap.release()

    position_tracker = PositionTrackerV2()
    if not position_tracker.extract_track_path(map_rois):
        print("Error: Could not extract track path")
        return

    track_path = position_tracker.track_path
    total_length = position_tracker.total_track_length

    print(f"Track path: {len(track_path)} points, total length: {total_length:.1f}px")

    # Analyze geometry around critical indices
    critical_indices = [0, 15, 25]
    window_size = 15  # Show ±15 indices around each critical point

    print("\n" + "="*80)
    print("GEOMETRY ANALYSIS")
    print("="*80)

    for idx in critical_indices:
        print(f"\nAround Index {idx}:")
        print(f"  Position: {track_path[idx]}")

        # Calculate cumulative arc length from index 0
        arc_length = 0.0
        for i in range(0, idx):
            if i + 1 >= len(track_path):
                break
            p1 = track_path[i]
            p2 = track_path[i + 1]
            dx = p2[0] - p1[0]
            dy = p2[1] - p1[1]
            arc_length += np.sqrt(dx*dx + dy*dy)

        position_pct = (arc_length / total_length * 100.0) if total_length > 0 else 0.0
        print(f"  Arc length from index 0: {arc_length:.1f}px ({position_pct:.3f}%)")

        # Show neighboring points
        print(f"  Neighbors (±5 indices):")
        for offset in range(-5, 6):
            neighbor_idx = idx + offset
            if 0 <= neighbor_idx < len(track_path):
                pt = track_path[neighbor_idx]

                # Distance from index point to neighbor
                dx = pt[0] - track_path[idx][0]
                dy = pt[1] - track_path[idx][1]
                dist = np.sqrt(dx*dx + dy*dy)

                marker = " <--" if offset == 0 else ""
                print(f"    Index {neighbor_idx:3d}: ({pt[0]:3d}, {pt[1]:3d}) dist={dist:5.2f}px{marker}")

    # Create visualization
    print("\n" + "="*80)
    print("CREATING VISUALIZATION")
    print("="*80)

    # Use first map ROI as base
    base_img = map_rois[0].copy()
    h, w = base_img.shape[:2]

    # Create large canvas for multiple views
    canvas_w = w * 3 + 100
    canvas_h = h + 400
    canvas = np.zeros((canvas_h, canvas_w, 3), dtype=np.uint8)

    # View 1: Full track path with critical indices highlighted
    view1 = base_img.copy()

    # Draw full path in white
    for i in range(len(track_path) - 1):
        pt1 = track_path[i]
        pt2 = track_path[i + 1]
        cv2.line(view1, pt1, pt2, (100, 100, 100), 1)

    # Highlight segments around critical indices
    colors = [(0, 255, 0), (255, 255, 0), (0, 165, 255)]  # Green, Yellow, Orange
    for color_idx, idx in enumerate(critical_indices):
        color = colors[color_idx]

        # Draw thicker line around this index
        for offset in range(-window_size, window_size):
            i = idx + offset
            if 0 <= i < len(track_path) - 1:
                pt1 = track_path[i]
                pt2 = track_path[i + 1]
                cv2.line(view1, pt1, pt2, color, 2)

        # Mark the exact index with a circle
        cv2.circle(view1, track_path[idx], 5, color, -1)
        cv2.putText(view1, f"{idx}", (track_path[idx][0] + 8, track_path[idx][1]),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

    # Add view1 to canvas
    canvas[50:50+h, 25:25+w] = view1
    cv2.putText(canvas, "Full Track Path (0=green, 15=yellow, 25=orange)",
               (25, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

    # View 2: Zoomed on start/finish area (indices 0-40)
    view2 = base_img.copy()

    # Draw path segments with index labels
    for i in range(0, min(40, len(track_path) - 1)):
        pt1 = track_path[i]
        pt2 = track_path[i + 1]

        # Color based on proximity to critical indices
        if i in critical_indices:
            color = (0, 0, 255)  # Red for exact matches
            thickness = 3
        elif abs(i - 0) <= 5:
            color = (0, 255, 0)  # Green near index 0
            thickness = 2
        elif abs(i - 15) <= 5:
            color = (255, 255, 0)  # Yellow near index 15
            thickness = 2
        elif abs(i - 25) <= 5:
            color = (0, 165, 255)  # Orange near index 25
            thickness = 2
        else:
            color = (150, 150, 150)  # Gray for others
            thickness = 1

        cv2.line(view2, pt1, pt2, color, thickness)

        # Add index label every 5 points
        if i % 5 == 0:
            cv2.circle(view2, pt1, 2, (255, 255, 255), -1)
            cv2.putText(view2, str(i), (pt1[0] + 3, pt1[1] - 3),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.3, (255, 255, 255), 1)

    # Mark critical indices with larger markers
    for idx in critical_indices:
        cv2.circle(view2, track_path[idx], 6, (0, 0, 255), 2)
        cv2.putText(view2, f"IDX {idx}", (track_path[idx][0] + 10, track_path[idx][1] - 10),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

    # Overlay the problematic dot positions
    lap1_dot = (15, 27)
    lap3_dot = (15, 26)

    cv2.drawMarker(view2, lap1_dot, (255, 0, 255), cv2.MARKER_DIAMOND, 12, 2)
    cv2.putText(view2, "Lap1/4 (15,27)", (lap1_dot[0] + 15, lap1_dot[1]),
               cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 0, 255), 1)

    cv2.drawMarker(view2, lap3_dot, (255, 255, 0), cv2.MARKER_DIAMOND, 12, 2)
    cv2.putText(view2, "Lap3 (15,26)", (lap3_dot[0] + 15, lap3_dot[1] - 15),
               cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 0), 1)

    canvas[50:50+h, 25+w+25:25+w+25+w] = view2
    cv2.putText(canvas, "Start Area Detail (indices 0-40)",
               (25+w+25, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

    # View 3: Super-zoomed on indices 10-30 with grid
    view3 = np.zeros_like(base_img)

    # Draw just the segment we care about, much larger
    for i in range(10, min(30, len(track_path) - 1)):
        pt1 = track_path[i]
        pt2 = track_path[i + 1]
        cv2.line(view3, pt1, pt2, (200, 200, 200), 2)

    # Mark each point
    for i in range(10, min(31, len(track_path))):
        pt = track_path[i]
        if i in critical_indices:
            cv2.circle(view3, pt, 6, (0, 0, 255), -1)
            cv2.putText(view3, f"{i}", (pt[0] + 8, pt[1] - 8),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
        else:
            cv2.circle(view3, pt, 3, (100, 255, 100), -1)
            cv2.putText(view3, str(i), (pt[0] + 5, pt[1] - 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.3, (200, 200, 200), 1)

    # Overlay dots
    cv2.drawMarker(view3, lap1_dot, (255, 0, 255), cv2.MARKER_CROSS, 15, 3)
    cv2.circle(view3, lap1_dot, 8, (255, 0, 255), 2)

    cv2.drawMarker(view3, lap3_dot, (255, 255, 0), cv2.MARKER_CROSS, 15, 3)
    cv2.circle(view3, lap3_dot, 8, (255, 255, 0), 2)

    canvas[50:50+h, 25+w+25+w+25:25+w+25+w+25+w] = view3
    cv2.putText(canvas, "Super Zoom (indices 10-30)",
               (25+w+25+w+25, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

    # Add text analysis below images
    text_y = 50 + h + 30
    cv2.putText(canvas, "CRITICAL FINDING:", (25, text_y),
               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
    text_y += 30

    cv2.putText(canvas, f"Index 15 (yellow) is at position {track_path[15]}", (25, text_y),
               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)
    text_y += 25
    cv2.putText(canvas, f"Index 25 (orange) is at position {track_path[25]}", (25, text_y),
               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 165, 255), 1)
    text_y += 25
    cv2.putText(canvas, f"These are only 2 pixels apart (Y: 25 vs 27)!", (25, text_y),
               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
    text_y += 35

    # Calculate distances
    dist_15_to_lap1 = np.sqrt((15 - 14)**2 + (27 - 25)**2)
    dist_15_to_lap3 = np.sqrt((15 - 14)**2 + (26 - 25)**2)
    dist_25_to_lap1 = np.sqrt((15 - 14)**2 + (27 - 27)**2)
    dist_25_to_lap3 = np.sqrt((15 - 14)**2 + (26 - 27)**2)

    cv2.putText(canvas, f"Lap 1/4 dot (15,27): distance to idx15={(dist_15_to_lap1):.2f}px, to idx25={dist_25_to_lap1:.2f}px",
               (25, text_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 255), 1)
    text_y += 25
    cv2.putText(canvas, f"Lap 3 dot (15,26):   distance to idx15={dist_15_to_lap3:.2f}px, to idx25={dist_25_to_lap3:.2f}px",
               (25, text_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)
    text_y += 35

    cv2.putText(canvas, "PROBLEM: When Y shifts by 1 pixel, the closest index changes!",
               (25, text_y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
    text_y += 30
    cv2.putText(canvas, f"This causes {abs(3.871 - 2.151):.2f}% position error (should be 0.0%)",
               (25, text_y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

    # Save
    output_path = f"{output_dir}/track_geometry_analysis.png"
    cv2.imwrite(output_path, canvas)
    print(f"\nSaved geometry visualization: {output_path}")
    print(f"Canvas size: {canvas_w}x{canvas_h}")

    # Print distance matrix
    print("\n" + "="*80)
    print("DISTANCE MATRIX (indices 10-30 to lap dot positions)")
    print("="*80)
    print(f"\n{'Index':>6} {'Position':>12} {'→ Lap1(15,27)':>15} {'→ Lap3(15,26)':>15}")
    print("-" * 60)

    for i in range(10, min(31, len(track_path))):
        pt = track_path[i]
        dist_lap1 = np.sqrt((15 - pt[0])**2 + (27 - pt[1])**2)
        dist_lap3 = np.sqrt((15 - pt[0])**2 + (26 - pt[1])**2)

        marker1 = " ← MATCH" if i == 25 else ""
        marker3 = " ← MATCH" if i == 15 else ""

        print(f"{i:6d} ({pt[0]:3d}, {pt[1]:3d}) {dist_lap1:14.2f}{marker1:12s} {dist_lap3:14.2f}{marker3:12s}")


if __name__ == '__main__':
    visualize_track_geometry()
