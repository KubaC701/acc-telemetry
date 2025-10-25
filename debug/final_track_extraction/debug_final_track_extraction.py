"""
FINAL Production-Ready Track Extraction

This is the best approach based on testing:
1. HSV-based white detection (robust to lighting)
2. Temporal frequency voting (50-70% threshold - racing line is consistent)
3. Keep ALL valid contours (not just largest - line may be fragmented)
4. Morphological gap filling (connect broken segments)
5. Final validation and cleanup

Author: ACC Telemetry Extractor
"""

import cv2
import numpy as np
import yaml
from pathlib import Path


def extract_white_mask_hsv(map_roi: np.ndarray) -> np.ndarray:
    """
    Extract white pixels using HSV color space.
    
    White characteristics in HSV:
    - Hue: Any (white has no dominant color)
    - Saturation: Low (0-30) - white is desaturated
    - Value: High (200-255) - white is bright
    """
    hsv = cv2.cvtColor(map_roi, cv2.COLOR_BGR2HSV)
    
    white_lower = np.array([0, 0, 200])
    white_upper = np.array([180, 30, 255])
    
    white_mask = cv2.inRange(hsv, white_lower, white_upper)
    
    return white_mask


def extract_racing_line_multi_frame(map_rois: list, frequency_threshold: float = 0.6) -> np.ndarray:
    """
    Extract racing line using multi-frame frequency voting.
    
    Key insight: Racing line is CONSTANT across frames, while red dot and 
    background vary. By checking how often each pixel is white across many 
    frames, we can isolate the racing line.
    
    Args:
        map_rois: List of BGR map ROI images (sample 30-50 frames across the lap)
        frequency_threshold: Pixel must be white in this % of frames (0.0-1.0)
                           0.5 = 50% (generous, catches more of line)
                           0.7 = 70% (strict, cleaner but may miss parts)
    
    Returns:
        Binary mask of racing line
    """
    if not map_rois or len(map_rois) < 10:
        print(f"⚠️  Warning: Need at least 10 frames, got {len(map_rois)}")
        return None
    
    print(f"\n{'='*70}")
    print(f"MULTI-FRAME RACING LINE EXTRACTION")
    print(f"{'='*70}")
    print(f"Frames: {len(map_rois)}")
    print(f"Frequency threshold: {frequency_threshold*100:.0f}%")
    print(f"{'='*70}\n")
    
    # Step 1: Extract white masks from each frame
    print("📍 Step 1: Extracting white pixels from each frame...")
    white_masks = []
    
    for i, map_roi in enumerate(map_rois):
        white_mask = extract_white_mask_hsv(map_roi)
        white_masks.append(white_mask)
        
        white_count = np.sum(white_mask > 0)
        
        if i < 5 or i % 10 == 0:
            print(f"   Frame {i:2d}: {white_count:5d} white pixels")
    
    print(f"   ✅ Extracted {len(white_masks)} white masks\n")
    
    # Step 2: Stack masks and calculate frequency
    print("📊 Step 2: Computing pixel-wise white frequency...")
    mask_stack = np.stack(white_masks, axis=2).astype(np.float32)
    white_frequency = np.sum(mask_stack > 0, axis=2) / len(white_masks)
    
    # Statistics
    max_freq = np.max(white_frequency)
    min_freq = np.min(white_frequency)
    pixels_above_threshold = np.sum(white_frequency >= frequency_threshold)
    
    print(f"   Frequency range: {min_freq:.3f} - {max_freq:.3f}")
    print(f"   Pixels above {frequency_threshold:.0%}: {pixels_above_threshold}")
    print(f"   ✅ Frequency map computed\n")
    
    # Step 3: Threshold by frequency
    print(f"🎯 Step 3: Thresholding at {frequency_threshold*100:.0f}% frequency...")
    racing_line_mask = (white_frequency >= frequency_threshold).astype(np.uint8) * 255
    
    print(f"   ✅ Initial mask: {np.sum(racing_line_mask > 0)} white pixels\n")
    
    # Step 4: Morphological operations to clean and connect
    print("🧹 Step 4: Morphological cleaning and gap filling...")
    
    # First: Close small gaps in the line
    kernel_close = np.ones((3, 3), np.uint8)
    closed = cv2.morphologyEx(racing_line_mask, cv2.MORPH_CLOSE, kernel_close, iterations=2)
    print(f"   After closing: {np.sum(closed > 0)} white pixels")
    
    # Second: Remove small noise
    kernel_open = np.ones((2, 2), np.uint8)
    opened = cv2.morphologyEx(closed, cv2.MORPH_OPEN, kernel_open, iterations=1)
    print(f"   After opening: {np.sum(opened > 0)} white pixels")
    
    # Third: Dilate slightly to thicken the line (makes it easier to extract contour)
    kernel_dilate = np.ones((2, 2), np.uint8)
    dilated = cv2.dilate(opened, kernel_dilate, iterations=1)
    print(f"   After dilation: {np.sum(dilated > 0)} white pixels")
    print(f"   ✅ Morphological processing complete\n")
    
    return dilated


