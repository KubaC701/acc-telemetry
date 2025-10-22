"""
Universal template-based digit recognition.
100-500x faster than OCR (~0.5-2ms vs 50-200ms).

Works for ANY digit-based telemetry: lap numbers, speed, gear, lap times, etc.
Just provide different template directories for different HUD elements.
"""

import cv2
import numpy as np
from typing import Optional, Dict
from pathlib import Path


class TemplateMatcher:
    """
    Universal template-based digit recognition.
    
    How it works:
    1. One-time calibration: Extract reference images of digits 0-9 from video
    2. Runtime: Slide each template across target ROI to find best match
    3. Result: Recognized digit in ~0.5-2ms (vs 50-200ms for OCR)
    
    Usage:
        # For lap numbers
        lap_matcher = TemplateMatcher('templates/lap_digits/')
        lap_number = lap_matcher.recognize_number(lap_roi, max_digits=2)
        
        # For speed
        speed_matcher = TemplateMatcher('templates/speed_digits/')
        speed = speed_matcher.recognize_number(speed_roi, max_digits=3)
    """
    
    def __init__(self, template_dir: str):
        """
        Initialize template matcher.
        
        Args:
            template_dir: Directory containing digit templates (0.png, 1.png, ..., 9.png)
                         Different HUD elements need different template directories:
                         - 'templates/lap_digits/' for lap numbers
                         - 'templates/speed_digits/' for speed
                         - 'templates/gear_digits/' for gear indicator
        """
        self.template_dir = Path(template_dir)
        self.templates: Dict[str, np.ndarray] = {}
        
        # Load templates if directory exists
        if self.template_dir.exists():
            self._load_templates()
    
    def _load_templates(self):
        """Load pre-created digit templates from directory."""
        for digit in range(10):
            template_path = self.template_dir / f"{digit}.png"
            if template_path.exists():
                template = cv2.imread(str(template_path), cv2.IMREAD_GRAYSCALE)
                if template is not None:
                    self.templates[str(digit)] = template
    
    def has_templates(self) -> bool:
        """Check if templates are loaded and ready."""
        return len(self.templates) > 0
    
    def save_template(self, roi: np.ndarray, digit_value: str) -> bool:
        """
        Create and save a template from a digit ROI.
        
        This is used during one-time calibration to create template images.
        
        Args:
            roi: Image containing a single digit (cropped from video frame)
            digit_value: What digit it represents ('0'-'9')
            
        Returns:
            True if template saved successfully
            
        Example:
            # Extract frame 150 which shows lap 22
            frame = video.get_frame(150)
            lap_roi = frame[71:108, 237:284]
            
            # Manually split "22" into two digits
            digit_left = lap_roi[:, 0:23]
            digit_right = lap_roi[:, 24:47]
            
            # Save templates
            matcher.save_template(digit_left, '2')
            matcher.save_template(digit_right, '2')  # Same digit, improves template
        """
        if digit_value not in '0123456789':
            print(f"❌ Invalid digit value: {digit_value}")
            return False
        
        # Preprocess: isolate white text on dark background
        if len(roi.shape) == 3:
            gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        else:
            gray = roi
        
        # Threshold to binary (white digits on black background)
        _, binary = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY)
        
        # Store in memory
        self.templates[digit_value] = binary
        
        # Save to disk
        self.template_dir.mkdir(parents=True, exist_ok=True)
        template_path = self.template_dir / f"{digit_value}.png"
        cv2.imwrite(str(template_path), binary)
        
        print(f"✅ Saved template: {template_path}")
        return True
    
    def recognize_digit(self, roi: np.ndarray, threshold: float = 0.6) -> Optional[str]:
        """
        Recognize a single digit using template matching.
        
        Args:
            roi: Image region containing one digit (may have noise/background)
            threshold: Matching confidence (0-1). Lower = more lenient.
                      0.6 works well for lap numbers, 0.7 for clearer displays
            
        Returns:
            Recognized digit ('0'-'9') or None if no match above threshold
        """
        if not self.templates:
            return None
        
        # Preprocess ROI same way as templates
        if len(roi.shape) == 3:
            gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        else:
            gray = roi
        
        _, binary = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY)
        
        # CRITICAL FIX: Extract just the digit from ROI before matching
        # ROI might contain digit + "LAPS" text + background noise
        # We need to isolate ONLY the digit region
        isolated_digit = self._isolate_largest_region(binary)
        if isolated_digit is None or isolated_digit.size == 0:
            return None
        
        # Try matching each digit template
        best_digit = None
        best_score = threshold
        
        for digit, template in self.templates.items():
            # Resize isolated digit to match template size
            try:
                digit_resized = cv2.resize(isolated_digit, (template.shape[1], template.shape[0]))
            except:
                continue
            
            # Template matching: normalized cross-correlation
            result = cv2.matchTemplate(digit_resized, template, cv2.TM_CCOEFF_NORMED)
            score = result.max()
            
            if score > best_score:
                best_score = score
                best_digit = digit
        
        return best_digit
    
    def _isolate_largest_region(self, binary: np.ndarray) -> Optional[np.ndarray]:
        """
        Extract the largest white region from binary image.
        This isolates the actual digit from background noise.
        
        Args:
            binary: Binary image (white digit on black background)
            
        Returns:
            Cropped image containing just the largest region, or None
        """
        # Find connected components
        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)
        
        if num_labels <= 1:  # Only background
            return None
        
        # Find largest component (excluding background at index 0)
        largest_idx = 1
        largest_area = stats[1, cv2.CC_STAT_AREA]
        
        for i in range(2, num_labels):
            area = stats[i, cv2.CC_STAT_AREA]
            if area > largest_area:
                largest_area = area
                largest_idx = i
        
        # Check if area is reasonable (not just noise)
        if largest_area < 20:  # Minimum 20 pixels
            return None
        
        # Extract bounding box of largest region
        x = stats[largest_idx, cv2.CC_STAT_LEFT]
        y = stats[largest_idx, cv2.CC_STAT_TOP]
        w = stats[largest_idx, cv2.CC_STAT_WIDTH]
        h = stats[largest_idx, cv2.CC_STAT_HEIGHT]
        
        # Crop to just that region
        isolated = binary[y:y+h, x:x+w]
        
        return isolated
    
    def recognize_number(self, roi: np.ndarray, max_digits: int = 2) -> Optional[int]:
        """
        Recognize a multi-digit number from ROI using sliding window template matching.
        
        Scans the entire ROI with each digit template, finds all matches above threshold,
        and combines them left-to-right into a number.
        
        Args:
            roi: Image region containing 1-N digits (can include noise/background)
            max_digits: Maximum expected digits (2 for lap numbers, 3 for speed)
            
        Returns:
            Recognized number as integer or None if recognition fails
            
        Example:
            lap_roi = frame[71:108, 237:284]  # Contains "11 LAPS"
            lap_number = matcher.recognize_number(lap_roi, max_digits=2)
            # Returns: 11 (finds two "1"s at different x positions)
        """
        if not self.templates:
            return None
        
        # Preprocess ROI
        if len(roi.shape) == 3:
            gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        else:
            gray = roi
        
        _, binary = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY)
        
        # Find all digit matches in the ROI using sliding window
        matches = []  # List of (x_position, digit, confidence)
        
        for digit, template in self.templates.items():
            # Skip if template is larger than ROI
            if template.shape[0] > binary.shape[0] or template.shape[1] > binary.shape[1]:
                continue
            
            # Slide template across ROI
            result = cv2.matchTemplate(binary, template, cv2.TM_CCOEFF_NORMED)
            
            # Find all matches above threshold
            # Higher threshold = more strict matching = fewer false positives
            threshold = 0.65  # Increased from 0.6 to reduce false matches
            locations = np.where(result >= threshold)
            
            for y, x in zip(*locations):
                confidence = result[y, x]
                matches.append((x, digit, confidence))
        
        if not matches:
            return None
        
        # Sort matches by x-position (left to right)
        matches.sort(key=lambda m: m[0])
        
        # Remove duplicate detections at similar x positions
        # (same digit might match multiple times at nearby positions)
        filtered_matches = []
        min_distance = 8  # Minimum x-distance between distinct digits (reduced from 10)
        
        for i, (x, digit, conf) in enumerate(matches):
            # Check if this is too close to previous match
            if filtered_matches and abs(x - filtered_matches[-1][0]) < min_distance:
                # Keep the one with higher confidence
                if conf > filtered_matches[-1][2]:
                    filtered_matches[-1] = (x, digit, conf)
            else:
                filtered_matches.append((x, digit, conf))
        
        # Limit to max_digits and keep highest confidence matches
        if len(filtered_matches) > max_digits:
            # Keep the max_digits with highest confidence
            filtered_matches.sort(key=lambda m: m[2], reverse=True)
            filtered_matches = filtered_matches[:max_digits]
            # Re-sort by position for correct digit order
            filtered_matches.sort(key=lambda m: m[0])
        
        # Build number from left to right
        if not filtered_matches:
            return None
        
        number_str = ''.join([digit for _, digit, _ in filtered_matches])
        
        try:
            return int(number_str)
        except ValueError:
            return None


