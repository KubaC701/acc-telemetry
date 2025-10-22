"""
Lap detection module for extracting lap numbers and lap times from ACC HUD.
Uses direct OCR with minimal preprocessing for fast and accurate digit recognition.

Performance: tesserocr (1-2ms) >> pytesseract (50ms) > template matching (2ms)
"""

import cv2
import numpy as np
import re
from typing import Optional, Tuple
from pathlib import Path
from src.template_matcher import TemplateMatcher

# Try to use fast tesserocr (direct C++ API), fall back to pytesseract
try:
    import tesserocr
    from PIL import Image
    USE_TESSEROCR = True
except ImportError:
    import pytesseract
    USE_TESSEROCR = False


class LapDetector:
    """
    Detects lap numbers and lap times from ACC gameplay video frames.
    
    Uses direct OCR on raw ROI for both lap numbers and lap times.
    Minimal preprocessing = faster performance and simpler code.
    
    The ACC HUD displays lap information in the top-left corner:
    - Lap number: Large red flag with white number (e.g., "21")
    - Lap times: Text panel showing BEST, LAST, PRED times
    """
    
    def __init__(self, roi_config: dict = None, template_dir: str = 'templates/lap_digits/',
                 enable_performance_stats: bool = False):
        """
        Initialize lap detector with ROI configuration.
        
        Args:
            roi_config: Dictionary with 'lap_number', 'last_lap_time', and 'speed' ROI coordinates
                       If None, uses default coordinates for 1280x720 video
            template_dir: Directory containing digit templates for lap number recognition
            enable_performance_stats: If True, tracks and reports detection statistics
        """
        if roi_config is None:
            # Default ROI coordinates for 1280x720 video
            self.lap_number_roi = {'x': 237, 'y': 71, 'width': 47, 'height': 37}
            self.last_lap_time_roi = {'x': 119, 'y': 87, 'width': 87, 'height': 20}
            self.speed_roi = {'x': 1177, 'y': 621, 'width': 54, 'height': 32}
            self.gear_roi = {'x': 1124, 'y': 591, 'width': 47, 'height': 72}
        else:
            self.lap_number_roi = roi_config.get('lap_number', {})
            self.last_lap_time_roi = roi_config.get('last_lap_time', {})
            self.speed_roi = roi_config.get('speed', {})
            self.gear_roi = roi_config.get('gear', {})
        
        # Initialize template matcher for lap numbers
        self.lap_matcher = TemplateMatcher(template_dir)
        
        # Cache for lap number with temporal smoothing
        self._last_valid_lap_number: Optional[int] = None
        self._last_valid_lap_time: Optional[str] = None
        self._last_valid_speed: Optional[int] = None
        self._last_valid_gear: Optional[int] = None
        self._lap_number_history: list = []  # Track recent detections for stability
        self._speed_history: list = []  # Track recent speed detections for stability
        self._gear_history: list = []  # Track recent gear detections for stability
        self._history_size: int = 15  # Number of frames to track (increased for better OCR stability)
        
        # Performance statistics
        self._enable_performance_stats = enable_performance_stats
        self._total_frames_processed: int = 0
        self._recognition_calls: int = 0
        
        # Tesseract config for lap numbers (digit-only, single word)
        # PSM 8: Single word mode works better for isolated lap numbers
        self.tesseract_config_lap = '--psm 8 --oem 3 -c tessedit_char_whitelist=0123456789'
        
        # Tesseract config for lap times (still using OCR for complex time format)
        self.tesseract_config_time = '--psm 7 --oem 3 -c tessedit_char_whitelist=0123456789:.'
        
        # Check if templates are loaded
        if not self.lap_matcher.has_templates():
            print(f"⚠️  Warning: No lap number templates found in {template_dir}")
            print(f"   Run calibration first: python -m src.template_matcher")
        
        # Initialize tesserocr API (much faster than pytesseract)
        self._tesserocr_api = None
        if USE_TESSEROCR:
            try:
                self._tesserocr_api = tesserocr.PyTessBaseAPI(
                    path='/opt/homebrew/share/tessdata/',
                    psm=tesserocr.PSM.SINGLE_WORD,
                    oem=tesserocr.OEM.LSTM_ONLY
                )
                self._tesserocr_api.SetVariable("tessedit_char_whitelist", "0123456789")
                print("✅ Using tesserocr (fast C++ API, ~2ms per frame)")
            except Exception as e:
                print(f"⚠️  tesserocr init failed: {e}, falling back to pytesseract")
                self._tesserocr_api = None
        else:
            print("ℹ️  Using pytesseract (~50ms per frame). Install tesserocr for 25x speedup!")
    
    def extract_lap_number(self, frame: np.ndarray) -> Optional[int]:
        """
        Extract lap number from the red flag area in top-left corner.
        
        Uses direct OCR on raw ROI (no preprocessing overhead).
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
        
        # Run OCR directly on raw BGR ROI
        # No preprocessing needed - Tesseract handles color images perfectly
        try:
            import time
            ocr_start = time.time()
            
            if self._tesserocr_api:
                # Fast path: tesserocr (1-2ms)
                roi_rgb = cv2.cvtColor(roi, cv2.COLOR_BGR2RGB)
                pil_image = Image.fromarray(roi_rgb)
                self._tesserocr_api.SetImage(pil_image)
                text = self._tesserocr_api.GetUTF8Text()
            else:
                # Slow path: pytesseract (50ms)
                import pytesseract
                text = pytesseract.image_to_string(roi, config=self.tesseract_config_lap)
            
            ocr_time = (time.time() - ocr_start) * 1000
            text = text.strip()
            
            # Debug: print OCR results (disabled by default for cleaner output)
            # if self._enable_performance_stats:
            #     print(f"[DEBUG Frame {self._total_frames_processed}] OCR took {ocr_time:.2f}ms - result: '{text}'")
            
            # Parse lap number (should be 1-2 digits)
            if text.isdigit():
                lap_number = int(text)
            else:
                # Try to extract digits from text (in case of noise)
                digits_only = ''.join(filter(str.isdigit, text))
                if digits_only:
                    lap_number = int(digits_only)
                else:
                    lap_number = None
        except Exception as e:
            lap_number = None
        
        if lap_number is not None:
            # Validate: lap numbers should be reasonable (0-999)
            # Lap 0 = on grid/warmup, laps 1+ = racing laps
            if 0 <= lap_number <= 999:
                # Add to history for temporal smoothing
                self._lap_number_history.append(lap_number)
                if len(self._lap_number_history) > self._history_size:
                    self._lap_number_history.pop(0)
                
                # Use majority voting from recent history to filter out noise
                smoothed_lap = self._get_smoothed_lap_number()
                
                if smoothed_lap is not None:
                    # Additional validation: lap number should not decrease or jump erratically
                    if self._last_valid_lap_number is not None:
                        lap_diff = smoothed_lap - self._last_valid_lap_number
                        
                        # Allow: no change, +1 only (normal progression)
                        # Reject: backward jumps or forward jumps > 1 (likely OCR errors)
                        if lap_diff == 0:
                            return self._last_valid_lap_number
                        elif lap_diff == 1:
                            # Normal lap progression - accept
                            self._last_valid_lap_number = smoothed_lap
                            return smoothed_lap
                        else:
                            # Jump by more than 1 or backward - reject as OCR error
                            # Keep previous value for stability
                            return self._last_valid_lap_number
                    else:
                        # First detection
                        self._last_valid_lap_number = smoothed_lap
                        return smoothed_lap
        
        # Return last known good value
        return self._last_valid_lap_number
    
    def _get_smoothed_lap_number(self) -> Optional[int]:
        """
        Apply majority voting to recent lap number detections to filter out noise.
        
        This prevents oscillation between two values (e.g., 10 vs 11, 20 vs 21).
        If the history shows [10, 11, 10, 11, 10], we need to determine which is correct.
        
        Returns:
            Most common lap number in recent history, or None if history is empty
        """
        if not self._lap_number_history:
            return None
        
        # Count occurrences of each lap number
        from collections import Counter
        lap_counts = Counter(self._lap_number_history)
        
        # Get the most common lap number
        most_common = lap_counts.most_common(1)[0]
        lap_number = most_common[0]
        count = most_common[1]
        
        # Require at least 70% agreement (e.g., 11 out of 15 frames)
        # This prevents flip-flopping from OCR errors but allows genuine transitions
        if count >= max(len(self._lap_number_history) * 0.7, 3):
            return lap_number
        
        # Not enough consensus, return None to keep previous value
        return None
    
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
            return self._last_valid_lap_time
        
        # Extract ROI
        roi = self._extract_roi(frame, self.last_lap_time_roi)
        if roi is None or roi.size == 0:
            return self._last_valid_lap_time
        
        # Preprocess: isolate white text
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        
        # Threshold to get white text (lap time is bright white)
        _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
        
        # Resize for better OCR (helps with small text)
        scale_factor = 3
        height, width = thresh.shape
        resized = cv2.resize(thresh, (width * scale_factor, height * scale_factor), 
                            interpolation=cv2.INTER_CUBIC)
        
        # Run OCR using same approach as lap numbers
        try:
            if self._tesserocr_api:
                # Fast path: tesserocr (1-2ms)
                # Need to convert grayscale to RGB for PIL
                resized_rgb = cv2.cvtColor(resized, cv2.COLOR_GRAY2RGB)
                pil_image = Image.fromarray(resized_rgb)
                
                # Temporarily set character whitelist for time format
                self._tesserocr_api.SetVariable("tessedit_char_whitelist", "0123456789:.")
                self._tesserocr_api.SetPageSegMode(tesserocr.PSM.SINGLE_LINE)
                self._tesserocr_api.SetImage(pil_image)
                text = self._tesserocr_api.GetUTF8Text()
                
                # Reset to digit-only for lap numbers
                self._tesserocr_api.SetVariable("tessedit_char_whitelist", "0123456789")
                self._tesserocr_api.SetPageSegMode(tesserocr.PSM.SINGLE_WORD)
            else:
                # Slow path: pytesseract (50ms)
                import pytesseract
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
                    self._last_valid_lap_time = lap_time
                    return lap_time
        
        except Exception as e:
            # OCR failed, keep previous valid time
            pass
        
        # Return last valid time if extraction failed
        return self._last_valid_lap_time
    
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
    
    def extract_speed(self, frame: np.ndarray) -> Optional[int]:
        """
        Extract current speed (km/h) from the HUD speed display.
        
        Uses direct OCR on raw ROI (no preprocessing overhead).
        The speed appears as white digits on a dark background in the bottom-right corner.
        
        Args:
            frame: Full video frame (BGR format)
            
        Returns:
            Speed in km/h as integer, or None if extraction fails
        """
        if frame is None or frame.size == 0:
            return self._last_valid_speed
        
        # Extract ROI
        roi = self._extract_roi(frame, self.speed_roi)
        if roi is None or roi.size == 0:
            return self._last_valid_speed
        
        # Run OCR directly on raw BGR ROI
        # No preprocessing needed - Tesseract handles it well
        try:
            if self._tesserocr_api:
                # Fast path: tesserocr (1-2ms)
                roi_rgb = cv2.cvtColor(roi, cv2.COLOR_BGR2RGB)
                pil_image = Image.fromarray(roi_rgb)
                self._tesserocr_api.SetImage(pil_image)
                text = self._tesserocr_api.GetUTF8Text()
            else:
                # Slow path: pytesseract (50ms)
                import pytesseract
                text = pytesseract.image_to_string(roi, config=self.tesseract_config_lap)
            
            text = text.strip()
            
            # Parse speed (should be 1-3 digits)
            if text.isdigit():
                speed = int(text)
            else:
                # Try to extract digits from text (in case of noise)
                digits_only = ''.join(filter(str.isdigit, text))
                if digits_only:
                    speed = int(digits_only)
                else:
                    speed = None
        except Exception as e:
            speed = None
        
        if speed is not None:
            # Validate: speed should be reasonable (0-400 km/h for ACC)
            if 0 <= speed <= 400:
                # Add to history for temporal smoothing
                self._speed_history.append(speed)
                if len(self._speed_history) > self._history_size:
                    self._speed_history.pop(0)
                
                # Use median filtering to smooth out OCR noise
                smoothed_speed = self._get_smoothed_speed()
                
                if smoothed_speed is not None:
                    self._last_valid_speed = smoothed_speed
                    return smoothed_speed
        
        # Return last known good value
        return self._last_valid_speed
    
    def _get_smoothed_speed(self) -> Optional[int]:
        """
        Apply median filtering to recent speed detections to filter out OCR noise.
        
        Median is more robust than mean for filtering out occasional OCR errors.
        
        Returns:
            Median speed from recent history, or None if history is empty
        """
        if not self._speed_history:
            return None
        
        # Use median to filter outliers (more robust than mean)
        import statistics
        return int(statistics.median(self._speed_history))
    
    def extract_gear(self, frame: np.ndarray) -> Optional[int]:
        """
        Extract current gear (1-6) from the HUD gear display.
        
        Uses direct OCR on raw ROI (no preprocessing overhead).
        The gear appears as a white digit in the center of the rev meter arc.
        
        Args:
            frame: Full video frame (BGR format)
            
        Returns:
            Gear as integer (1-6), or None if extraction fails
        """
        if frame is None or frame.size == 0:
            return self._last_valid_gear
        
        # Extract ROI
        roi = self._extract_roi(frame, self.gear_roi)
        if roi is None or roi.size == 0:
            return self._last_valid_gear
        
        # Run OCR directly on raw BGR ROI
        # No preprocessing needed - Tesseract handles it well
        try:
            if self._tesserocr_api:
                # Fast path: tesserocr (1-2ms)
                roi_rgb = cv2.cvtColor(roi, cv2.COLOR_BGR2RGB)
                pil_image = Image.fromarray(roi_rgb)
                
                # Temporarily set character whitelist for gears (1-6)
                self._tesserocr_api.SetVariable("tessedit_char_whitelist", "123456")
                self._tesserocr_api.SetImage(pil_image)
                text = self._tesserocr_api.GetUTF8Text()
                
                # Reset to digit-only (0-9) for lap numbers/speed
                self._tesserocr_api.SetVariable("tessedit_char_whitelist", "0123456789")
            else:
                # Slow path: pytesseract (50ms)
                import pytesseract
                tesseract_config_gear = '--psm 8 --oem 3 -c tessedit_char_whitelist=123456'
                text = pytesseract.image_to_string(roi, config=tesseract_config_gear)
            
            text = text.strip()
            
            # Parse gear (should be single digit 1-6)
            if text.isdigit():
                gear = int(text)
            else:
                # Try to extract digits from text (in case of noise)
                digits_only = ''.join(filter(str.isdigit, text))
                if digits_only:
                    gear = int(digits_only)
                else:
                    gear = None
        except Exception as e:
            gear = None
        
        if gear is not None:
            # Validate: gear should be 1-6 (ACC gears)
            if 1 <= gear <= 6:
                # Add to history for temporal smoothing
                self._gear_history.append(gear)
                if len(self._gear_history) > self._history_size:
                    self._gear_history.pop(0)
                
                # Use median filtering to smooth out OCR noise
                smoothed_gear = self._get_smoothed_gear()
                
                if smoothed_gear is not None:
                    self._last_valid_gear = smoothed_gear
                    return smoothed_gear
        
        # Return last known good value
        return self._last_valid_gear
    
    def _get_smoothed_gear(self) -> Optional[int]:
        """
        Apply majority voting to recent gear detections to filter out OCR noise.
        
        Uses same approach as lap number smoothing - requires consensus to prevent
        single-frame OCR errors from causing gear jumps (e.g., 2 -> 4 -> 2).
        
        While gears CAN jump arbitrarily (6 to 2, 3 to 5), these jumps happen
        intentionally over multiple frames, not single-frame OCR glitches.
        
        Returns:
            Most common gear in recent history (with 70% consensus), or None if no consensus
        """
        if not self._gear_history:
            return None
        
        # Count occurrences of each gear
        from collections import Counter
        gear_counts = Counter(self._gear_history)
        
        # Get the most common gear
        most_common = gear_counts.most_common(1)[0]
        gear = most_common[0]
        count = most_common[1]
        
        # Require at least 70% agreement (e.g., 11 out of 15 frames)
        # This prevents single-frame OCR errors but allows genuine gear changes
        if count >= max(len(self._gear_history) * 0.7, 3):
            return gear
        
        # Not enough consensus, return None to keep previous value
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
    
    def close(self):
        """
        Clean up resources (close tesserocr API if initialized).
        Call this when done processing to free resources.
        """
        if self._tesserocr_api:
            try:
                self._tesserocr_api.End()
            except:
                pass
    
    def __del__(self):
        """Destructor to ensure cleanup."""
        self.close()
    
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

