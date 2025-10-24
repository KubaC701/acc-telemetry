"""
Outline-Based Track Extraction

KEY INSIGHT: The racing line is a WHITE OUTLINE, not a filled region!

Individual frames show:
- White outline of the racing line (the actual line we want)
- Black interior (track surface)
- Variable background outside

The multi-frame approach should extract the OUTLINE that's consistent,
not try to fill regions.

New approach:
1. Extract white pixels (outline) from each frame
2. Use frequency voting to keep pixels that are consistently white
3. DON'T filter by contour area - keep ALL parts of the outline
4. Connect nearby segments with aggressive morphological closing
5. Extract the skeleton/centerline if needed

Author: ACC Telemetry Extractor
"""

import cv2
import numpy as np
import yaml
from pathlib import Path


def extract_white_mask_hsv(map_roi: np.ndarray) -> np.ndarray:
    """Extract white pixels using HSV color space."""
    hsv = cv2.cvtColor(map_roi, cv2.COLOR_BGR2HSV)
    
    white_lower = np.array([0, 0, 200])
    white_upper = np.array([180, 30, 255])
    
    white_mask = cv2.inRange(hsv, white_lower, white_upper)
    
    return white_mask


def extract_racing_line_outline(map_rois: list, frequency_threshold: float = 0.6) -> np.ndarray:
    """
    Extract the racing line OUTLINE using frequency voting.
    
    This version focuses on preserving the outline structure rather than
    filling areas.
    """
    if not map_rois or len(map_rois) < 10:
        print(f"⚠️  Need at least 10 frames, got {len(map_rois)}")
        return None
    
    print(f"\n{'='*70}")
    print(f"OUTLINE-BASED RACING LINE EXTRACTION")
    print(f"{'='*70}")
    print(f"Frames: {len(map_rois)}")
    print(f"Frequency threshold: {frequency_threshold*100:.0f}%")
    print(f"Strategy: Keep ALL pixels that are white in {frequency_threshold*100:.0f}%+ of frames")
    print(f"{'='*70}\n")
    
    # Extract white masks
    print("📍 Step 1: Extracting white pixels...")
    white_masks = []
    
    for i, map_roi in enumerate(map_rois):
        white_mask = extract_white_mask_hsv(map_roi)
        white_masks.append(white_mask)
        
        if i < 3:
            white_count = np.sum(white_mask > 0)
            print(f"   Frame {i}: {white_count} white pixels")
    
    print(f"   ✅ Extracted {len(white_masks)} masks\n")
    
    # Calculate frequency
    print("📊 Step 2: Computing frequency...")
    mask_stack = np.stack(white_masks, axis=2).astype(np.float32)
    white_frequency = np.sum(mask_stack > 0, axis=2) / len(white_masks)
    
    print(f"   Max frequency: {np.max(white_frequency):.3f}")
    print(f"   Pixels ≥{frequency_threshold:.0%}: {np.sum(white_frequency >= frequency_threshold)}")
    
    # Threshold
    outline_mask = (white_frequency >= frequency_threshold).astype(np.uint8) * 255
    print(f"   ✅ Outline pixels: {np.sum(outline_mask > 0)}\n")
    
    # Morphological operations to connect nearby segments
    print("🔗 Step 3: Connecting outline segments...")
    
    # Use AGGRESSIVE closing to connect gaps left by the red dot
    kernel_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    connected = cv2.morphologyEx(outline_mask, cv2.MORPH_CLOSE, kernel_close, iterations=3)
    print(f"   After closing (connect gaps): {np.sum(connected > 0)} pixels")
    
    # Light opening to remove noise
    kernel_open = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2, 2))
    cleaned = cv2.morphologyEx(connected, cv2.MORPH_OPEN, kernel_open, iterations=1)
    print(f"   After opening (remove noise): {np.sum(cleaned > 0)} pixels")
    
    print(f"   ✅ Connected outline\n")
    
    return cleaned, outline_mask


def keep_all_significant_contours(mask: np.ndarray, min_area: int = 30) -> np.ndarray:
    """
    Keep ALL contours above minimum size (not just the largest).
    
    The racing line might be broken into multiple segments, so we want to keep
    all of them.
    """
    print("🔍 Step 4: Analyzing contours...")
    
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    
    if not contours:
        print("   ❌ No contours found")
        return mask
    
    print(f"   Found {len(contours)} contours")
    
    # Keep all above minimum area
    valid_contours = []
    total_area = 0
    
    for i, contour in enumerate(contours):
        area = cv2.contourArea(contour)
        if area >= min_area:
            valid_contours.append(contour)
            total_area += area
            
            if len(valid_contours) <= 10:  # Print first 10
                perimeter = cv2.arcLength(contour, True)
                print(f"      #{i}: area={area:.1f}px², perimeter={perimeter:.1f}px")
    
    print(f"   ✅ Keeping {len(valid_contours)} contours (total area: {total_area:.1f}px²)")
    
    if len(valid_contours) > 10:
        print(f"      (showing first 10, {len(valid_contours)-10} more...)")
    
    # Create mask with all valid contours
    result = np.zeros_like(mask)
    cv2.drawContours(result, valid_contours, -1, 255, -1)
    
    print(f"   ✅ Combined mask: {np.sum(result > 0)} pixels\n")
    
    return result


def main():
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
    
    # Sample frames
    sample_interval = 30
    max_frames = 1500
    sample_frames = list(range(0, min(max_frames, video_info['frame_count']), sample_interval))
    
    print(f"Sampling {len(sample_frames)} frames...")
    
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
    
    # Test different thresholds
    output_base = Path('debug/outline_extraction')
    
    for threshold in [0.5, 0.6, 0.7]:
        print(f"\n{'='*70}")
        print(f"TESTING THRESHOLD: {threshold*100:.0f}%")
        print(f"{'='*70}")
        
        # Extract outline
        connected_mask, raw_outline = extract_racing_line_outline(map_rois, frequency_threshold=threshold)
        
        if connected_mask is None:
            continue
        
        # Keep all significant contours
        final_mask = keep_all_significant_contours(connected_mask, min_area=30)
        
        # Create output directory
        output_dir = output_base / f"threshold_{int(threshold*100)}pct"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save masks
        cv2.imwrite(str(output_dir / 'raw_outline.png'), raw_outline)
        cv2.imwrite(str(output_dir / 'connected.png'), connected_mask)
        cv2.imwrite(str(output_dir / 'final_mask.png'), final_mask)
        
        # Visualize
        if map_rois:
            original = map_rois[0].copy()
            overlay = original.copy()
            
            # Draw contours
            contours, _ = cv2.findContours(final_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
            if contours:
                cv2.drawContours(overlay, contours, -1, (0, 255, 0), 2)
            
            # Side-by-side comparison
            h, w = original.shape[:2]
            comparison = np.zeros((h, w*3, 3), dtype=np.uint8)
            comparison[:, 0:w] = original
            comparison[:, w:w*2] = cv2.cvtColor(raw_outline, cv2.COLOR_GRAY2BGR)
            comparison[:, w*2:w*3] = overlay
            
            # Labels
            cv2.putText(comparison, "Original", (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            cv2.putText(comparison, "Raw Outline", (w+10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            cv2.putText(comparison, f"Final ({threshold*100:.0f}%)", (w*2+10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            
            cv2.imwrite(str(output_dir / 'COMPARISON.png'), comparison)
        
        print(f"✅ Results saved to {output_dir}/\n")
    
    print(f"\n{'='*70}")
    print(f"DONE! Check debug/outline_extraction/")
    print(f"{'='*70}\n")


if __name__ == '__main__':
    main()

