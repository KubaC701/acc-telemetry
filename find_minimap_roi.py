"""
Interactive script to find the correct minimap ROI coordinates.
This will help you identify where the minimap actually is in your video.
"""

import cv2
import yaml
from pathlib import Path


def find_minimap_interactive(video_path: str):
    """
    Interactive tool to find minimap ROI.
    Shows the video frame and lets you click to define the minimap region.
    """
    # Load current config
    with open('config/roi_config.yaml', 'r') as f:
        roi_config = yaml.safe_load(f)
    
    # Open video
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print("❌ Error: Could not open video file")
        return
    
    # Get a sample frame
    cap.set(cv2.CAP_PROP_POS_FRAMES, 1000)
    ret, frame = cap.read()
    
    if not ret:
        print("❌ Error: Could not read frame")
        return
    
    print(f"📊 Frame: {frame.shape[1]}x{frame.shape[0]} (width x height)")
    print(f"🎯 Current track_map ROI: x={roi_config['track_map']['x']}, y={roi_config['track_map']['y']}, w={roi_config['track_map']['width']}, h={roi_config['track_map']['height']}")
    
    # Draw current ROI rectangle
    current_roi = roi_config['track_map']
    x, y, w, h = current_roi['x'], current_roi['y'], current_roi['width'], current_roi['height']
    
    frame_with_roi = frame.copy()
    cv2.rectangle(frame_with_roi, (x, y), (x+w, y+h), (0, 255, 0), 2)
    cv2.putText(frame_with_roi, 'CURRENT track_map ROI', (x, y-10), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    
    # Save current ROI for inspection
    output_dir = Path('debug/minimap_finding')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    cv2.imwrite(str(output_dir / 'current_roi_frame.png'), frame_with_roi)
    cv2.imwrite(str(output_dir / 'current_roi_content.png'), frame[y:y+h, x:x+w])
    
    print(f"\n📁 Saved debug images to: {output_dir}")
    print(f"   - current_roi_frame.png: Full frame with current ROI rectangle")
    print(f"   - current_roi_content.png: What the current ROI is capturing")
    
    print(f"\n🔍 MANUAL INSPECTION REQUIRED:")
    print(f"   1. Open current_roi_frame.png")
    print(f"   2. Check if the green rectangle is around the minimap")
    print(f"   3. Check if current_roi_content.png shows the minimap with white racing line")
    print(f"   4. If NOT, you need to find the correct coordinates")
    
    print(f"\n💡 TO FIND CORRECT COORDINATES:")
    print(f"   1. Open current_roi_frame.png in an image viewer")
    print(f"   2. Find the minimap (circular, shows white racing line)")
    print(f"   3. Note the minimap's top-left corner (x, y)")
    print(f"   4. Note the minimap's width and height")
    print(f"   5. Update config/roi_config.yaml with correct values")
    
    # Show some common minimap locations to check
    print(f"\n🎯 COMMON MINIMAP LOCATIONS TO CHECK:")
    print(f"   - Top-left corner: x=0-50, y=0-200")
    print(f"   - Bottom-left corner: x=0-50, y=400-720") 
    print(f"   - Top-right corner: x=1000-1280, y=0-200")
    print(f"   - Bottom-right corner: x=1000-1280, y=400-720")
    
    cap.release()


def create_roi_test_script():
    """
    Create a script to test different ROI coordinates.
    """
    script_content = '''"""
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
    print(f"\\n📁 Test ROIs saved to: {output_dir}")
    print(f"\\n🔍 Check each ROI image to see which one shows the minimap!")

if __name__ == '__main__':
    test_roi_coordinates()
'''
    
    with open('test_roi_coordinates.py', 'w') as f:
        f.write(script_content)
    
    print(f"✅ Created test_roi_coordinates.py - run this to test different coordinates")


if __name__ == '__main__':
    video_path = './panorama.mp4'
    find_minimap_interactive(video_path)
    create_roi_test_script()
