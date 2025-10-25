"""
Test script for updated PositionTrackerV2 with frequency voting.

This script tests the new racing line extraction method and visualizes the results.
"""

import cv2
import numpy as np
import yaml
from pathlib import Path
from src.position_tracker_v2 import PositionTrackerV2


def test_position_tracker_v2():
    """Test the updated PositionTrackerV2 with frequency voting."""
    
    VIDEO_PATH = './panorama.mp4'
    CONFIG_PATH = 'config/roi_config.yaml'
    
    # Load config
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
    print(f"TESTING PositionTrackerV2 with Frequency Voting")
    print(f"{'='*70}")
    print(f"Video: {VIDEO_PATH}")
    print(f"Frames: {video_info['frame_count']} @ {video_info['fps']:.1f} FPS")
    print(f"{'='*70}\n")
    
    # Sample 50 frames for path extraction
    sample_interval = max(1, video_info['frame_count'] // 50)
    sample_frames = list(range(0, video_info['frame_count'], sample_interval))[:50]
    
    print(f"📍 Sampling {len(sample_frames)} frames for path extraction...")
    
    # Extract ROIs
    map_rois = []
    roi_coords = roi_config['track_map']
    x, y, w, h = roi_coords['x'], roi_coords['y'], roi_coords['width'], roi_coords['height']
    
    for i, frame_num in enumerate(sample_frames):
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
        ret, frame = cap.read()
        
        if not ret:
            continue
        
        map_roi = frame[y:y+h, x:x+w]
        map_rois.append(map_roi)
        
        if (i+1) % 10 == 0:
            print(f"   Progress: {i+1}/{len(sample_frames)}")
    
    print(f"✅ Extracted {len(map_rois)} ROIs\n")
    
    # Initialize tracker and extract path
    print(f"{'='*70}")
    print(f"EXTRACTING RACING LINE")
    print(f"{'='*70}\n")
    
    tracker = PositionTrackerV2()
    success = tracker.extract_track_path(map_rois, frequency_threshold=0.6)
    
    if not success:
        print("\n❌ Path extraction failed!")
        cap.release()
        return
    
    # Get debug info
    debug_info = tracker.get_debug_info()
    
    print(f"\n{'='*70}")
    print(f"PATH EXTRACTION RESULTS")
    print(f"{'='*70}")
    print(f"Path extracted: {debug_info['path_extracted']}")
    print(f"Validation passed: {debug_info['validation_passed']}")
    print(f"Path points: {debug_info['path_points']}")
    print(f"Total length: {debug_info['total_length']:.1f}px")
    print(f"Start line index: {debug_info['start_line_index']}")
    print(f"{'='*70}\n")
    
    # Test position tracking on a few frames
    print(f"{'='*70}")
    print(f"TESTING POSITION TRACKING")
    print(f"{'='*70}\n")
    
    test_frames = [0, 500, 1000, 1500, 2000, 2500]
    positions = []
    
    for frame_num in test_frames:
        if frame_num >= video_info['frame_count']:
            break
        
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
        ret, frame = cap.read()
        
        if not ret:
            continue
        
        # Extract map ROI
        map_roi = frame[y:y+h, x:x+w]
        
        # Get position
        position = tracker.extract_position(map_roi)
        positions.append(position)
        
        time_seconds = frame_num / video_info['fps']
        print(f"   Frame {frame_num:5d} (t={time_seconds:6.2f}s): Position = {position:6.2f}%")
    
    cap.release()
    
    # Visualize the extracted path
    print(f"\n{'='*70}")
    print(f"CREATING VISUALIZATION")
    print(f"{'='*70}\n")
    
    output_dir = Path('debug/tracker_v2_test')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create visualization on first frame
    if map_rois:
        original = map_rois[0].copy()
        
        # Draw the extracted path
        path_array = np.array(tracker.track_path)
        
        # Draw path as green line
        for i in range(len(path_array) - 1):
            pt1 = tuple(path_array[i])
            pt2 = tuple(path_array[i + 1])
            cv2.line(original, pt1, pt2, (0, 255, 0), 2)
        
        # Close the loop
        pt1 = tuple(path_array[-1])
        pt2 = tuple(path_array[0])
        cv2.line(original, pt1, pt2, (0, 255, 0), 2)
        
        # Mark start line
        start_point = path_array[tracker.start_line_index]
        cv2.circle(original, tuple(start_point), 5, (0, 0, 255), -1)
        cv2.putText(original, "START", 
                   (start_point[0] + 10, start_point[1]), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
        
        # Add info overlay
        cv2.putText(original, f"Path Points: {len(path_array)}", 
                   (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
        cv2.putText(original, f"Path Length: {tracker.total_path_length:.1f}px", 
                   (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
        
        cv2.imwrite(str(output_dir / 'extracted_path_visualization.png'), original)
        print(f"   ✅ Saved visualization to {output_dir}/extracted_path_visualization.png")
    
    # Summary
    print(f"\n{'='*70}")
    print(f"TEST SUMMARY")
    print(f"{'='*70}")
    print(f"✅ Path extraction: {'SUCCESS' if success else 'FAILED'}")
    print(f"✅ Path points: {debug_info['path_points']}")
    print(f"✅ Position tracking: Tested on {len(positions)} frames")
    print(f"   Position range: {min(positions):.2f}% - {max(positions):.2f}%")
    print(f"✅ Visualization saved")
    print(f"{'='*70}\n")
    
    print(f"🎉 Test complete! The new frequency voting method is working!\n")


if __name__ == '__main__':
    test_position_tracker_v2()