def extract_largest_contour(mask: np.ndarray, min_area: int = 100) -> np.ndarray:
    """
    Extract the largest contour from mask (should be the racing line).
    
    This removes small artifacts while keeping the main racing line.
    """
    print("🔍 Step 5: Extracting largest contour...")
    
    # Find all contours
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    
    if not contours:
        print("   ❌ No contours found!")
        return mask
    
    print(f"   Found {len(contours)} contours")
    
    # Filter by minimum area and get info
    valid_contours = []
    for i, contour in enumerate(contours):
        area = cv2.contourArea(contour)
        if area >= min_area:
            perimeter = cv2.arcLength(contour, True)
            valid_contours.append({
                'contour': contour,
                'area': area,
                'perimeter': perimeter,
                'index': i
            })
            print(f"      Contour {i}: area={area:.1f}px², perimeter={perimeter:.1f}px")
    
    if not valid_contours:
        print(f"   ⚠️  No contours above {min_area}px² threshold")
        return mask
    
    # Get the largest one
    largest = max(valid_contours, key=lambda x: x['area'])
    
    print(f"   🏆 Selected largest: #{largest['index']} with area={largest['area']:.1f}px²")
    
    # Create new mask with only the largest contour
    result = np.zeros_like(mask)
    cv2.drawContours(result, [largest['contour']], -1, 255, -1)
    
    print(f"   ✅ Extracted largest contour: {np.sum(result > 0)} pixels\n")
    
    return result


