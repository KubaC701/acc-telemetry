"""
Search specifically for throttle/brake horizontal bars in bottom-right corner.
Based on user description: small horizontal bars showing throttle (green/yellow/orange) and brake (red/yellow/orange)
"""

import cv2
import numpy as np

VIDEO_PATH = './input_video.mp4'

# Open video
cap = cv2.VideoCapture(VIDEO_PATH)
frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

print(f"Video: {width}x{height}")
print("Searching for throttle/brake bars in bottom-right corner...")

# Get a frame from middle where there should be some throttle/brake activity
cap.set(cv2.CAP_PROP_POS_FRAMES, frame_count // 2)
ret, frame = cap.read()
cap.release()

if not ret:
    print("Error reading frame")
    exit(1)

# Focus on bottom-right area (last 300 pixels horizontally, last 150 pixels vertically)
bottom_right = frame[height-150:height, width-300:width]

# Save it for inspection
cv2.imwrite('bottom_right_corner.png', bottom_right)
print(f"✅ Saved bottom_right_corner.png")

# Also save a larger bottom-right section
larger_section = frame[height-200:height, width-400:width]
cv2.imwrite('bottom_right_larger.png', larger_section)
print(f"✅ Saved bottom_right_larger.png")

# Let's look for small horizontal bars (width > 50, height 5-15 pixels)
# Search for green/yellow/orange/red colors
hsv = cv2.cvtColor(bottom_right, cv2.COLOR_BGR2HSV)

# Combined mask for all relevant colors
colors_to_find = {
    'green': ([35, 50, 50], [85, 255, 255]),
    'yellow': ([15, 100, 100], [35, 255, 255]),
    'red': ([0, 100, 100], [10, 255, 255]),
    'red2': ([170, 100, 100], [180, 255, 255]),  # Red wraps around in HSV
}

combined_mask = np.zeros(bottom_right.shape[:2], dtype=np.uint8)
for color_name, (lower, upper) in colors_to_find.items():
    mask = cv2.inRange(hsv, np.array(lower), np.array(upper))
    combined_mask = cv2.bitwise_or(combined_mask, mask)

# Find contours
contours, _ = cv2.findContours(combined_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

print(f"\nSearching for small horizontal bars...")
potential_bars = []

for cnt in contours:
    x, y, w, h = cv2.boundingRect(cnt)
    aspect_ratio = w / h if h > 0 else 0
    
    # Look for horizontal bars: width > height, reasonable size
    if aspect_ratio > 2 and w > 30 and 4 < h < 20:
        potential_bars.append((x, y, w, h, aspect_ratio))
        print(f"  Found bar: x={x + (width-300)}, y={y + (height-150)}, size: {w}x{h} (aspect: {aspect_ratio:.1f})")

if potential_bars:
    # Draw rectangles on the bottom-right section
    marked = bottom_right.copy()
    for x, y, w, h, _ in potential_bars:
        cv2.rectangle(marked, (x, y), (x+w, y+h), (0, 255, 255), 1)
        # Show actual frame coordinates
        actual_x = x + (width - 300)
        actual_y = y + (height - 150)
        cv2.putText(marked, f"({actual_x},{actual_y})", (x, y-2), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.3, (0, 255, 255), 1)
    
    cv2.imwrite('found_throttle_brake_bars.png', marked)
    print(f"\n✅ Saved found_throttle_brake_bars.png with detected bars marked")
else:
    print("\n❌ No horizontal bars found matching criteria")
    print("The bars might be:")
    print("  - Smaller or larger than expected")
    print("  - In a different location")
    print("  - Only visible in certain camera views/replay mode")

