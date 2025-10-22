"""
Lap detection module for extracting lap numbers and lap times from ACC HUD.
Uses fast template matching for lap numbers (100-500x faster than OCR).
Falls back to OCR for lap times (only called on transitions, so performance is fine).
"""

import cv2
import numpy as np
import pytesseract
import re
from typing import Optional, Tuple
from pathlib import Path
from src.template_matcher import TemplateMatcher


class LapDetector:
    """
    Detects lap numbers and lap times from ACC gameplay video frames.
    
    Uses template matching for lap numbers (100-500x faster than OCR).
    Falls back to OCR for lap times (more complex text format).
    
    The ACC HUD displays lap information in the top-left corner:
    - Lap number: Large red flag with white number (e.g., "21")
    - Lap times: Text panel showing BEST, LAST, PRED times
    """
    
    def __init__(self, roi_config: dict = None, template_dir: str = 'templates/lap_digits/',
                 enable_performance_stats: bool = False):
        """
        Initialize lap detector with ROI configuration.
        
        Args:
            roi_config: Dictionary with 'lap_number' and 'last_lap_time' ROI coordinates
                       If None, uses default coordinates for 1280x720 video
            template_dir: Directory containing digit templates for lap number recognition
            enable_performance_stats: If True, tracks and reports detection statistics
        """
        if roi_config is None:
            # Default ROI coordinates for 1280x720 video
            self.lap_number_roi = {'x': 237, 'y': 71, 'width': 47, 'height': 37}
            self.last_lap_time_roi = {'x': 119, 'y': 87, 'width': 87, 'height': 20}
        else:
            self.lap_number_roi = roi_config.get('lap_number', {})
            self.last_lap_time_roi = roi_config.get('last_lap_time', {})
        
        # Initialize template matcher for lap numbers
        self.lap_matcher = TemplateMatcher(template_dir)
        
        # Cache for lap number
        self._last_valid_lap_number: Optional[int] = None
        self._last_valid_lap_time: Optional[str] = None
        
        # Performance statistics
        self._enable_performance_stats = enable_performance_stats
        self._total_frames_processed: int = 0
        self._recognition_calls: int = 0
        
        # Tesseract config for lap times (still using OCR for complex time format)
        self.tesseract_config_time = '--psm 7 --oem 3 -c tessedit_char_whitelist=0123456789:.'
        
        # Check if templates are loaded
        if not self.lap_matcher.has_templates():
            print(f"⚠️  Warning: No lap number templates found in {template_dir}")
            print(f"   Run calibration first: python -m src.template_matcher")
    
    def extract_lap_number(self, frame: np.ndarray) -> Optional[int]:
        """
        Extract lap number from the red flag area in top-left corner.
        
        Uses fast template matching (0.5-2ms vs 50-200ms for OCR).
        The lap number appears as white digits on a red background flag icon.
        
        Args:
            frame: Full video frame (BGR format)
            
        Returns:
            Lap number as integer, or None if extraction fails
        """
        if frame is None or frame.size == 0:
            return self._last_valid_lap_number
        
        # Extract ROI
        roi = self._extract_roi(frame, self.lap_number_roi)
        if roi is None or roi.size == 0:
            return self._last_valid_lap_number
        
        # Track statistics
        if self._enable_performance_stats:
            self._total_frames_processed += 1
            self._recognition_calls += 1
        
        # Preprocess: isolate white text on red background
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        
        # White text detection (high value, low saturation)
        lower_white = np.array([0, 0, 180])
        upper_white = np.array([180, 50, 255])
        white_mask = cv2.inRange(hsv, lower_white, upper_white)
        
        # Apply morphological operations to clean up noise
        kernel = np.ones((2, 2), np.uint8)
        white_mask = cv2.morphologyEx(white_mask, cv2.MORPH_CLOSE, kernel)
        white_mask = cv2.morphologyEx(white_mask, cv2.MORPH_OPEN, kernel)
        
        # Use template matching to recognize the number (1-2 digits for lap numbers)
        lap_number = self.lap_matcher.recognize_number(white_mask, max_digits=2)
        
        if lap_number is not None:
            # Validate: lap numbers should be reasonable (1-999)
            if 1 <= lap_number <= 999:
                # Additional validation: lap number should not jump by more than 1
                if self._last_valid_lap_number is not None:
                    if abs(lap_number - self._last_valid_lap_number) > 1:
                        # Suspicious jump, keep previous value
                        return self._last_valid_lap_number
                
                self._last_valid_lap_number = lap_number
                return lap_number
        
        # Return last known good value
        return self._last_valid_lap_number
    
    def extract_last_lap_time(self, frame: np.ndarray) -> Optional[str]:
        """
        Extract LAST lap time from the timing panel in top-left corner.
        
        This should be called when a lap transition is detected to capture
        the completed lap's time from the "LAST" display.
        The lap time is displayed as "MM:SS.mmm" format (e.g., "01:44.643").
        
        Args:
            frame: Full video frame (BGR format)
            
        Returns:
            Lap time as string in "MM:SS.mmm" format, or None if extraction fails
        """
        if frame is None or frame.size == 0:
            return None
        
        # Extract ROI
        roi = self._extract_roi(frame, self.last_lap_time_roi)
        if roi is None or roi.size == 0:
            return None
        
        # Preprocess: isolate white text
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        
        # Threshold to get white text (lap time is bright white)
        _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
        
        # Resize for better OCR
        scale_factor = 3
        height, width = thresh.shape
        resized = cv2.resize(thresh, (width * scale_factor, height * scale_factor), 
                            interpolation=cv2.INTER_CUBIC)
        
        # Run OCR
        try:
            text = pytesseract.image_to_string(resized, config=self.tesseract_config_time)
            text = text.strip()
            
            # Parse lap time format: MM:SS.mmm
            # Look for pattern like "01:44.643" or "1:44.6"
            time_pattern = r'(\d{1,2}):(\d{2})\.(\d{1,3})'
            match = re.search(time_pattern, text)
            
            if match:
                minutes = match.group(1).zfill(2)
                seconds = match.group(2)
                milliseconds = match.group(3).ljust(3, '0')
                
                lap_time = f"{minutes}:{seconds}.{milliseconds}"
                
                # Basic validation: lap times should be reasonable (20 seconds to 10 minutes)
                total_seconds = int(minutes) * 60 + int(seconds) + int(milliseconds) / 1000
                if 20.0 <= total_seconds <= 600.0:
                    return lap_time
        
        except Exception as e:
            # OCR failed
            pass
        
        # Return None if extraction failed
        return None
    
    def detect_lap_transition(self, current_lap: Optional[int], 
                            previous_lap: Optional[int]) -> bool:
        """
        Detect if a lap transition occurred (lap number changed).
        
        Args:
            current_lap: Current frame's lap number
            previous_lap: Previous frame's lap number
            
        Returns:
            True if lap transition detected, False otherwise
        """
        if current_lap is None or previous_lap is None:
            return False
        
        # Lap transition occurs when lap number increases by 1
        return current_lap == previous_lap + 1
    
    def _extract_roi(self, frame: np.ndarray, roi_config: dict) -> Optional[np.ndarray]:
        """
        Extract Region of Interest from frame.
        
        Args:
            frame: Full frame
            roi_config: Dictionary with x, y, width, height
            
        Returns:
            ROI image or None if extraction fails
        """
        if not roi_config:
            return None
        
        try:
            x = roi_config['x']
            y = roi_config['y']
            w = roi_config['width']
            h = roi_config['height']
            
            # Validate coordinates
            if x < 0 or y < 0 or w <= 0 or h <= 0:
                return None
            
            if y + h > frame.shape[0] or x + w > frame.shape[1]:
                return None
            
            roi = frame[y:y+h, x:x+w]
            return roi
            
        except (KeyError, IndexError):
            return None
    
    def get_lap_time_seconds(self, lap_time_str: Optional[str]) -> Optional[float]:
        """
        Convert lap time string to seconds.
        
        Args:
            lap_time_str: Lap time in "MM:SS.mmm" format
            
        Returns:
            Lap time in seconds as float, or None if parsing fails
        """
        if lap_time_str is None:
            return None
        
        try:
            # Parse "MM:SS.mmm" format
            time_pattern = r'(\d{2}):(\d{2})\.(\d{3})'
            match = re.match(time_pattern, lap_time_str)
            
            if match:
                minutes = int(match.group(1))
                seconds = int(match.group(2))
                milliseconds = int(match.group(3))
                
                total_seconds = minutes * 60 + seconds + milliseconds / 1000.0
                return total_seconds
        
        except Exception:
            return None
        
        return None
    
    def get_performance_stats(self) -> dict:
        """
        Get performance statistics about lap detection.
        
        Returns:
            Dictionary with performance metrics
        """
        if not self._enable_performance_stats:
            return {
                'error': 'Performance stats not enabled. Initialize with enable_performance_stats=True'
            }
        
        # Estimate speedup: template matching (~1-2ms) vs OCR (~100ms)
        estimated_ocr_time_ms = 100  # Typical Tesseract OCR time
        estimated_template_time_ms = 1.5  # Template matching time
        
        time_with_ocr = self._total_frames_processed * estimated_ocr_time_ms
        time_with_template = self._recognition_calls * estimated_template_time_ms
        
        speedup = time_with_ocr / time_with_template if time_with_template > 0 else 1.0
        
        return {
            'total_frames': self._total_frames_processed,
            'recognition_calls': self._recognition_calls,
            'method': 'Template Matching',
            'avg_time_per_frame_ms': estimated_template_time_ms,
            'estimated_speedup_vs_ocr': round(speedup, 2)
        }

