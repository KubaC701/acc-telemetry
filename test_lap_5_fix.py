"""
Test the lap 5 detection fix with finalize_lap_detection().
"""

import cv2
import yaml
from pathlib import Path
from src.lap_detector import LapDetector

# Load ROI config
config_path = Path('config/roi_config.yaml')
with open(config_path, 'r') as f:
    roi_config = yaml.safe_load(f)

# Use lap_number_training ROI
lap_roi_config = {'lap_number': roi_config['lap_number_training']}

print(f"Using lap_number_training ROI: {lap_roi_config['lap_number']}")
print()

# Initialize lap detector
detector = LapDetector(roi_config=lap_roi_config, enable_performance_stats=False)

# Open panorama video
video_path = 'panorama.mp4'
cap = cv2.VideoCapture(video_path)

total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
fps = cap.get(cv2.CAP_PROP_FPS)

print(f"Video: {total_frames} frames @ {fps:.2f} FPS")
print()

# Process all frames (simulate main.py behavior)
print("Processing frames...")
detected_laps = []
previous_lap = None
lap_transitions = []

for frame_idx in range(total_frames):
    ret, frame = cap.read()
    if not ret:
        break
    
    # Extract lap number
    lap_number = detector.extract_lap_number(frame)
    
    # Track transitions
    if detector.detect_lap_transition(lap_number, previous_lap):
        lap_transitions.append({
            'frame': frame_idx,
            'from_lap': previous_lap,
            'to_lap': lap_number
        })
        print(f"Frame {frame_idx:5d} ({frame_idx/fps:6.2f}s): Lap {previous_lap} → {lap_number}")
    
    if lap_number is not None and lap_number not in detected_laps:
        detected_laps.append(lap_number)
    
    previous_lap = lap_number

cap.release()

print()
print("=" * 80)
print("BEFORE FINALIZATION:")
print(f"Detected laps: {detected_laps}")
print(f"Last lap: {previous_lap}")
print()

# Now finalize (this should catch lap 5)
final_lap = detector.finalize_lap_detection()
print("AFTER FINALIZATION:")
print(f"Final lap: {final_lap}")

if final_lap is not None and final_lap not in detected_laps:
    print(f"✅ Finalization caught lap {final_lap} (was missing before)")
    detected_laps.append(final_lap)
    
    if previous_lap is not None and final_lap == previous_lap + 1:
        print(f"   Adding final transition: Lap {previous_lap} → {final_lap}")
        lap_transitions.append({
            'frame': total_frames - 1,
            'from_lap': previous_lap,
            'to_lap': final_lap
        })

print()
print("=" * 80)
print("FINAL RESULTS:")
print(f"All detected laps: {detected_laps}")
print(f"Lap transitions: {len(lap_transitions)}")
for t in lap_transitions:
    print(f"  Frame {t['frame']:5d}: Lap {t['from_lap']} → {t['to_lap']}")

print()
if sorted(detected_laps) == [0, 1, 2, 3, 4, 5]:
    print("✅ SUCCESS! All expected laps (0-5) detected correctly!")
else:
    print(f"⚠️  Expected: [0, 1, 2, 3, 4, 5]")
    print(f"   Got: {detected_laps}")

detector.close()

