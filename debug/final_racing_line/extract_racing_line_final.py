"""
Racing Line Extraction - FINAL WORKING VERSION

Strategy that WORKS:
1. Frequency voting (60%) - gives perfect raw outline ✅
2. Dilate to connect nearby line segments
3. Keep largest connected component (main racing line)
4. Erode back to original thickness
5. This removes small artifacts while preserving the complete racing line

Author: ACC Telemetry Extractor
"""

import cv2
import numpy as np
import yaml
from pathlib import Path
from typing import Optional, Tuple, List


def extract_white_mask_hsv(map_roi: np.ndarray) -> np.ndarray:
    """Extract white pixels using HSV color space."""
    hsv = cv2.cvtColor(map_roi, cv2.COLOR_BGR2HSV)
    white_lower = np.array([0, 0, 200])
    white_upper = np.array([180, 30, 255])
    return cv2.inRange(hsv, white_lower, white_upper)


def extract_racing_line_frequency_voting(map_rois: List[np.ndarray], 
                                         frequency_threshold: float = 0.6) -> np.ndarray:
    """
    Extract racing line using frequency voting.
    This gives us the perfect raw outline!
    """
    if not map_rois or len(map_rois) < 10:
        print(f"⚠️  Need at least 10 frames, got {len(map_rois)}")
        return None
    
    print(f"\n{'='*70}")
    print(f"RACING LINE EXTRACTION - DILATE-FILTER-ERODE METHOD")
    print(f"{'='*70}")
    print(f"Frames: {len(map_rois)}")
    print(f"Frequency threshold: {frequency_threshold*100:.0f}%")
    print(f"{'='*70}\n")
    
    # Extract white masks
    print(f"🎯 Step 1: Frequency voting ({frequency_threshold*100:.0f}% threshold)...")
    white_masks = [extract_white_mask_hsv(roi) for roi in map_rois]
    
    # Calculate frequency
    mask_stack = np.stack(white_masks, axis=2).astype(np.float32)
    white_frequency = np.sum(mask_stack > 0, axis=2) / len(white_masks)
    
    # Threshold
    racing_line_raw = (white_frequency >= frequency_threshold).astype(np.uint8) * 255
    
    pixels = np.sum(racing_line_raw > 0)
    print(f"   ✅ Raw outline: {pixels} pixels\n")
    
    return racing_line_raw


