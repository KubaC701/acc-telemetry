"""
Debug script to find exactly when lap 5 appears and how many frames it's visible.
This will help us understand why the temporal smoothing is rejecting it.
"""

import cv2
import yaml
from pathlib import Path
from src.lap_detector import LapDetector

# Load ROI config
config_path = Path('config/roi_config.yaml')
with open(config_path, 'r') as f:
    roi_config = yaml.safe_load(f)

lap_number_roi = roi_config['lap_number_training']

print(f"Using lap_number_training ROI: {lap_number_roi}")

# Initialize lap detector
detector = LapDetector(
    roi_config={'lap_number': lap_number_roi},
    enable_performance_stats=False
)

# Open panorama video
video_path = 'panorama.mp4'
cap = cv2.VideoCapture(video_path)

total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
fps = cap.get(cv2.CAP_PROP_FPS)

print(f"Video: {total_frames} frames @ {fps:.2f} FPS")
print()

# Focus on the last 200 frames to see lap 4->5 transition
start_frame = max(0, total_frames - 200)
cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

print(f"Analyzing frames {start_frame} to {total_frames} (last {total_frames - start_frame} frames):")
print("=" * 80)

frame_idx = start_frame
raw_ocr_results = []
smoothed_results = []

while frame_idx < total_frames:
    ret, frame = cap.read()
    if not ret:
        break
    
    # Get raw OCR by directly reading ROI
    x = lap_number_roi['x']
    y = lap_number_roi['y']
    w = lap_number_roi['width']
    h = lap_number_roi['height']
    roi = frame[y:y+h, x:x+w]
    
    # Run OCR directly (bypass smoothing)
    try:
        if detector._tesserocr_api:
            import cv2
            from PIL import Image
            roi_rgb = cv2.cvtColor(roi, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(roi_rgb)
            detector._tesserocr_api.SetImage(pil_image)
            text = detector._tesserocr_api.GetUTF8Text().strip()
            
            if text.isdigit():
                raw_lap = int(text)
            else:
                digits_only = ''.join(filter(str.isdigit, text))
                raw_lap = int(digits_only) if digits_only else None
        else:
            raw_lap = None
    except:
        raw_lap = None
    
    # Get smoothed result (with temporal filtering)
    smoothed_lap = detector.extract_lap_number(frame)
    
    raw_ocr_results.append(raw_lap)
    smoothed_results.append(smoothed_lap)
    
    # Print when we see changes
    if frame_idx == start_frame or raw_lap != raw_ocr_results[-2] or smoothed_lap != smoothed_results[-2]:
        print(f"Frame {frame_idx:5d} ({frame_idx/fps:6.2f}s): RAW OCR={raw_lap}, SMOOTHED={smoothed_lap}")
    
    frame_idx += 1

cap.release()
detector.close()

print()
print("=" * 80)
print("ANALYSIS:")
print()

# Count how many frames show lap 5 in raw OCR
lap_5_raw_count = sum(1 for x in raw_ocr_results if x == 5)
lap_5_smoothed_count = sum(1 for x in smoothed_results if x == 5)

print(f"Lap 5 detected in RAW OCR: {lap_5_raw_count} frames")
print(f"Lap 5 detected in SMOOTHED output: {lap_5_smoothed_count} frames")
print()

# Show the smoothing parameters
print("Smoothing parameters from LapDetector:")
print(f"  History size: {detector._history_size} frames")
print(f"  Consensus required: 70% (i.e., {int(detector._history_size * 0.7)} out of {detector._history_size} frames)")
print()

if lap_5_raw_count > 0 and lap_5_smoothed_count == 0:
    print("⚠️  ISSUE IDENTIFIED:")
    print(f"   Lap 5 appears in {lap_5_raw_count} frames (RAW OCR), but temporal smoothing rejects it.")
    print()
    print("   Why this happens:")
    print(f"   1. The smoothing requires {int(detector._history_size * 0.7)} consistent frames to accept a new lap")
    print(f"   2. Lap 5 only appears for {lap_5_raw_count} frames before video ends")
    print(f"   3. Not enough frames to reach 70% consensus in the {detector._history_size}-frame history window")
    print()
    print("   Solutions:")
    print("   A. Reduce history_size for end-of-video detection")
    print("   B. Lower consensus threshold (e.g., 50% instead of 70%)")
    print("   C. Add special logic to flush remaining history at end of video")
    print("   D. Keep recording a few more seconds after crossing finish line")




