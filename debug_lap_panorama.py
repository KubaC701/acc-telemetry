"""
Debug script to analyze lap detection issues in panorama.mp4.
Extracts frames at key points and shows what the OCR is detecting.
"""

import cv2
import numpy as np
import yaml
from pathlib import Path
from src.lap_detector import LapDetector

# Load ROI config
config_path = Path('config/roi_config.yaml')
with open(config_path, 'r') as f:
    roi_config = yaml.safe_load(f)

# Use the training ROI (x=181 as mentioned by user)
lap_number_roi = roi_config['lap_number_training']

print(f"Using lap_number_training ROI: {lap_number_roi}")

# Initialize lap detector with the training ROI
detector = LapDetector(
    roi_config={'lap_number': lap_number_roi},
    enable_performance_stats=True
)

# Open panorama video
video_path = 'panorama.mp4'
cap = cv2.VideoCapture(video_path)

if not cap.isOpened():
    print(f"❌ Failed to open {video_path}")
    exit(1)

total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
fps = cap.get(cv2.CAP_PROP_FPS)

print(f"Video: {total_frames} frames @ {fps:.2f} FPS")
print(f"Duration: {total_frames/fps:.2f} seconds")
print()

# Create debug output directory
debug_dir = Path('debug/panorama_lap_debug')
debug_dir.mkdir(parents=True, exist_ok=True)

# Sample frames throughout the video
sample_points = [
    0,                          # Start (should be lap 0)
    int(total_frames * 0.2),   # 20% through
    int(total_frames * 0.4),   # 40% through
    int(total_frames * 0.6),   # 60% through
    int(total_frames * 0.8),   # 80% through
    total_frames - 1            # End (should be lap 5)
]

print("Sampling frames to visualize lap number detection:")
print("=" * 80)

detected_laps = []
previous_lap = None

for frame_idx in range(total_frames):
    ret, frame = cap.read()
    if not ret:
        break
    
    # Extract lap number
    lap_number = detector.extract_lap_number(frame)
    
    # Track lap transitions
    if lap_number is not None:
        if lap_number not in detected_laps:
            detected_laps.append(lap_number)
            print(f"Frame {frame_idx:5d} ({frame_idx/fps:6.2f}s): Lap {lap_number} detected")
    
    # Save debug images at sample points
    if frame_idx in sample_points:
        # Extract ROI
        x = lap_number_roi['x']
        y = lap_number_roi['y']
        w = lap_number_roi['width']
        h = lap_number_roi['height']
        
        roi = frame[y:y+h, x:x+w]
        
        # Save full frame with ROI highlighted
        frame_with_roi = frame.copy()
        cv2.rectangle(frame_with_roi, (x, y), (x+w, y+h), (0, 255, 0), 2)
        cv2.putText(frame_with_roi, f"Frame {frame_idx}", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.putText(frame_with_roi, f"Detected: {lap_number}", (10, 60), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        
        output_frame_path = debug_dir / f"frame_{frame_idx:05d}_full.png"
        cv2.imwrite(str(output_frame_path), frame_with_roi)
        
        # Save enlarged ROI for inspection
        roi_enlarged = cv2.resize(roi, (roi.shape[1]*4, roi.shape[0]*4), 
                                 interpolation=cv2.INTER_NEAREST)
        output_roi_path = debug_dir / f"frame_{frame_idx:05d}_roi_enlarged.png"
        cv2.imwrite(str(output_roi_path), roi_enlarged)
        
        print(f"  Saved debug images: frame_{frame_idx:05d}_*.png")
    
    previous_lap = lap_number

cap.release()
detector.close()

print()
print("=" * 80)
print("SUMMARY:")
print(f"Expected laps: 0, 1, 2, 3, 4, 5")
print(f"Detected laps: {detected_laps}")
print()

if detected_laps == [7]:
    print("⚠️  Issue confirmed: Only lap 7 detected when expecting laps 0-5")
    print()
    print("Possible causes:")
    print("1. OCR is consistently misreading a specific digit (e.g., 0 as 7)")
    print("2. ROI is capturing wrong part of the HUD")
    print("3. Video quality/compression affecting digit clarity")
    print()
    print(f"Check debug images in: {debug_dir}/")
elif sorted(detected_laps) == [0, 1, 2, 3, 4, 5]:
    print("✅ All expected laps detected correctly!")
else:
    print(f"⚠️  Unexpected detection pattern")
    print(f"Missing laps: {set([0,1,2,3,4,5]) - set(detected_laps)}")
    print(f"Extra laps: {set(detected_laps) - set([0,1,2,3,4,5])}")

print()
print("Performance stats:")
print(detector.get_performance_stats())

