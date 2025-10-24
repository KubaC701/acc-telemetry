"""
Position Tracker Module

Extracts track position from ACC minimap by tracking the red dot along the white racing line.
Calculates position as percentage (0-100%) of lap completion.

Author: ACC Telemetry Extractor
"""

import cv2
import numpy as np
from typing import Optional, Tuple, List


class PositionTracker:
    """
    Tracks car position on track by analyzing the minimap.
    
    Uses computer vision to:
    1. Extract white racing line from minimap (one-time extraction)
    2. Detect red dot position (every frame)
    3. Calculate position percentage by measuring arc length along path
    
    Attributes:
        track_path: List of (x, y) points representing the racing line
        total_path_length: Total arc length of the racing line in pixels
        last_position: Last known position percentage (for interpolation)
        path_extracted: Whether track path has been successfully extracted
    """
    
    def __init__(self):
        """Initialize the position tracker."""
        self.track_path: Optional[List[Tuple[int, int]]] = None
        self.total_path_length: float = 0.0
        self.last_position: float = 0.0
        self.path_extracted: bool = False
        
        # HSV color ranges for detection
        # White racing line: high value, low saturation
        self.white_lower = np.array([0, 0, 200])
        self.white_upper = np.array([180, 30, 255])
        
        # Red dot: two ranges because red wraps around HSV hue (0-180)
        self.red_lower1 = np.array([0, 120, 120])
        self.red_upper1 = np.array([10, 255, 255])
        self.red_lower2 = np.array([170, 120, 120])
        self.red_upper2 = np.array([180, 255, 255])
    
    def extract_track_path(self, map_rois: List[np.ndarray]) -> bool:
        """
        Extract the racing line from multiple map frames.
        
        Uses grayscale thresholding instead of HSV, as the racing line appears
        as light gray (not pure white). Combines multiple frames to avoid gaps
        where the red dot occludes the path.
        
        Args:
            map_rois: List of map ROI images from different frames
        
        Returns:
            True if path extraction successful, False otherwise
        """
        if not map_rois or len(map_rois) == 0:
            print("Warning: No map ROIs provided for path extraction")
            return False
        
        # Combine masks from all frames to fill gaps
        # BUT: Filter out frames with too much noise (bright backgrounds)
        combined_mask = None
        good_frames = 0
        
        for map_roi in map_rois:
            if map_roi is None or map_roi.size == 0:
                continue
            
            # Convert to grayscale
            gray = cv2.cvtColor(map_roi, cv2.COLOR_BGR2GRAY)
            
            # Threshold to extract bright white pixels (racing line)
            # Racing line appears at gray values 200+
            # Lower thresholds capture too much background/borders
            _, binary_mask = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
            
            # Filter out noisy frames
            # Clean frames have ~1000-2000 white pixels (just the racing line)
            # Noisy frames have >3000 white pixels (bright backgrounds)
            white_pixel_count = np.sum(binary_mask > 0)
            
            if white_pixel_count > 2500:
                # Skip this frame - too much noise
                print(f"   ⚠️  Skipping noisy frame: {white_pixel_count} white pixels")
                continue
            
            good_frames += 1
            
            # Combine with previous masks
            if combined_mask is None:
                combined_mask = binary_mask
            else:
                combined_mask = cv2.bitwise_or(combined_mask, binary_mask)
        
        print(f"   ✅ Combined {good_frames}/{len(map_rois)} frames (filtered out noise)")
        
        if combined_mask is None:
            print("Warning: Failed to create combined mask for path extraction")
            return False
        
        # Clean up the mask with morphological operations
        # Use CLOSE to connect gaps, but skip OPEN to avoid breaking the line
        kernel = np.ones((2, 2), np.uint8)  # Smaller kernel to preserve thin lines
        combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_CLOSE, kernel)
        
        # Find contours of the racing line
        contours, _ = cv2.findContours(combined_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        
        if not contours:
            print("Warning: No contours found in track path extraction")
            return False
        
        # Since we've filtered out noisy frames, the largest contour should be the racing line
        # Just select it directly
        largest_contour = max(contours, key=cv2.contourArea)
        contour_area = cv2.contourArea(largest_contour)
        
        print(f"   📍 Selected contour: area={contour_area:.1f}px²")
        
        # Convert contour to ordered list of points
        # Reshape from (n, 1, 2) to (n, 2)
        path_points = largest_contour.reshape(-1, 2)
        
        # Calculate total path length
        total_length = 0.0
        for i in range(len(path_points) - 1):
            p1 = path_points[i]
            p2 = path_points[i + 1]
            segment_length = np.linalg.norm(p2 - p1)
            total_length += segment_length
        
        # Close the loop (connect last point to first)
        if len(path_points) > 0:
            loop_closure = np.linalg.norm(path_points[-1] - path_points[0])
            total_length += loop_closure
        
        self.track_path = [(int(p[0]), int(p[1])) for p in path_points]
        self.total_path_length = total_length
        self.path_extracted = True
        
        print(f"Track path extracted: {len(self.track_path)} points, {total_length:.1f}px total length")
        return True
    
    def detect_red_dot(self, map_roi: np.ndarray) -> Optional[Tuple[int, int]]:
        """
        Detect the red dot position on the minimap.
        
        Args:
            map_roi: Map ROI image
        
        Returns:
            (x, y) coordinates of red dot center, or None if not detected
        """
        if map_roi is None or map_roi.size == 0:
            return None
        
        # Convert to HSV
        hsv = cv2.cvtColor(map_roi, cv2.COLOR_BGR2HSV)
        
        # Create masks for both red ranges
        red_mask1 = cv2.inRange(hsv, self.red_lower1, self.red_upper1)
        red_mask2 = cv2.inRange(hsv, self.red_lower2, self.red_upper2)
        
        # Combine masks
        red_mask = cv2.bitwise_or(red_mask1, red_mask2)
        
        # Find centroid using moments
        moments = cv2.moments(red_mask)
        
        if moments['m00'] == 0:
            # No red pixels found
            return None
        
        # Calculate centroid
        cx = int(moments['m10'] / moments['m00'])
        cy = int(moments['m01'] / moments['m00'])
        
        return (cx, cy)
    
    def calculate_position(self, dot_x: int, dot_y: int) -> float:
        """
        Calculate position percentage by finding closest point on path.
        
        Args:
            dot_x: Red dot x-coordinate
            dot_y: Red dot y-coordinate
        
        Returns:
            Position percentage (0.0 - 100.0)
        """
        if not self.path_extracted or not self.track_path or self.total_path_length == 0:
            return 0.0
        
        # Find closest point on path to red dot
        min_distance = float('inf')
        closest_index = 0
        
        dot_pos = np.array([dot_x, dot_y])
        
        for i, (px, py) in enumerate(self.track_path):
            path_point = np.array([px, py])
            distance = np.linalg.norm(dot_pos - path_point)
            
            if distance < min_distance:
                min_distance = distance
                closest_index = i
        
        # Calculate arc length from start to closest point
        arc_length = 0.0
        for i in range(closest_index):
            p1 = np.array(self.track_path[i])
            p2 = np.array(self.track_path[i + 1])
            segment_length = np.linalg.norm(p2 - p1)
            arc_length += segment_length
        
        # Calculate position percentage
        position = (arc_length / self.total_path_length) * 100.0
        
        # Clamp to valid range
        position = max(0.0, min(100.0, position))
        
        return position
    
    def extract_position(self, map_roi: np.ndarray) -> float:
        """
        Extract track position from map ROI.
        
        Main method called each frame to get current position.
        
        Args:
            map_roi: Map ROI image from current frame
        
        Returns:
            Position percentage (0.0 - 100.0)
        """
        if not self.path_extracted:
            # Path not yet extracted, return 0
            return 0.0
        
        # Detect red dot
        dot_position = self.detect_red_dot(map_roi)
        
        if dot_position is None:
            # Red dot not detected, return last known position
            # (Interpolation could be improved with velocity estimation)
            return self.last_position
        
        # Calculate position
        dot_x, dot_y = dot_position
        position = self.calculate_position(dot_x, dot_y)
        
        # Store for next frame
        self.last_position = position
        
        return position
    
    def reset_for_new_lap(self) -> None:
        """
        Reset position tracking for a new lap.
        
        Called when lap transition is detected. In practice, position naturally
        wraps around (100% → 0%), so this is mainly for reference tracking.
        """
        # Position naturally wraps, but we can reset last_position for clarity
        # The algorithm handles wrap-around automatically via modulo on path index
        pass
    
    def is_ready(self) -> bool:
        """
        Check if position tracker is ready to track position.
        
        Returns:
            True if track path has been extracted and tracker is ready
        """
        return self.path_extracted and self.track_path is not None

