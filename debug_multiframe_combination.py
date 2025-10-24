"""
Debug script to visualize multi-frame combination.
Let's see what happens when we combine masks from multiple frames.
"""

import cv2
import numpy as np
import yaml
from pathlib import Path


def debug_multiframe_extraction(video_path: str, roi_config: dict):
    """
    Visualize each step of multi-frame track path extraction.
    """
    # Open video
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print("❌ Error: Could not open video file")
        return
    
    video_info = {
        'fps': cap.get(cv2.CAP_PROP_FPS),
        'frame_count': int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    }
    
    # Sample frames
    sample_frames = [0, 100, 200, 300, 400, 500]
    
    # Create output directory
    output_dir = Path('debug/multiframe_extraction')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("=" * 60)
    print("MULTI-FRAME EXTRACTION DEBUG")
    print("=" * 60)
    
    # Extract ROI from each frame
    map_rois = []
    individual_masks = []
    
    for i, frame_num in enumerate(sample_frames):
        if frame_num >= video_info['frame_count']:
            break
        
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
        ret, frame = cap.read()
        
        if not ret:
            continue
        
        # Extract track_map ROI
        roi_coords = roi_config['track_map']
        x, y, w, h = roi_coords['x'], roi_coords['y'], roi_coords['width'], roi_coords['height']
        map_roi = frame[y:y+h, x:x+w]
        
        map_rois.append(map_roi)
        
        # Convert to grayscale and threshold
        gray = cv2.cvtColor(map_roi, cv2.COLOR_BGR2GRAY)
        _, binary_mask = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
        
        individual_masks.append(binary_mask)
        
        # Save individual results
        cv2.imwrite(str(output_dir / f'frame{i}_original.png'), map_roi)
        cv2.imwrite(str(output_dir / f'frame{i}_mask.png'), binary_mask)
        
        # Count white pixels
        white_pixels = np.sum(binary_mask > 0)
        print(f"Frame {frame_num:3d} (index {i}): {white_pixels:5d} white pixels")
    
    cap.release()
    
    if not individual_masks:
        print("❌ No masks extracted")
        return
    
    print(f"\n📊 Combining {len(individual_masks)} masks...")
    
    # Method 1: Simple OR (current approach)
    combined_or = individual_masks[0].copy()
    for mask in individual_masks[1:]:
        combined_or = cv2.bitwise_or(combined_or, mask)
    
    cv2.imwrite(str(output_dir / 'combined_OR.png'), combined_or)
    print(f"   OR combination: {np.sum(combined_or > 0)} white pixels")
    
    # Method 2: Voting (pixel must appear in at least N frames)
    mask_stack = np.stack(individual_masks, axis=2)
    vote_count = np.sum(mask_stack > 0, axis=2)
    
    for threshold in [1, 2, 3]:
        voted_mask = (vote_count >= threshold).astype(np.uint8) * 255
        cv2.imwrite(str(output_dir / f'combined_VOTE{threshold}.png'), voted_mask)
        print(f"   VOTE{threshold} (appear in {threshold}+ frames): {np.sum(voted_mask > 0)} white pixels")
    
    # Clean up each mask and visualize
    print(f"\n🧹 Analyzing contours in each combination method...")
    
    for method_name, mask in [('OR', combined_or), ('VOTE2', (vote_count >= 2).astype(np.uint8) * 255)]:
        # Clean mask
        kernel = np.ones((3, 3), np.uint8)
        cleaned = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_OPEN, kernel)
        
        cv2.imwrite(str(output_dir / f'{method_name}_cleaned.png'), cleaned)
        
        # Find contours
        contours, _ = cv2.findContours(cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        
        print(f"\n   {method_name} method:")
        print(f"      Found {len(contours)} contours")
        
        # Visualize all contours
        if map_rois:
            vis = map_rois[0].copy()
            colors = [(0, 255, 0), (255, 0, 0), (0, 0, 255), (255, 255, 0), (255, 0, 255)]
            
            contour_info = []
            for i, contour in enumerate(contours):
                area = cv2.contourArea(contour)
                if area < 50:  # Skip tiny contours
                    continue
                
                perimeter = cv2.arcLength(contour, True)
                x_rect, y_rect, w_rect, h_rect = cv2.boundingRect(contour)
                
                contour_info.append({
                    'index': i,
                    'area': area,
                    'perimeter': perimeter,
                    'x': x_rect,
                    'y': y_rect,
                    'w': w_rect,
                    'h': h_rect
                })
                
                # Draw contour
                color = colors[i % len(colors)]
                cv2.drawContours(vis, [contour], -1, color, 2)
                
                # Add label
                cv2.putText(vis, f"{i}:{int(area)}", (x_rect, y_rect-5),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
                
                print(f"      Contour {i}: area={area:6.1f}px², pos=({x_rect},{y_rect}), size={w_rect}x{h_rect}")
            
            cv2.imwrite(str(output_dir / f'{method_name}_contours.png'), vis)
            
            # Find largest contour
            if contour_info:
                largest = max(contour_info, key=lambda x: x['area'])
                print(f"      ✅ LARGEST: Contour {largest['index']} (area={largest['area']:.1f}px²)")
                
                # Draw only the largest
                vis_largest = map_rois[0].copy()
                largest_contour = contours[largest['index']]
                
                # Draw as green dots
                for point in largest_contour:
                    px, py = point[0]
                    cv2.circle(vis_largest, (px, py), 1, (0, 255, 0), -1)
                
                cv2.imwrite(str(output_dir / f'{method_name}_LARGEST.png'), vis_largest)
    
    print(f"\n✅ Debug complete! Check {output_dir}/")
    print(f"\n🔍 Files to examine:")
    print(f"   - frameX_mask.png: Individual frame masks")
    print(f"   - combined_OR.png: Current OR combination")
    print(f"   - combined_VOTEX.png: Vote-based combinations")
    print(f"   - X_LARGEST.png: The contour we're actually selecting")


def main():
    VIDEO_PATH = './panorama.mp4'
    CONFIG_PATH = 'config/roi_config.yaml'
    
    with open(CONFIG_PATH, 'r') as f:
        roi_config = yaml.safe_load(f)
    
    debug_multiframe_extraction(VIDEO_PATH, roi_config)


if __name__ == '__main__':
    main()

