"""
Inspect the lap number history at end of video to understand what's in there.
"""

import cv2
import yaml
from pathlib import Path
from src.lap_detector import LapDetector

# Load ROI config
config_path = Path('config/roi_config.yaml')
with open(config_path, 'r') as f:
    roi_config = yaml.safe_load(f)

lap_roi_config = {'lap_number': roi_config['lap_number_training']}

# Initialize lap detector
detector = LapDetector(roi_config=lap_roi_config, enable_performance_stats=False)

# Open panorama video
video_path = 'panorama.mp4'
cap = cv2.VideoCapture(video_path)

total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
fps = cap.get(cv2.CAP_PROP_FPS)

# Process all frames
for frame_idx in range(total_frames):
    ret, frame = cap.read()
    if not ret:
        break
    
    lap_number = detector.extract_lap_number(frame)

cap.release()

# Inspect final state
print("=" * 80)
print("LAP DETECTOR STATE AT END OF VIDEO:")
print()
print(f"Last valid lap number: {detector._last_valid_lap_number}")
print(f"Lap number history (last {detector._history_size} detections):")
print(f"  {detector._lap_number_history}")
print()

# Count frequencies
from collections import Counter
counts = Counter(detector._lap_number_history)
print("Frequency breakdown:")
for lap_num, count in sorted(counts.items()):
    percentage = (count / len(detector._lap_number_history)) * 100
    print(f"  Lap {lap_num}: {count} frames ({percentage:.1f}%)")
print()

# Check if lap 5 is in there
if 5 in detector._lap_number_history:
    lap_5_count = detector._lap_number_history.count(5)
    print(f"✅ Lap 5 IS in history ({lap_5_count} times)")
    print(f"   But 30% threshold requires {int(detector._history_size * 0.3)} frames")
    print(f"   {lap_5_count} < {int(detector._history_size * 0.3)} = not enough for consensus")
else:
    print(f"❌ Lap 5 NOT in history at all")
    print(f"   This means the temporal smoothing rejected it before it even entered history")

detector.close()

