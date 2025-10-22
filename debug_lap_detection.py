"""
Debug script to visualize lap number detection.
Shows what the ROI looks like and what the template matching sees.
"""

import cv2
import numpy as np
import yaml
from pathlib import Path
from src.lap_detector import LapDetector
from src.template_matcher import TemplateMatcher


def visualize_lap_detection(video_path: str, test_frames: list):
    """
    Visualize lap number detection at specific frames.
    
    Args:
        video_path: Path to video file
        test_frames: List of frame numbers to test
    """
    # Load config
    with open('config/roi_config.yaml', 'r') as f:
        roi_config = yaml.safe_load(f)
    
    lap_roi = roi_config['lap_number']
    
    # Initialize detector
    lap_detector = LapDetector(roi_config)
    
    # Open video
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"❌ Failed to open video: {video_path}")
        return
    
    # Create debug output directory
    debug_dir = Path('debug/lap_detection_debug')
    debug_dir.mkdir(parents=True, exist_ok=True)
    
    print("="*60)
    print("Lap Number Detection Debug")
    print("="*60)
    print(f"ROI: x={lap_roi['x']}, y={lap_roi['y']}, w={lap_roi['width']}, h={lap_roi['height']}")
    print(f"Testing {len(test_frames)} frames...\n")
    
    for frame_num in test_frames:
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
        ret, frame = cap.read()
        
        if not ret:
            print(f"⚠️  Could not read frame {frame_num}")
            continue
        
        # Extract lap number ROI
        x, y, w, h = lap_roi['x'], lap_roi['y'], lap_roi['width'], lap_roi['height']
        roi = frame[y:y+h, x:x+w]
        
        # Preprocess (same as in LapDetector)
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        lower_white = np.array([0, 0, 180])
        upper_white = np.array([180, 50, 255])
        white_mask = cv2.inRange(hsv, lower_white, upper_white)
        
        # Apply morphological operations
        kernel = np.ones((2, 2), np.uint8)
        white_mask = cv2.morphologyEx(white_mask, cv2.MORPH_CLOSE, kernel)
        white_mask = cv2.morphologyEx(white_mask, cv2.MORPH_OPEN, kernel)
        
        # Try to recognize
        lap_number = lap_detector.extract_lap_number(frame)
        
        # Create visualization
        vis = np.hstack([
            cv2.cvtColor(roi, cv2.COLOR_BGR2RGB),
            cv2.cvtColor(white_mask, cv2.COLOR_GRAY2RGB)
        ])
        
        # Save debug images
        roi_path = debug_dir / f"frame{frame_num}_roi_color.png"
        mask_path = debug_dir / f"frame{frame_num}_white_mask.png"
        vis_path = debug_dir / f"frame{frame_num}_visualization.png"
        
        cv2.imwrite(str(roi_path), roi)
        cv2.imwrite(str(mask_path), white_mask)
        cv2.imwrite(str(vis_path), vis)
        
        print(f"📷 Frame {frame_num}:")
        print(f"   Detected lap: {lap_number if lap_number else 'None'}")
        print(f"   ROI size: {roi.shape[1]}x{roi.shape[0]}")
        print(f"   White pixels: {np.count_nonzero(white_mask)}")
        print(f"   Saved: {vis_path}")
        
        # Analyze white mask
        if np.count_nonzero(white_mask) > 0:
            # Find connected components
            num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(white_mask, connectivity=8)
            print(f"   Connected components: {num_labels - 1}")  # -1 for background
            
            if num_labels > 1:
                for i in range(1, min(num_labels, 6)):  # Show first 5
                    area = stats[i, cv2.CC_STAT_AREA]
                    x_comp = stats[i, cv2.CC_STAT_LEFT]
                    w_comp = stats[i, cv2.CC_STAT_WIDTH]
                    h_comp = stats[i, cv2.CC_STAT_HEIGHT]
                    print(f"      Component {i}: area={area}, x={x_comp}, w={w_comp}, h={h_comp}")
        
        print()
    
    cap.release()
    
    print("="*60)
    print("Debug files saved to:", debug_dir)
    print("="*60)


def test_template_matching_directly():
    """Test template matching on sample frames to see what's going wrong."""
    
    # Load templates
    matcher = TemplateMatcher('templates/lap_digits/')
    
    print("\n" + "="*60)
    print("Template Info")
    print("="*60)
    print(f"Templates loaded: {matcher.has_templates()}")
    print(f"Available digits: {sorted(matcher.templates.keys())}")
    
    for digit, template in matcher.templates.items():
        print(f"   Digit {digit}: {template.shape[1]}x{template.shape[0]} pixels")
    
    print()


if __name__ == '__main__':
    import sys
    
    # Use shorter video for faster debugging
    video_path = './input_video.mp4'
    
    # Test various frames throughout the video
    # For input_video.mp4 (should be about 1-2 minutes)
    test_frames = [
        0,        # Start
        50,       # Few seconds in
        240,      # ~10 seconds (might be lap 1)
        500,      # ~20 seconds
        1000,     # ~40 seconds
        2000,     # ~1m20s
        2500,     # ~1m45s
        3000,     # ~2min
    ]
    
    if not Path(video_path).exists():
        print(f"❌ Video not found: {video_path}")
        sys.exit(1)
    
    # Show template info
    test_template_matching_directly()
    
    # Visualize detection
    visualize_lap_detection(video_path, test_frames)

