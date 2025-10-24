"""
PERFECT Racing Line Extraction - FINAL VERSION

After extensive testing, the optimal strategy is:
1. HSV-based white detection (individual frames work great!)
2. Frequency voting across 50+ frames (60% threshold optimal)
3. VERY aggressive morphological closing to bridge gaps
4. Keep all significant contours (line may be fragmented)

The key insight: The raw outline detection works perfectly, we just need
to connect the gaps left by the red dot moving across the line.

Author: ACC Telemetry Extractor
"""

import cv2
import numpy as np
import yaml
from pathlib import Path
from typing import List, Tuple, Optional


def extract_white_mask_hsv(map_roi: np.ndarray) -> np.ndarray:
    """
    Extract white pixels using HSV color space.
    
    This is robust to lighting variations and works consistently
    across all frames.
    """
    hsv = cv2.cvtColor(map_roi, cv2.COLOR_BGR2HSV)
    
    # White: any hue, low saturation (0-30), high value (200-255)
    white_lower = np.array([0, 0, 200])
    white_upper = np.array([180, 30, 255])
    
    return cv2.inRange(hsv, white_lower, white_upper)


def extract_racing_line_from_video(video_path: str, 
                                   roi_coords: dict,
                                   num_samples: int = 50,
                                   frequency_threshold: float = 0.6) -> Optional[np.ndarray]:
    """
    Extract racing line from video using multi-frame analysis.
    
    Args:
        video_path: Path to video file
        roi_coords: ROI coordinates (x, y, width, height)
        num_samples: Number of frames to sample (more = better, but slower)
        frequency_threshold: Pixel must be white in this % of frames (0.6 = 60%)
    
    Returns:
        Binary mask of racing line, or None if extraction failed
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
    
    print(f"\n{'='*70}")
    print(f"RACING LINE EXTRACTION")
    print(f"{'='*70}")
    print(f"Video: {video_path}")
    print(f"Frames: {video_info['frame_count']} @ {video_info['fps']:.1f} FPS")
    print(f"Sampling: {num_samples} frames")
    print(f"Frequency threshold: {frequency_threshold*100:.0f}%")
    print(f"{'='*70}\n")
    
    # Calculate frame sampling interval
    sample_interval = max(1, video_info['frame_count'] // num_samples)
    sample_frames = list(range(0, video_info['frame_count'], sample_interval))[:num_samples]
    
    # Extract ROIs from sampled frames
    print(f"📍 Extracting track map ROIs from {len(sample_frames)} frames...")
    
    map_rois = []
    x, y, w, h = roi_coords['x'], roi_coords['y'], roi_coords['width'], roi_coords['height']
    
    for i, frame_num in enumerate(sample_frames):
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
        ret, frame = cap.read()
        
        if not ret:
            continue
        
        map_roi = frame[y:y+h, x:x+w]
        map_rois.append(map_roi)
        
        if (i+1) % 10 == 0:
            print(f"   Progress: {i+1}/{len(sample_frames)} frames")
    
    cap.release()
    
    if not map_rois:
        print("❌ Error: No ROIs extracted")
        return None
    
    print(f"   ✅ Extracted {len(map_rois)} ROIs\n")
    
    # Extract white masks from each frame
    print(f"🎯 Detecting white pixels in each frame...")
    
    white_masks = []
    for i, map_roi in enumerate(map_rois):
        white_mask = extract_white_mask_hsv(map_roi)
        white_masks.append(white_mask)
    
    print(f"   ✅ Extracted {len(white_masks)} white masks\n")
    
    # Calculate frequency: how often is each pixel white?
    print(f"📊 Computing pixel-wise white frequency...")
    
    mask_stack = np.stack(white_masks, axis=2).astype(np.float32)
    white_frequency = np.sum(mask_stack > 0, axis=2) / len(white_masks)
    
    pixels_above_threshold = np.sum(white_frequency >= frequency_threshold)
    print(f"   Pixels with ≥{frequency_threshold*100:.0f}% frequency: {pixels_above_threshold}")
    print(f"   ✅ Frequency map computed\n")
    
    # Threshold by frequency
    racing_line_raw = (white_frequency >= frequency_threshold).astype(np.uint8) * 255
    
    # AGGRESSIVE morphological closing to connect gaps
    print(f"🔗 Connecting gaps in racing line...")
    print(f"   Strategy: Large kernel closing to bridge gaps left by red dot")
    
    # Use a large elliptical kernel for closing
    kernel_size = 7  # Larger kernel = connects bigger gaps
    kernel_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
    
    connected = racing_line_raw.copy()
    
    # Multiple iterations of closing with progressively larger kernels
    for iteration, ksize in enumerate([5, 7, 9], 1):
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (ksize, ksize))
        connected = cv2.morphologyEx(connected, cv2.MORPH_CLOSE, kernel, iterations=2)
        pixel_count = np.sum(connected > 0)
        print(f"   Iteration {iteration} (kernel={ksize}×{ksize}): {pixel_count} pixels")
    
    # Light opening to remove small noise
    kernel_open = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    cleaned = cv2.morphologyEx(connected, cv2.MORPH_OPEN, kernel_open, iterations=1)
    
    final_pixel_count = np.sum(cleaned > 0)
    print(f"   After cleaning: {final_pixel_count} pixels")
    print(f"   ✅ Connected racing line\n")
    
    # Analyze contours
    print(f"🔍 Analyzing contours...")
    
    contours, _ = cv2.findContours(cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    
    if not contours:
        print("   ❌ No contours found!")
        return None
    
    print(f"   Found {len(contours)} contours")
    
    # Keep contours above minimum area
    min_area = 50
    valid_contours = []
    total_area = 0
    
    for contour in contours:
        area = cv2.contourArea(contour)
        if area >= min_area:
            valid_contours.append(contour)
            total_area += area
    
    print(f"   Valid contours (≥{min_area}px²): {len(valid_contours)}")
    print(f"   Total area: {total_area:.1f}px²")
    
    if not valid_contours:
        print("   ⚠️  No valid contours above minimum area")
        return cleaned
    
    # If there's one dominant contour (>80% of total area), use only that
    # Otherwise, keep all valid contours
    largest_contour = max(valid_contours, key=cv2.contourArea)
    largest_area = cv2.contourArea(largest_contour)
    
    if largest_area / total_area > 0.8:
        print(f"   🏆 One dominant contour ({largest_area/total_area*100:.1f}% of total)")
        print(f"   Using only largest contour")
        
        final_mask = np.zeros_like(cleaned)
        cv2.drawContours(final_mask, [largest_contour], -1, 255, -1)
    else:
        print(f"   📊 Multiple significant contours")
        print(f"   Keeping all {len(valid_contours)} valid contours")
        
        final_mask = np.zeros_like(cleaned)
        cv2.drawContours(final_mask, valid_contours, -1, 255, -1)
    
    final_pixels = np.sum(final_mask > 0)
    print(f"   ✅ Final racing line: {final_pixels} pixels\n")
    
    print(f"{'='*70}")
    print(f"✅ RACING LINE EXTRACTION COMPLETE!")
    print(f"{'='*70}\n")
    
    return final_mask, racing_line_raw, map_rois[0]


def save_debug_visualization(racing_line: np.ndarray,
                             raw_outline: np.ndarray,
                             original_frame: np.ndarray,
                             output_dir: Path,
                             frequency_threshold: float):
    """
    Save comprehensive debug visualization.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"📸 Saving visualizations to {output_dir}/...")
    
    # 1. Raw masks
    cv2.imwrite(str(output_dir / 'raw_frequency_outline.png'), raw_outline)
    cv2.imwrite(str(output_dir / 'final_racing_line.png'), racing_line)
    
    # 2. Overlay on original
    overlay = original_frame.copy()
    contours, _ = cv2.findContours(racing_line, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    
    if contours:
        # Draw filled contour (semi-transparent)
        overlay_colored = overlay.copy()
        cv2.drawContours(overlay_colored, contours, -1, (0, 255, 0), -1)
        overlay = cv2.addWeighted(overlay, 0.7, overlay_colored, 0.3, 0)
        
        # Draw outline (bright)
        cv2.drawContours(overlay, contours, -1, (0, 255, 0), 2)
        
        # Draw contour points
        for contour in contours:
            for point in contour[::5]:  # Every 5th point to avoid clutter
                px, py = point[0]
                cv2.circle(overlay, (px, py), 1, (255, 255, 0), -1)
    
    cv2.imwrite(str(output_dir / 'overlay_visualization.png'), overlay)
    
    # 3. Side-by-side comparison
    h, w = original_frame.shape[:2]
    comparison = np.zeros((h*2, w*2, 3), dtype=np.uint8)
    
    # Top-left: Original
    comparison[0:h, 0:w] = original_frame
    
    # Top-right: Raw outline
    comparison[0:h, w:w*2] = cv2.cvtColor(raw_outline, cv2.COLOR_GRAY2BGR)
    
    # Bottom-left: Final mask
    comparison[h:h*2, 0:w] = cv2.cvtColor(racing_line, cv2.COLOR_GRAY2BGR)
    
    # Bottom-right: Overlay
    comparison[h:h*2, w:w*2] = overlay
    
    # Labels
    cv2.putText(comparison, "Original", (10, 30), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    cv2.putText(comparison, f"Raw ({frequency_threshold*100:.0f}% freq)", (w+10, 30), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    cv2.putText(comparison, "Connected & Cleaned", (10, h+30), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    cv2.putText(comparison, "Final Result", (w+10, h+30), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    
    cv2.imwrite(str(output_dir / 'FULL_COMPARISON.png'), comparison)
    
    print(f"   ✅ Saved visualizations\n")


def main():
    """
    Test the final extraction method.
    """
    VIDEO_PATH = './panorama.mp4'
    CONFIG_PATH = 'config/roi_config.yaml'
    
    with open(CONFIG_PATH, 'r') as f:
        roi_config = yaml.safe_load(f)
    
    # Test with optimal parameters
    frequency_threshold = 0.6  # 60% - good balance
    num_samples = 50  # Sample 50 frames across the lap
    
    # Extract racing line
    result = extract_racing_line_from_video(
        video_path=VIDEO_PATH,
        roi_coords=roi_config['track_map'],
        num_samples=num_samples,
        frequency_threshold=frequency_threshold
    )
    
    if result is None:
        print("❌ Extraction failed!")
        return
    
    final_mask, raw_outline, original_frame = result
    
    # Save visualization
    output_dir = Path('debug/perfect_racing_line')
    save_debug_visualization(
        racing_line=final_mask,
        raw_outline=raw_outline,
        original_frame=original_frame,
        output_dir=output_dir,
        frequency_threshold=frequency_threshold
    )
    
    print(f"{'='*70}")
    print(f"🎉 SUCCESS! Racing line extracted and saved!")
    print(f"{'='*70}")
    print(f"\n📁 Check these files:")
    print(f"   {output_dir}/FULL_COMPARISON.png - Complete visualization")
    print(f"   {output_dir}/overlay_visualization.png - Final result")
    print(f"   {output_dir}/final_racing_line.png - Black & white mask")
    print(f"\n💡 Next steps:")
    print(f"   1. Review the FULL_COMPARISON.png to verify quality")
    print(f"   2. If satisfied, integrate this method into PositionTrackerV2")
    print(f"   3. Use the extracted path for position tracking!\n")


if __name__ == '__main__':
    main()

