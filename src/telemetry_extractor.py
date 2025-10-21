"""
Telemetry extraction module for detecting throttle, brake, and steering values from ROI images.
"""

import cv2
import numpy as np
from typing import Dict, Tuple


class TelemetryExtractor:
    """Extracts telemetry values from ROI images using computer vision."""
    
    @staticmethod
    def extract_bar_percentage(roi_image: np.ndarray, target_color: str = 'green', orientation: str = 'vertical') -> float:
        """
        Extract percentage value from a bar by detecting filled portion.
        Supports both horizontal and vertical bars.
        
        Args:
            roi_image: Cropped image of the bar
            target_color: 'green' for throttle, 'gray' for brake
            orientation: 'vertical' or 'horizontal'
            
        Returns:
            Percentage value (0.0 to 100.0)
        """
        if roi_image is None or roi_image.size == 0:
            return 0.0
            
        # Convert to HSV for better color detection
        hsv = cv2.cvtColor(roi_image, cv2.COLOR_BGR2HSV)
        
        if target_color == 'green':
            # Green AND Yellow color ranges (bars change color when TC activate)
            # Green range
            lower_green = np.array([35, 50, 50])
            upper_green = np.array([85, 255, 255])
            mask_green = cv2.inRange(hsv, lower_green, upper_green)
            
            # Yellow/Orange range (when TC active)
            lower_yellow = np.array([15, 100, 100])
            upper_yellow = np.array([35, 255, 255])
            mask_yellow = cv2.inRange(hsv, lower_yellow, upper_yellow)
            
            # Combine both masks
            mask = cv2.bitwise_or(mask_green, mask_yellow)
            
        elif target_color == 'red':
            # Red, Orange, Yellow color ranges (brake bar changes when ABS activates)
            # Red range (HSV red wraps around at 0/180)
            lower_red1 = np.array([0, 100, 100])
            upper_red1 = np.array([10, 255, 255])
            mask_red1 = cv2.inRange(hsv, lower_red1, upper_red1)
            
            lower_red2 = np.array([170, 100, 100])
            upper_red2 = np.array([180, 255, 255])
            mask_red2 = cv2.inRange(hsv, lower_red2, upper_red2)
            
            # Orange/Yellow range (when ABS active)
            lower_orange = np.array([10, 100, 100])
            upper_orange = np.array([40, 255, 255])
            mask_orange = cv2.inRange(hsv, lower_orange, upper_orange)
            
            # Combine all masks
            mask = cv2.bitwise_or(cv2.bitwise_or(mask_red1, mask_red2), mask_orange)
            
        else:  # gray/white
            # Gray/white color range
            lower_bound = np.array([0, 0, 100])
            upper_bound = np.array([180, 50, 255])
            mask = cv2.inRange(hsv, lower_bound, upper_bound)
        
        height, width = mask.shape
        
        if orientation == 'vertical':
            # For vertical bars, fill goes from bottom to top
            # Sample middle columns to avoid edge artifacts
            middle_cols = mask[:, width//3:2*width//3]
            
            # Find the topmost filled pixel for each column (bar fills from bottom)
            filled_heights = []
            for col_idx in range(middle_cols.shape[1]):
                col = middle_cols[:, col_idx]
                non_zero_rows = np.where(col > 0)[0]
                if len(non_zero_rows) > 0:
                    # Calculate filled height from bottom
                    filled_height = height - non_zero_rows[0]
                    filled_heights.append(filled_height)
            
            if not filled_heights:
                return 0.0
            
            # Use median to avoid outliers
            filled_height = np.median(filled_heights)
            percentage = (filled_height / height) * 100.0
            
        else:  # horizontal
            # Sample middle rows to avoid edge artifacts
            middle_rows = mask[height//3:2*height//3, :]
            
            # Find rightmost filled pixel for each row
            filled_widths = []
            for row in middle_rows:
                non_zero_cols = np.where(row > 0)[0]
                if len(non_zero_cols) > 0:
                    filled_widths.append(non_zero_cols[-1] + 1)
            
            if not filled_widths:
                return 0.0
            
            # Check if enough pixels detected to be real bar vs noise
            # For horizontal bars, we need substantial pixel count
            total_detected_pixels = np.count_nonzero(mask)
            min_pixels_threshold = 50  # Minimum pixels to consider valid detection
            
            if total_detected_pixels < min_pixels_threshold:
                # Too few pixels - likely noise/text artifacts, not actual bar
                return 0.0
            
            # Use median to avoid outliers
            filled_width = np.median(filled_widths)
            percentage = (filled_width / width) * 100.0
        
        return min(100.0, max(0.0, percentage))
    
    @staticmethod
    def extract_steering_position(roi_image: np.ndarray) -> float:
        """
        Extract steering position from the steering indicator.
        Detects white dot position on horizontal scale.
        
        Args:
            roi_image: Cropped image of the steering indicator
            
        Returns:
            Normalized steering position (-1.0 = full left, 0.0 = center, +1.0 = full right)
        """
        # Convert to grayscale
        gray = cv2.cvtColor(roi_image, cv2.COLOR_BGR2GRAY)
        
        # Threshold to find bright white pixels (the dot)
        _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
        
        # Find contours/bright regions
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            return 0.0
        
        # Find the brightest/largest contour (the steering dot)
        largest_contour = max(contours, key=cv2.contourArea)
        
        # Get centroid of the contour
        M = cv2.moments(largest_contour)
        if M['m00'] == 0:
            return 0.0
        
        cx = int(M['m10'] / M['m00'])
        
        # Normalize to -1.0 to +1.0 range
        width = roi_image.shape[1]
        normalized_position = (cx / width) * 2.0 - 1.0
        
        return max(-1.0, min(1.0, normalized_position))
    
    def extract_frame_telemetry(self, roi_dict: Dict[str, np.ndarray]) -> Dict[str, float]:
        """
        Extract all telemetry values from a frame's ROI images.
        
        Args:
            roi_dict: Dictionary with 'throttle', 'brake', 'steering' ROI images
            
        Returns:
            Dictionary with extracted values
        """
        return {
            'throttle': self.extract_bar_percentage(roi_dict['throttle'], 'green', 'horizontal'),
            'brake': self.extract_bar_percentage(roi_dict['brake'], 'red', 'horizontal'),
            'steering': self.extract_steering_position(roi_dict['steering'])
        }