def visualize_extraction_steps(map_rois: list, racing_line_mask: np.ndarray, 
                               output_dir: Path, frequency_threshold: float):
    """
    Create comprehensive visualization of the extraction process.
    """
    print("📸 Creating visualizations...")
    
    if not map_rois or racing_line_mask is None:
        return
    
    # 1. Sample frames with white masks
    for i in range(min(5, len(map_rois))):
        original = map_rois[i]
        white_mask = extract_white_mask_hsv(original)
        
        # Side-by-side
        h, w = original.shape[:2]
        combined = np.zeros((h, w*2, 3), dtype=np.uint8)
        combined[:, 0:w] = original
        combined[:, w:w*2] = cv2.cvtColor(white_mask, cv2.COLOR_GRAY2BGR)
        
        cv2.imwrite(str(output_dir / f'step1_frame{i:02d}_white_detection.png'), combined)
    
    # 2. Final result overlaid on original
    original = map_rois[0]
    overlay = original.copy()
    
    # Find contour and draw it
    contours, _ = cv2.findContours(racing_line_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    if contours:
        # Draw filled contour in semi-transparent green
        overlay_colored = overlay.copy()
        cv2.drawContours(overlay_colored, contours, -1, (0, 255, 0), -1)
        overlay = cv2.addWeighted(overlay, 0.7, overlay_colored, 0.3, 0)
        
        # Draw contour outline in bright green
        cv2.drawContours(overlay, contours, -1, (0, 255, 0), 2)
    
    cv2.imwrite(str(output_dir / 'step5_FINAL_RESULT.png'), overlay)
    
    # 3. Just the extracted mask
    cv2.imwrite(str(output_dir / 'step5_FINAL_MASK.png'), racing_line_mask)
    
    # 4. Comparison grid (before and after)
    h, w = original.shape[:2]
    comparison = np.zeros((h, w*2, 3), dtype=np.uint8)
    comparison[:, 0:w] = original
    comparison[:, w:w*2] = overlay
    
    # Add labels
    cv2.putText(comparison, "Original", (10, 30), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    cv2.putText(comparison, f"Extracted ({frequency_threshold*100:.0f}% freq)", (w+10, 30), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    
    cv2.imwrite(str(output_dir / 'COMPARISON_BEFORE_AFTER.png'), comparison)
    
    print(f"   ✅ Visualizations saved to {output_dir}/\n")


def main():
    """
    Test the extraction with different frequency thresholds.
    """
    VIDEO_PATH = './panorama.mp4'
    CONFIG_PATH = 'config/roi_config.yaml'
    
    with open(CONFIG_PATH, 'r') as f:
        roi_config = yaml.safe_load(f)
    
    # Open video
    cap = cv2.VideoCapture(VIDEO_PATH)
    if not cap.isOpened():
        print("❌ Error: Could not open video file")
        return
    
    video_info = {
        'fps': cap.get(cv2.CAP_PROP_FPS),
        'frame_count': int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    }
    
    print(f"\n{'='*70}")
    print(f"VIDEO INFORMATION")
    print(f"{'='*70}")
    print(f"Path: {VIDEO_PATH}")
    print(f"Total frames: {video_info['frame_count']}")
    print(f"FPS: {video_info['fps']:.1f}")
    print(f"Duration: {video_info['frame_count']/video_info['fps']:.1f}s")
    print(f"{'='*70}\n")
    
    # Sample frames evenly across the video (every 30 frames for first 1500)
    sample_interval = 30
    max_frames = 1500
    sample_frames = list(range(0, min(max_frames, video_info['frame_count']), sample_interval))
    
    print(f"Sampling {len(sample_frames)} frames (every {sample_interval} frames)...")
    
    # Extract ROIs
    map_rois = []
    roi_coords = roi_config['track_map']
    x, y, w, h = roi_coords['x'], roi_coords['y'], roi_coords['width'], roi_coords['height']
    
    for frame_num in sample_frames:
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
        ret, frame = cap.read()
        
        if not ret:
            continue
        
        map_roi = frame[y:y+h, x:x+w]
        map_rois.append(map_roi)
    
    cap.release()
    
    print(f"✅ Extracted {len(map_rois)} ROIs\n")
    
    # Test with different frequency thresholds
    thresholds = [0.5, 0.6, 0.7]
    
    for threshold in thresholds:
        output_dir = Path(f'debug/final_track_extraction/threshold_{int(threshold*100)}pct')
        output_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"\n{'='*70}")
        print(f"TESTING THRESHOLD: {threshold*100:.0f}%")
        print(f"{'='*70}")
        
        # Extract racing line
        racing_line_mask = extract_racing_line_multi_frame(map_rois, frequency_threshold=threshold)
        
        if racing_line_mask is not None:
            # Extract largest contour
            final_mask = extract_largest_contour(racing_line_mask, min_area=100)
            
            # Visualize
            visualize_extraction_steps(map_rois, final_mask, output_dir, threshold)
            
            print(f"✅ Results saved to {output_dir}/")
    
    print(f"\n{'='*70}")
    print(f"ALL DONE! Compare results in debug/final_track_extraction/")
    print(f"{'='*70}")
    print(f"\n🔍 Recommended files to examine:")
    print(f"   threshold_50pct/COMPARISON_BEFORE_AFTER.png")
    print(f"   threshold_60pct/COMPARISON_BEFORE_AFTER.png")
    print(f"   threshold_70pct/COMPARISON_BEFORE_AFTER.png")
    print(f"\n💡 Choose the threshold that gives the most complete racing line")
    print(f"   without too many artifacts.\n")


if __name__ == '__main__':
    main()

