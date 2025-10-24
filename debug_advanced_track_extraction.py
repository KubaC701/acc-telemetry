"""
Advanced Multi-Frame Track Extraction

This script implements sophisticated techniques to extract the cleanest possible
racing line by exploiting the fact that the track is CONSTANT across frames.

Techniques used:
1. Temporal Median - Statistical filtering across frames
2. Temporal Standard Deviation - Detect stable vs. variable pixels
3. Weighted Confidence Voting - Use pixel brightness confidence
4. Morphological Skeleton - Extract centerline of path
5. Multi-method comparison - Visual comparison of all techniques

Author: ACC Telemetry Extractor
"""

import cv2
import numpy as np
import yaml
from pathlib import Path


def extract_with_temporal_median(masks: list) -> np.ndarray:
    """
    Method 1: Temporal Median
    
    The racing line appears white in ALL frames, while background and red dot vary.
    Taking the median value across frames will preserve constant features and 
    eliminate variable ones.
    
    Args:
        masks: List of binary masks from different frames
    
    Returns:
        Combined mask using temporal median
    """
    # Stack all masks into 3D array [height, width, num_frames]
    mask_stack = np.stack(masks, axis=2).astype(np.float32)
    
    # Calculate median value per pixel across all frames
    # If a pixel is white in >50% of frames, median will be high
    median_mask = np.median(mask_stack, axis=2)
    
    # Threshold the median (can be lower than 255 if some frames are missing)
    threshold = 200  # Generous threshold for median
    result = (median_mask > threshold).astype(np.uint8) * 255
    
    return result


def extract_with_temporal_variance(masks: list) -> np.ndarray:
    """
    Method 2: Temporal Variance (Low variance = stable = racing line)
    
    Racing line pixels have LOW variance (always white).
    Background pixels have HIGH variance (light/dark changes).
    Red dot pixels have HIGH variance (dot moves around).
    
    This inverts the typical approach: we want LOW variance pixels!
    
    Args:
        masks: List of binary masks from different frames
    
    Returns:
        Combined mask highlighting low-variance (stable) pixels
    """
    # Stack masks
    mask_stack = np.stack(masks, axis=2).astype(np.float32)
    
    # Calculate mean and variance per pixel
    mean_mask = np.mean(mask_stack, axis=2)
    variance_mask = np.var(mask_stack, axis=2)
    
    # Racing line: high mean (often white) + low variance (stable)
    # Normalize variance to 0-255 range
    if np.max(variance_mask) > 0:
        variance_normalized = (variance_mask / np.max(variance_mask)) * 255
    else:
        variance_normalized = variance_mask
    
    # Invert variance: low variance = high score
    stability_score = 255 - variance_normalized
    
    # Combine: pixel must have high mean AND high stability
    combined = (mean_mask * 0.5 + stability_score * 0.5).astype(np.uint8)
    
    # Threshold
    _, result = cv2.threshold(combined, 200, 255, cv2.THRESH_BINARY)
    
    return result


def extract_with_weighted_confidence(map_rois: list) -> np.ndarray:
    """
    Method 3: Weighted Confidence Voting
    
    Instead of binary masks, use the actual pixel brightness values.
    Brighter pixels get more weight in the voting process.
    
    Args:
        map_rois: List of BGR map ROI images
    
    Returns:
        Combined mask using weighted confidence
    """
    if not map_rois:
        return None
    
    # Convert each ROI to grayscale and accumulate weighted sum
    height, width = map_rois[0].shape[:2]
    weighted_sum = np.zeros((height, width), dtype=np.float32)
    
    for map_roi in map_rois:
        # Convert to grayscale
        gray = cv2.cvtColor(map_roi, cv2.COLOR_BGR2GRAY)
        
        # Normalize to 0-1 range (this is the "confidence")
        normalized = gray.astype(np.float32) / 255.0
        
        # Add to weighted sum (brighter = more weight)
        weighted_sum += normalized
    
    # Average across all frames
    weighted_avg = weighted_sum / len(map_rois)
    
    # Convert back to 0-255
    weighted_avg_8bit = (weighted_avg * 255).astype(np.uint8)
    
    # Threshold (racing line should have high average brightness)
    _, result = cv2.threshold(weighted_avg_8bit, 200, 255, cv2.THRESH_BINARY)
    
    return result


