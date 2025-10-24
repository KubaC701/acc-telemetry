"""
Improved Position Tracker Module

Addresses the fundamental issues with the original implementation:
1. Better path extraction with start line detection
2. More robust red dot detection
3. Proper position calculation with start line reference
4. Better error handling and validation

Author: ACC Telemetry Extractor
"""

import cv2
import numpy as np
from typing import Optional, Tuple, List, Dict


class PositionTrackerV2:
    """
    Improved track position tracker with better start line detection and validation.
    
    Key improvements:
    - Detects start/finish line from path geometry
    - More robust red dot detection
    - Better position calculation with proper start reference
    - Comprehensive validation and error handling
    """
    
    def __init__(self):
        """Initialize the improved position tracker."""
        self.track_path: Optional[List[Tuple[int, int]]] = None
        self.total_path_pixels: int = 0  # Total number of pixels in the racing line path
        self.start_position: Optional[Tuple[int, int]] = None  # (x, y) where lap starts (set on lap change)
        self.track_center: Optional[Tuple[float, float]] = None  # (x, y) center of track
        self.start_angle: float = 0.0  # Angle from center to start position
        self.last_position: float = 0.0
        self.path_extracted: bool = False
        self.validation_passed: bool = False
        self.lap_just_started: bool = False  # Flag to capture start position on next detection
        
        # HSV color ranges for detection
        self.white_lower = np.array([0, 0, 200])
        self.white_upper = np.array([180, 30, 255])
        
        # Red dot detection - more restrictive to avoid false positives
        self.red_lower1 = np.array([0, 150, 150])
        self.red_upper1 = np.array([10, 255, 255])
        self.red_lower2 = np.array([170, 150, 150])
        self.red_upper2 = np.array([180, 255, 255])
    
    def extract_track_path(self, map_rois: List[np.ndarray], frequency_threshold: float = 0.6) -> bool:
        """
        Extract the white racing line using multi-frame frequency voting.
        
        This method uses the proven technique:
        1. Frequency voting: Keep pixels that are white in ≥60% of frames
        2. Dilate to connect segments
        3. Keep largest connected component (removes artifacts like car cage)
        4. Erode back to original thickness
        5. Intersect with raw to ensure accuracy
        
        Args:
            map_rois: List of map ROI images from different frames (recommended: 50+)
            frequency_threshold: Pixel must be white in this % of frames (default: 0.6 = 60%)
        
        Returns:
            True if path extraction successful and validated, False otherwise
        """
        if not map_rois or len(map_rois) < 10:
            print(f"❌ Error: Need at least 10 frames for path extraction, got {len(map_rois)}")
            return False
        
        print(f"🔍 Extracting track path from {len(map_rois)} frames...")
        print(f"   Method: Frequency voting ({frequency_threshold*100:.0f}% threshold)")
        
        # STEP 1: Extract white masks from each frame
        print(f"\n   Step 1: Extracting white pixels from each frame...")
        white_masks = []
        
        for i, map_roi in enumerate(map_rois):
            if map_roi is None or map_roi.size == 0:
                print(f"      ⚠️  Frame {i}: Empty ROI, skipping")
                continue
            
            # Convert to HSV and extract white pixels
            hsv = cv2.cvtColor(map_roi, cv2.COLOR_BGR2HSV)
            white_mask = cv2.inRange(hsv, self.white_lower, self.white_upper)
            white_masks.append(white_mask)
        
        if len(white_masks) < 10:
            print(f"❌ Error: Too few valid masks ({len(white_masks)})")
            return False
        
        print(f"      ✅ Extracted {len(white_masks)} white masks")
        
        # STEP 2: Calculate pixel-wise frequency (how often is each pixel white?)
        print(f"   Step 2: Computing pixel-wise white frequency...")
        mask_stack = np.stack(white_masks, axis=2).astype(np.float32)
        white_frequency = np.sum(mask_stack > 0, axis=2) / len(white_masks)
        
        # Threshold by frequency (racing line is consistently white)
        racing_line_raw = (white_frequency >= frequency_threshold).astype(np.uint8) * 255
        raw_pixels = np.sum(racing_line_raw > 0)
        print(f"      ✅ Raw outline: {raw_pixels} pixels")
        
        # STEP 3: Dilate-Filter-Erode to remove artifacts
        print(f"   Step 3: Removing small artifacts (car cage, UI elements)...")
        
        # Dilate to connect nearby segments
        kernel_dilate = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        dilated = cv2.dilate(racing_line_raw, kernel_dilate, iterations=2)
        
        # Find connected components
        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(
            dilated, connectivity=8, ltype=cv2.CV_32S
        )
        
        if num_labels <= 1:
            print("      ❌ No connected components found")
            return False
        
        # Find largest component (main racing line)
        areas = [(i, stats[i, cv2.CC_STAT_AREA]) for i in range(1, num_labels)]
        areas.sort(key=lambda x: x[1], reverse=True)
        
        largest_label = areas[0][0]
        largest_area = areas[0][1]
        
        print(f"      Found {num_labels - 1} components, keeping largest ({largest_area:.0f}px²)")
        
        # Keep only largest component
        largest_component_dilated = np.zeros_like(dilated)
        largest_component_dilated[labels == largest_label] = 255
        
        # Erode back to original thickness
        kernel_erode = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        eroded = cv2.erode(largest_component_dilated, kernel_erode, iterations=2)
        
        # Intersect with raw to ensure accuracy (don't add false pixels)
        cleaned_mask = cv2.bitwise_and(eroded, racing_line_raw)
        cleaned_pixels = np.sum(cleaned_mask > 0)
        
        print(f"      ✅ Cleaned racing line: {cleaned_pixels} pixels ({cleaned_pixels/raw_pixels*100:.1f}% of raw)")
        
        # STEP 4: Extract contour from cleaned mask
        print(f"   Step 4: Extracting racing line contour...")
        contours, _ = cv2.findContours(cleaned_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        
        if not contours:
            print("      ❌ No contours found in cleaned mask")
            return False
        
        # Get the largest contour
        largest_contour = max(contours, key=cv2.contourArea)
        contour_area = cv2.contourArea(largest_contour)
        
        print(f"      Found {len(contours)} contours, using largest ({contour_area:.1f}px²)")
        
        if contour_area < 100:
            print("      ❌ Contour too small - likely not a racing line")
            return False
        
        # Convert contour to ordered list of points
        path_points = largest_contour.reshape(-1, 2)
        
        if len(path_points) < 50:
            print(f"      ❌ Too few path points ({len(path_points)})")
            return False
        
        print(f"      ✅ Path points: {len(path_points)}")
        
        # STEP 5: Store path and calculate track center
        print(f"   Step 5: Calculating track center and storing path...")
        
        # Store results (path_points is already in order from contour)
        self.track_path = [(int(p[0]), int(p[1])) for p in path_points]
        self.total_path_pixels = len(path_points)
        
        # Calculate track center as the centroid of all path points
        path_array = np.array(self.track_path)
        center_x = np.mean(path_array[:, 0])
        center_y = np.mean(path_array[:, 1])
        self.track_center = (center_x, center_y)
        
        self.path_extracted = True
        
        print(f"      ✅ Total racing line pixels: {self.total_path_pixels}")
        print(f"      ✅ Track center: ({center_x:.1f}, {center_y:.1f})")
        print(f"      ℹ️  Start position will be set on first lap change")
        
        # STEP 6: Validate extraction
        print(f"   Step 6: Validating path extraction...")
        self.validation_passed = self._validate_path_extraction()
        
        if not self.validation_passed:
            print("      ❌ Path validation failed")
            return False
        
        print(f"\n✅ Track path extraction successful and validated!")
        return True
    
    
    def _validate_path_extraction(self) -> bool:
        """
        Validate that the extracted path makes sense.
        
        Returns:
            True if path is valid, False otherwise
        """
        if not self.track_path or len(self.track_path) < 50:
            print("   ❌ Validation: Too few path points")
            return False
        
        if self.total_path_pixels < 100:
            print("   ❌ Validation: Path too short")
            return False
        
        # Check if path has reasonable shape (not just a straight line)
        path_array = np.array(self.track_path)
        x_range = np.max(path_array[:, 0]) - np.min(path_array[:, 0])
        y_range = np.max(path_array[:, 1]) - np.min(path_array[:, 1])
        
        if x_range < 50 or y_range < 50:
            print(f"   ❌ Validation: Path too small (x_range: {x_range}, y_range: {y_range})")
            return False
        
        print(f"   ✅ Validation: Path size {x_range}x{y_range}, {self.total_path_pixels} pixels")
        return True
    
    def detect_red_dot(self, map_roi: np.ndarray) -> Optional[Tuple[int, int]]:
        """
        Detect the red dot position with improved validation.
        
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
        
        # Find contours of red regions
        contours, _ = cv2.findContours(red_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            return None
        
        # Find the largest red contour (should be the car dot)
        largest_contour = max(contours, key=cv2.contourArea)
        contour_area = cv2.contourArea(largest_contour)
        
        # Validate contour size (car dot should be reasonably sized)
        if contour_area < 5 or contour_area > 200:  # Too small or too large
            return None
        
        # Calculate centroid
        moments = cv2.moments(largest_contour)
        if moments['m00'] == 0:
            return None
        
        cx = int(moments['m10'] / moments['m00'])
        cy = int(moments['m01'] / moments['m00'])
        
        return (cx, cy)
    
    def calculate_position(self, dot_x: int, dot_y: int) -> float:
        """
        Calculate position percentage using angular position around track center.
        
        This method is independent of contour ordering:
        1. Calculate angle from track center to red dot
        2. Calculate angle from track center to start position  
        3. Position = (angle_difference / 360°) × 100%
        
        Args:
            dot_x: Red dot x-coordinate
            dot_y: Red dot y-coordinate
        
        Returns:
            Position percentage (0.0 - 100.0) from start position
        """
        if not self.path_extracted or self.track_center is None or self.start_position is None:
            return 0.0
        
        # Calculate angle from center to current red dot position
        dx = dot_x - self.track_center[0]
        dy = dot_y - self.track_center[1]
        current_angle = np.arctan2(dy, dx)  # Returns -π to +π
        
        # Calculate angular difference from start position
        # Convert to degrees for easier handling
        current_angle_deg = np.degrees(current_angle)
        start_angle_deg = np.degrees(self.start_angle)
        
        # Calculate counter-clockwise angle from start to current
        # (ACC tracks typically go counter-clockwise when viewed from above)
        angle_diff = start_angle_deg - current_angle_deg
        
        # Normalize to 0-360 range (handle wraparound)
        if angle_diff < 0:
            angle_diff += 360
        elif angle_diff >= 360:
            angle_diff -= 360
        
        # Convert to percentage
        position = (angle_diff / 360.0) * 100.0
        
        # Clamp to valid range
        position = max(0.0, min(100.0, position))
        
        return position
    
    def extract_position(self, map_roi: np.ndarray) -> float:
        """
        Extract track position from map ROI.
        
        Args:
            map_roi: Map ROI image from current frame
        
        Returns:
            Position percentage (0.0 - 100.0)
        """
        if not self.path_extracted or not self.validation_passed:
            return 0.0
        
        # Detect red dot
        dot_position = self.detect_red_dot(map_roi)
        
        if dot_position is None:
            # Red dot not detected, return last known position
            return self.last_position
        
        dot_x, dot_y = dot_position
        
        # If lap just started, set current position as new start point
        if self.lap_just_started:
            # Set the red dot position as the start position
            self.start_position = (dot_x, dot_y)
            
            # Calculate the angle from track center to start position
            dx = dot_x - self.track_center[0]
            dy = dot_y - self.track_center[1]
            self.start_angle = np.arctan2(dy, dx)
            
            self.lap_just_started = False
            
            start_angle_deg = np.degrees(self.start_angle)
            print(f"      ✅ New lap start set at ({dot_x}, {dot_y}), angle: {start_angle_deg:.1f}°")
            
            # Return 0.0 for the first frame of new lap
            self.last_position = 0.0
            return 0.0
        
        # Calculate position normally
        position = self.calculate_position(dot_x, dot_y)
        
        # Store for next frame
        self.last_position = position
        
        return position
    
    def reset_for_new_lap(self) -> None:
        """
        Reset position tracking for a new lap.
        
        This method MUST be called on the FIRST frame after a lap number change.
        It sets the current red dot position as the new start position (pixel index 0).
        
        The next call to extract_position() will detect the red dot and use that
        pixel index as the new start_pixel_index.
        """
        # Set flag to capture start position on next detection
        self.lap_just_started = True
        print(f"      🏁 Lap reset triggered - next detected position will be new start (0%)")
    
    def is_ready(self) -> bool:
        """
        Check if position tracker is ready to track position.
        
        Returns:
            True if track path has been extracted and validated
        """
        return self.path_extracted and self.validation_passed and self.track_path is not None
    
    def get_debug_info(self) -> Dict:
        """
        Get debug information about the current state.
        
        Returns:
            Dictionary with debug information
        """
        return {
            'path_extracted': self.path_extracted,
            'validation_passed': self.validation_passed,
            'path_points': len(self.track_path) if self.track_path else 0,
            'total_path_pixels': self.total_path_pixels,
            'start_position': self.start_position,
            'start_angle_deg': np.degrees(self.start_angle) if self.start_angle else 0,
            'track_center': self.track_center,
            'last_position': self.last_position,
            'lap_just_started': self.lap_just_started
        }
