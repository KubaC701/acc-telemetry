"""
Red Dot Position Detection Diagnostic Script

Analyzes frames 3064 (Lap 1), 9430 (Lap 3), and 12431 (Lap 4) to identify
why a 1-pixel difference in Y coordinate causes different track_path index matching.

This script will:
1. Extract ROI images for track_map from the specified frames
2. Detect red dot position using HSV color detection
3. Visualize the HSV color space at the detected positions
4. Show which track_path indices are matched and why
5. Generate comparative visualizations
6. Provide recommendations for fixing the issue

Author: ACC Telemetry Debugging Specialist
"""

import cv2
import numpy as np
import yaml
import sys
from pathlib import Path
from typing import Tuple, Optional, List, Dict

# Add src to path for imports
sys.path.insert(0, '/Users/jakub.cieply/Personal/acc-telemetry')
from src.position_tracker_v2 import PositionTrackerV2


class RedDotDiagnostics:
    """Diagnostic tool for analyzing red dot detection issues."""

    def __init__(self, video_path: str, roi_config: dict):
        """
        Initialize diagnostics.

        Args:
            video_path: Path to video file
            roi_config: ROI configuration dictionary
        """
        self.video_path = video_path
        self.roi_config = roi_config
        self.cap = None

        # Red dot detection parameters (from PositionTrackerV2)
        self.red_lower1 = np.array([0, 150, 150])
        self.red_upper1 = np.array([10, 255, 255])
        self.red_lower2 = np.array([170, 150, 150])
        self.red_upper2 = np.array([180, 255, 255])

        # White line detection parameters
        self.white_lower = np.array([0, 0, 210])
        self.white_upper = np.array([180, 30, 255])

        # Track path (to be extracted)
        self.track_path = None
        self.position_tracker = PositionTrackerV2()

    def open_video(self) -> bool:
        """Open video file."""
        self.cap = cv2.VideoCapture(self.video_path)
        if not self.cap.isOpened():
            print(f"Error: Could not open video: {self.video_path}")
            return False
        return True

    def extract_roi(self, frame: np.ndarray, roi_name: str) -> np.ndarray:
        """Extract ROI from frame."""
        if roi_name not in self.roi_config:
            return None

        roi = self.roi_config[roi_name]
        x, y, w, h = roi['x'], roi['y'], roi['width'], roi['height']
        return frame[y:y+h, x:x+w]

    def get_frame_at(self, frame_number: int) -> Optional[np.ndarray]:
        """Get frame at specific frame number."""
        if not self.cap:
            return None

        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        ret, frame = self.cap.read()

        if not ret:
            print(f"Error: Could not read frame {frame_number}")
            return None

        return frame

    def detect_red_dot_verbose(self, map_roi: np.ndarray) -> Tuple[Optional[Tuple[int, int]], np.ndarray, Dict]:
        """
        Detect red dot with verbose diagnostic info.

        Returns:
            (dot_position, red_mask, debug_info)
        """
        if map_roi is None or map_roi.size == 0:
            return None, None, {}

        # Convert to HSV
        hsv = cv2.cvtColor(map_roi, cv2.COLOR_BGR2HSV)

        # Create masks for both red ranges
        red_mask1 = cv2.inRange(hsv, self.red_lower1, self.red_upper1)
        red_mask2 = cv2.inRange(hsv, self.red_lower2, self.red_upper2)

        # Combine masks
        red_mask = cv2.bitwise_or(red_mask1, red_mask2)

        # Find contours
        contours, _ = cv2.findContours(red_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        debug_info = {
            'num_contours': len(contours),
            'contour_areas': [],
            'red_pixels_total': np.sum(red_mask > 0)
        }

        if not contours:
            return None, red_mask, debug_info

        # Find largest contour
        contour_areas = [(i, cv2.contourArea(c)) for i, c in enumerate(contours)]
        contour_areas.sort(key=lambda x: x[1], reverse=True)

        debug_info['contour_areas'] = contour_areas

        largest_idx, largest_area = contour_areas[0]
        largest_contour = contours[largest_idx]

        # Calculate centroid
        moments = cv2.moments(largest_contour)
        if moments['m00'] == 0:
            return None, red_mask, debug_info

        cx = int(moments['m10'] / moments['m00'])
        cy = int(moments['m01'] / moments['m00'])

        debug_info['centroid'] = (cx, cy)
        debug_info['largest_area'] = largest_area

        return (cx, cy), red_mask, debug_info

    def find_closest_track_points(self, dot_x: int, dot_y: int, n: int = 10) -> List[Tuple[int, int, float]]:
        """
        Find N closest track_path points to the given dot position.

        Returns:
            List of (index, distance, (x, y)) tuples, sorted by distance
        """
        if not self.track_path:
            return []

        distances = []
        for i, (px, py) in enumerate(self.track_path):
            dx = dot_x - px
            dy = dot_y - py
            distance = np.sqrt(dx*dx + dy*dy)
            distances.append((i, distance, (px, py)))

        distances.sort(key=lambda x: x[1])
        return distances[:n]

    def analyze_frame(self, frame_number: int, lap_number: int) -> Dict:
        """
        Analyze a specific frame in detail.

        Returns:
            Dictionary with all diagnostic info
        """
        print(f"\n{'='*80}")
        print(f"Analyzing Frame {frame_number} (Lap {lap_number})")
        print(f"{'='*80}")

        # Get frame
        frame = self.get_frame_at(frame_number)
        if frame is None:
            return None

        # Extract track_map ROI
        map_roi = self.extract_roi(frame, 'track_map')
        if map_roi is None:
            print("Error: Could not extract track_map ROI")
            return None

        # Detect red dot
        dot_pos, red_mask, debug_info = self.detect_red_dot_verbose(map_roi)

        if dot_pos is None:
            print("Error: Could not detect red dot")
            return None

        dot_x, dot_y = dot_pos

        # Get HSV values at dot position
        hsv = cv2.cvtColor(map_roi, cv2.COLOR_BGR2HSV)
        hsv_at_dot = hsv[dot_y, dot_x]
        bgr_at_dot = map_roi[dot_y, dot_x]

        # Find closest track points
        closest_points = self.find_closest_track_points(dot_x, dot_y, n=10)

        print(f"\nRed Dot Detection:")
        print(f"  Position: ({dot_x}, {dot_y})")
        print(f"  BGR value: {bgr_at_dot}")
        print(f"  HSV value: H={hsv_at_dot[0]}° S={hsv_at_dot[1]/255*100:.1f}% V={hsv_at_dot[2]/255*100:.1f}%")
        print(f"  Contours found: {debug_info['num_contours']}")
        print(f"  Largest contour area: {debug_info.get('largest_area', 0):.1f} pixels²")
        print(f"  Total red pixels: {debug_info['red_pixels_total']}")

        print(f"\nClosest Track Path Points:")
        for i, (idx, dist, (px, py)) in enumerate(closest_points[:5]):
            print(f"  {i+1}. Index {idx:4d}: distance={dist:6.2f}px  position=({px:3d}, {py:3d})")

        # Calculate arc length offset from track_path[0] to closest point
        if closest_points:
            closest_idx = closest_points[0][0]
            arc_offset = self.calculate_arc_length(0, closest_idx)
            total_length = self.position_tracker.total_track_length
            offset_pct = (arc_offset / total_length * 100.0) if total_length > 0 else 0.0

            print(f"\nPosition Calculation:")
            print(f"  Closest index: {closest_idx} (out of {len(self.track_path)})")
            print(f"  Arc length from index 0: {arc_offset:.1f} pixels")
            print(f"  Total track length: {total_length:.1f} pixels")
            print(f"  Position percentage: {offset_pct:.3f}%")

        return {
            'frame_number': frame_number,
            'lap_number': lap_number,
            'map_roi': map_roi,
            'red_mask': red_mask,
            'hsv': hsv,
            'dot_position': dot_pos,
            'hsv_at_dot': hsv_at_dot,
            'bgr_at_dot': bgr_at_dot,
            'closest_points': closest_points,
            'debug_info': debug_info
        }

    def calculate_arc_length(self, start_idx: int, end_idx: int) -> float:
        """Calculate arc length between two indices on track_path."""
        if not self.track_path:
            return 0.0

        arc_length = 0.0

        if end_idx >= start_idx:
            for i in range(start_idx, end_idx):
                if i + 1 >= len(self.track_path):
                    break
                p1 = self.track_path[i]
                p2 = self.track_path[i + 1]
                dx = p2[0] - p1[0]
                dy = p2[1] - p1[1]
                arc_length += np.sqrt(dx*dx + dy*dy)
        else:
            # Wraparound
            for i in range(start_idx, len(self.track_path) - 1):
                p1 = self.track_path[i]
                p2 = self.track_path[i + 1]
                dx = p2[0] - p1[0]
                dy = p2[1] - p1[1]
                arc_length += np.sqrt(dx*dx + dy*dy)

            p1 = self.track_path[-1]
            p2 = self.track_path[0]
            dx = p2[0] - p1[0]
            dy = p2[1] - p1[1]
            arc_length += np.sqrt(dx*dx + dy*dy)

            for i in range(0, end_idx):
                p1 = self.track_path[i]
                p2 = self.track_path[i + 1]
                dx = p2[0] - p1[0]
                dy = p2[1] - p1[1]
                arc_length += np.sqrt(dx*dx + dy*dy)

        return arc_length

    def create_visualization(self, results: List[Dict], output_path: str):
        """
        Create comprehensive side-by-side visualization of all frames.

        Args:
            results: List of analysis results for each frame
            output_path: Path to save visualization
        """
        print(f"\n{'='*80}")
        print("Creating Diagnostic Visualization")
        print(f"{'='*80}")

        # Create large canvas for all visualizations
        num_frames = len(results)
        num_rows = 5  # Original, HSV, Red Mask, Track overlay, Zoomed region

        # Get ROI dimensions
        roi_h, roi_w = results[0]['map_roi'].shape[:2]

        # Canvas dimensions
        canvas_h = num_rows * roi_h + 100  # Extra space for titles
        canvas_w = num_frames * roi_w + 100
        canvas = np.zeros((canvas_h, canvas_w, 3), dtype=np.uint8)

        # Font settings
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.5
        font_thickness = 1

        # Process each frame
        for col_idx, result in enumerate(results):
            frame_num = result['frame_number']
            lap_num = result['lap_number']
            map_roi = result['map_roi']
            red_mask = result['red_mask']
            hsv = result['hsv']
            dot_pos = result['dot_position']
            closest_points = result['closest_points']

            x_offset = col_idx * roi_w + 50

            # Add column header
            header_text = f"Frame {frame_num} (Lap {lap_num})"
            cv2.putText(canvas, header_text, (x_offset, 20), font, 0.6, (255, 255, 255), 2)

            # Row 1: Original ROI with red dot marked
            row1_y = 40
            original_annotated = map_roi.copy()
            if dot_pos:
                cv2.drawMarker(original_annotated, dot_pos, (0, 255, 255), cv2.MARKER_CROSS, 10, 2)
                cv2.circle(original_annotated, dot_pos, 3, (0, 255, 255), -1)
            canvas[row1_y:row1_y+roi_h, x_offset:x_offset+roi_w] = original_annotated
            cv2.putText(canvas, "Original + Dot", (x_offset, row1_y-5), font, font_scale, (255, 255, 255), font_thickness)

            # Row 2: HSV visualization (Hue channel colorized)
            row2_y = row1_y + roi_h
            hsv_vis = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
            canvas[row2_y:row2_y+roi_h, x_offset:x_offset+roi_w] = hsv_vis
            cv2.putText(canvas, "HSV View", (x_offset, row2_y-5), font, font_scale, (255, 255, 255), font_thickness)

            # Row 3: Red mask
            row3_y = row2_y + roi_h
            red_mask_colored = cv2.cvtColor(red_mask, cv2.COLOR_GRAY2BGR)
            canvas[row3_y:row3_y+roi_h, x_offset:x_offset+roi_w] = red_mask_colored
            cv2.putText(canvas, "Red Dot Mask", (x_offset, row3_y-5), font, font_scale, (255, 255, 255), font_thickness)

            # Row 4: Track path overlay with matched indices
            row4_y = row3_y + roi_h
            track_overlay = map_roi.copy()

            # Draw track path in green
            if self.track_path:
                for i in range(len(self.track_path) - 1):
                    pt1 = self.track_path[i]
                    pt2 = self.track_path[i + 1]
                    cv2.line(track_overlay, pt1, pt2, (0, 255, 0), 1)

            # Highlight closest points
            if closest_points:
                for i, (idx, dist, (px, py)) in enumerate(closest_points[:5]):
                    if i == 0:
                        # Closest point in red
                        cv2.circle(track_overlay, (px, py), 4, (0, 0, 255), -1)
                        cv2.putText(track_overlay, f"{idx}", (px+5, py-5), font, 0.3, (0, 0, 255), 1)
                    else:
                        # Next closest in yellow
                        cv2.circle(track_overlay, (px, py), 2, (0, 255, 255), -1)

                # Draw line from dot to closest point
                if dot_pos:
                    closest_pt = (closest_points[0][2][0], closest_points[0][2][1])
                    cv2.line(track_overlay, dot_pos, closest_pt, (255, 0, 255), 1)
                    cv2.drawMarker(track_overlay, dot_pos, (0, 255, 255), cv2.MARKER_CROSS, 8, 1)

            canvas[row4_y:row4_y+roi_h, x_offset:x_offset+roi_w] = track_overlay
            cv2.putText(canvas, "Track Path Match", (x_offset, row4_y-5), font, font_scale, (255, 255, 255), font_thickness)

            # Row 5: Zoomed region around dot (10x10 pixel region, scaled up 15x)
            row5_y = row4_y + roi_h
            if dot_pos:
                dot_x, dot_y = dot_pos
                zoom_size = 10
                zoom_scale = 15

                # Extract region
                y1 = max(0, dot_y - zoom_size//2)
                y2 = min(roi_h, dot_y + zoom_size//2)
                x1 = max(0, dot_x - zoom_size//2)
                x2 = min(roi_w, dot_x + zoom_size//2)

                zoom_region = map_roi[y1:y2, x1:x2]
                zoom_h, zoom_w = zoom_region.shape[:2]

                # Scale up
                zoomed = cv2.resize(zoom_region, (zoom_w * zoom_scale, zoom_h * zoom_scale), interpolation=cv2.INTER_NEAREST)

                # Place on canvas (center it)
                zoom_y = row5_y
                zoom_x = x_offset
                zh, zw = zoomed.shape[:2]

                if zh <= roi_h and zw <= roi_w:
                    canvas[zoom_y:zoom_y+zh, zoom_x:zoom_x+zw] = zoomed

                    # Draw grid
                    for i in range(1, zoom_size):
                        x_line = zoom_x + i * zoom_scale
                        y_line = zoom_y + i * zoom_scale
                        if x_line < zoom_x + zw:
                            cv2.line(canvas, (x_line, zoom_y), (x_line, zoom_y+zh), (100, 100, 100), 1)
                        if y_line < zoom_y + zh:
                            cv2.line(canvas, (zoom_x, y_line), (zoom_x+zw, y_line), (100, 100, 100), 1)

                    # Mark center pixel
                    center_pixel_x = zoom_x + (zoom_w // 2) * zoom_scale
                    center_pixel_y = zoom_y + (zoom_h // 2) * zoom_scale
                    cv2.drawMarker(canvas, (center_pixel_x, center_pixel_y), (0, 255, 255), cv2.MARKER_CROSS, zoom_scale, 2)

            cv2.putText(canvas, "Zoomed (15x)", (x_offset, row5_y-5), font, font_scale, (255, 255, 255), font_thickness)

            # Add data annotation
            if closest_points:
                info_y = row5_y + roi_h + 20
                closest_idx = closest_points[0][0]
                closest_dist = closest_points[0][1]
                cv2.putText(canvas, f"Dot: ({dot_pos[0]}, {dot_pos[1]})", (x_offset, info_y), font, 0.4, (255, 255, 255), 1)
                cv2.putText(canvas, f"Index: {closest_idx}", (x_offset, info_y+15), font, 0.4, (255, 255, 255), 1)
                cv2.putText(canvas, f"Dist: {closest_dist:.2f}px", (x_offset, info_y+30), font, 0.4, (255, 255, 255), 1)

        # Save visualization
        cv2.imwrite(output_path, canvas)
        print(f"\n✓ Saved diagnostic visualization: {output_path}")
        print(f"  Image size: {canvas_w}x{canvas_h} pixels")

    def generate_report(self, results: List[Dict], output_path: str):
        """
        Generate detailed markdown report.

        Args:
            results: List of analysis results
            output_path: Path to save report
        """
        print(f"\n{'='*80}")
        print("Generating Diagnostic Report")
        print(f"{'='*80}")

        report = []
        report.append("# Red Dot Position Detection - Diagnostic Report\n")
        report.append(f"**Generated:** {Path(output_path).name}\n")
        report.append("**Issue:** 1-pixel Y-coordinate difference causes different track_path index matching\n\n")

        report.append("## Executive Summary\n\n")
        report.append("This report analyzes why a 1-pixel difference in red dot Y-coordinate detection ")
        report.append("(Y=27 vs Y=26) causes the position tracker to match different track_path indices ")
        report.append("(index 25 vs index 15), leading to incorrect lap position percentages.\n\n")

        report.append("## Frame Analysis\n\n")

        # Comparative table
        report.append("### Red Dot Detection Comparison\n\n")
        report.append("| Frame | Lap | Red Dot (x,y) | Closest Index | Distance (px) | Position % |\n")
        report.append("|-------|-----|---------------|---------------|---------------|------------|\n")

        for result in results:
            frame_num = result['frame_number']
            lap_num = result['lap_number']
            dot_pos = result['dot_position']
            closest_points = result['closest_points']

            if dot_pos and closest_points:
                dot_x, dot_y = dot_pos
                closest_idx, closest_dist, _ = closest_points[0]

                # Calculate position percentage
                arc_offset = self.calculate_arc_length(0, closest_idx)
                total_length = self.position_tracker.total_track_length
                offset_pct = (arc_offset / total_length * 100.0) if total_length > 0 else 0.0

                report.append(f"| {frame_num} | {lap_num} | ({dot_x}, {dot_y}) | {closest_idx} | {closest_dist:.2f} | {offset_pct:.3f}% |\n")

        report.append("\n")

        # Detailed analysis for each frame
        report.append("### Detailed Frame Analysis\n\n")

        for result in results:
            frame_num = result['frame_number']
            lap_num = result['lap_number']
            dot_pos = result['dot_position']
            hsv_at_dot = result['hsv_at_dot']
            bgr_at_dot = result['bgr_at_dot']
            closest_points = result['closest_points']
            debug_info = result['debug_info']

            report.append(f"#### Frame {frame_num} (Lap {lap_num})\n\n")

            if dot_pos:
                report.append(f"**Red Dot Detection:**\n")
                report.append(f"- Position: ({dot_pos[0]}, {dot_pos[1]})\n")
                report.append(f"- BGR value: {bgr_at_dot.tolist()}\n")
                report.append(f"- HSV value: H={hsv_at_dot[0]}° S={hsv_at_dot[1]/255*100:.1f}% V={hsv_at_dot[2]/255*100:.1f}%\n")
                report.append(f"- Contours detected: {debug_info['num_contours']}\n")
                report.append(f"- Largest contour area: {debug_info.get('largest_area', 0):.1f}px²\n")
                report.append(f"- Total red pixels: {debug_info['red_pixels_total']}\n\n")

                if closest_points:
                    report.append(f"**Track Path Matching:**\n")
                    report.append(f"- Closest index: {closest_points[0][0]}\n")
                    report.append(f"- Distance: {closest_points[0][1]:.2f} pixels\n")
                    report.append(f"- Track point: ({closest_points[0][2][0]}, {closest_points[0][2][1]})\n\n")

                    report.append(f"**Top 5 Nearest Track Points:**\n")
                    for i, (idx, dist, (px, py)) in enumerate(closest_points[:5]):
                        report.append(f"{i+1}. Index {idx}: distance={dist:.2f}px, position=({px}, {py})\n")
                    report.append("\n")

        # Root cause analysis
        report.append("## Root Cause Analysis\n\n")

        if len(results) >= 2:
            # Compare lap 1 and lap 3
            lap1 = results[0]
            lap3 = results[1]

            dot1 = lap1['dot_position']
            dot3 = lap3['dot_position']

            if dot1 and dot3:
                y_diff = dot1[1] - dot3[1]
                idx1 = lap1['closest_points'][0][0] if lap1['closest_points'] else None
                idx3 = lap3['closest_points'][0][0] if lap3['closest_points'] else None

                report.append(f"**Key Observation:**\n")
                report.append(f"- Lap 1 dot: ({dot1[0]}, {dot1[1]}) → matched to index {idx1}\n")
                report.append(f"- Lap 3 dot: ({dot3[0]}, {dot3[1]}) → matched to index {idx3}\n")
                report.append(f"- Y-coordinate difference: {y_diff} pixel(s)\n")
                report.append(f"- Index difference: {abs(idx1 - idx3) if idx1 and idx3 else 'N/A'} indices\n\n")

                report.append("**Why does 1 pixel matter?**\n\n")
                report.append("The track path near the start/finish line is tightly spaced. A single pixel ")
                report.append("difference in Y-coordinate can be enough to make the dot closer to a different ")
                report.append("track_path point. This is especially problematic when:\n\n")
                report.append("1. The track path has multiple points within 1-2 pixels of each other\n")
                report.append("2. The red dot detection varies slightly between frames (sub-pixel centroid shifts)\n")
                report.append("3. The closest-point matching uses Euclidean distance without tolerance\n\n")

        # Recommendations
        report.append("## Recommendations\n\n")

        report.append("### 1. Use Search Window Instead of Single Closest Point\n\n")
        report.append("Instead of matching to the single closest point, find all track_path points ")
        report.append("within a radius (e.g., 3 pixels) and use the one with the smallest arc length ")
        report.append("deviation from expected position.\n\n")

        report.append("```python\n")
        report.append("# Find all points within tolerance radius\n")
        report.append("tolerance_radius = 3.0  # pixels\n")
        report.append("candidates = []\n")
        report.append("for i, (px, py) in enumerate(track_path):\n")
        report.append("    distance = sqrt((dot_x - px)**2 + (dot_y - py)**2)\n")
        report.append("    if distance <= tolerance_radius:\n")
        report.append("        candidates.append((i, distance))\n")
        report.append("\n")
        report.append("# Among candidates, pick the one closest to expected position\n")
        report.append("# (based on last known position + velocity)\n")
        report.append("```\n\n")

        report.append("### 2. Lock Start Position on First Lap Detection\n\n")
        report.append("The current implementation sets `start_position = track_path[0]` during path extraction. ")
        report.append("This is correct. However, we should ALSO capture the actual red dot pixel position ")
        report.append("on the first lap start and use that for sub-pixel refinement.\n\n")

        report.append("### 3. Use Sub-Pixel Interpolation\n\n")
        report.append("Instead of using integer pixel coordinates, interpolate between track_path points ")
        report.append("to get sub-pixel precision. This reduces sensitivity to 1-pixel variations.\n\n")

        report.append("### 4. Add Temporal Consistency Check\n\n")
        report.append("At lap start, the position should be very close to 0%. If the matched index gives ")
        report.append("a position >5%, reject it and search for a better match closer to the start line.\n\n")

        report.append("### 5. Visualize Track Path Geometry Near Start\n\n")
        report.append("Examine the track_path points near index 0, 15, and 25 to understand their spacing. ")
        report.append("If they're extremely close together, consider resampling the track path to have ")
        report.append("more uniform point spacing.\n\n")

        # Test plan
        report.append("## Validation Test Plan\n\n")
        report.append("After implementing fixes:\n\n")
        report.append("1. **Consistency Test**: Extract position at lap start for laps 1-5. All should show <1% variation.\n")
        report.append("2. **Robustness Test**: Manually shift red dot detection by ±1 pixel. Position change should be <0.5%.\n")
        report.append("3. **Arc Length Test**: Verify arc length from index 0 to indices 15 and 25. Compare to expected position.\n")
        report.append("4. **Visual Inspection**: Overlay detected positions on track map. Start positions should align.\n\n")

        # Write report
        with open(output_path, 'w') as f:
            f.writelines(report)

        print(f"✓ Saved diagnostic report: {output_path}")

    def close(self):
        """Clean up resources."""
        if self.cap:
            self.cap.release()


def main():
    """Main diagnostic routine."""

    print("="*80)
    print("RED DOT POSITION DETECTION DIAGNOSTIC")
    print("="*80)
    print("\nAnalyzing frames: 3064 (Lap 1), 9430 (Lap 3), 12431 (Lap 4)")
    print("\n")

    # Configuration
    video_path = '/Users/jakub.cieply/Personal/acc-telemetry/panorama.mp4'
    config_path = '/Users/jakub.cieply/Personal/acc-telemetry/config/roi_config.yaml'
    output_dir = '/Users/jakub.cieply/Personal/acc-telemetry/data/debug/red_dot_analysis'

    # Load ROI config
    with open(config_path, 'r') as f:
        roi_config = yaml.safe_load(f)

    # Initialize diagnostics
    diagnostics = RedDotDiagnostics(video_path, roi_config)

    if not diagnostics.open_video():
        return

    # Extract track path first
    print("\nStep 1: Extracting track path...")
    sample_frames = [0, 50, 100, 150, 200, 250, 500, 750, 1000, 1250, 1500]
    map_rois = []

    for frame_num in sample_frames:
        frame = diagnostics.get_frame_at(frame_num)
        if frame is not None:
            map_roi = diagnostics.extract_roi(frame, 'track_map')
            if map_roi is not None:
                map_rois.append(map_roi)

    if diagnostics.position_tracker.extract_track_path(map_rois):
        diagnostics.track_path = diagnostics.position_tracker.track_path
        print(f"✓ Track path extracted: {len(diagnostics.track_path)} points")
    else:
        print("Error: Could not extract track path")
        return

    # Analyze target frames
    print("\nStep 2: Analyzing target frames...")
    frames_to_analyze = [
        (3064, 1),    # Lap 1 start
        (9430, 3),    # Lap 3 start (PROBLEMATIC)
        (12431, 4)    # Lap 4 start
    ]

    results = []
    for frame_num, lap_num in frames_to_analyze:
        result = diagnostics.analyze_frame(frame_num, lap_num)
        if result:
            results.append(result)

    if not results:
        print("Error: No results to visualize")
        return

    # Generate outputs
    print("\nStep 3: Generating outputs...")

    viz_path = f"{output_dir}/dot_recognition_frames_3064_9430_12431.png"
    diagnostics.create_visualization(results, viz_path)

    report_path = f"{output_dir}/diagnostic_report.md"
    diagnostics.generate_report(results, report_path)

    # Cleanup
    diagnostics.close()

    print("\n" + "="*80)
    print("DIAGNOSTIC COMPLETE")
    print("="*80)
    print(f"\nOutput files:")
    print(f"  Visualization: {viz_path}")
    print(f"  Report:        {report_path}")
    print("\n")


if __name__ == '__main__':
    main()