def extract_with_maximum_intensity(map_rois: list) -> np.ndarray:
    """
    Method 4: Maximum Intensity Projection
    
    For each pixel, take the MAXIMUM value across all frames.
    This assumes the racing line is white in all frames, so max will be 255.
    Background varies, so max might still be high if it's ever bright.
    
    Combine with variance filtering for best results.
    
    Args:
        map_rois: List of BGR map ROI images
    
    Returns:
        Combined mask using maximum intensity
    """
    if not map_rois:
        return None
    
    # Convert all to grayscale
    gray_stack = []
    for map_roi in map_rois:
        gray = cv2.cvtColor(map_roi, cv2.COLOR_BGR2GRAY)
        gray_stack.append(gray)
    
    # Stack and get maximum
    gray_array = np.stack(gray_stack, axis=2)
    max_intensity = np.max(gray_array, axis=2).astype(np.uint8)
    
    # Threshold
    _, result = cv2.threshold(max_intensity, 220, 255, cv2.THRESH_BINARY)
    
    return result


def extract_skeleton(mask: np.ndarray) -> np.ndarray:
    """
    Method 5: Morphological Skeleton
    
    After extracting the racing line (which may have variable thickness),
    reduce it to a 1-pixel wide centerline. This removes artifacts from
    thickness variations.
    
    Args:
        mask: Binary mask of racing line
    
    Returns:
        Skeleton (centerline) of the racing line
    """
    # Zhang-Suen thinning algorithm
    skeleton = np.zeros_like(mask)
    element = cv2.getStructuringElement(cv2.MORPH_CROSS, (3, 3))
    
    done = False
    temp = mask.copy()
    
    while not done:
        eroded = cv2.erode(temp, element)
        opened = cv2.morphologyEx(eroded, cv2.MORPH_OPEN, element)
        subset = temp - opened
        skeleton = cv2.bitwise_or(skeleton, subset)
        temp = eroded.copy()
        
        done = (cv2.countNonZero(temp) == 0)
    
    return skeleton


