"""
Check pixel counts for each detected blip to see if some are below confidence threshold.
"""

import cv2
import yaml
import numpy as np

# Load configuration
with open('config/roi_config.yaml', 'r') as f:
    roi_config = yaml.safe_load(f)

throttle_roi = roi_config['throttle']
video = cv2.VideoCapture('input_video.mp4')

# Blip frames from previous analysis
blips = [
    (58, 59, "Blip 1"),
    (64, 66, "Blip 2"),
    (72, 77, "Blip 3"),
    (81, 90, "Blip 4"),
    (94, 100, "Blip 5"),
    (104, 105, "Blip 6"),
]

print("="*80)
print("PIXEL COUNT ANALYSIS FOR EACH BLIP")
print("="*80)
print("\nChecking if any blips have suspiciously low pixel counts...\n")

for start_frame, end_frame, label in blips:
    print(f"{label} (frames {start_frame}-{end_frame}):")
    
    pixel_counts = []
    throttle_percentages = []
    
    for frame_num in range(start_frame, end_frame + 1):
        video.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
        ret, frame = video.read()
        if not ret:
            continue
        
        # Extract throttle ROI
        throttle_img = frame[throttle_roi['y']:throttle_roi['y']+throttle_roi['height'],
                             throttle_roi['x']:throttle_roi['x']+throttle_roi['width']]
        
        # Convert to HSV and detect
        hsv = cv2.cvtColor(throttle_img, cv2.COLOR_BGR2HSV)
        mask_green = cv2.inRange(hsv, np.array([35, 50, 50]), np.array([85, 255, 255]))
        mask_yellow = cv2.inRange(hsv, np.array([15, 100, 100]), np.array([35, 255, 255]))
        mask = cv2.bitwise_or(mask_green, mask_yellow)
        
        pixel_count = np.count_nonzero(mask)
        pixel_counts.append(pixel_count)
        
        # Calculate percentage (simplified)
        height, width = mask.shape
        middle_rows = mask[height//3:2*height//3, :]
        filled_widths = []
        for row in middle_rows:
            non_zero_cols = np.where(row > 0)[0]
            if len(non_zero_cols) > 0:
                filled_widths.append(non_zero_cols[-1] + 1)
        
        if filled_widths and pixel_count >= 50:
            percentage = (np.median(filled_widths) / width) * 100.0
        else:
            percentage = 0.0
        
        throttle_percentages.append(percentage)
        
        print(f"  Frame {frame_num}: {pixel_count:4d} pixels → {percentage:5.1f}% throttle")
    
    avg_pixels = np.mean(pixel_counts)
    min_pixels = min(pixel_counts)
    max_pixels = max(pixel_counts)
    
    print(f"  Summary: avg={avg_pixels:.0f}, min={min_pixels}, max={max_pixels}")
    
    if min_pixels < 50:
        print(f"  ⚠️  WARNING: Some frames below 50 pixel threshold!")
    if avg_pixels < 100:
        print(f"  ⚠️  SUSPICIOUS: Low average pixel count - might be noise")
    if max_pixels < 200:
        print(f"  ⚠️  WEAK SIGNAL: Low peak pixels - questionable blip")
    
    print()

video.release()

print("="*80)
print("RECOMMENDATIONS")
print("="*80)
print("""
Based on pixel counts, consider:

1. If blips have <100 avg pixels: Likely noise/artifacts
   → Increase pixel threshold from 50 to 100

2. If blips are very short (1-2 frames): Transient detection
   → Require minimum blip duration (3+ consecutive frames)

3. If blips occur <0.15s apart: Might be same downshift
   → Merge blips that are close together

This should consolidate the 6 detected blips into 3 real downshifts.
""")