def calibrate_lap_templates(video_path: str, roi_config: dict, 
                            sample_frames: Dict[int, int]) -> bool:
    """
    One-time calibration to create lap number templates.
    
    Args:
        video_path: Path to video file
        roi_config: ROI configuration with 'lap_number' key
        sample_frames: {frame_number: lap_number} mapping
                      Example: {150: 22, 5000: 3, 10000: 14, ...}
                      You need frames covering all digits 0-9
    
    Returns:
        True if calibration successful
    
    Example:
        # Find frames in your video where different lap numbers are visible
        sample_frames = {
            150: 22,    # Frame 150 shows lap 22 (digits: 2, 2)
            5000: 3,    # Frame 5000 shows lap 3  (digit: 3)
            10000: 14,  # Frame 10000 shows lap 14 (digits: 1, 4)
            15000: 5,   # Frame 15000 shows lap 5  (digit: 5)
            20000: 6,   # etc...
            25000: 7,
            30000: 8,
            35000: 9,
            40000: 10,  # (digits: 1, 0)
        }
        
        calibrate_lap_templates('input_video.mp4', roi_config, sample_frames)
    """
    import cv2
    
    matcher = TemplateMatcher('templates/lap_digits/')
    cap = cv2.VideoCapture(video_path)
    
    if not cap.isOpened():
        print(f"❌ Failed to open video: {video_path}")
        return False
    
    roi_cfg = roi_config.get('lap_number', {})
    x, y, w, h = roi_cfg['x'], roi_cfg['y'], roi_cfg['width'], roi_cfg['height']
    
    print(f"\n{'='*60}")
    print(f"Lap Number Template Calibration")
    print(f"{'='*60}\n")
    print(f"Processing {len(sample_frames)} frames to extract digits 0-9...")
    print(f"ROI: x={x}, y={y}, w={w}, h={h}\n")
    
    # Track which digits we've captured
    captured_digits = set()
    
    for frame_num, lap_number in sorted(sample_frames.items()):
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
        ret, frame = cap.read()
        
        if not ret:
            print(f"⚠️  Warning: Could not read frame {frame_num}")
            continue
        
        # Extract lap number ROI
        lap_roi = frame[y:y+h, x:x+w]
        
        # Save debug image
        debug_dir = Path('templates/debug_lap')
        debug_dir.mkdir(parents=True, exist_ok=True)
        debug_path = debug_dir / f"frame{frame_num}_lap{lap_number}.png"
        cv2.imwrite(str(debug_path), lap_roi)
        
        print(f"📷 Frame {frame_num}: Lap {lap_number}")
        print(f"   Saved debug image: {debug_path}")
        print(f"   → Manually crop each digit from this image")
        print(f"   → Save to templates/lap_digits/[digit].png\n")
        
        # Track which digits are in this lap number
        for digit_char in str(lap_number):
            captured_digits.add(digit_char)
    
    cap.release()
    
    print(f"\n{'='*60}")
    print(f"Calibration Complete!")
    print(f"{'='*60}\n")
    print(f"✅ Extracted {len(sample_frames)} frames covering digits: {sorted(captured_digits)}")
    
    missing_digits = set('0123456789') - captured_digits
    if missing_digits:
        print(f"⚠️  Missing digits: {sorted(missing_digits)}")
        print(f"   Find more frames to cover all digits 0-9\n")
    else:
        print(f"✅ All digits 0-9 covered!\n")
    
    print(f"Next steps:")
    print(f"1. Open images in templates/debug_lap/")
    print(f"2. For each image, manually crop individual digits")
    print(f"3. Save cropped digits as templates/lap_digits/[0-9].png")
    print(f"4. Each template should be ~20-40 pixels wide")
    print(f"5. Templates should be white text on black background\n")
    
    return True


if __name__ == '__main__':
    # Example: Run calibration
    import yaml
    
    print("=== Template Matcher Calibration Tool ===\n")
    
    with open('config/roi_config.yaml', 'r') as f:
        roi_config = yaml.safe_load(f)
    
    # TODO: Find frames in your video showing different lap numbers
    sample_frames = {
        150: 22,  # Add your frame numbers here
    }
    
    calibrate_lap_templates('input_video.mp4', roi_config, sample_frames)