def clean_and_filter_contours(mask: np.ndarray, min_area: int = 100) -> np.ndarray:
    """
    Clean mask by removing small artifacts and keeping only the largest contour.
    
    Args:
        mask: Binary mask
        min_area: Minimum contour area to keep
    
    Returns:
        Cleaned mask with only racing line contour
    """
    # Morphological cleaning
    kernel = np.ones((3, 3), np.uint8)
    cleaned = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
    cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_OPEN, kernel, iterations=1)
    
    # Find contours
    contours, _ = cv2.findContours(cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    
    if not contours:
        return cleaned
    
    # Keep only contours above minimum area
    valid_contours = [c for c in contours if cv2.contourArea(c) >= min_area]
    
    if not valid_contours:
        return cleaned
    
    # Get the largest contour (should be the racing line)
    largest_contour = max(valid_contours, key=cv2.contourArea)
    
    # Create new mask with only the largest contour
    result = np.zeros_like(mask)
    cv2.drawContours(result, [largest_contour], -1, 255, -1)
    
    return result


def debug_advanced_extraction(video_path: str, roi_config: dict):
    """
    Main debug function comparing all extraction methods.
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
    
    # Sample MORE frames for better statistics (every 50 frames for first 1000)
    sample_frames = list(range(0, min(1000, video_info['frame_count']), 50))
    
    # Create output directory
    output_dir = Path('debug/advanced_track_extraction')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("=" * 70)
    print("ADVANCED MULTI-FRAME TRACK EXTRACTION")
    print("=" * 70)
    print(f"Sampling {len(sample_frames)} frames for analysis...")
    print(f"Video: {video_path}")
    print(f"Total frames: {video_info['frame_count']}, FPS: {video_info['fps']:.1f}")
    print("=" * 70)
    
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
        
        # Convert to grayscale and threshold for basic mask
        gray = cv2.cvtColor(map_roi, cv2.COLOR_BGR2GRAY)
        _, binary_mask = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
        
        individual_masks.append(binary_mask)
        
        # Save sample frames for reference
        if i < 6:
            cv2.imwrite(str(output_dir / f'sample_frame{i:02d}.png'), map_roi)
        
        if i % 5 == 0:
            print(f"   Processed frame {frame_num:4d} ({i+1}/{len(sample_frames)})")
    
    cap.release()
    
    if not individual_masks or not map_rois:
        print("❌ No masks extracted")
        return
    
    print(f"\n✅ Extracted {len(individual_masks)} frames\n")
    print("=" * 70)
    print("APPLYING EXTRACTION METHODS")
    print("=" * 70)
    
    # Dictionary to store all results
    results = {}
    
    # Method 1: Temporal Median
    print("\n1️⃣  TEMPORAL MEDIAN (constant features preserved)")
    median_mask = extract_with_temporal_median(individual_masks)
    median_clean = clean_and_filter_contours(median_mask)
    results['median'] = median_clean
    cv2.imwrite(str(output_dir / 'method1_temporal_median.png'), median_clean)
    print(f"   ✅ White pixels: {np.sum(median_clean > 0)}")
    
    # Method 2: Temporal Variance
    print("\n2️⃣  TEMPORAL VARIANCE (stable pixels highlighted)")
    variance_mask = extract_with_temporal_variance(individual_masks)
    variance_clean = clean_and_filter_contours(variance_mask)
    results['variance'] = variance_clean
    cv2.imwrite(str(output_dir / 'method2_temporal_variance.png'), variance_clean)
    print(f"   ✅ White pixels: {np.sum(variance_clean > 0)}")
    
    # Method 3: Weighted Confidence
    print("\n3️⃣  WEIGHTED CONFIDENCE (brightness-weighted voting)")
    confidence_mask = extract_with_weighted_confidence(map_rois)
    confidence_clean = clean_and_filter_contours(confidence_mask)
    results['confidence'] = confidence_clean
    cv2.imwrite(str(output_dir / 'method3_weighted_confidence.png'), confidence_clean)
    print(f"   ✅ White pixels: {np.sum(confidence_clean > 0)}")
    
    # Method 4: Maximum Intensity
    print("\n4️⃣  MAXIMUM INTENSITY (brightest across all frames)")
    max_intensity_mask = extract_with_maximum_intensity(map_rois)
    max_intensity_clean = clean_and_filter_contours(max_intensity_mask)
    results['max_intensity'] = max_intensity_clean
    cv2.imwrite(str(output_dir / 'method4_maximum_intensity.png'), max_intensity_clean)
    print(f"   ✅ White pixels: {np.sum(max_intensity_clean > 0)}")
    
    # Method 5: HYBRID (combine best methods)
    print("\n5️⃣  HYBRID (median + variance combined)")
    # Combine median and variance using AND operation (must pass both tests)
    hybrid_mask = cv2.bitwise_and(median_clean, variance_clean)
    hybrid_clean = clean_and_filter_contours(hybrid_mask)
    results['hybrid'] = hybrid_clean
    cv2.imwrite(str(output_dir / 'method5_hybrid.png'), hybrid_clean)
    print(f"   ✅ White pixels: {np.sum(hybrid_clean > 0)}")
    
    # Method 6: CONSENSUS (pixel must pass at least 3 out of 4 methods)
    print("\n6️⃣  CONSENSUS (pass 3/4 methods)")
    vote_stack = np.stack([
        median_clean > 0,
        variance_clean > 0,
        confidence_clean > 0,
        max_intensity_clean > 0
    ], axis=2).astype(np.uint8)
    
    vote_count = np.sum(vote_stack, axis=2)
    consensus_mask = (vote_count >= 3).astype(np.uint8) * 255
    consensus_clean = clean_and_filter_contours(consensus_mask)
    results['consensus'] = consensus_clean
    cv2.imwrite(str(output_dir / 'method6_consensus.png'), consensus_clean)
    print(f"   ✅ White pixels: {np.sum(consensus_clean > 0)}")
    
    print("\n" + "=" * 70)
    print("CONTOUR ANALYSIS")
    print("=" * 70)
    
    # Analyze contours for each method
    method_names = ['median', 'variance', 'confidence', 'max_intensity', 'hybrid', 'consensus']
    method_labels = [
        'Temporal Median',
        'Temporal Variance',
        'Weighted Confidence',
        'Maximum Intensity',
        'Hybrid (Median+Variance)',
        'Consensus (3/4 vote)'
    ]
    
    contour_stats = []
    
    for name, label in zip(method_names, method_labels):
        mask = results[name]
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        
        if contours:
            largest = max(contours, key=cv2.contourArea)
            area = cv2.contourArea(largest)
            perimeter = cv2.arcLength(largest, True)
            num_points = len(largest)
            
            # Calculate smoothness (lower is smoother)
            hull = cv2.convexHull(largest)
            hull_area = cv2.contourArea(hull)
            solidity = area / hull_area if hull_area > 0 else 0
            
            stat = {
                'name': name,
                'label': label,
                'contour_count': len(contours),
                'area': area,
                'perimeter': perimeter,
                'num_points': num_points,
                'solidity': solidity
            }
            contour_stats.append(stat)
            
            print(f"\n{label}:")
            print(f"   Contours: {len(contours)}")
            print(f"   Largest area: {area:.1f}px²")
            print(f"   Perimeter: {perimeter:.1f}px")
            print(f"   Points: {num_points}")
            print(f"   Solidity: {solidity:.3f} (1.0 = perfect, lower = more complex)")
            
            # Visualize the largest contour
            if map_rois:
                vis = map_rois[0].copy()
                cv2.drawContours(vis, [largest], -1, (0, 255, 0), 2)
                cv2.imwrite(str(output_dir / f'{name}_contour_visualization.png'), vis)
    
    print("\n" + "=" * 70)
    print("RECOMMENDATIONS")
    print("=" * 70)
    
    # Recommend best method
    if contour_stats:
        # Prefer high solidity (smooth contour) and reasonable area
        best = max(contour_stats, key=lambda x: x['solidity'])
        print(f"\n🏆 RECOMMENDED METHOD: {best['label']}")
        print(f"   Reason: Highest solidity ({best['solidity']:.3f}) = smoothest contour")
        print(f"   Area: {best['area']:.1f}px²")
        print(f"   Points: {best['num_points']}")
    
    print(f"\n✅ Analysis complete! Results saved to {output_dir}/")
    print("\n📁 Files to examine:")
    print(f"   method1_temporal_median.png - Best for constant features")
    print(f"   method2_temporal_variance.png - Best for stable pixels")
    print(f"   method3_weighted_confidence.png - Best for brightness-based")
    print(f"   method5_hybrid.png - Conservative (AND of best methods)")
    print(f"   method6_consensus.png - Democratic (majority vote)")
    print(f"   *_contour_visualization.png - Visual comparison on original frame")


def main():
    VIDEO_PATH = './panorama.mp4'
    CONFIG_PATH = 'config/roi_config.yaml'
    
    with open(CONFIG_PATH, 'r') as f:
        roi_config = yaml.safe_load(f)
    
    debug_advanced_extraction(VIDEO_PATH, roi_config)


if __name__ == '__main__':
    main()

