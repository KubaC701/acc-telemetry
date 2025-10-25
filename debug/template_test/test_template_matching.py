"""
Debug script to test template matching on specific frames.
"""

import cv2
import numpy as np
import yaml
from pathlib import Path
from src.lap_detector import LapDetector

def test_on_frame(video_path: str, frame_num: int, roi_config: dict):
    """Test lap detection on a specific frame."""
    cap = cv2.VideoCapture(video_path)
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
    ret, frame = cap.read()
    cap.release()
    
    if not ret:
        print(f"❌ Failed to read frame {frame_num}")
        return
    
    # Create lap detector
    detector = LapDetector(roi_config)
    
    # Extract ROI and show it
    roi_cfg = roi_config['lap_number']
    x, y, w, h = roi_cfg['x'], roi_cfg['y'], roi_cfg['width'], roi_cfg['height']
    roi = frame[y:y+h, x:x+w]
    
    print(f"\n{'='*60}")
    print(f"Testing Frame {frame_num}")
    print(f"{'='*60}")
    print(f"ROI shape: {roi.shape}")
    
    # Save ROI for visual inspection
    debug_dir = Path('debug/template_test')
    debug_dir.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(debug_dir / f'frame{frame_num}_roi_color.png'), roi)
    
    # Show preprocessed version
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    lower_white = np.array([0, 0, 180])
    upper_white = np.array([180, 50, 255])
    white_mask = cv2.inRange(hsv, lower_white, upper_white)
    
    kernel = np.ones((2, 2), np.uint8)
    white_mask = cv2.morphologyEx(white_mask, cv2.MORPH_CLOSE, kernel)
    white_mask = cv2.morphologyEx(white_mask, cv2.MORPH_OPEN, kernel)
    
    cv2.imwrite(str(debug_dir / f'frame{frame_num}_preprocessed.png'), white_mask)
    
    # Try template matching
    lap_number = detector.extract_lap_number(frame)
    
    print(f"Detected lap number: {lap_number}")
    print(f"Templates loaded: {detector.lap_matcher.has_templates()}")
    print(f"Number of templates: {len(detector.lap_matcher.templates)}")
    print(f"Template digits: {sorted(detector.lap_matcher.templates.keys())}")
    
    # Show saved debug images
    print(f"\n📁 Debug images saved to: {debug_dir}")
    print(f"   - frame{frame_num}_roi_color.png (original ROI)")
    print(f"   - frame{frame_num}_preprocessed.png (after preprocessing)")
    
    return lap_number


def main():
    """Test template matching on various frames."""
    VIDEO_PATH = './test-acc.mp4'
    
    with open('config/roi_config.yaml', 'r') as f:
        roi_config = yaml.safe_load(f)
    
    # Test on frames we know should show different lap numbers
    test_frames = [
        240,    # Should be lap 22 or similar (from extraction)
        2010,   # Early lap
        5070,   # Mid race
        10000,  # Later
        20000,  # Much later
    ]
    
    print(f"Testing template matching on {len(test_frames)} frames from {VIDEO_PATH}\n")
    
    for frame_num in test_frames:
        result = test_on_frame(VIDEO_PATH, frame_num, roi_config)
        print(f"Result: {result}\n")


if __name__ == '__main__':
    main()