def clean_with_dilate_filter_erode(raw_mask: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """
    Clean racing line using dilate→filter→erode strategy.
    
    This connects nearby segments, removes small artifacts, then restores
    original thickness.
    
    Returns:
        (final_mask, dilated_mask)
    """
    print(f"🔧 Step 2: Dilate-Filter-Erode cleaning...")
    print(f"   Strategy: Connect segments → Keep largest → Restore thickness")
    
    # DILATE to connect nearby segments
    kernel_dilate = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    dilated = cv2.dilate(raw_mask, kernel_dilate, iterations=2)
    dilated_pixels = np.sum(dilated > 0)
    print(f"   After dilation (5×5, 2 iter): {dilated_pixels} pixels")
    
    # Find connected components in dilated mask
    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(
        dilated, connectivity=8, ltype=cv2.CV_32S
    )
    
    print(f"   Found {num_labels - 1} components in dilated mask")
    
    if num_labels <= 1:
        print("   ⚠️  No components found!")
        return raw_mask, dilated
    
    # Find largest component (skip label 0 = background)
    areas = [(i, stats[i, cv2.CC_STAT_AREA]) for i in range(1, num_labels)]
    areas.sort(key=lambda x: x[1], reverse=True)
    
    # Show top components
    total_area = sum(a[1] for a in areas)
    print(f"   Top components:")
    for i, (label, area) in enumerate(areas[:5], 1):
        percentage = (area / total_area) * 100
        print(f"      #{i}: {area:5.0f}px² ({percentage:5.1f}%)")
    
    # Keep only largest component
    largest_label = areas[0][0]
    largest_area = areas[0][1]
    
    print(f"   ✅ Keeping largest: {largest_area:.0f}px²")
    
    # Create mask with only largest component
    largest_component_dilated = np.zeros_like(dilated)
    largest_component_dilated[labels == largest_label] = 255
    
    # ERODE back to restore original thickness
    # Use same kernel but fewer iterations
    kernel_erode = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    eroded = cv2.erode(largest_component_dilated, kernel_erode, iterations=2)
    eroded_pixels = np.sum(eroded > 0)
    print(f"   After erosion (5×5, 2 iter): {eroded_pixels} pixels")
    
    # Intersect with original to ensure we don't add false positives
    final = cv2.bitwise_and(eroded, raw_mask)
    final_pixels = np.sum(final > 0)
    print(f"   After intersection with raw: {final_pixels} pixels")
    print(f"   ✅ Cleaning complete\n")
    
    return final, largest_component_dilated


def extract_racing_line_from_video(video_path: str, 
                                   roi_coords: dict,
                                   num_samples: int = 50,
                                   frequency_threshold: float = 0.6) -> Optional[Tuple]:
    """
    Extract racing line from video.
    
    Returns:
        (final_mask, raw_mask, dilated_mask, sample_frame) or None
    """
    # Open video
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"❌ Error: Could not open video {video_path}")
        return None
    
    video_info = {
        'fps': cap.get(cv2.CAP_PROP_FPS),
        'frame_count': int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    }
    
    # Sample frames
    sample_interval = max(1, video_info['frame_count'] // num_samples)
    sample_frames = list(range(0, video_info['frame_count'], sample_interval))[:num_samples]
    
    # Extract ROIs
    map_rois = []
    x, y, w, h = roi_coords['x'], roi_coords['y'], roi_coords['width'], roi_coords['height']
    
    for frame_num in sample_frames:
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
        ret, frame = cap.read()
        
        if not ret:
            continue
        
        map_roi = frame[y:y+h, x:x+w]
        map_rois.append(map_roi)
    
    cap.release()
    
    if not map_rois:
        print("❌ Error: No ROIs extracted")
        return None
    
    print(f"✅ Extracted {len(map_rois)} ROIs from video\n")
    
    # Extract racing line
    raw_mask = extract_racing_line_frequency_voting(map_rois, frequency_threshold)
    
    if raw_mask is None:
        return None
    
    # Clean with dilate-filter-erode
    final_mask, dilated_mask = clean_with_dilate_filter_erode(raw_mask)
    
    print(f"{'='*70}")
    print(f"✅ EXTRACTION COMPLETE!")
    print(f"{'='*70}")
    print(f"Raw pixels: {np.sum(raw_mask > 0)}")
    print(f"Final pixels: {np.sum(final_mask > 0)}")
    print(f"{'='*70}\n")
    
    return final_mask, raw_mask, dilated_mask, map_rois[0]


def visualize_results(final_mask: np.ndarray,
                     raw_mask: np.ndarray,
                     dilated_mask: np.ndarray,
                     original_frame: np.ndarray,
                     output_dir: Path,
                     frequency_threshold: float):
    """Create visualization of the extraction pipeline."""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"📸 Creating visualizations...")
    
    # Save masks
    cv2.imwrite(str(output_dir / 'step1_raw_frequency.png'), raw_mask)
    cv2.imwrite(str(output_dir / 'step2_dilated.png'), dilated_mask)
    cv2.imwrite(str(output_dir / 'step3_final.png'), final_mask)
    
    # Create overlays
    h, w = original_frame.shape[:2]
    
    overlay_raw = original_frame.copy()
    overlay_raw[raw_mask > 0] = [0, 255, 0]
    
    overlay_final = original_frame.copy()
    contours, _ = cv2.findContours(final_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    if contours:
        cv2.drawContours(overlay_final, contours, -1, (0, 255, 0), 2)
    
    # 2×3 grid comparison
    comparison = np.zeros((h*2, w*3, 3), dtype=np.uint8)
    
    # Row 1: Masks
    comparison[0:h, 0:w] = cv2.cvtColor(raw_mask, cv2.COLOR_GRAY2BGR)
    comparison[0:h, w:w*2] = cv2.cvtColor(dilated_mask, cv2.COLOR_GRAY2BGR)
    comparison[0:h, w*2:w*3] = cv2.cvtColor(final_mask, cv2.COLOR_GRAY2BGR)
    
    # Row 2: Overlays
    comparison[h:h*2, 0:w] = overlay_raw
    comparison[h:h*2, w:w*2] = original_frame  # Original in middle
    comparison[h:h*2, w*2:w*3] = overlay_final
    
    # Labels
    font = cv2.FONT_HERSHEY_SIMPLEX
    cv2.putText(comparison, f"1. Raw ({frequency_threshold*100:.0f}%)", 
               (10, 30), font, 0.6, (255, 255, 255), 2)
    cv2.putText(comparison, "2. Dilated (connect)", 
               (w+10, 30), font, 0.6, (255, 255, 255), 2)
    cv2.putText(comparison, "3. Final (largest)", 
               (w*2+10, 30), font, 0.6, (255, 255, 255), 2)
    
    cv2.putText(comparison, "Raw Overlay", 
               (10, h+30), font, 0.6, (0, 255, 0), 2)
    cv2.putText(comparison, "Original", 
               (w+10, h+30), font, 0.6, (255, 255, 255), 2)
    cv2.putText(comparison, "Final Result", 
               (w*2+10, h+30), font, 0.6, (0, 255, 0), 2)
    
    cv2.imwrite(str(output_dir / 'COMPARISON_PIPELINE.png'), comparison)
    
    # Simple before/after
    simple = np.zeros((h, w*2, 3), dtype=np.uint8)
    simple[:, 0:w] = overlay_raw
    simple[:, w:w*2] = overlay_final
    
    cv2.putText(simple, f"Raw ({frequency_threshold*100:.0f}% freq)", 
               (10, 30), font, 0.7, (255, 255, 255), 2)
    cv2.putText(simple, "Final (cleaned)", 
               (w+10, 30), font, 0.7, (0, 255, 0), 2)
    
    cv2.imwrite(str(output_dir / 'BEFORE_AFTER.png'), simple)
    
    print(f"   ✅ Saved to {output_dir}/\n")


def main():
    """Test the final extraction method."""
    VIDEO_PATH = './panorama.mp4'
    CONFIG_PATH = 'config/roi_config.yaml'
    
    with open(CONFIG_PATH, 'r') as f:
        roi_config = yaml.safe_load(f)
    
    # Extract
    result = extract_racing_line_from_video(
        video_path=VIDEO_PATH,
        roi_coords=roi_config['track_map'],
        num_samples=50,
        frequency_threshold=0.6
    )
    
    if result is None:
        print("❌ Extraction failed!")
        return
    
    final_mask, raw_mask, dilated_mask, original_frame = result
    
    # Visualize
    output_dir = Path('debug/final_racing_line')
    visualize_results(
        final_mask=final_mask,
        raw_mask=raw_mask,
        dilated_mask=dilated_mask,
        original_frame=original_frame,
        output_dir=output_dir,
        frequency_threshold=0.6
    )
    
    print(f"{'='*70}")
    print(f"🎉 DONE!")
    print(f"{'='*70}")
    print(f"\n📁 Files to check:")
    print(f"   {output_dir}/COMPARISON_PIPELINE.png - Full pipeline")
    print(f"   {output_dir}/BEFORE_AFTER.png - Before/After comparison")
    print(f"   {output_dir}/step3_final.png - Final mask (for use in tracking)")
    print(f"\n✅ This final mask removes artifacts while preserving the racing line!\n")


if __name__ == '__main__':
    main()

