"""
Debug script to investigate TC false positives during braking.
Analyzes frame around 22 seconds where ABS is active but TC shouldn't be.
"""

import cv2
import numpy as np
import yaml
import matplotlib.pyplot as plt
from pathlib import Path

def load_config(config_path='config/roi_config.yaml'):
    """Load ROI configuration."""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def extract_frame_at_time(video_path, time_seconds):
    """Extract a specific frame at given time."""
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_num = int(time_seconds * fps)
    
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
    ret, frame = cap.read()
    cap.release()
    
    return frame, frame_num

def analyze_tc_detection(roi_image, name="ROI"):
    """Analyze what the TC detector sees."""
    if roi_image is None or roi_image.size == 0:
        print(f"{name}: Empty image")
        return
    
    # Convert to HSV
    hsv = cv2.cvtColor(roi_image, cv2.COLOR_BGR2HSV)
    
    # Yellow/Orange range used for TC detection
    lower_yellow = np.array([15, 100, 100])
    upper_yellow = np.array([35, 255, 255])
    mask_yellow = cv2.inRange(hsv, lower_yellow, upper_yellow)
    
    # Count pixels
    yellow_pixels = np.count_nonzero(mask_yellow)
    total_pixels = roi_image.shape[0] * roi_image.shape[1]
    
    print(f"\n{name} Analysis:")
    print(f"  Total pixels: {total_pixels}")
    print(f"  Yellow/orange pixels detected: {yellow_pixels}")
    print(f"  Percentage: {(yellow_pixels/total_pixels)*100:.2f}%")
    print(f"  TC Active (threshold=50): {yellow_pixels >= 50}")
    
    # Also check green (normal throttle)
    lower_green = np.array([35, 50, 50])
    upper_green = np.array([85, 255, 255])
    mask_green = cv2.inRange(hsv, lower_green, upper_green)
    green_pixels = np.count_nonzero(mask_green)
    print(f"  Green pixels detected: {green_pixels}")
    
    return mask_yellow, mask_green

