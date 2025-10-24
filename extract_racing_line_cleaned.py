"""
Racing Line Extraction - Fixed Version

Problem identified:
- Raw 60% frequency looks PERFECT (complete outline)
- Aggressive morphological closing (9×9) DESTROYS the thin line
- Small artifacts (car cage, UI elements) need removal

Solution:
1. Use LIGHT morphological operations (preserve thin lines)
2. Remove small disconnected components (car cage artifacts)
3. Keep only the largest connected component (main racing line)

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
    
    Returns raw mask where each pixel that's white in ≥60% of frames is kept.
    """
    if not map_rois or len(map_rois) < 10:
        print(f"⚠️  Need at least 10 frames, got {len(map_rois)}")
        return None
    
    print(f"\n{'='*70}")
    print(f"RACING LINE EXTRACTION - LIGHT TOUCH VERSION")
    print(f"{'='*70}")
    print(f"Frames: {len(map_rois)}")
    print(f"Frequency threshold: {frequency_threshold*100:.0f}%")
    print(f"{'='*70}\n")
    
    # Extract white masks
    print(f"🎯 Step 1: Extracting white pixels from {len(map_rois)} frames...")
    white_masks = [extract_white_mask_hsv(roi) for roi in map_rois]
    print(f"   ✅ Done\n")
    
    # Calculate frequency
    print(f"📊 Step 2: Computing pixel-wise frequency...")
    mask_stack = np.stack(white_masks, axis=2).astype(np.float32)
    white_frequency = np.sum(mask_stack > 0, axis=2) / len(white_masks)
    
    pixels_above = np.sum(white_frequency >= frequency_threshold)
    print(f"   Pixels ≥{frequency_threshold*100:.0f}% frequency: {pixels_above}")
    print(f"   ✅ Done\n")
    
    # Threshold
    racing_line_raw = (white_frequency >= frequency_threshold).astype(np.uint8) * 255
    
    return racing_line_raw


def clean_racing_line_gentle(raw_mask: np.ndarray) -> np.ndarray:
    """
    Clean the racing line mask GENTLY to preserve thin lines.
    
    Strategy:
    1. Very light morphological operations (small kernels)
    2. Remove small disconnected artifacts using connected components
    3. Keep only the largest connected component (main racing line)
    """
    print(f"🧹 Step 3: Gentle cleaning (preserve thin lines)...")
    print(f"   Input: {np.sum(raw_mask > 0)} white pixels")
    
    # LIGHT closing to connect tiny gaps (3×3 kernel only!)
    kernel_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    closed = cv2.morphologyEx(raw_mask, cv2.MORPH_CLOSE, kernel_close, iterations=1)
    print(f"   After light closing (3×3): {np.sum(closed > 0)} pixels")
    
    # VERY light opening to remove single-pixel noise
    kernel_open = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2, 2))
    cleaned = cv2.morphologyEx(closed, cv2.MORPH_OPEN, kernel_open, iterations=1)
    print(f"   After light opening (2×2): {np.sum(cleaned > 0)} pixels")
    print(f"   ✅ Morphological cleaning complete\n")
    
    return cleaned


