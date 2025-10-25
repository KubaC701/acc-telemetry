"""
Automatic extraction of lap number digit templates from full race video.
Scans through the video to find all lap numbers and creates template images for digits 0-9.
"""

import cv2
import numpy as np
import yaml
from pathlib import Path
from typing import Dict, Set, Optional, Tuple
import sys


class DigitTemplateExtractor:
    """
    Automatically extracts digit templates from lap number ROI across a full race video.
    """
    
    def __init__(self, video_path: str, roi_config: dict):
        """
        Initialize template extractor.
        
        Args:
            video_path: Path to full race video
            roi_config: ROI configuration with 'lap_number' coordinates
        """
        self.video_path = video_path
        self.roi_config = roi_config.get('lap_number', {})
        self.template_dir = Path('templates/lap_digits')
        self.debug_dir = Path('debug/digit_extraction')
        
        # Create directories
        self.template_dir.mkdir(parents=True, exist_ok=True)
        self.debug_dir.mkdir(parents=True, exist_ok=True)
        
        # Track extracted digits
        self.extracted_digits: Set[str] = set()
        self.digit_samples: Dict[str, list] = {str(i): [] for i in range(10)}
        
    def extract_lap_roi(self, frame: np.ndarray) -> Optional[np.ndarray]:
        """Extract lap number ROI from frame."""
        if frame is None or frame.size == 0:
            return None
        
        x = self.roi_config['x']
        y = self.roi_config['y']
        w = self.roi_config['width']
        h = self.roi_config['height']
        
        if y + h > frame.shape[0] or x + w > frame.shape[1]:
            return None
        
        roi = frame[y:y+h, x:x+w]
        return roi
    
    def preprocess_roi(self, roi: np.ndarray) -> np.ndarray:
        """
        Preprocess ROI to isolate white digits on red background.
        
        Returns:
            Binary image with white digits on black background
        """
        # Convert to HSV
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        
        # Extract white text (high value, low saturation)
        lower_white = np.array([0, 0, 180])
        upper_white = np.array([180, 50, 255])
        white_mask = cv2.inRange(hsv, lower_white, upper_white)
        
        # Clean up noise
        kernel = np.ones((2, 2), np.uint8)
        white_mask = cv2.morphologyEx(white_mask, cv2.MORPH_CLOSE, kernel)
        white_mask = cv2.morphologyEx(white_mask, cv2.MORPH_OPEN, kernel)
        
        return white_mask
    
    def detect_lap_change(self, prev_mask: np.ndarray, curr_mask: np.ndarray) -> bool:
        """
        Detect if lap number changed between frames by comparing masks.
        
        Returns:
            True if significant change detected
        """
        if prev_mask is None or curr_mask is None:
            return False
        
        # Resize to same size if needed
        if prev_mask.shape != curr_mask.shape:
            return True
        
        # Calculate difference
        diff = cv2.absdiff(prev_mask, curr_mask)
        change_ratio = np.sum(diff > 0) / diff.size
        
        # If more than 20% of pixels changed, likely a lap transition
        return change_ratio > 0.20
    
    def split_digits(self, mask: np.ndarray, expected_digits: int = 2) -> list[np.ndarray]:
        """
        Split mask into individual digit regions.
        
        Uses connected components to find separate digits.
        
        Args:
            mask: Binary mask with white digits on black background
            expected_digits: Expected number of digits (1 or 2 for lap numbers)
            
        Returns:
            List of digit images (left to right)
        """
        # Find connected components
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(mask, connectivity=8)
        
        # Filter out background (label 0) and tiny noise
        digit_regions = []
        for i in range(1, num_labels):
            area = stats[i, cv2.CC_STAT_AREA]
            if area > 20:  # Minimum area to be considered a digit
                x = stats[i, cv2.CC_STAT_LEFT]
                y = stats[i, cv2.CC_STAT_TOP]
                w = stats[i, cv2.CC_STAT_WIDTH]
                h = stats[i, cv2.CC_STAT_HEIGHT]
                digit_regions.append((x, y, w, h))
        
        # Sort left to right
        digit_regions.sort(key=lambda r: r[0])
        
        # Extract digit images
        digits = []
        for x, y, w, h in digit_regions:
            digit_img = mask[y:y+h, x:x+w]
            digits.append(digit_img)
        
        return digits
    
    def guess_lap_number(self, mask: np.ndarray) -> Optional[int]:
        """
        Try to guess lap number by analyzing digit count and position.
        
        This is a heuristic - not 100% accurate but good enough for template extraction.
        We'll manually verify the templates after extraction.
        
        Returns:
            Guessed lap number or None
        """
        digits = self.split_digits(mask)
        
        if len(digits) == 0:
            return None
        
        # For now, we can't reliably OCR without templates
        # So we'll just return the number of digits as a hint
        # The user will manually label these later
        return len(digits)
    
    def save_digit_template(self, digit_img: np.ndarray, digit_value: str, 
                           lap_number: int, frame_num: int) -> bool:
        """
        Save a digit template to disk.
        
        Args:
            digit_img: Binary image of single digit
            digit_value: What digit it represents ('0'-'9')
            lap_number: Which lap number this came from
            frame_num: Frame number in video
            
        Returns:
            True if saved successfully
        """
        if digit_value not in '0123456789':
            return False
        
        # Normalize size (templates should be consistent)
        # Target size: ~20-30 pixels wide, ~30-40 pixels tall
        target_height = 35
        aspect_ratio = digit_img.shape[1] / digit_img.shape[0]
        target_width = int(target_height * aspect_ratio)
        
        resized = cv2.resize(digit_img, (target_width, target_height), 
                            interpolation=cv2.INTER_AREA)
        
        # Save to template directory
        template_path = self.template_dir / f"{digit_value}.png"
        cv2.imwrite(str(template_path), resized)
        
        # Also save debug version with metadata
        debug_path = self.debug_dir / f"{digit_value}_lap{lap_number}_frame{frame_num}.png"
        cv2.imwrite(str(debug_path), resized)
        
        # Track extraction
        self.extracted_digits.add(digit_value)
        self.digit_samples[digit_value].append({
            'lap': lap_number,
            'frame': frame_num,
            'path': str(debug_path)
        })
        
        return True
    
    def extract_from_video(self, sample_every_n_frames: int = 30, 
                          max_frames: Optional[int] = None) -> Dict[int, list]:
        """
        Scan video and extract lap number ROIs.
        
        This captures all unique lap numbers throughout the race.
        
        Args:
            sample_every_n_frames: Check every N frames (30 = once per second at 30fps)
            max_frames: Optional limit on frames to process (for testing)
            
        Returns:
            Dictionary mapping frame_number -> list of digit images
        """
        cap = cv2.VideoCapture(self.video_path)
        
        if not cap.isOpened():
            print(f"❌ Failed to open video: {self.video_path}")
            return {}
        
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        
        print(f"\n{'='*60}")
        print(f"Extracting Lap Number Digit Templates")
        print(f"{'='*60}\n")
        print(f"Video: {self.video_path}")
        print(f"Total frames: {total_frames} ({total_frames/fps:.1f} seconds)")
        print(f"Sampling: Every {sample_every_n_frames} frames (~{sample_every_n_frames/fps:.1f}s intervals)")
        print(f"ROI: x={self.roi_config['x']}, y={self.roi_config['y']}, "
              f"w={self.roi_config['width']}, h={self.roi_config['height']}\n")
        
        if max_frames:
            total_frames = min(total_frames, max_frames)
            print(f"⚠️  Limited to first {max_frames} frames for testing\n")
        
        extracted_samples = {}
        prev_mask = None
        last_lap_mask = None
        frame_num = 0
        samples_collected = 0
        
        try:
            while frame_num < total_frames:
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
                ret, frame = cap.read()
                
                if not ret:
                    break
                
                # Extract and preprocess ROI
                roi = self.extract_lap_roi(frame)
                if roi is not None:
                    mask = self.preprocess_roi(roi)
                    
                    # Check if lap number changed
                    if self.detect_lap_change(prev_mask, mask):
                        # Save this as a new lap number sample
                        digits = self.split_digits(mask)
                        
                        if len(digits) > 0:
                            extracted_samples[frame_num] = digits
                            samples_collected += 1
                            
                            # Save debug image
                            debug_path = self.debug_dir / f"frame{frame_num}_mask.png"
                            cv2.imwrite(str(debug_path), mask)
                            
                            print(f"📷 Frame {frame_num} ({frame_num/fps:.1f}s): "
                                  f"Found {len(digits)} digit(s)")
                        
                        last_lap_mask = mask
                    
                    prev_mask = mask
                
                # Progress indicator
                frame_num += sample_every_n_frames
                if frame_num % (sample_every_n_frames * 30) == 0:
                    progress = (frame_num / total_frames) * 100
                    print(f"   Progress: {progress:.1f}% ({frame_num}/{total_frames} frames, "
                          f"{samples_collected} samples collected)")
        
        finally:
            cap.release()
        
        print(f"\n✅ Extraction complete!")
        print(f"   Collected {samples_collected} lap number samples")
        print(f"   Saved to: {self.debug_dir}\n")
        
        return extracted_samples
    
    def manual_labeling_guide(self, extracted_samples: Dict[int, list]):
        """
        Print guide for manually labeling extracted digits.
        """
        print(f"\n{'='*60}")
        print(f"Manual Labeling Required")
        print(f"{'='*60}\n")
        
        print(f"I've extracted {len(extracted_samples)} lap number samples.")
        print(f"Now you need to manually label and save digit templates:\n")
        
        print(f"1. Open folder: {self.debug_dir}")
        print(f"2. Look at each 'frame*_mask.png' image")
        print(f"3. For each digit, crop it and save to {self.template_dir}/[digit].png")
        print(f"4. Template naming: 0.png, 1.png, 2.png, ..., 9.png\n")
        
        print(f"Tips:")
        print(f"   • Focus on clear, well-defined digits")
        print(f"   • Templates should be ~20-40 pixels wide")
        print(f"   • White digit on black background (already preprocessed)")
        print(f"   • You only need ONE good template per digit")
        print(f"   • Start with lap 1-9 for single digits, then 10-19 for compound digits\n")
        
        # Show which frames likely contain which lap numbers
        print(f"Suggested frames to check (in order):")
        for i, (frame_num, digits) in enumerate(sorted(extracted_samples.items())[:20]):
            print(f"   Frame {frame_num}: {len(digits)} digit(s)")
        
        if len(extracted_samples) > 20:
            print(f"   ... and {len(extracted_samples) - 20} more frames\n")
        
        print(f"\nAfter labeling, run your main script to test template matching!")


def main():
    """Main extraction pipeline."""
    
    # Configuration
    VIDEO_PATH = './test-acc.mp4'  # Full race video
    CONFIG_PATH = 'config/roi_config.yaml'
    
    # Check if video exists
    if not Path(VIDEO_PATH).exists():
        print(f"\n❌ Error: Video file not found at '{VIDEO_PATH}'")
        print(f"Please update VIDEO_PATH in this script to point to your full race video.")
        return
    
    # Load ROI config
    with open(CONFIG_PATH, 'r') as f:
        roi_config = yaml.safe_load(f)
    
    # Create extractor
    extractor = DigitTemplateExtractor(VIDEO_PATH, roi_config)
    
    # Extract digit samples from video
    # Sample every 30 frames (1 second at 30fps) to catch lap changes
    extracted_samples = extractor.extract_from_video(
        sample_every_n_frames=30,
        max_frames=None  # Process entire video (set to ~1000 for quick test)
    )
    
    # Provide manual labeling instructions
    extractor.manual_labeling_guide(extracted_samples)
    
    print(f"\n{'='*60}")
    print(f"✅ Extraction Complete!")
    print(f"{'='*60}\n")


if __name__ == '__main__':
    main()

