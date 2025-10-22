"""
Find the correct ROI coordinates for the lap number in the RED FLAG.
"""

import cv2
import numpy as np
from pathlib import Path


def test_roi_coordinates(video_path: str, frame_num: int, roi_coords: dict):
    """
    Test specific ROI coordinates and show the result.
    """
    cap = cv2.VideoCapture(video_path)
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
    ret, frame = cap.read()
    cap.release()
    
    if not ret:
        return None
    
    x, y, w, h = roi_coords['x'], roi_coords['y'], roi_coords['width'], roi_coords['height']
    roi = frame[y:y+h, x:x+w]
    
    # Preprocess
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    lower_white = np.array([0, 0, 180])
    upper_white = np.array([180, 50, 255])
    white_mask = cv2.inRange(hsv, lower_white, upper_white)
    
    kernel = np.ones((2, 2), np.uint8)
    white_mask = cv2.morphologyEx(white_mask, cv2.MORPH_CLOSE, kernel)
    white_mask = cv2.morphologyEx(white_mask, cv2.MORPH_OPEN, kernel)
    
    return roi, white_mask


def main():
    """Find correct ROI for red flag lap number."""
    VIDEO_PATH = './test-acc.mp4'
    
    # Based on visual inspection of the HUD images:
    # The red flag with lap number is in top-left corner
    # Trying different coordinates to find the best fit
    
    test_rois = [
        {'name': 'Original (WRONG - white box)', 'x': 237, 'y': 71, 'width': 47, 'height': 37},
        {'name': 'Red Flag - Attempt 1', 'x': 30, 'y': 47, 'width': 35, 'height': 25},
        {'name': 'Red Flag - Attempt 2', 'x': 35, 'y': 50, 'width': 40, 'height': 28},
        {'name': 'Red Flag - Attempt 3', 'x': 33, 'y': 48, 'width': 42, 'height': 30},
    ]
    
    test_frames = [2010, 10000, 30000]  # Frames with clear lap numbers
    
    debug_dir = Path('debug/roi_finding')
    debug_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\n{'='*70}")
    print(f"Finding Correct Lap Number ROI")
    print(f"{'='*70}\n")
    
    for roi_config in test_rois:
        print(f"\n{roi_config['name']}:")
        print(f"  x={roi_config['x']}, y={roi_config['y']}, w={roi_config['width']}, h={roi_config['height']}")
        
        for frame_num in test_frames:
            result = test_roi_coordinates(VIDEO_PATH, frame_num, roi_config)
            if result:
                roi_img, preprocessed = result
                
                # Scale up 10x for visibility
                scale = 10
                roi_large = cv2.resize(roi_img, 
                                      (roi_img.shape[1]*scale, roi_img.shape[0]*scale),
                                      interpolation=cv2.INTER_NEAREST)
                pre_large = cv2.resize(preprocessed,
                                      (preprocessed.shape[1]*scale, preprocessed.shape[0]*scale),
                                      interpolation=cv2.INTER_NEAREST)
                
                # Save
                name_safe = roi_config['name'].replace(' ', '_').replace('-', '')
                roi_path = debug_dir / f"{name_safe}_frame{frame_num}_ROI.png"
                pre_path = debug_dir / f"{name_safe}_frame{frame_num}_PREPROCESSED.png"
                
                cv2.imwrite(str(roi_path), roi_large)
                cv2.imwrite(str(pre_path), pre_large)
                
                print(f"    Frame {frame_num}: saved {roi_path.name}")
    
    print(f"\n{'='*70}")
    print(f"✅ Test Complete!")
    print(f"{'='*70}\n")
    print(f"📁 Check images in: {debug_dir}")
    print(f"\nLook for the ROI that clearly shows the lap number digits!")
    print(f"Once you find the best one, update config/roi_config.yaml")


if __name__ == '__main__':
    main()

