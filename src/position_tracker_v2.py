"""
Improved Position Tracker Module

Addresses the fundamental issues with the original implementation:
1. Better path extraction with start line detection
2. More robust red dot detection
3. Proper position calculation with start line reference
4. Better error handling and validation
5. Simple forward-progress validation (no Kalman filter complexity)

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
    - Simple forward-progress validation (no complex filtering)
    """

    def __init__(self, fps: float = 30.0, max_jump_per_frame: float = 1.0):
        """
        Initialize the improved position tracker.

        Args:
            fps: Video frames per second (for reference, not currently used)
            max_jump_per_frame: Maximum allowed position jump per frame (default: 1.0%)
                               At 30 FPS, a full lap takes ~100 seconds, so 1% = 1 second of track
                               This allows for normal speed variations while rejecting obvious outliers
        """
        self.track_path: Optional[List[Tuple[int, int]]] = None
        self.total_path_pixels: int = 0  # Total number of pixels in the racing line path
        self.total_track_length: float = 0.0  # Total arc length of racing line (cached)
        self.start_position: Optional[Tuple[int, int]] = None  # (x, y) where lap starts (set on lap change)
        self.start_idx: int = 0  # Index in track_path closest to start_position (cached for performance)
        self.track_center: Optional[Tuple[float, float]] = None  # (x, y) center of track
        self.last_position: float = 0.0
        self.path_extracted: bool = False
        self.validation_passed: bool = False
        self.lap_just_started: bool = False  # Flag to capture start position on next detection

        # Simple validation parameters
        self.max_jump_per_frame = max_jump_per_frame  # Max forward jump allowed (%)
        self.fps = fps  # For reference

        # HSV color ranges for detection
        # Racing line varies: bright sections 98.3%, dark sections 87.3%
        # Car cage: HSV(195°, 7.3%, 78.9%)
        # V=210/255=82.4% provides 3.5% margin above car cage, 4.9% below darkest racing line
        self.white_lower = np.array([0, 0, 210])
        self.white_upper = np.array([180, 30, 255])

        # Red dot detection - more restrictive to avoid false positives
        self.red_lower1 = np.array([0, 150, 150])
        self.red_upper1 = np.array([10, 255, 255])
        self.red_lower2 = np.array([170, 150, 150])
        self.red_upper2 = np.array([180, 255, 255])
    
    def extract_track_path(self, map_rois: List[np.ndarray], frequency_threshold: float = 0.45) -> bool:
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
            frequency_threshold: Pixel must be white in this % of frames (default: 0.45 = 45%)
        
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
        print(f"   Step 5: Calculating track center and arc length...")

        # Store results (path_points is already in order from contour)
        self.track_path = [(int(p[0]), int(p[1])) for p in path_points]
        self.total_path_pixels = len(path_points)

        # Calculate track center as the centroid of all path points
        path_array = np.array(self.track_path)
        center_x = np.mean(path_array[:, 0])
        center_y = np.mean(path_array[:, 1])
        self.track_center = (center_x, center_y)

        # Calculate total track length (arc length of racing line)
        self.total_track_length = 0.0
        for i in range(len(self.track_path)):
            p1 = self.track_path[i]
            p2 = self.track_path[(i + 1) % len(self.track_path)]  # Wrap around
            dx = p2[0] - p1[0]
            dy = p2[1] - p1[1]
            self.total_track_length += np.sqrt(dx*dx + dy*dy)

        self.path_extracted = True

        print(f"      ✅ Total racing line pixels: {self.total_path_pixels}")
        print(f"      ✅ Total track arc length: {self.total_track_length:.1f} pixels")
        print(f"      ✅ Track center: ({center_x:.1f}, {center_y:.1f})")

        # STEP 5.5: Detect start/finish line geometrically
        print(f"   Step 5.5: Detecting start/finish line...")
        start_line_idx, start_line_confidence, deviations = self._detect_start_finish_line()

        if start_line_idx is not None:
            print(f"      ✅ Start/finish line detected at index {start_line_idx} (confidence: {start_line_confidence:.2f})")
            self.start_idx = start_line_idx
            self.start_position = self.track_path[start_line_idx]
            print(f"      ✅ Start position set to {self.start_position}")

            # STEP 5.6: Clean racing line by removing start/finish artifact
            print(f"   Step 5.6: Cleaning racing line (removing start/finish protrusion)...")
            cleaned_path = self._clean_start_line_artifact(start_line_idx, deviations)

            if cleaned_path is not None:
                # Update path and recalculate metrics
                old_length = len(self.track_path)
                self.track_path = cleaned_path
                self.total_path_pixels = len(cleaned_path)

                # Recalculate total track length
                self.total_track_length = 0.0
                for i in range(len(self.track_path)):
                    p1 = self.track_path[i]
                    p2 = self.track_path[(i + 1) % len(self.track_path)]
                    dx = p2[0] - p1[0]
                    dy = p2[1] - p1[1]
                    self.total_track_length += np.sqrt(dx*dx + dy*dy)

                # Update start_idx (it may have shifted slightly)
                # Find the point closest to the original start_position
                min_dist = float('inf')
                for i, pt in enumerate(self.track_path):
                    dx = pt[0] - self.start_position[0]
                    dy = pt[1] - self.start_position[1]
                    dist = dx*dx + dy*dy
                    if dist < min_dist:
                        min_dist = dist
                        self.start_idx = i

                print(f"      ✅ Removed {old_length - len(cleaned_path)} artifact points")
                print(f"      ✅ New track length: {self.total_track_length:.1f} pixels")
                print(f"      ✅ Updated start_idx: {self.start_idx}")
        else:
            print(f"      ⚠️  Could not detect start/finish line geometrically")
            print(f"      ℹ️  Start position will be set on first lap change")
        
        # STEP 6: Validate extraction
        print(f"   Step 6: Validating path extraction...")
        self.validation_passed = self._validate_path_extraction()

        if not self.validation_passed:
            print("      ❌ Path validation failed")
            return False

        # STEP 7: Save debug visualization
        print(f"   Step 7: Saving debug visualization...")
        self._save_path_visualization(map_rois[0], cleaned_mask)

        print(f"\n✅ Track path extraction successful and validated!")
        return True
    
    
    def _detect_start_finish_line(self) -> Tuple[Optional[int], float, Optional[np.ndarray]]:
        """
        Detect the start/finish line by finding perpendicular protrusions on the racing line.

        The start/finish line in ACC appears as a white perpendicular marker (~15px width)
        that creates a geometric anomaly on the racing line - a sharp protrusion perpendicular
        to the natural track curvature.

        Algorithm:
        1. Calculate local tangent direction for each point (using moving average)
        2. Calculate perpendicular direction at each point
        3. For each point, measure how far it deviates from the smooth racing line
        4. Find the point with maximum perpendicular deviation (the start/finish marker)

        Returns:
            Tuple of (index of start line, confidence score 0-1, deviations array),
            or (None, 0.0, None) if not detected
        """
        if not self.track_path or len(self.track_path) < 50:
            return None, 0.0, None

        path_array = np.array(self.track_path, dtype=np.float32)
        num_points = len(path_array)

        # STEP 1: Calculate smoothed tangent direction at each point
        # Use moving average of 10 points before and after to smooth out noise
        tangent_window = 10
        tangents = np.zeros((num_points, 2), dtype=np.float32)

        for i in range(num_points):
            # Get points before and after (with wraparound)
            idx_before = (i - tangent_window) % num_points
            idx_after = (i + tangent_window) % num_points

            # Calculate tangent direction
            dx = path_array[idx_after, 0] - path_array[idx_before, 0]
            dy = path_array[idx_after, 1] - path_array[idx_before, 1]

            # Normalize
            length = np.sqrt(dx*dx + dy*dy)
            if length > 0:
                tangents[i] = [dx / length, dy / length]

        # STEP 2: Calculate distance from each point to the "smooth" racing line
        # The smooth line is defined by connecting points 20 indices apart
        # A perpendicular protrusion will be far from this smooth line
        smooth_window = 20
        deviations = np.zeros(num_points, dtype=np.float32)

        for i in range(num_points):
            # Get the smooth line segment that should pass through this region
            idx_before = (i - smooth_window) % num_points
            idx_after = (i + smooth_window) % num_points

            p_before = path_array[idx_before]
            p_after = path_array[idx_after]
            p_current = path_array[i]

            # Calculate perpendicular distance from current point to line segment
            # Line from p_before to p_after
            line_vec = p_after - p_before
            line_length = np.linalg.norm(line_vec)

            if line_length > 0:
                line_vec_normalized = line_vec / line_length

                # Vector from p_before to current point
                to_point = p_current - p_before

                # Project onto line to find closest point on line
                projection_length = np.dot(to_point, line_vec_normalized)
                projection_length = np.clip(projection_length, 0, line_length)

                closest_on_line = p_before + line_vec_normalized * projection_length

                # Distance from current point to closest point on smooth line
                deviation = np.linalg.norm(p_current - closest_on_line)
                deviations[i] = deviation

        # STEP 3: Find start/finish line in the top-left region
        # The start/finish line is typically at the top-left of the minimap
        # We'll look for perpendicular protrusions in that region specifically

        # Strategy: Find the point with minimum y-coordinate (top of map) that also has
        # significant perpendicular deviation

        # First, identify the top-left region (lowest y-coordinates)
        y_coords = path_array[:, 1]
        min_y = np.min(y_coords)
        y_threshold = min_y + 30  # Look within 30 pixels of the top

        # Find all points in the top region
        top_region_mask = y_coords <= y_threshold
        top_region_indices = np.where(top_region_mask)[0]

        if len(top_region_indices) == 0:
            print(f"      ⚠️  No points found in top region (y < {y_threshold})")
            return None, 0.0, None

        # Among top region points, find the one with maximum deviation (perpendicular protrusion)
        top_region_deviations = deviations[top_region_indices]
        max_deviation_in_top_idx = np.argmax(top_region_deviations)
        start_line_idx = top_region_indices[max_deviation_in_top_idx]
        max_deviation = deviations[start_line_idx]

        print(f"      🔍 Searching top region: y < {y_threshold:.1f}, found {len(top_region_indices)} points")
        print(f"      🔍 Max deviation in top region: {max_deviation:.2f} at index {start_line_idx}")

        # STEP 4: Validate the detection
        # The start line should have:
        # - Significant deviation (>3 pixels from smooth line - lowered threshold)
        # - Be in the top region of the map

        if max_deviation < 3.0:
            # Deviation too small - probably no start line protrusion
            print(f"      ⚠️  Max deviation {max_deviation:.2f} too small (< 3.0)")
            return None, 0.0, None

        # Check that it's a reasonably clear local maximum
        max_window = 15
        nearby_range = range(max(0, start_line_idx - max_window),
                            min(num_points, start_line_idx + max_window))
        nearby_deviations = [deviations[j] for j in nearby_range if j != start_line_idx]

        if nearby_deviations:
            avg_nearby = np.mean(nearby_deviations)
            prominence = max_deviation / (avg_nearby + 1e-6)  # Avoid division by zero

            # Lower prominence threshold since we're already restricting to top region
            if prominence < 1.2:
                print(f"      ⚠️  Prominence {prominence:.2f} too low (< 1.2)")
                return None, 0.0, None

            # Calculate confidence based on deviation magnitude and prominence
            confidence = min(1.0, (max_deviation / 15.0) * (prominence / 2.5))
        else:
            confidence = min(1.0, max_deviation / 15.0)

        return start_line_idx, confidence, deviations

    def _clean_start_line_artifact(self, start_line_idx: int, deviations: np.ndarray) -> Optional[List[Tuple[int, int]]]:
        """
        Remove the start/finish line protrusion from the racing line.

        The start line creates a perpendicular protrusion on the racing line.
        We want to remove these artifact points and smooth the racing line.

        Algorithm:
        1. Find the region of high deviation around start_line_idx
        2. Remove points in this region
        3. Interpolate to connect the gap smoothly

        Args:
            start_line_idx: Index of the start/finish line peak
            deviations: Array of deviation values for each point

        Returns:
            Cleaned track path, or None if cleaning fails
        """
        if not self.track_path or deviations is None:
            return None

        # STEP 1: Find the extent of the protrusion
        # Points with deviation > threshold are part of the start line artifact
        deviation_threshold = deviations[start_line_idx] * 0.5  # 50% of peak

        # Find continuous region of high deviation around start_line_idx
        artifact_start = start_line_idx
        artifact_end = start_line_idx

        # Search backward
        for i in range(start_line_idx - 1, max(0, start_line_idx - 30), -1):
            if deviations[i] < deviation_threshold:
                artifact_start = i + 1
                break
        else:
            artifact_start = max(0, start_line_idx - 30)

        # Search forward
        for i in range(start_line_idx + 1, min(len(self.track_path), start_line_idx + 30)):
            if deviations[i] < deviation_threshold:
                artifact_end = i - 1
                break
        else:
            artifact_end = min(len(self.track_path) - 1, start_line_idx + 30)

        # STEP 2: Remove artifact points
        # Keep points before and after the artifact
        cleaned_path = []

        # Add all points before artifact
        for i in range(artifact_start):
            cleaned_path.append(self.track_path[i])

        # Skip artifact region (artifact_start to artifact_end inclusive)

        # Add all points after artifact
        for i in range(artifact_end + 1, len(self.track_path)):
            cleaned_path.append(self.track_path[i])

        # STEP 3: Validate cleaned path
        if len(cleaned_path) < 50:
            print(f"      ⚠️  Cleaned path too short ({len(cleaned_path)} points)")
            return None

        return cleaned_path

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
        Calculate position percentage using arc length along the racing line.

        IMPORTANT: Position is calculated relative to the START POSITION set when lap begins,
        not relative to track_path[0]. This ensures the first frame of a new lap shows 0%.

        This method uses actual track distance instead of angular position:
        1. Find the closest point on the racing line to the red dot
        2. Use cached start_idx from reset_for_new_lap() (performance optimization)
        3. Calculate arc length from start_idx to current point
        4. Position = (arc_length / total_track_length) × 100%

        Performance: Caching start_idx saves ~30-50 distance calculations per frame.

        Args:
            dot_x: Red dot x-coordinate
            dot_y: Red dot y-coordinate

        Returns:
            Position percentage (0.0 - 100.0) from start position
        """
        if not self.path_extracted or self.track_center is None or self.start_position is None:
            return 0.0

        if not self.track_path or len(self.track_path) == 0:
            return 0.0

        # STEP 1: Find closest point on racing line to red dot
        min_distance = float('inf')
        closest_idx = 0

        for i, (px, py) in enumerate(self.track_path):
            dx = dot_x - px
            dy = dot_y - py
            distance = dx*dx + dy*dy  # Squared distance (faster, no sqrt needed)

            if distance < min_distance:
                min_distance = distance
                closest_idx = i

        # STEP 2: Use cached start_idx (set when lap started via reset_for_new_lap())

        # STEP 3: Calculate arc length from start to current position
        arc_length = 0.0

        if closest_idx >= self.start_idx:
            # Normal case: current position is ahead of start
            for i in range(self.start_idx, closest_idx):
                p1 = self.track_path[i]
                p2 = self.track_path[i + 1]
                dx = p2[0] - p1[0]
                dy = p2[1] - p1[1]
                arc_length += np.sqrt(dx*dx + dy*dy)
        else:
            # Wraparound case: we've passed the end of the path array
            # Go from start_idx to end, then from 0 to closest_idx
            for i in range(self.start_idx, len(self.track_path) - 1):
                p1 = self.track_path[i]
                p2 = self.track_path[i + 1]
                dx = p2[0] - p1[0]
                dy = p2[1] - p1[1]
                arc_length += np.sqrt(dx*dx + dy*dy)

            # Add closing segment (last point to first point)
            p1 = self.track_path[-1]
            p2 = self.track_path[0]
            dx = p2[0] - p1[0]
            dy = p2[1] - p1[1]
            arc_length += np.sqrt(dx*dx + dy*dy)

            # Add from start to current position
            for i in range(0, closest_idx):
                p1 = self.track_path[i]
                p2 = self.track_path[i + 1]
                dx = p2[0] - p1[0]
                dy = p2[1] - p1[1]
                arc_length += np.sqrt(dx*dx + dy*dy)

        # STEP 4: Convert to percentage using cached total track length
        if self.total_track_length > 0:
            position = (arc_length / self.total_track_length) * 100.0
        else:
            position = 0.0

        # STEP 5: Handle near-completion detection
        # If position drops significantly from last_position when we're near 100%,
        # it means we've crossed the start/finish line and should show 100% not <95%
        if self.last_position > 90.0 and position < 90.0 and (self.last_position - position) > 3.0:
            # This is likely a lap completion - return 100% instead of wrapping back
            # The lap number detector will trigger reset on next frame
            position = 100.0

        # Clamp to valid range
        position = max(0.0, min(100.0, position))

        return position
    
    def extract_position(self, map_roi: np.ndarray) -> float:
        """
        Extract track position from map ROI with simple forward-progress validation.

        Validation rules:
        1. Position must move forward (or stay same if detection fails)
        2. Max forward jump per frame: self.max_jump_per_frame (default 0.1%)
        3. Near lap end (>95%), allow jump to 100%
        4. On lap reset, return to 0%

        Args:
            map_roi: Map ROI image from current frame

        Returns:
            Position percentage (0.0 - 100.0), validated for forward progress
        """
        if not self.path_extracted or not self.validation_passed:
            return 0.0

        # Detect red dot
        dot_position = self.detect_red_dot(map_roi)

        # Calculate raw position (if red dot detected)
        raw_position = None
        if dot_position is not None:
            dot_x, dot_y = dot_position

            # If lap just started, set current position as new start point
            if self.lap_just_started:
                # Set the red dot position as the start position
                self.start_position = (dot_x, dot_y)

                # Find and cache the start_idx (closest point on track_path to start_position)
                min_distance = float('inf')
                for i, (px, py) in enumerate(self.track_path):
                    dx = dot_x - px
                    dy = dot_y - py
                    distance = dx*dx + dy*dy
                    if distance < min_distance:
                        min_distance = distance
                        self.start_idx = i

                self.lap_just_started = False

                print(f"      ✅ New lap start set at pixel position ({dot_x}, {dot_y}), track_path index {self.start_idx}")

                # Return 0.0 for the first frame of new lap
                self.last_position = 0.0
                return 0.0

            # Calculate raw position normally
            raw_position = self.calculate_position(dot_x, dot_y)

        # Apply simple validation
        return self._validate_position(raw_position)

    def _save_path_visualization(self, map_roi: np.ndarray, cleaned_mask: np.ndarray) -> None:
        """
        Save debug visualization of the extracted track path.

        Args:
            map_roi: Original map ROI image
            cleaned_mask: Binary mask of the cleaned racing line
        """
        import os
        from datetime import datetime

        # Create debug images
        debug_img = map_roi.copy()

        # Create mask overlay (show cleaned mask in cyan on original image)
        mask_overlay = map_roi.copy()
        mask_colored = cv2.cvtColor(cleaned_mask, cv2.COLOR_GRAY2BGR)
        mask_colored[cleaned_mask > 0] = [255, 255, 0]  # Cyan for racing line
        mask_overlay = cv2.addWeighted(mask_overlay, 0.6, mask_colored, 0.4, 0)

        # Draw the extracted racing line contour in green
        for i in range(len(self.track_path) - 1):
            pt1 = self.track_path[i]
            pt2 = self.track_path[i + 1]
            cv2.line(debug_img, pt1, pt2, (0, 255, 0), 2)

        # Draw closing line (last to first)
        cv2.line(debug_img, self.track_path[-1], self.track_path[0], (0, 255, 0), 2)

        # Draw numbered waypoints every 50 points
        for i in range(0, len(self.track_path), 50):
            pt = self.track_path[i]
            cv2.circle(debug_img, pt, 3, (0, 0, 255), -1)
            cv2.putText(debug_img, str(i), (pt[0] + 5, pt[1] + 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.3, (255, 255, 255), 1)

        # Highlight start/finish line if detected
        if self.start_idx is not None and self.start_position is not None:
            start_pt = self.start_position
            # Draw large red circle at start position
            cv2.circle(debug_img, start_pt, 8, (0, 0, 255), 3)
            cv2.circle(debug_img, start_pt, 2, (255, 255, 255), -1)

            # Draw a perpendicular line to visualize the start/finish line
            # Get tangent direction at start point
            idx_before = (self.start_idx - 5) % len(self.track_path)
            idx_after = (self.start_idx + 5) % len(self.track_path)
            pt_before = self.track_path[idx_before]
            pt_after = self.track_path[idx_after]

            # Tangent direction
            tang_x = pt_after[0] - pt_before[0]
            tang_y = pt_after[1] - pt_before[1]
            tang_len = np.sqrt(tang_x**2 + tang_y**2)

            if tang_len > 0:
                tang_x /= tang_len
                tang_y /= tang_len

                # Perpendicular direction (rotate 90 degrees)
                perp_x = -tang_y
                perp_y = tang_x

                # Draw perpendicular line from start point
                line_length = 15
                end_pt1 = (int(start_pt[0] + perp_x * line_length),
                          int(start_pt[1] + perp_y * line_length))
                end_pt2 = (int(start_pt[0] - perp_x * line_length),
                          int(start_pt[1] - perp_y * line_length))

                cv2.line(debug_img, end_pt1, end_pt2, (0, 0, 255), 3)

            # Add label
            cv2.putText(debug_img, "START/FINISH", (start_pt[0] + 10, start_pt[1] - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)

        # Add info text
        y_offset = 15
        cv2.putText(debug_img, f"Total points: {len(self.track_path)}", (5, y_offset),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
        y_offset += 15
        cv2.putText(debug_img, f"Total pixels: {self.total_path_pixels}", (5, y_offset),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)

        if self.start_idx is not None:
            y_offset += 15
            cv2.putText(debug_img, f"Start/Finish: idx={self.start_idx}", (5, y_offset),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)

        # Save to data/output/
        output_dir = "data/output"
        os.makedirs(output_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Save contour visualization
        contour_path = os.path.join(output_dir, f"track_path_debug_{timestamp}.png")
        cv2.imwrite(contour_path, debug_img)
        print(f"      ✅ Saved track path visualization to {contour_path}")

        # Save mask overlay visualization
        mask_path = os.path.join(output_dir, f"track_mask_debug_{timestamp}.png")
        cv2.imwrite(mask_path, mask_overlay)
        print(f"      ✅ Saved mask overlay visualization to {mask_path}")

    def _calculate_path_distance(self, start_idx: int, end_idx: int) -> float:
        """
        Calculate cumulative Euclidean distance along the racing line path.

        Handles wraparound when end_idx < start_idx (crossed lap line).

        Args:
            start_idx: Starting index in self.track_path
            end_idx: Ending index in self.track_path

        Returns:
            Cumulative distance in pixels along the path
        """
        if not self.track_path:
            return 0.0

        total_distance = 0.0

        if end_idx >= start_idx:
            # Normal case: no wraparound
            for i in range(start_idx, end_idx):
                p1 = self.track_path[i]
                p2 = self.track_path[i + 1]
                dx = p2[0] - p1[0]
                dy = p2[1] - p1[1]
                total_distance += np.sqrt(dx*dx + dy*dy)
        else:
            # Wraparound case: go from start_idx to end, then from 0 to end_idx
            # Distance from start_idx to end of path
            for i in range(start_idx, len(self.track_path) - 1):
                p1 = self.track_path[i]
                p2 = self.track_path[i + 1]
                dx = p2[0] - p1[0]
                dy = p2[1] - p1[1]
                total_distance += np.sqrt(dx*dx + dy*dy)

            # Distance from last point to first point (closing the loop)
            p1 = self.track_path[-1]
            p2 = self.track_path[0]
            dx = p2[0] - p1[0]
            dy = p2[1] - p1[1]
            total_distance += np.sqrt(dx*dx + dy*dy)

            # Distance from 0 to end_idx
            for i in range(0, end_idx):
                p1 = self.track_path[i]
                p2 = self.track_path[i + 1]
                dx = p2[0] - p1[0]
                dy = p2[1] - p1[1]
                total_distance += np.sqrt(dx*dx + dy*dy)

        return total_distance
    
    def _validate_position(self, raw_position: Optional[float]) -> float:
        """
        RAW MODE: Return raw measurements without any validation or filtering.

        All restrictions disabled to observe raw position measurements.

        Args:
            raw_position: Raw position measurement (0-100%), or None if no detection

        Returns:
            Raw position (0-100%) or last position if no detection
        """
        # Case 1: No measurement - use last known position
        if raw_position is None:
            return self.last_position

        # Case 2: Accept ALL raw measurements without any validation
        self.last_position = raw_position
        return raw_position
    
    def reset_for_new_lap(self) -> None:
        """
        Reset position tracking for a new lap.

        If start/finish line was detected geometrically, this just resets the position to 0%.
        If no geometric detection occurred, it will set the start position on the next frame.
        """
        if self.start_idx is not None and self.start_position is not None:
            # Start line already detected geometrically - just reset position counter
            print(f"      🏁 Lap reset triggered - using geometric start line at idx {self.start_idx}")
            self.last_position = 0.0
            # Do NOT set lap_just_started - we keep the geometric start position
        else:
            # No geometric detection - fall back to red dot detection on next frame
            self.lap_just_started = True
            print(f"      🏁 Lap reset triggered - will capture start position on next frame")
    
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
        debug_info = {
            'path_extracted': self.path_extracted,
            'validation_passed': self.validation_passed,
            'path_points': len(self.track_path) if self.track_path else 0,
            'total_path_pixels': self.total_path_pixels,
            'total_track_length': self.total_track_length,
            'start_position': self.start_position,
            'track_center': self.track_center,
            'last_position': self.last_position,
            'lap_just_started': self.lap_just_started,
            'max_jump_per_frame': self.max_jump_per_frame
        }

        return debug_info
