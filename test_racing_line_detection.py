import cv2
import numpy as np
import yaml

# Load config
with open('config/roi_config.yaml', 'r') as f:
    roi_config = yaml.safe_load(f)

# Open video
cap = cv2.VideoCapture('./panorama.mp4')
cap.set(cv2.CAP_PROP_POS_FRAMES, 1000)
ret, frame = cap.read()
cap.release()

# Extract ROI
roi_coords = roi_config['track_map']
x, y, w, h = roi_coords['x'], roi_coords['y'], roi_coords['width'], roi_coords['height']
map_roi = frame[y:y+h, x:x+w]

# Convert to grayscale
gray = cv2.cvtColor(map_roi, cv2.COLOR_BGR2GRAY)

# Save grayscale
cv2.imwrite('debug/gray_minimap.png', gray)

# Try different gray thresholds
thresholds = [100, 120, 140, 160, 180, 200]

for thresh_val in thresholds:
    _, binary = cv2.threshold(gray, thresh_val, 255, cv2.THRESH_BINARY)
    cv2.imwrite(f'debug/threshold_{thresh_val}.png', binary)
    print(f"Threshold {thresh_val}: {np.sum(binary > 0)} white pixels")

print("\n✅ Check debug/threshold_*.png to see which threshold captures the racing line!")
