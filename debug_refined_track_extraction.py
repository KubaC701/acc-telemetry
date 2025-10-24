"""
Refined Track Extraction - Focused on White Line Detection

This version specifically targets the WHITE racing line using HSV color space
and applies the best multi-frame techniques.

Key improvements:
1. HSV-based white detection (not grayscale)
2. Temporal median for statistical robustness
3. Adaptive thresholding based on median statistics
4. Contour filtering by shape (racing lines are thin, continuous curves)

Author: ACC Telemetry Extractor
"""

import cv2
import numpy as np
import yaml
from pathlib import Path


def extract_white_mask_hsv(map_roi: np.ndarray) -> np.ndarray:
    """
    Extract white pixels using HSV color space.
    
    This is more robust than grayscale thresholding because it considers
    saturation (white = low saturation) and value (white = high brightness).
    
    Args:
        map_roi: BGR image of map ROI
    
    Returns:
        Binary mask of white pixels
    """
    # Convert to HSV
    hsv = cv2.cvtColor(map_roi, cv2.COLOR_BGR2HSV)
    
    # White detection in HSV:
    # - Hue: any (0-180)
    # - Saturation: low (0-30) - white has little color
    # - Value: high (200-255) - white is bright
    white_lower = np.array([0, 0, 200])
    white_upper = np.array([180, 30, 255])
    
    white_mask = cv2.inRange(hsv, white_lower, white_upper)
    
    return white_mask


def extract_with_temporal_median_hsv(map_rois: list) -> np.ndarray:
    """
    Extract racing line using temporal median on HSV white masks.
    
    Process:
    1. Extract white pixels from each frame using HSV
    2. Stack all masks into 3D array
    3. Calculate median per pixel (racing line is consistently white)
    4. Threshold the median to get final mask
    
    Args:
        map_rois: List of BGR map ROI images
    
    Returns:
        Combined mask of racing line
    """
    if not map_rois:
        return None
    
    print(f"\n🔍 Extracting white masks from {len(map_rois)} frames...")
    
    # Extract white masks from each frame
    white_masks = []
    for i, map_roi in enumerate(map_rois):
        white_mask = extract_white_mask_hsv(map_roi)
        white_masks.append(white_mask)
        
        white_pixel_count = np.sum(white_mask > 0)
        if i < 5 or i % 10 == 0:
            print(f"   Frame {i:2d}: {white_pixel_count:5d} white pixels")
    
    # Stack into 3D array [height, width, num_frames]
    mask_stack = np.stack(white_masks, axis=2).astype(np.float32)
    
    print(f"\n📊 Computing temporal statistics...")
    
    # Calculate median value per pixel
    median_value = np.median(mask_stack, axis=2)
    
    # Calculate what percentage of frames each pixel is white
    white_frequency = np.sum(mask_stack > 0, axis=2) / len(white_masks)
    
    print(f"   Median range: {np.min(median_value):.1f} - {np.max(median_value):.1f}")
    print(f"   White frequency range: {np.min(white_frequency):.3f} - {np.max(white_frequency):.3f}")
    
    # Racing line should appear white in MOST frames (high frequency)
    # We can use adaptive threshold based on frequency
    frequency_threshold = 0.5  # Pixel must be white in >50% of frames
    
    result = (white_frequency > frequency_threshold).astype(np.uint8) * 255
    
    white_count = np.sum(result > 0)
    print(f"   ✅ Result: {white_count} pixels pass {frequency_threshold*100:.0f}% frequency threshold")
    
    return result


def extract_with_high_confidence_voting(map_rois: list, min_frequency: float = 0.7) -> np.ndarray:
    """
    Extract pixels that are white in at least X% of frames.
    
    This is a stricter version that requires high confidence.
    Racing line should be white in 70%+ of frames.
    
    Args:
        map_rois: List of BGR map ROI images
        min_frequency: Minimum frequency threshold (0.0 - 1.0)
    
    Returns:
        Binary mask of high-confidence white pixels
    """
    if not map_rois:
        return None
    
    print(f"\n🎯 High-confidence voting (min {min_frequency*100:.0f}% frequency)...")
    
    # Extract white masks
    white_masks = [extract_white_mask_hsv(roi) for roi in map_rois]
    
    # Stack and calculate frequency
    mask_stack = np.stack(white_masks, axis=2).astype(np.float32)
    white_frequency = np.sum(mask_stack > 0, axis=2) / len(white_masks)
    
    # Threshold by frequency
    result = (white_frequency >= min_frequency).astype(np.uint8) * 255
    
    white_count = np.sum(result > 0)
    print(f"   ✅ Result: {white_count} pixels with {min_frequency*100:.0f}%+ frequency")
    
    return result