def main():
    """Debug TC false positive at 22 seconds."""
    VIDEO_PATH = './input_video.mp4'
    roi_config = load_config()
    
    # Extract frame at 22 seconds (during braking with ABS)
    print("Extracting frame at 22.0 seconds...")
    frame, frame_num = extract_frame_at_time(VIDEO_PATH, 22.0)
    
    if frame is None:
        print("Error: Could not extract frame")
        return
    
    print(f"Frame number: {frame_num}")
    
    # Extract throttle ROI (current configuration)
    throttle_roi_config = roi_config['throttle']
    x, y, w, h = throttle_roi_config['x'], throttle_roi_config['y'], throttle_roi_config['width'], throttle_roi_config['height']
    throttle_roi = frame[y:y+h, x:x+w]
    
    # Extract brake ROI
    brake_roi_config = roi_config['brake']
    bx, by, bw, bh = brake_roi_config['x'], brake_roi_config['y'], brake_roi_config['width'], brake_roi_config['height']
    brake_roi = frame[by:by+bh, bx:bx+bw]
    
    # Analyze both
    throttle_mask_yellow, throttle_mask_green = analyze_tc_detection(throttle_roi, "Throttle ROI (Current)")
    brake_mask_orange, _ = analyze_tc_detection(brake_roi, "Brake ROI")
    
    # Try reduced throttle height to avoid glow from brake
    print("\n" + "="*60)
    print("TESTING: Reduced throttle height (12 instead of 14)")
    print("="*60)
    reduced_h = 12
    throttle_roi_reduced = frame[y:y+reduced_h, x:x+w]
    throttle_mask_yellow_reduced, throttle_mask_green_reduced = analyze_tc_detection(throttle_roi_reduced, "Throttle ROI (Reduced Height)")
    
    # Create debug visualization
    debug_dir = Path('debug/tc_false_positive')
    debug_dir.mkdir(parents=True, exist_ok=True)
    
    # Save full context
    context_area = frame[y-20:by+bh+20, x-20:x+w+20]
    cv2.imwrite(str(debug_dir / 'context_22s.jpg'), context_area)
    
    # Save ROIs
    cv2.imwrite(str(debug_dir / 'throttle_roi_current.jpg'), throttle_roi)
    cv2.imwrite(str(debug_dir / 'throttle_roi_reduced.jpg'), throttle_roi_reduced)
    cv2.imwrite(str(debug_dir / 'brake_roi.jpg'), brake_roi)
    
    # Create comparison visualization
    fig, axes = plt.subplots(3, 3, figsize=(15, 12))
    
    # Row 1: Current throttle ROI
    axes[0, 0].imshow(cv2.cvtColor(throttle_roi, cv2.COLOR_BGR2RGB))
    axes[0, 0].set_title(f'Throttle ROI (Current)\n{h}px height')
    axes[0, 0].axis('off')
    
    axes[0, 1].imshow(throttle_mask_green, cmap='gray')
    axes[0, 1].set_title(f'Green Mask\n{np.count_nonzero(throttle_mask_green)} pixels')
    axes[0, 1].axis('off')
    
    axes[0, 2].imshow(throttle_mask_yellow, cmap='gray')
    axes[0, 2].set_title(f'Yellow/Orange Mask\n{np.count_nonzero(throttle_mask_yellow)} pixels (TC={np.count_nonzero(throttle_mask_yellow)>=50})')
    axes[0, 2].axis('off')
    
    # Row 2: Reduced throttle ROI
    axes[1, 0].imshow(cv2.cvtColor(throttle_roi_reduced, cv2.COLOR_BGR2RGB))
    axes[1, 0].set_title(f'Throttle ROI (Reduced)\n{reduced_h}px height')
    axes[1, 0].axis('off')
    
    axes[1, 1].imshow(throttle_mask_green_reduced, cmap='gray')
    axes[1, 1].set_title(f'Green Mask\n{np.count_nonzero(throttle_mask_green_reduced)} pixels')
    axes[1, 1].axis('off')
    
    axes[1, 2].imshow(throttle_mask_yellow_reduced, cmap='gray')
    axes[1, 2].set_title(f'Yellow/Orange Mask\n{np.count_nonzero(throttle_mask_yellow_reduced)} pixels (TC={np.count_nonzero(throttle_mask_yellow_reduced)>=50})')
    axes[1, 2].axis('off')
    
    # Row 3: Brake ROI
    axes[2, 0].imshow(cv2.cvtColor(brake_roi, cv2.COLOR_BGR2RGB))
    axes[2, 0].set_title(f'Brake ROI\n{bh}px height')
    axes[2, 0].axis('off')
    
    axes[2, 1].imshow(brake_mask_orange, cmap='gray')
    axes[2, 1].set_title(f'Orange Mask (ABS)\n{np.count_nonzero(brake_mask_orange)} pixels')
    axes[2, 1].axis('off')
    
    # Context image
    axes[2, 2].imshow(cv2.cvtColor(context_area, cv2.COLOR_BGR2RGB))
    axes[2, 2].set_title('Full Context\n(Throttle + Brake area)')
    axes[2, 2].axis('off')
    
    # Add rectangle showing current vs reduced ROI
    from matplotlib.patches import Rectangle
    rect_current = Rectangle((20, 20), w, h, linewidth=2, edgecolor='red', facecolor='none', label='Current')
    rect_reduced = Rectangle((20, 20), w, reduced_h, linewidth=2, edgecolor='green', facecolor='none', label='Reduced')
    axes[2, 2].add_patch(rect_current)
    axes[2, 2].add_patch(rect_reduced)
    axes[2, 2].legend()
    
    plt.tight_layout()
    plt.savefig(debug_dir / 'tc_false_positive_analysis.png', dpi=150)
    print(f"\n✅ Debug visualization saved to {debug_dir}/tc_false_positive_analysis.png")
    
    # Recommendation
    print("\n" + "="*60)
    print("RECOMMENDATION:")
    print("="*60)
    if np.count_nonzero(throttle_mask_yellow) >= 50 and np.count_nonzero(throttle_mask_yellow_reduced) < 50:
        print("✅ Reducing throttle ROI height from 14 to 12 pixels fixes the false positive!")
        print("   This removes the bottom 2 rows that are catching glow from the brake bar.")
        print("\nSuggested fix in config/roi_config.yaml:")
        print("  throttle:")
        print("    height: 12  # Changed from 14 to avoid brake bar glow")
    else:
        print("❌ Height reduction alone doesn't fix it. Further investigation needed.")
        print("   Consider also adjusting the HSV threshold or pixel count threshold.")

if __name__ == '__main__':
    main()

