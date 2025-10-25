"""
Debug script to test better contour selection.
The issue is that we're detecting the minimap border instead of the racing line.
"""

import cv2
import numpy as np
import yaml
from pathlib import Path


def test_contour_selection(video_path: str, roi_config: dict):
    """
    Test different contour selection strategies to find the racing line.
    """
    # Open video
    cap = cv2.VideoCapture(video_path)
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
    output_dir = Path('debug/contour_selection')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Convert to HSV and create mask
    hsv = cv2.cvtColor(map_roi, cv2.COLOR_BGR2HSV)
    
    # Use medium_bright range (captures both border and racing line)
    white_lower = np.array([0, 0, 180])
    white_upper = np.array([180, 50, 255])
    mask = cv2.inRange(hsv, white_lower, white_upper)
    
    # Clean up mask
    kernel = np.ones((3, 3), np.uint8)
    mask_cleaned = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    mask_cleaned = cv2.morphologyEx(mask_cleaned, cv2.MORPH_OPEN, kernel)
    
    # Save mask
    cv2.imwrite(str(output_dir / '1_mask.png'), mask_cleaned)
    print(f"✅ Saved mask: {output_dir / '1_mask.png'}")
    
    # Find ALL contours
    contours, _ = cv2.findContours(mask_cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    
    print(f"\n📊 Found {len(contours)} contours")
    
    # Analyze each contour
    contour_info = []
    for i, contour in enumerate(contours):
        area = cv2.contourArea(contour)
        perimeter = cv2.arcLength(contour, True)
        
        # Calculate bounding rectangle
        x_rect, y_rect, w_rect, h_rect = cv2.boundingRect(contour)
        
        # Calculate aspect ratio
        aspect_ratio = float(w_rect) / h_rect if h_rect > 0 else 0
        
        # Calculate extent (contour area / bounding rectangle area)
        rect_area = w_rect * h_rect
        extent = float(area) / rect_area if rect_area > 0 else 0
        
        # Calculate circularity (how round/curved the contour is)
        # circularity = 4 * pi * area / perimeter^2
        # Circle = 1.0, straight line = 0.0
        circularity = 4 * np.pi * area / (perimeter * perimeter) if perimeter > 0 else 0
        
        contour_info.append({
            'index': i,
            'contour': contour,
            'area': area,
            'perimeter': perimeter,
            'aspect_ratio': aspect_ratio,
            'extent': extent,
            'circularity': circularity,
            'width': w_rect,
            'height': h_rect
        })
        
        if area > 50:  # Only print significant contours
            print(f"\n   Contour {i}:")
            print(f"      Area: {area:.1f}px²")
            print(f"      Perimeter: {perimeter:.1f}px")
            print(f"      Size: {w_rect}x{h_rect}")
            print(f"      Aspect ratio: {aspect_ratio:.2f}")
            print(f"      Extent: {extent:.2f}")
            print(f"      Circularity: {circularity:.2f}")
    
    # Draw all significant contours with different colors
    result_all = map_roi.copy()
    colors = [(0, 255, 0), (255, 0, 0), (0, 0, 255), (255, 255, 0), (255, 0, 255)]
    
    for info in contour_info:
        if info['area'] > 50:
            color = colors[info['index'] % len(colors)]
            cv2.drawContours(result_all, [info['contour']], -1, color, 2)
            
            # Add label
            M = cv2.moments(info['contour'])
            if M['m00'] != 0:
                cx = int(M['m10'] / M['m00'])
                cy = int(M['m01'] / M['m00'])
                cv2.putText(result_all, f"{info['index']}", (cx, cy),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
    
    cv2.imwrite(str(output_dir / '2_all_contours.png'), result_all)
    print(f"\n✅ Saved all contours: {output_dir / '2_all_contours.png'}")
    
    # Strategy 1: Select by circularity (racing line should be more curved than rectangle)
    # Racing lines typically have low circularity (long and winding)
    # Rectangles have moderate circularity
    racing_line_candidates = [info for info in contour_info if 0.05 < info['circularity'] < 0.3 and info['area'] > 100]
    
    if racing_line_candidates:
        print(f"\n🎯 Racing line candidates (by circularity):")
        for info in racing_line_candidates:
            print(f"   Contour {info['index']}: circularity={info['circularity']:.2f}, area={info['area']:.1f}")
        
        # Draw racing line candidates
        result_candidates = map_roi.copy()
        for info in racing_line_candidates:
            # Draw path points
            for point in info['contour']:
                px, py = point[0]
                cv2.circle(result_candidates, (px, py), 1, (0, 255, 0), -1)
        
        cv2.imwrite(str(output_dir / '3_racing_line_candidates.png'), result_candidates)
        print(f"   ✅ Saved: {output_dir / '3_racing_line_candidates.png'}")
    
    # Strategy 2: Exclude rectangular contours (high aspect ratio close to 1.0 and high extent)
    non_rectangular = [info for info in contour_info if not (0.7 < info['aspect_ratio'] < 1.3 and info['extent'] > 0.8) and info['area'] > 100]
    
    if non_rectangular:
        print(f"\n🎯 Non-rectangular contours:")
        for info in non_rectangular:
            print(f"   Contour {info['index']}: area={info['area']:.1f}, aspect={info['aspect_ratio']:.2f}, extent={info['extent']:.2f}")
        
        result_non_rect = map_roi.copy()
        for info in non_rectangular:
            for point in info['contour']:
                px, py = point[0]
                cv2.circle(result_non_rect, (px, py), 1, (0, 255, 0), -1)
        
        cv2.imwrite(str(output_dir / '4_non_rectangular.png'), result_non_rect)
        print(f"   ✅ Saved: {output_dir / '4_non_rectangular.png'}")
    
    # Strategy 3: Select by area (racing line should be medium-sized, not tiny or huge)
    medium_sized = [info for info in contour_info if 200 < info['area'] < 3000]
    
    if medium_sized:
        print(f"\n🎯 Medium-sized contours (200-3000px²):")
        for info in medium_sized:
            print(f"   Contour {info['index']}: area={info['area']:.1f}")
        
        result_medium = map_roi.copy()
        for info in medium_sized:
            for point in info['contour']:
                px, py = point[0]
                cv2.circle(result_medium, (px, py), 1, (0, 255, 0), -1)
        
        cv2.imwrite(str(output_dir / '5_medium_sized.png'), result_medium)
        print(f"   ✅ Saved: {output_dir / '5_medium_sized.png'}")
    
    # Combined strategy: non-rectangular AND medium-sized
    best_candidates = [info for info in contour_info 
                      if not (0.7 < info['aspect_ratio'] < 1.3 and info['extent'] > 0.8)
                      and 200 < info['area'] < 3000]
    
    if best_candidates:
        print(f"\n🏆 BEST CANDIDATES (non-rectangular + medium-sized):")
        for info in best_candidates:
            print(f"   Contour {info['index']}: area={info['area']:.1f}, aspect={info['aspect_ratio']:.2f}")
        
        # Select largest from best candidates
        best = max(best_candidates, key=lambda x: x['area'])
        print(f"\n✅ SELECTED: Contour {best['index']} (area={best['area']:.1f}px²)")
        
        result_best = map_roi.copy()
        for point in best['contour']:
            px, py = point[0]
            cv2.circle(result_best, (px, py), 1, (0, 255, 0), -1)
        
        cv2.imwrite(str(output_dir / '6_BEST_RESULT.png'), result_best)
        print(f"   ✅ Saved BEST result: {output_dir / '6_BEST_RESULT.png'}")
        
        return best
    else:
        print(f"\n❌ No good candidates found!")
        return None


def main():
    VIDEO_PATH = './panorama.mp4'
    CONFIG_PATH = 'config/roi_config.yaml'
    
    # Load configuration
    with open(CONFIG_PATH, 'r') as f:
        roi_config = yaml.safe_load(f)
    
    print("=" * 60)
    print("CONTOUR SELECTION DEBUG")
    print("=" * 60)
    
    best_contour = test_contour_selection(VIDEO_PATH, roi_config)
    
    print("\n" + "=" * 60)
    print("✅ ANALYSIS COMPLETE")
    print("=" * 60)
    print(f"\n📁 Check debug/contour_selection/ for results")
    print(f"\n🎯 Look at 6_BEST_RESULT.png - does it show the racing line?")


if __name__ == '__main__':
    main()