def filter_racing_line_contour(mask: np.ndarray, min_area: int = 50, max_area: int = 20000) -> np.ndarray:
    """
    Filter contours to find the racing line.
    
    Racing line characteristics:
    - Continuous curve (single large contour)
    - Moderate area (not too small, not too large)
    - Non-rectangular shape (aspect ratio != 1)
    - Connected (no gaps)
    
    Args:
        mask: Binary mask
        min_area: Minimum contour area
        max_area: Maximum contour area
    
    Returns:
        Filtered mask with only racing line
    """
    # Morphological cleaning
    kernel = np.ones((3, 3), np.uint8)
    cleaned = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
    cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_OPEN, kernel, iterations=1)
    
    # Find contours
    contours, _ = cv2.findContours(cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    
    if not contours:
        print(f"   ⚠️  No contours found")
        return cleaned
    
    print(f"\n🔍 Analyzing {len(contours)} contours...")
    
    # Analyze each contour
    valid_contours = []
    for i, contour in enumerate(contours):
        area = cv2.contourArea(contour)
        
        if area < min_area:
            print(f"   ❌ Contour {i}: area={area:.1f}px² (too small)")
            continue
        
        if area > max_area:
            print(f"   ❌ Contour {i}: area={area:.1f}px² (too large, likely artifact)")
            continue
        
        # Check bounding box aspect ratio (racing line shouldn't be square)
        x, y, w, h = cv2.boundingRect(contour)
        aspect_ratio = max(w, h) / min(w, h) if min(w, h) > 0 else 0
        
        # Check solidity (area / convex hull area)
        hull = cv2.convexHull(contour)
        hull_area = cv2.contourArea(hull)
        solidity = area / hull_area if hull_area > 0 else 0
        
        print(f"   ✅ Contour {i}: area={area:.1f}px², bbox={w}×{h}, " 
              f"aspect={aspect_ratio:.2f}, solidity={solidity:.3f}")
        
        valid_contours.append((contour, area))
    
    if not valid_contours:
        print(f"   ⚠️  No valid contours found")
        return cleaned
    
    # Get the largest valid contour
    largest_contour, largest_area = max(valid_contours, key=lambda x: x[1])
    
    print(f"   🏆 Selected largest contour: {largest_area:.1f}px²")
    
    # Create mask with only the selected contour
    result = np.zeros_like(mask)
    cv2.drawContours(result, [largest_contour], -1, 255, -1)
    
    return result


def debug_refined_extraction(video_path: str, roi_config: dict):
    """
    Main debug function with refined extraction.
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
    
    # Sample MORE frames (every 25 frames for first 1250 frames = 50 frames)
    sample_frames = list(range(0, min(1250, video_info['frame_count']), 25))
    
    # Create output directory
    output_dir = Path('debug/refined_track_extraction')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("=" * 70)
    print("REFINED TRACK EXTRACTION - HSV-BASED MULTI-FRAME ANALYSIS")
    print("=" * 70)
    print(f"Sampling {len(sample_frames)} frames...")
    print(f"Video: {video_path}")
    print(f"Total frames: {video_info['frame_count']}, FPS: {video_info['fps']:.1f}")
    print("=" * 70)
    
    # Extract ROI from each frame
    map_rois = []
    
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
        
        # Save sample frames
        if i < 10:
            cv2.imwrite(str(output_dir / f'input_frame{i:02d}.png'), map_roi)
            
            # Also save white mask for inspection
            white_mask = extract_white_mask_hsv(map_roi)
            cv2.imwrite(str(output_dir / f'input_frame{i:02d}_white_mask.png'), white_mask)
    
    cap.release()
    
    if not map_rois:
        print("❌ No frames extracted")
        return
    
    print(f"\n✅ Extracted {len(map_rois)} frames")
    
    print("\n" + "=" * 70)
    print("METHOD 1: TEMPORAL MEDIAN (50% frequency threshold)")
    print("=" * 70)
    
    median_mask = extract_with_temporal_median_hsv(map_rois)
    median_filtered = filter_racing_line_contour(median_mask, min_area=50, max_area=10000)
    
    cv2.imwrite(str(output_dir / 'method1_median_raw.png'), median_mask)
    cv2.imwrite(str(output_dir / 'method1_median_filtered.png'), median_filtered)
    
    # Visualize on original frame
    if map_rois:
        vis = map_rois[0].copy()
        contours, _ = cv2.findContours(median_filtered, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        if contours:
            cv2.drawContours(vis, contours, -1, (0, 255, 0), 2)
        cv2.imwrite(str(output_dir / 'method1_visualization.png'), vis)
    
    print("\n" + "=" * 70)
    print("METHOD 2: HIGH CONFIDENCE (70% frequency threshold)")
    print("=" * 70)
    
    high_conf_mask = extract_with_high_confidence_voting(map_rois, min_frequency=0.7)
    high_conf_filtered = filter_racing_line_contour(high_conf_mask, min_area=50, max_area=10000)
    
    cv2.imwrite(str(output_dir / 'method2_highconf_raw.png'), high_conf_mask)
    cv2.imwrite(str(output_dir / 'method2_highconf_filtered.png'), high_conf_filtered)
    
    # Visualize
    if map_rois:
        vis = map_rois[0].copy()
        contours, _ = cv2.findContours(high_conf_filtered, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        if contours:
            cv2.drawContours(vis, contours, -1, (0, 255, 0), 2)
        cv2.imwrite(str(output_dir / 'method2_visualization.png'), vis)
    
    print("\n" + "=" * 70)
    print("METHOD 3: ULTRA STRICT (90% frequency threshold)")
    print("=" * 70)
    
    ultra_strict_mask = extract_with_high_confidence_voting(map_rois, min_frequency=0.9)
    ultra_strict_filtered = filter_racing_line_contour(ultra_strict_mask, min_area=50, max_area=10000)
    
    cv2.imwrite(str(output_dir / 'method3_ultrastrict_raw.png'), ultra_strict_mask)
    cv2.imwrite(str(output_dir / 'method3_ultrastrict_filtered.png'), ultra_strict_filtered)
    
    # Visualize
    if map_rois:
        vis = map_rois[0].copy()
        contours, _ = cv2.findContours(ultra_strict_filtered, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        if contours:
            cv2.drawContours(vis, contours, -1, (0, 255, 0), 2)
        cv2.imwrite(str(output_dir / 'method3_visualization.png'), vis)
    
    print("\n" + "=" * 70)
    print("COMPARISON GRID")
    print("=" * 70)
    
    # Create side-by-side comparison
    if map_rois:
        h, w = map_rois[0].shape[:2]
        comparison = np.zeros((h * 2, w * 2, 3), dtype=np.uint8)
        
        # Top-left: Original
        comparison[0:h, 0:w] = map_rois[0]
        
        # Top-right: Method 1
        vis1 = map_rois[0].copy()
        contours1, _ = cv2.findContours(median_filtered, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        if contours1:
            cv2.drawContours(vis1, contours1, -1, (0, 255, 0), 2)
        comparison[0:h, w:w*2] = vis1
        
        # Bottom-left: Method 2
        vis2 = map_rois[0].copy()
        contours2, _ = cv2.findContours(high_conf_filtered, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        if contours2:
            cv2.drawContours(vis2, contours2, -1, (0, 255, 0), 2)
        comparison[h:h*2, 0:w] = vis2
        
        # Bottom-right: Method 3
        vis3 = map_rois[0].copy()
        contours3, _ = cv2.findContours(ultra_strict_filtered, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        if contours3:
            cv2.drawContours(vis3, contours3, -1, (0, 255, 0), 2)
        comparison[h:h*2, w:w*2] = vis3
        
        # Add labels
        cv2.putText(comparison, "Original", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(comparison, "Median (50%)", (w+10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(comparison, "Strict (70%)", (10, h+30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(comparison, "Ultra (90%)", (w+10, h+30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        cv2.imwrite(str(output_dir / 'COMPARISON_GRID.png'), comparison)
        print("\n✅ Comparison grid saved!")
    
    print(f"\n✅ Analysis complete! Results saved to {output_dir}/")
    print("\n📁 Key files to examine:")
    print(f"   COMPARISON_GRID.png - Side-by-side comparison of all methods")
    print(f"   method1_visualization.png - Median (50%) result")
    print(f"   method2_visualization.png - High confidence (70%) result")
    print(f"   method3_visualization.png - Ultra strict (90%) result")
    print(f"   input_frameXX_white_mask.png - Individual frame white detection")


def main():
    VIDEO_PATH = './panorama.mp4'
    CONFIG_PATH = 'config/roi_config.yaml'
    
    with open(CONFIG_PATH, 'r') as f:
        roi_config = yaml.safe_load(f)
    
    debug_refined_extraction(VIDEO_PATH, roi_config)


if __name__ == '__main__':
    main()

