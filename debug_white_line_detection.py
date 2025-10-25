"""
Debug script to test and tune white racing line detection.
This will show exactly what the HSV color filter is detecting.
"""

import cv2
import numpy as np
import yaml
from pathlib import Path


def test_white_line_detection(video_path: str, roi_config: dict):
    """
    Test different HSV ranges to find the correct white line detection.
    """
    # Open video
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print("❌ Error: Could not open video file")
        return
    
    # Get a sample frame
    cap.set(cv2.CAP_PROP_POS_FRAMES, 1000)
    ret, frame = cap.read()
    cap.release()
    
    if not ret:
        print("❌ Error: Could not read frame")
        return
    
    # Extract track_map ROI
    roi_coords = roi_config['track_map']
    x, y, w, h = roi_coords['x'], roi_coords['y'], roi_coords['width'], roi_coords['height']
    map_roi = frame[y:y+h, x:x+w]
    
    # Create output directory
    output_dir = Path('debug/white_line_detection')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save original ROI
    cv2.imwrite(str(output_dir / '1_original_roi.png'), map_roi)
    print(f"✅ Saved original ROI: {output_dir / '1_original_roi.png'}")
    
    # Convert to HSV
    hsv = cv2.cvtColor(map_roi, cv2.COLOR_BGR2HSV)
    cv2.imwrite(str(output_dir / '2_hsv.png'), hsv)
    print(f"✅ Saved HSV version: {output_dir / '2_hsv.png'}")
    
    # Test different HSV ranges
    test_ranges = [
        {
            'name': 'original',
            'lower': np.array([0, 0, 200]),
            'upper': np.array([180, 30, 255]),
            'desc': 'Original: Low sat, high value (H:any, S:0-30, V:200-255)'
        },
        {
            'name': 'very_bright',
            'lower': np.array([0, 0, 240]),
            'upper': np.array([180, 20, 255]),
            'desc': 'Very bright: (H:any, S:0-20, V:240-255)'
        },
        {
            'name': 'pure_white',
            'lower': np.array([0, 0, 250]),
            'upper': np.array([180, 10, 255]),
            'desc': 'Pure white: (H:any, S:0-10, V:250-255)'
        },
        {
            'name': 'medium_bright',
            'lower': np.array([0, 0, 180]),
            'upper': np.array([180, 50, 255]),
            'desc': 'Medium bright: (H:any, S:0-50, V:180-255)'
        },
        {
            'name': 'light_gray',
            'lower': np.array([0, 0, 150]),
            'upper': np.array([180, 30, 255]),
            'desc': 'Light gray: (H:any, S:0-30, V:150-255)'
        }
    ]
    
    print(f"\n🔬 Testing {len(test_ranges)} different HSV ranges:")
    
    best_result = None
    best_count = 0
    
    for i, test_range in enumerate(test_ranges, start=3):
        # Apply mask
        mask = cv2.inRange(hsv, test_range['lower'], test_range['upper'])
        
        # Count white pixels
        white_pixels = np.sum(mask > 0)
        
        # Apply morphological operations
        kernel = np.ones((3, 3), np.uint8)
        mask_cleaned = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        mask_cleaned = cv2.morphologyEx(mask_cleaned, cv2.MORPH_OPEN, kernel)
        
        # Find contours
        contours, _ = cv2.findContours(mask_cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        
        # Save mask
        cv2.imwrite(str(output_dir / f'{i}a_mask_{test_range["name"]}.png'), mask)
        cv2.imwrite(str(output_dir / f'{i}b_mask_cleaned_{test_range["name"]}.png'), mask_cleaned)
        
        # Draw contours on original
        result = map_roi.copy()
        if contours:
            largest_contour = max(contours, key=cv2.contourArea)
            contour_area = cv2.contourArea(largest_contour)
            cv2.drawContours(result, [largest_contour], -1, (0, 255, 0), 2)
            
            # Draw all points in the contour
            for point in largest_contour:
                px, py = point[0]
                cv2.circle(result, (px, py), 1, (255, 0, 0), -1)
            
            cv2.imwrite(str(output_dir / f'{i}c_result_{test_range["name"]}.png'), result)
            
            print(f"   {test_range['name']:15s}: {white_pixels:5d} white pixels, largest contour: {contour_area:6.1f}px²")
            print(f"      {test_range['desc']}")
            
            # Track best result (contour that looks like a racing line)
            # Racing line should have area between 500-5000 pixels
            if 500 < contour_area < 5000 and contour_area > best_count:
                best_count = contour_area
                best_result = test_range['name']
        else:
            print(f"   {test_range['name']:15s}: {white_pixels:5d} white pixels, NO contours found")
            print(f"      {test_range['desc']}")
    
    print(f"\n📊 Results saved to: {output_dir}")
    print(f"\n🔍 Check these files:")
    print(f"   1. 1_original_roi.png - The minimap")
    print(f"   2. X_mask_*.png - What each HSV range detects (white = detected)")
    print(f"   3. X_result_*.png - Detected racing line drawn on minimap")
    
    if best_result:
        print(f"\n🎯 Best candidate: {best_result}")
        print(f"   Look for the result that draws a line following the white racing line!")
    else:
        print(f"\n❌ No good candidates found - may need custom HSV tuning")


def analyze_minimap_colors(video_path: str, roi_config: dict):
    """
    Analyze what colors are actually in the minimap.
    """
    print(f"\n" + "=" * 60)
    print("COLOR ANALYSIS")
    print("=" * 60)
    
    # Open video
    cap = cv2.VideoCapture(video_path)
    cap.set(cv2.CAP_PROP_POS_FRAMES, 1000)
    ret, frame = cap.read()
    cap.release()
    
    if not ret:
        return
    
    # Extract track_map ROI
    roi_coords = roi_config['track_map']
    x, y, w, h = roi_coords['x'], roi_coords['y'], roi_coords['width'], roi_coords['height']
    map_roi = frame[y:y+h, x:x+w]
    
    # Convert to HSV
    hsv = cv2.cvtColor(map_roi, cv2.COLOR_BGR2HSV)
    
    # Analyze HSV values
    h_values = hsv[:,:,0].flatten()
    s_values = hsv[:,:,1].flatten()
    v_values = hsv[:,:,2].flatten()
    
    print(f"📊 HSV Value Ranges in Minimap:")
    print(f"   Hue (H):        {h_values.min():3d} - {h_values.max():3d} (avg: {h_values.mean():.1f})")
    print(f"   Saturation (S): {s_values.min():3d} - {s_values.max():3d} (avg: {s_values.mean():.1f})")
    print(f"   Value (V):      {v_values.min():3d} - {v_values.max():3d} (avg: {v_values.mean():.1f})")
    
    # Find pixels with high value (bright)
    bright_pixels = hsv[v_values.reshape(hsv.shape[:2]) > 200]
    if len(bright_pixels) > 0:
        print(f"\n💡 Bright pixels (V > 200):")
        print(f"   Count: {len(bright_pixels)}")
        print(f"   H range: {bright_pixels[:,0].min():3d} - {bright_pixels[:,0].max():3d}")
        print(f"   S range: {bright_pixels[:,1].min():3d} - {bright_pixels[:,1].max():3d}")
        print(f"   V range: {bright_pixels[:,2].min():3d} - {bright_pixels[:,2].max():3d}")


def main():
    VIDEO_PATH = './panorama.mp4'
    CONFIG_PATH = 'config/roi_config.yaml'
    
    # Load configuration
    with open(CONFIG_PATH, 'r') as f:
        roi_config = yaml.safe_load(f)
    
    print("=" * 60)
    print("WHITE LINE DETECTION DEBUG")
    print("=" * 60)
    
    # Analyze colors first
    analyze_minimap_colors(VIDEO_PATH, roi_config)
    
    # Test different HSV ranges
    print(f"\n" + "=" * 60)
    print("TESTING HSV RANGES")
    print("=" * 60)
    test_white_line_detection(VIDEO_PATH, roi_config)
    
    print(f"\n" + "=" * 60)
    print("✅ ANALYSIS COMPLETE")
    print("=" * 60)
    print(f"\n📁 Check debug/white_line_detection/ for results")
    print(f"\n🎯 ACTION ITEMS:")
    print(f"   1. Look at the X_result_*.png images")
    print(f"   2. Find which one correctly traces the white racing line")
    print(f"   3. Update PositionTracker to use that HSV range")


if __name__ == '__main__':
    main()




