"""
Detailed debugging of template matching to see WHY it's failing.
"""

import cv2
import numpy as np
import yaml
from pathlib import Path
from src.template_matcher import TemplateMatcher


def test_single_digit_matching(video_path: str, frame_num: int, roi_config: dict):
    """
    Test template matching with detailed scoring information.
    """
    # Load frame
    cap = cv2.VideoCapture(video_path)
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
    ret, frame = cap.read()
    cap.release()
    
    if not ret:
        return
    
    # Extract ROI
    roi_cfg = roi_config['lap_number']
    x, y, w, h = roi_cfg['x'], roi_cfg['y'], roi_cfg['width'], roi_cfg['height']
    roi = frame[y:y+h, x:x+w]
    
    # Preprocess
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    lower_white = np.array([0, 0, 180])
    upper_white = np.array([180, 50, 255])
    white_mask = cv2.inRange(hsv, lower_white, upper_white)
    
    kernel = np.ones((2, 2), np.uint8)
    white_mask = cv2.morphologyEx(white_mask, cv2.MORPH_CLOSE, kernel)
    white_mask = cv2.morphologyEx(white_mask, cv2.MORPH_OPEN, kernel)
    
    # Load templates
    matcher = TemplateMatcher('templates/lap_digits/')
    
    print(f"\n{'='*70}")
    print(f"Frame {frame_num} - Detailed Template Matching")
    print(f"{'='*70}\n")
    print(f"ROI shape: {white_mask.shape}")
    print(f"Templates loaded: {len(matcher.templates)}")
    
    # Try matching each template individually with scoring
    best_digit = None
    best_score = 0.0
    
    for digit, template in sorted(matcher.templates.items()):
        print(f"\nTesting digit '{digit}':")
        print(f"  Template shape: {template.shape}")
        print(f"  ROI shape: {white_mask.shape}")
        
        # Resize ROI to match template
        try:
            roi_resized = cv2.resize(white_mask, (template.shape[1], template.shape[0]))
            
            # Template matching
            result = cv2.matchTemplate(roi_resized, template, cv2.TM_CCOEFF_NORMED)
            score = result.max()
            
            print(f"  Match score: {score:.4f}")
            
            if score > best_score:
                best_score = score
                best_digit = digit
        
        except Exception as e:
            print(f"  ERROR: {e}")
    
    print(f"\n{'='*70}")
    print(f"RESULT:")
    print(f"  Best match: '{best_digit}' with score {best_score:.4f}")
    print(f"  Threshold: 0.60 (default)")
    print(f"  Match? {'YES ✅' if best_score > 0.60 else 'NO ❌'}")
    print(f"{'='*70}\n")
    
    # Save debug images
    debug_dir = Path('debug/matching_detail')
    debug_dir.mkdir(parents=True, exist_ok=True)
    
    cv2.imwrite(str(debug_dir / f'frame{frame_num}_roi.png'), white_mask)
    if best_digit:
        best_template = matcher.templates[best_digit]
        cv2.imwrite(str(debug_dir / f'frame{frame_num}_best_template_{best_digit}.png'), best_template)


def main():
    """Test on specific frames."""
    VIDEO_PATH = './test-acc.mp4'
    
    with open('config/roi_config.yaml', 'r') as f:
        roi_config = yaml.safe_load(f)
    
    # Test frames
    test_frames = [240, 2010, 10000]
    
    for frame_num in test_frames:
        test_single_digit_matching(VIDEO_PATH, frame_num, roi_config)


if __name__ == '__main__':
    main()

