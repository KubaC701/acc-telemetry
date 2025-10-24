"""
Comprehensive test script for improved track position tracking.

Addresses the issues identified:
1. ROI coordinate validation
2. Path extraction validation  
3. Start line detection
4. Position calculation accuracy
5. Full video processing test

Usage:
    python test_position_tracking_v2.py
"""

import cv2
import numpy as np
import yaml
from pathlib import Path
from src.position_tracker_v2 import PositionTrackerV2
from src.video_processor import VideoProcessor


def test_roi_coordinates(video_path: str, roi_config: dict):
    """
    Test if the ROI coordinates are capturing the correct region.
    """
    print("=" * 60)
    print("ROI COORDINATE VALIDATION")
    print("=" * 60)
    
    processor = VideoProcessor(video_path, roi_config)
    
    if not processor.open_video():
        print("❌ Error: Could not open video file")
        return False
    
    video_info = processor.get_video_info()
    print(f"📊 Video: {video_info['frame_count']} frames, {video_info['fps']:.2f} FPS")
    
    # Test ROI on multiple frames
    test_frames = [0, 1000, 5000, 10000]
    output_dir = Path('debug/roi_validation')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    for frame_num in test_frames:
        if frame_num >= video_info['frame_count']:
            continue
        
        processor.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
        ret, frame = processor.cap.read()
        
        if not ret:
            continue
        
        # Extract track_map ROI
        map_roi = processor.extract_roi(frame, 'track_map')
        
        # Save for inspection
        cv2.imwrite(str(output_dir / f'frame{frame_num:05d}_track_map.png'), map_roi)
        
        # Draw ROI rectangle on full frame
        roi_coords = roi_config['track_map']
        x, y, w, h = roi_coords['x'], roi_coords['y'], roi_coords['width'], roi_coords['height']
        
        frame_with_roi = frame.copy()
        cv2.rectangle(frame_with_roi, (x, y), (x+w, y+h), (0, 255, 0), 2)
        cv2.putText(frame_with_roi, f'TRACK_MAP ROI - Frame {frame_num}', (x, y-10), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        cv2.imwrite(str(output_dir / f'frame{frame_num:05d}_full_with_roi.png'), frame_with_roi)
        
        print(f"   ✅ Frame {frame_num:5d}: Saved ROI and full frame with rectangle")
    
    processor.close()
    
    print(f"\n📁 ROI validation images saved to: {output_dir}")
    print(f"\n🔍 MANUAL INSPECTION REQUIRED:")
    print(f"   1. Check frameXXXXX_full_with_roi.png - is green rectangle around minimap?")
    print(f"   2. Check frameXXXXX_track_map.png - does it show minimap with white racing line?")
    print(f"   3. Is there a red dot visible in the minimap?")
    print(f"   4. If NO to any of the above, the ROI coordinates are wrong!")
    
    return True


def test_path_extraction(video_path: str, roi_config: dict):
    """
    Test track path extraction with improved validation.
    """
    print("\n" + "=" * 60)
    print("TRACK PATH EXTRACTION TEST")
    print("=" * 60)
    
    processor = VideoProcessor(video_path, roi_config)
    position_tracker = PositionTrackerV2()
    
    if not processor.open_video():
        print("❌ Error: Could not open video file")
        return False
    
    video_info = processor.get_video_info()
    
    # Sample more frames for better path extraction
    sample_frames = [0, 200, 500, 1000, 2000, 3000, 4000, 5000]
    map_rois = []
    
    print(f"🗺️  Sampling {len(sample_frames)} frames for path extraction...")
    
    for sample_frame_num in sample_frames:
        if sample_frame_num >= video_info['frame_count']:
            break
        
        processor.cap.set(cv2.CAP_PROP_POS_FRAMES, sample_frame_num)
        ret, frame = processor.cap.read()
        
        if ret:
            map_roi = processor.extract_roi(frame, 'track_map')
            map_rois.append(map_roi)
            print(f"   ✅ Frame {sample_frame_num:4d}: {map_roi.shape[1]}x{map_roi.shape[0]}")
        else:
            print(f"   ❌ Frame {sample_frame_num:4d}: Failed to read")
    
    # Reset video to start
    processor.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
    
    # Extract path
    if not position_tracker.extract_track_path(map_rois):
        print("❌ Path extraction failed!")
        return False
    
    # Get debug info
    debug_info = position_tracker.get_debug_info()
    print(f"\n📊 Path Extraction Results:")
    print(f"   Path points: {debug_info['path_points']}")
    print(f"   Total length: {debug_info['total_length']:.1f}px")
    print(f"   Start line index: {debug_info['start_line_index']}")
    print(f"   Validation passed: {debug_info['validation_passed']}")
    
    # Create visualization
    if map_rois:
        output_dir = Path('debug/path_extraction')
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Visualize extracted path on first frame
        first_map = map_rois[0].copy()
        
        # Draw path points
        for i, (px, py) in enumerate(position_tracker.track_path):
            color = (0, 255, 0) if i == position_tracker.start_line_index else (255, 255, 255)
            cv2.circle(first_map, (px, py), 1, color, -1)
        
        # Mark start line with a larger circle
        if position_tracker.start_line_index < len(position_tracker.track_path):
            start_x, start_y = position_tracker.track_path[position_tracker.start_line_index]
            cv2.circle(first_map, (start_x, start_y), 5, (0, 0, 255), 2)
            cv2.putText(first_map, 'START', (start_x+10, start_y), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
        
        cv2.imwrite(str(output_dir / 'extracted_path_v2.png'), first_map)
        print(f"   📁 Visualization saved: {output_dir / 'extracted_path_v2.png'}")
        print(f"      - White dots: Racing line points")
        print(f"      - Green dot: Start line")
        print(f"      - Red circle: Start line marker")
    
    processor.close()
    return True


def test_position_tracking(video_path: str, roi_config: dict):
    """
    Test position tracking on sample frames.
    """
    print("\n" + "=" * 60)
    print("POSITION TRACKING TEST")
    print("=" * 60)
    
    processor = VideoProcessor(video_path, roi_config)
    position_tracker = PositionTrackerV2()
    
    if not processor.open_video():
        print("❌ Error: Could not open video file")
        return False
    
    video_info = processor.get_video_info()
    
    # First extract path
    sample_frames = [0, 1000, 2000, 3000, 4000, 5000]
    map_rois = []
    
    for sample_frame_num in sample_frames:
        if sample_frame_num >= video_info['frame_count']:
            break
        
        processor.cap.set(cv2.CAP_PROP_POS_FRAMES, sample_frame_num)
        ret, frame = processor.cap.read()
        
        if ret:
            map_roi = processor.extract_roi(frame, 'track_map')
            map_rois.append(map_roi)
    
    processor.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
    
    if not position_tracker.extract_track_path(map_rois):
        print("❌ Path extraction failed - cannot test position tracking")
        return False
    
    # Test position tracking on more frames
    test_frames = [0, 1000, 2000, 3000, 4000, 5000, 6000, 7000, 8000, 9000, 10000]
    positions = []
    
    print(f"🔍 Testing position tracking on {len(test_frames)} frames...")
    
    for frame_num in test_frames:
        if frame_num >= video_info['frame_count']:
            break
        
        processor.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
        ret, frame = processor.cap.read()
        
        if not ret:
            continue
        
        map_roi = processor.extract_roi(frame, 'track_map')
        
        # Detect red dot
        dot_position = position_tracker.detect_red_dot(map_roi)
        
        if dot_position:
            dot_x, dot_y = dot_position
            track_position = position_tracker.extract_position(map_roi)
            positions.append(track_position)
            
            print(f"   Frame {frame_num:5d}: Position = {track_position:6.2f}% (dot at {dot_x:3d}, {dot_y:3d})")
        else:
            print(f"   Frame {frame_num:5d}: Red dot NOT detected")
    
    # Analyze position progression
    if len(positions) >= 2:
        print(f"\n📈 Position Analysis:")
        print(f"   First position: {positions[0]:.2f}%")
        print(f"   Last position:  {positions[-1]:.2f}%")
        print(f"   Min position:  {min(positions):.2f}%")
        print(f"   Max position:  {max(positions):.2f}%")
        print(f"   Range: {max(positions) - min(positions):.2f}%")
        
        # Check for reasonable progression
        if max(positions) - min(positions) > 30:
            print(f"   ✅ Good position variation detected")
        else:
            print(f"   ⚠️  Warning: Small position variation - check ROI coordinates")
    
    processor.close()
    return True


def test_full_video_processing(video_path: str, roi_config: dict, max_frames: int = 1000):
    """
    Test position tracking on a larger sample of the video.
    
    Args:
        max_frames: Maximum number of frames to process (for testing)
    """
    print("\n" + "=" * 60)
    print(f"FULL VIDEO PROCESSING TEST (max {max_frames} frames)")
    print("=" * 60)
    
    processor = VideoProcessor(video_path, roi_config)
    position_tracker = PositionTrackerV2()
    
    if not processor.open_video():
        print("❌ Error: Could not open video file")
        return False
    
    video_info = processor.get_video_info()
    print(f"📊 Video: {video_info['frame_count']} frames, {video_info['fps']:.2f} FPS")
    
    # Extract path first
    sample_frames = [0, 1000, 2000, 3000, 4000, 5000]
    map_rois = []
    
    for sample_frame_num in sample_frames:
        if sample_frame_num >= video_info['frame_count']:
            break
        
        processor.cap.set(cv2.CAP_PROP_POS_FRAMES, sample_frame_num)
        ret, frame = processor.cap.read()
        
        if ret:
            map_roi = processor.extract_roi(frame, 'track_map')
            map_rois.append(map_roi)
    
    processor.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
    
    if not position_tracker.extract_track_path(map_rois):
        print("❌ Path extraction failed")
        return False
    
    # Process frames
    positions = []
    red_dot_detections = 0
    frame_count = 0
    
    print(f"🔄 Processing frames...")
    
    for frame_num, timestamp, roi_dict in processor.process_frames():
        if frame_count >= max_frames:
            break
        
        if 'track_map' in roi_dict:
            map_roi = roi_dict['track_map']
            
            # Detect red dot
            dot_position = position_tracker.detect_red_dot(map_roi)
            
            if dot_position:
                red_dot_detections += 1
                track_position = position_tracker.extract_position(map_roi)
                positions.append(track_position)
                
                if frame_count % 100 == 0:  # Print every 100 frames
                    print(f"   Frame {frame_num:5d}: Position = {track_position:6.2f}%")
        
        frame_count += 1
    
    processor.close()
    
    # Analyze results
    print(f"\n📊 Full Video Processing Results:")
    print(f"   Frames processed: {frame_count}")
    print(f"   Red dot detections: {red_dot_detections}")
    print(f"   Detection rate: {(red_dot_detections/frame_count)*100:.1f}%")
    
    if positions:
        print(f"   Position range: {min(positions):.2f}% - {max(positions):.2f}%")
        print(f"   Position variation: {max(positions) - min(positions):.2f}%")
        
        # Check for lap progression
        if max(positions) - min(positions) > 50:
            print(f"   ✅ Good lap progression detected")
        else:
            print(f"   ⚠️  Warning: Limited position variation")
    
    return True


def main():
    """Run comprehensive position tracking tests."""
    VIDEO_PATH = './panorama.mp4'
    CONFIG_PATH = 'config/roi_config.yaml'
    
    # Check if video exists
    if not Path(VIDEO_PATH).exists():
        print(f"❌ Error: Video file not found at '{VIDEO_PATH}'")
        return
    
    # Load configuration
    with open(CONFIG_PATH, 'r') as f:
        roi_config = yaml.safe_load(f)
    
    print("🚀 COMPREHENSIVE POSITION TRACKING TEST")
    print("=" * 60)
    
    # Test 1: ROI Coordinate Validation
    if not test_roi_coordinates(VIDEO_PATH, roi_config):
        print("❌ ROI validation failed - fix coordinates first!")
        return
    
    # Test 2: Path Extraction
    if not test_path_extraction(VIDEO_PATH, roi_config):
        print("❌ Path extraction failed - check minimap visibility!")
        return
    
    # Test 3: Position Tracking
    if not test_position_tracking(VIDEO_PATH, roi_config):
        print("❌ Position tracking failed - check red dot detection!")
        return
    
    # Test 4: Full Video Processing (limited sample)
    if not test_full_video_processing(VIDEO_PATH, roi_config, max_frames=1000):
        print("❌ Full video processing failed!")
        return
    
    print("\n" + "=" * 60)
    print("✅ ALL TESTS COMPLETED!")
    print("=" * 60)
    print("\n📁 Check debug images in:")
    print("   - debug/roi_validation/")
    print("   - debug/path_extraction/")
    print("\n🔍 If any test failed, check the debug images and:")
    print("   1. Verify ROI coordinates capture the minimap correctly")
    print("   2. Ensure minimap shows white racing line and red dot")
    print("   3. Check that position values progress 0→100% during laps")


if __name__ == '__main__':
    main()
