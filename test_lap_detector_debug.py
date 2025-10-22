"""Debug the LapDetector to see why it's failing"""
import cv2
import yaml
from src.lap_detector import LapDetector

# Load config
with open('config/roi_config.yaml', 'r') as f:
    roi_config = yaml.safe_load(f)

lap_detector = LapDetector(roi_config)

# Test on frame 1000 (known to have lap 22)
cap = cv2.VideoCapture('./input_video.mp4')
cap.set(cv2.CAP_PROP_POS_FRAMES, 1000)
ret, frame = cap.read()

if ret:
    print("Testing frame 1000...")
    
    # Try extracting multiple times (history buffer needs multiple frames)
    for i in range(10):
        lap_number = lap_detector.extract_lap_number(frame)
        print(f"  Attempt {i+1}: {lap_number}")
        
        # Check history
        print(f"    History: {lap_detector._lap_number_history}")
        print(f"    Last valid: {lap_detector._last_valid_lap_number}")

cap.release()


