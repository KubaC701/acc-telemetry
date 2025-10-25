"""
Visualize exactly what ROI we're extracting and why template matching might be failing.
"""

import cv2
import numpy as np
import yaml
from pathlib import Path


def visualize_frame_with_roi(video_path: str, frame_num: int, roi_config: dict):
    """
    Show full frame with ROI box drawn on it.
    """
    cap = cv2.VideoCapture(video_path)
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
    ret, frame = cap.read()
    cap.release()
    
    if not ret:
        print(f"❌ Failed to read frame {frame_num}")
        return
    
    # Draw all ROIs on the frame
    debug_frame = frame.copy()
    
    # Lap number ROI (RED box)
    lap_roi = roi_config.get('lap_number', {})
    if lap_roi:
        x, y, w, h = lap_roi['x'], lap_roi['y'], lap_roi['width'], lap_roi['height']
        cv2.rectangle(debug_frame, (x, y), (x+w, y+h), (0, 0, 255), 2)
        cv2.putText(debug_frame, 'LAP NUMBER', (x, y-10), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
        
        # Extract and show the ROI
        lap_roi_img = frame[y:y+h, x:x+w]
        
        # Also show preprocessed version
        hsv = cv2.cvtColor(lap_roi_img, cv2.COLOR_BGR2HSV)
        lower_white = np.array([0, 0, 180])
        upper_white = np.array([180, 50, 255])
        white_mask = cv2.inRange(hsv, lower_white, upper_white)
        
        kernel = np.ones((2, 2), np.uint8)
        white_mask = cv2.morphologyEx(white_mask, cv2.MORPH_CLOSE, kernel)
        white_mask = cv2.morphologyEx(white_mask, cv2.MORPH_OPEN, kernel)
        
        return debug_frame, lap_roi_img, white_mask
    
    return debug_frame, None, None


def main():
    """Visualize ROI extraction on various frames."""
    VIDEO_PATH = './test-acc.mp4'
    
    with open('config/roi_config.yaml', 'r') as f:
        roi_config = yaml.safe_load(f)
    
    # Test different frames
    test_frames = [
        240,    # Early
        2010,   # Should show lap number
        5070,   # Mid
        10000,  # Later
        30000,  # Much later
    ]
    
    debug_dir = Path('debug/roi_visualization')
    debug_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\n{'='*70}")
    print(f"ROI Visualization - Understanding What We're Extracting")
    print(f"{'='*70}\n")
    print(f"ROI Config for lap_number:")
    lap_cfg = roi_config.get('lap_number', {})
    print(f"  x={lap_cfg.get('x')}, y={lap_cfg.get('y')}, ")
    print(f"  width={lap_cfg.get('width')}, height={lap_cfg.get('height')}")
    print(f"\nGenerating visualization images...\n")
    
    for frame_num in test_frames:
        full_frame, roi_img, preprocessed = visualize_frame_with_roi(
            VIDEO_PATH, frame_num, roi_config
        )
        
        if full_frame is not None:
            # Save full frame with ROI box
            full_path = debug_dir / f'frame{frame_num}_FULL_with_ROI.png'
            cv2.imwrite(str(full_path), full_frame)
            
            # Save zoomed top-left corner (where HUD is)
            hud_area = full_frame[0:300, 0:500]  # Top-left corner
            hud_path = debug_dir / f'frame{frame_num}_HUD_AREA.png'
            cv2.imwrite(str(hud_path), hud_area)
            
            if roi_img is not None:
                # Save extracted ROI
                roi_path = debug_dir / f'frame{frame_num}_EXTRACTED_ROI.png'
                cv2.imwrite(str(roi_path), roi_img)
                
                # Scale up ROI for better visibility
                scale = 10
                roi_large = cv2.resize(roi_img, 
                                      (roi_img.shape[1]*scale, roi_img.shape[0]*scale),
                                      interpolation=cv2.INTER_NEAREST)
                roi_large_path = debug_dir / f'frame{frame_num}_ROI_10X.png'
                cv2.imwrite(str(roi_large_path), roi_large)
            
            if preprocessed is not None:
                # Save preprocessed
                pre_path = debug_dir / f'frame{frame_num}_PREPROCESSED.png'
                cv2.imwrite(str(pre_path), preprocessed)
                
                # Scale up preprocessed
                pre_large = cv2.resize(preprocessed,
                                      (preprocessed.shape[1]*scale, preprocessed.shape[0]*scale),
                                      interpolation=cv2.INTER_NEAREST)
                pre_large_path = debug_dir / f'frame{frame_num}_PREPROCESSED_10X.png'
                cv2.imwrite(str(pre_large_path), pre_large)
            
            print(f"✅ Frame {frame_num}:")
            print(f"   - {full_path.name}")
            print(f"   - {hud_path.name}")
            print(f"   - {roi_large_path.name}")
            print(f"   - {pre_large_path.name}")
    
    print(f"\n{'='*70}")
    print(f"✅ Visualization Complete!")
    print(f"{'='*70}\n")
    print(f"📁 All images saved to: {debug_dir}")
    print(f"\nNow open these images to see:")
    print(f"  1. *_FULL_with_ROI.png - Full frame with RED box showing ROI")
    print(f"  2. *_HUD_AREA.png - Zoomed HUD area")
    print(f"  3. *_ROI_10X.png - 10x zoomed ROI (what we extract)")
    print(f"  4. *_PREPROCESSED_10X.png - After preprocessing (what templates see)")
    print(f"\nThis will show us if:")
    print(f"  - ROI is in the wrong position")
    print(f"  - ROI is too small/large")
    print(f"  - Preprocessing is removing the digits")
    print(f"  - Digits look different than templates")


if __name__ == '__main__':
    main()

