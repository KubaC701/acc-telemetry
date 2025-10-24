"""
Debug script to visualize what ROI regions are actually capturing.
This will help identify if the track_map ROI is correct.
"""

import cv2
import yaml
from pathlib import Path


def visualize_rois(video_path: str, config_path: str = 'config/roi_config.yaml'):
    """
    Extract and save ROI regions to see what we're actually capturing.
    """
    # Load config
    with open(config_path, 'r') as f:
        roi_config = yaml.safe_load(f)
    
    # Open video
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print("❌ Error: Could not open video file")
        return
    
    # Get a sample frame
    cap.set(cv2.CAP_PROP_POS_FRAMES, 1000)  # Sample frame 1000
    ret, frame = cap.read()
    
    if not ret:
        print("❌ Error: Could not read frame")
        return
    
    print(f"📊 Frame info: {frame.shape[1]}x{frame.shape[0]} (width x height)")
    
    # Create output directory
    output_dir = Path('debug/roi_visualization')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save full frame
    cv2.imwrite(str(output_dir / 'full_frame.png'), frame)
    print(f"✅ Saved full frame: {output_dir / 'full_frame.png'}")
    
    # Extract and save each ROI
    for roi_name, roi_coords in roi_config.items():
        x = roi_coords['x']
        y = roi_coords['y'] 
        w = roi_coords['width']
        h = roi_coords['height']
        
        # Extract ROI
        roi = frame[y:y+h, x:x+w]
        
        # Save ROI
        filename = f'{roi_name}_roi.png'
        cv2.imwrite(str(output_dir / filename), roi)
        
        print(f"✅ {roi_name}: {x},{y} {w}x{h} -> {filename}")
        
        # For track_map, also create a version with the ROI rectangle drawn on full frame
        if roi_name == 'track_map':
            # Draw rectangle on full frame
            frame_with_roi = frame.copy()
            cv2.rectangle(frame_with_roi, (x, y), (x+w, y+h), (0, 255, 0), 2)
            cv2.putText(frame_with_roi, 'TRACK_MAP ROI', (x, y-10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.imwrite(str(output_dir / 'full_frame_with_track_map_roi.png'), frame_with_roi)
            print(f"✅ Track map ROI rectangle: full_frame_with_track_map_roi.png")
    
    cap.release()
    
    print(f"\n📁 Debug images saved to: {output_dir}")
    print(f"\n🔍 Check these files:")
    print(f"   - full_frame.png: The full video frame")
    print(f"   - full_frame_with_track_map_roi.png: Frame with green rectangle showing track_map ROI")
    print(f"   - track_map_roi.png: What the track_map ROI is actually capturing")
    print(f"\n❓ Questions to verify:")
    print(f"   1. Is the green rectangle around the minimap?")
    print(f"   2. Does track_map_roi.png show the minimap with white racing line?")
    print(f"   3. Is there a red dot visible in the minimap?")


if __name__ == '__main__':
    video_path = './panorama.mp4'
    visualize_rois(video_path)