def remove_small_artifacts(mask: np.ndarray, min_area: int = 100) -> np.ndarray:
    """
    Remove small disconnected artifacts (car cage, UI elements, etc.).
    
    Strategy:
    - Use connected components analysis
    - Keep only components above minimum area
    - If there's one dominant component (the racing line), keep only that
    """
    print(f"🔍 Step 4: Removing small artifacts...")
    
    # Find all connected components
    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(
        mask, connectivity=8, ltype=cv2.CV_32S
    )
    
    # Skip label 0 (background)
    print(f"   Found {num_labels - 1} connected components")
    
    # Analyze components
    components = []
    for i in range(1, num_labels):
        area = stats[i, cv2.CC_STAT_AREA]
        x = stats[i, cv2.CC_STAT_LEFT]
        y = stats[i, cv2.CC_STAT_TOP]
        w = stats[i, cv2.CC_STAT_WIDTH]
        h = stats[i, cv2.CC_STAT_HEIGHT]
        
        components.append({
            'label': i,
            'area': area,
            'x': x, 'y': y, 'w': w, 'h': h
        })
    
    if not components:
        print("   ⚠️  No components found!")
        return mask
    
    # Sort by area (largest first)
    components.sort(key=lambda c: c['area'], reverse=True)
    
    # Print component info
    total_area = sum(c['area'] for c in components)
    print(f"\n   Component analysis (sorted by area):")
    for i, comp in enumerate(components[:10], 1):  # Show top 10
        percentage = (comp['area'] / total_area) * 100
        print(f"      #{i}: {comp['area']:5.0f}px² ({percentage:5.1f}%) @ ({comp['x']},{comp['y']}) size {comp['w']}×{comp['h']}")
    
    if len(components) > 10:
        print(f"      ... and {len(components) - 10} more")
    
    # Decision: If largest component is >50% of total area, keep only that
    # Otherwise, keep all components above min_area
    largest_area = components[0]['area']
    largest_percentage = (largest_area / total_area) * 100
    
    print(f"\n   Largest component: {largest_area:.0f}px² ({largest_percentage:.1f}% of total)")
    
    result = np.zeros_like(mask)
    
    if largest_percentage > 50:
        # One dominant component - keep only that (it's the racing line)
        print(f"   ✅ Keeping only largest component (dominant)")
        result[labels == components[0]['label']] = 255
        kept_count = 1
    else:
        # Multiple significant components - keep all above min_area
        print(f"   ✅ Keeping all components ≥{min_area}px²")
        kept_count = 0
        for comp in components:
            if comp['area'] >= min_area:
                result[labels == comp['label']] = 255
                kept_count += 1
    
    final_pixels = np.sum(result > 0)
    print(f"   ✅ Kept {kept_count} component(s): {final_pixels} pixels\n")
    
    return result


