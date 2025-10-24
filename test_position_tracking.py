"""
Debug script to test and visualize track position tracking.

Tests:
1. Track path extraction from minimap
2. Red dot detection
3. Position calculation
4. Visual output of detected path and position

Usage:
    python test_position_tracking.py
"""

import cv2
import numpy as np
import yaml
from pathlib import Path
from src.position_tracker import PositionTracker
from src.video_processor import VideoProcessor


def visualize_track_extraction(video_path: str, roi_config: dict, output_dir: str = 'debug/position_tracking'):
    """
    Test and visualize track position tracking.
    
    Creates debug images showing:
    - Extracted white racing line
    - Red dot detection
    - Position calculation
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    print("=" * 60)
    print("Track Position Tracking Test")
    print("=" * 60)
    
    # Initialize components
    processor = VideoProcessor(video_path, roi_config)
    position_tracker = PositionTracker()
    
    if not processor.open_video():
        print("❌ Error: Could not open video file")
        return
    
    video_info = processor.get_video_info()
    print(f"\n📊 Video Info:")
    print(f"   FPS: {video_info['fps']:.2f}")
    print(f"   Frames: {video_info['frame_count']}")
    
    # Check if track_map ROI is configured
    if 'track_map' not in roi_config:
        print("\n❌ Error: 'track_map' ROI not found in config")
        print("   Please add track_map configuration to roi_config.yaml")
        return
    
    # Extract track path from multiple frames
    print(f"\n🗺️  Extracting track path from minimap...")
    # Sample more frames to increase chance of clean frames
    sample_frames = [0, 50, 100, 150, 200, 250, 500, 750, 1000, 1250, 1500]
    map_rois = []
    
    for sample_frame_num in sample_frames:
        if sample_frame_num >= video_info['frame_count']:
            break
        
        # Seek to frame and read
        processor.cap.set(cv2.CAP_PROP_POS_FRAMES, sample_frame_num)
        ret, frame = processor.cap.read()
        
        if ret:
            map_roi = processor.extract_roi(frame, 'track_map')
            map_rois.append(map_roi)
            
            # Save sample frame for inspection
            cv2.imwrite(str(output_path / f'map_sample_frame{sample_frame_num:04d}.png'), map_roi)
    
    print(f"   Sampled {len(map_rois)} frames")
    
    # Extract path
    if not position_tracker.extract_track_path(map_rois):
        print("\n❌ Error: Track path extraction failed")
        return
    
    print(f"   ✅ Path extracted: {len(position_tracker.track_path)} points")
    print(f"   Total path length: {position_tracker.total_path_length:.1f}px")
    
    # Visualize extracted path on first frame
    if map_rois:
        first_map = map_rois[0].copy()
        
        # Draw white racing line points in green
        for px, py in position_tracker.track_path:
            cv2.circle(first_map, (px, py), 1, (0, 255, 0), -1)
        
        cv2.imwrite(str(output_path / 'extracted_path.png'), first_map)
        print(f"   Saved visualization: {output_path / 'extracted_path.png'}")
    
    # Test position tracking on sample frames
    print(f"\n🔍 Testing position tracking on sample frames...")
    
    test_frames = [0, 500, 1000, 1500, 2000, 2500]
    positions = []
    
    for test_frame_num in test_frames:
        if test_frame_num >= video_info['frame_count']:
            break
        
        processor.cap.set(cv2.CAP_PROP_POS_FRAMES, test_frame_num)
        ret, frame = processor.cap.read()
        
        if not ret:
            continue
        
        map_roi = processor.extract_roi(frame, 'track_map')
        
        # Detect red dot
        dot_position = position_tracker.detect_red_dot(map_roi)
        
        if dot_position:
            dot_x, dot_y = dot_position
            
            # Calculate position
            track_position = position_tracker.extract_position(map_roi)
            positions.append(track_position)
            
            # Visualize
            vis_map = map_roi.copy()
            
            # Draw extracted path in green
            for px, py in position_tracker.track_path:
                cv2.circle(vis_map, (px, py), 1, (0, 255, 0), -1)
            
            # Draw red dot in blue (large circle for visibility)
            cv2.circle(vis_map, (dot_x, dot_y), 5, (255, 0, 0), 2)
            
            # Add position text
            cv2.putText(vis_map, f'{track_position:.1f}%', (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
            
            cv2.imwrite(str(output_path / f'position_frame{test_frame_num:04d}.png'), vis_map)
            
            print(f"   Frame {test_frame_num:4d}: Position = {track_position:6.2f}% (dot at {dot_x:3d}, {dot_y:3d})")
        else:
            print(f"   Frame {test_frame_num:4d}: Red dot NOT detected")
    
    # Check if positions are progressing (should increase from 0 to 100)
    if len(positions) >= 2:
        print(f"\n📈 Position progression check:")
        print(f"   First position: {positions[0]:.2f}%")
        print(f"   Last position:  {positions[-1]:.2f}%")
        print(f"   Range: {max(positions) - min(positions):.2f}%")
        
        if max(positions) - min(positions) > 20:
            print(f"   ✅ Positions are progressing (good variation)")
        else:
            print(f"   ⚠️  Warning: Small variation in positions - check if path extraction captured full track")
    
    processor.close()
    
    print(f"\n✅ Test complete! Debug images saved to: {output_path}")
    print(f"\nVisualization files:")
    print(f"   - map_sample_frameXXXX.png: Sampled minimap frames")
    print(f"   - extracted_path.png: White racing line extraction")
    print(f"   - position_frameXXXX.png: Position tracking visualization")


def main():
    """Run track position tracking test."""
    VIDEO_PATH = './panorama.mp4'
    CONFIG_PATH = 'config/roi_config.yaml'
    
    # Check if video exists
    if not Path(VIDEO_PATH).exists():
        print(f"\n❌ Error: Video file not found at '{VIDEO_PATH}'")
        print("\nPlease update VIDEO_PATH in this script to point to your ACC video")
        return
    
    # Load ROI configuration
    with open(CONFIG_PATH, 'r') as f:
        roi_config = yaml.safe_load(f)
    
    # Run test
    visualize_track_extraction(VIDEO_PATH, roi_config)


if __name__ == '__main__':
    main()

