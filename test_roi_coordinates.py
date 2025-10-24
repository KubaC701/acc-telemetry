"""
Test different ROI coordinates to find the correct minimap location.
Edit the coordinates below and run this script to see what each ROI captures.
"""

import cv2
import yaml
from pathlib import Path

def test_roi_coordinates():
    # Test coordinates - EDIT THESE to try different locations
    test_coords = [
        {"name": "current", "x": 3, "y": 215, "w": 269, "h": 183},
        {"name": "top_left", "x": 10, "y": 10, "w": 200, "h": 150},
        {"name": "bottom_left", "x": 10, "y": 500, "w": 200, "h": 150},
        {"name": "top_right", "x": 1000, "y": 10, "w": 200, "h": 150},
        {"name": "bottom_right", "x": 1000, "y": 500, "w": 200, "h": 150},
    ]
    
    # Open video
    cap = cv2.VideoCapture('./panorama.mp4')
    cap.set(cv2.CAP_PROP_POS_FRAMES, 1000)
    ret, frame = cap.read()
    
    if not ret:
        print("❌ Error: Could not read frame")
        return
    
    output_dir = Path('debug/roi_testing')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Test each coordinate set
    for coords in test_coords:
        x, y, w, h = coords["x"], coords["y"], coords["width"], coords["height"]
        
        # Extract ROI
        roi = frame[y:y+h, x:x+w]
        
        # Save ROI
        filename = f'{coords["name"]}_roi.png'
        cv2.imwrite(str(output_dir / filename), roi)
        
        print(f"✅ {coords['name']}: {x},{y} {w}x{h} -> {filename}")
    
    cap.release()
    print(f"\n📁 Test ROIs saved to: {output_dir}")
    print(f"\n🔍 Check each ROI image to see which one shows the minimap!")

if __name__ == '__main__':
    test_roi_coordinates()