def extract_racing_line_from_video(video_path: str, 
                                   roi_coords: dict,
                                   num_samples: int = 50,
                                   frequency_threshold: float = 0.6) -> Optional[Tuple]:
    """
    Extract racing line from video with gentle processing.
    
    Returns:
        (final_mask, raw_mask, gentle_cleaned, sample_frame) or None
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
    
    # Step 1: Frequency voting (this works perfectly!)
    raw_mask = extract_racing_line_frequency_voting(map_rois, frequency_threshold)
    
    if raw_mask is None:
        return None
    
    # Step 2: Gentle cleaning (preserve the line!)
    gentle_cleaned = clean_racing_line_gentle(raw_mask)
    
    # Step 3: Remove small artifacts
    final_mask = remove_small_artifacts(gentle_cleaned, min_area=100)
    
    print(f"{'='*70}")
    print(f"✅ EXTRACTION COMPLETE!")
    print(f"{'='*70}\n")
    
    return final_mask, raw_mask, gentle_cleaned, map_rois[0]


def visualize_results(final_mask: np.ndarray,
                     raw_mask: np.ndarray,
                     gentle_cleaned: np.ndarray,
                     original_frame: np.ndarray,
                     output_dir: Path,
                     frequency_threshold: float):
    """
    Create comprehensive visualization comparing all stages.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"📸 Creating visualizations...")
    
    # Save individual masks
    cv2.imwrite(str(output_dir / 'step1_raw_frequency.png'), raw_mask)
    cv2.imwrite(str(output_dir / 'step2_gentle_cleaned.png'), gentle_cleaned)
    cv2.imwrite(str(output_dir / 'step3_final_mask.png'), final_mask)
    
    # Create overlay for each stage
    h, w = original_frame.shape[:2]
    
    # Stage 1: Raw
    overlay1 = original_frame.copy()
    overlay1[raw_mask > 0] = [0, 255, 0]
    
    # Stage 2: Gentle cleaned
    overlay2 = original_frame.copy()
    overlay2[gentle_cleaned > 0] = [0, 255, 0]
    
    # Stage 3: Final (with contours)
    overlay3 = original_frame.copy()
    contours, _ = cv2.findContours(final_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    if contours:
        cv2.drawContours(overlay3, contours, -1, (0, 255, 0), 2)
    
    # Create mega comparison (2×3 grid)
    comparison = np.zeros((h*2, w*3, 3), dtype=np.uint8)
    
    # Row 1: Masks
    comparison[0:h, 0:w] = cv2.cvtColor(raw_mask, cv2.COLOR_GRAY2BGR)
    comparison[0:h, w:w*2] = cv2.cvtColor(gentle_cleaned, cv2.COLOR_GRAY2BGR)
    comparison[0:h, w*2:w*3] = cv2.cvtColor(final_mask, cv2.COLOR_GRAY2BGR)
    
    # Row 2: Overlays
    comparison[h:h*2, 0:w] = overlay1
    comparison[h:h*2, w:w*2] = overlay2
    comparison[h:h*2, w*2:w*3] = overlay3
    
    # Add labels
    font = cv2.FONT_HERSHEY_SIMPLEX
    
    # Row 1 labels
    cv2.putText(comparison, f"1. Raw ({frequency_threshold*100:.0f}% freq)", 
               (10, 30), font, 0.6, (255, 255, 255), 2)
    cv2.putText(comparison, "2. Gentle Clean", 
               (w+10, 30), font, 0.6, (255, 255, 255), 2)
    cv2.putText(comparison, "3. Artifacts Removed", 
               (w*2+10, 30), font, 0.6, (255, 255, 255), 2)
    
    # Row 2 labels
    cv2.putText(comparison, "Overlay", 
               (10, h+30), font, 0.6, (0, 255, 0), 2)
    cv2.putText(comparison, "Overlay", 
               (w+10, h+30), font, 0.6, (0, 255, 0), 2)
    cv2.putText(comparison, "Final Result", 
               (w*2+10, h+30), font, 0.6, (0, 255, 0), 2)
    
    cv2.imwrite(str(output_dir / 'COMPARISON_ALL_STAGES.png'), comparison)
    
    # Simple side-by-side: Raw vs Final
    simple_comparison = np.zeros((h, w*2, 3), dtype=np.uint8)
    simple_comparison[:, 0:w] = overlay1
    simple_comparison[:, w:w*2] = overlay3
    
    cv2.putText(simple_comparison, f"Raw ({frequency_threshold*100:.0f}% freq)", 
               (10, 30), font, 0.7, (255, 255, 255), 2)
    cv2.putText(simple_comparison, "Final (cleaned)", 
               (w+10, 30), font, 0.7, (0, 255, 0), 2)
    
    cv2.imwrite(str(output_dir / 'COMPARISON_BEFORE_AFTER.png'), simple_comparison)
    
    print(f"   ✅ Saved visualizations to {output_dir}/\n")


def main():
    """Test the improved extraction."""
    VIDEO_PATH = './panorama.mp4'
    CONFIG_PATH = 'config/roi_config.yaml'
    
    with open(CONFIG_PATH, 'r') as f:
        roi_config = yaml.safe_load(f)
    
    # Extract with optimal parameters
    result = extract_racing_line_from_video(
        video_path=VIDEO_PATH,
        roi_coords=roi_config['track_map'],
        num_samples=50,
        frequency_threshold=0.6
    )
    
    if result is None:
        print("❌ Extraction failed!")
        return
    
    final_mask, raw_mask, gentle_cleaned, original_frame = result
    
    # Visualize
    output_dir = Path('debug/cleaned_racing_line')
    visualize_results(
        final_mask=final_mask,
        raw_mask=raw_mask,
        gentle_cleaned=gentle_cleaned,
        original_frame=original_frame,
        output_dir=output_dir,
        frequency_threshold=0.6
    )
    
    print(f"{'='*70}")
    print(f"🎉 SUCCESS!")
    print(f"{'='*70}")
    print(f"\n📁 Check these files:")
    print(f"   {output_dir}/COMPARISON_ALL_STAGES.png - Complete pipeline")
    print(f"   {output_dir}/COMPARISON_BEFORE_AFTER.png - Raw vs Final")
    print(f"   {output_dir}/step3_final_mask.png - Clean black & white mask")
    print(f"\n💡 The raw 60% frequency mask is preserved!")
    print(f"   Only gentle cleaning applied to remove small artifacts.\n")


if __name__ == '__main__':
    main()

