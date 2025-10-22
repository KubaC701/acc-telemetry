"""
Debug script to visualize lap number detection.
Shows what the ROI looks like and measures OCR performance.
"""

import cv2
import numpy as np
import yaml
import time
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
    print("Lap Number Detection Debug (OCR Performance Test)")
    print("="*60)
    print(f"ROI: x={lap_roi['x']}, y={lap_roi['y']}, w={lap_roi['width']}, h={lap_roi['height']}")
    print(f"Testing {len(test_frames)} frames...\n")
    
    total_ocr_time = 0
    successful_detections = 0
    
    for frame_num in test_frames:
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
        ret, frame = cap.read()
        
        if not ret:
            print(f"⚠️  Could not read frame {frame_num}")
            continue
        
        # Extract lap number ROI
        x, y, w, h = lap_roi['x'], lap_roi['y'], lap_roi['width'], lap_roi['height']
        roi = frame[y:y+h, x:x+w]
        
        # Show preprocessing (same as in LapDetector)
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY)
        inverted = cv2.bitwise_not(binary)
        scale_factor = 3
        height_roi, width_roi = inverted.shape
        upscaled = cv2.resize(inverted, (width_roi * scale_factor, height_roi * scale_factor), 
                              interpolation=cv2.INTER_LINEAR)
        
        # Measure OCR time
        start_time = time.time()
        lap_number = lap_detector.extract_lap_number(frame)
        ocr_time = (time.time() - start_time) * 1000  # Convert to ms
        
        total_ocr_time += ocr_time
        if lap_number is not None:
            successful_detections += 1
        
        # Save debug images
        roi_path = debug_dir / f"frame{frame_num}_roi.png"
        preprocessed_path = debug_dir / f"frame{frame_num}_preprocessed.png"
        cv2.imwrite(str(roi_path), roi)
        cv2.imwrite(str(preprocessed_path), upscaled)
        
        print(f"📷 Frame {frame_num}:")
        print(f"   Detected lap: {lap_number if lap_number else 'None'}")
        print(f"   ROI size: {roi.shape[1]}x{roi.shape[0]} → {upscaled.shape[1]}x{upscaled.shape[0]}")
        print(f"   OCR time: {ocr_time:.2f}ms")
        print(f"   Saved: {roi_path}, {preprocessed_path}")
        print()
    
    cap.release()
    
    # Print performance summary
    print("="*60)
    print("Performance Summary")
    print("="*60)
    if test_frames:
        avg_ocr_time = total_ocr_time / len(test_frames)
        success_rate = (successful_detections / len(test_frames)) * 100
        print(f"Total frames tested: {len(test_frames)}")
        print(f"Successful detections: {successful_detections} ({success_rate:.1f}%)")
        print(f"Average OCR time: {avg_ocr_time:.2f}ms")
        print(f"Min expected: 10-20ms")
        print(f"Max acceptable: 25-40ms")
        
        if avg_ocr_time <= 25:
            print(f"✅ SUCCESS: OCR is fast enough!")
        elif avg_ocr_time <= 40:
            print(f"⚠️  ACCEPTABLE: OCR is slightly slow but usable")
        else:
            print(f"❌ FAILURE: OCR is too slow, consider optimizations")
    
    print()
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

