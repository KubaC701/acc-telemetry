"""
Debug script to visualize position tracking and red dot detection.
"""

import cv2
import numpy as np
import yaml
from pathlib import Path
from src.position_tracker_v2 import PositionTrackerV2
from src.video_processor import VideoProcessor

def load_config(config_path: str = 'config/roi_config.yaml'):
    """Load ROI configuration from YAML file."""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def main():
    VIDEO_PATH = './panorama.mp4'
    CONFIG_PATH = 'config/roi_config.yaml'
    
    print("🔍 Debug: Position Tracking")
    print("=" * 60)
    
    # Load config and initialize
    roi_config = load_config(CONFIG_PATH)
    processor = VideoProcessor(VIDEO_PATH, roi_config)
    tracker = PositionTrackerV2()
    
    if not processor.open_video():
        print("❌ Error: Could not open video")
        return
    
    video_info = processor.get_video_info()
    print(f"\n📊 Video: {video_info['frame_count']} frames, {video_info['fps']:.2f} FPS")
    
    # Extract track path
    print(f"\n🗺️  Extracting track path...")
    sample_frames = [0, 50, 100, 150, 200, 250, 500, 750, 1000, 1250, 1500]
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
    
    if not tracker.extract_track_path(map_rois):
        print("❌ Path extraction failed")
        return
    
    # Set start position at first detected red dot (simulate lap transition)
    # We'll set it on the first debug frame
    tracker.lap_just_started = True
    
    # Debug specific frames around lap transition
    debug_frames = [
        3063,  # Before lap change
        3064,  # Lap change frame
        3065,  # First frame of new lap (should be 0.0%)
        3066,  # Should be ~0%
        3070,  # Should be ~0%
        3071,  # Jumps to 99.92%
        3075,  # Should continue
        3079,  # Drops to 44.49%
    ]
    
    print(f"\n🔍 Debugging {len(debug_frames)} frames...")
    print(f"   Track center: {tracker.track_center}")
    print(f"   Total path pixels: {tracker.total_path_pixels}")
    
    output_dir = Path("debug/position_tracking_v2")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    for frame_num in debug_frames:
        processor.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
        ret, frame = processor.cap.read()
        
        if not ret:
            print(f"\n   ❌ Frame {frame_num}: Could not read")
            continue
        
        map_roi = processor.extract_roi(frame, 'track_map')
        
        # Use extract_position (handles lap start flag)
        position = tracker.extract_position(map_roi)
        
        # Get red dot for visualization
        dot_pos = tracker.detect_red_dot(map_roi)
        
        if dot_pos is None:
            print(f"\n   Frame {frame_num}: ❌ No red dot detected")
            continue
        
        # Calculate angle for debugging
        if tracker.start_position:
            dx = dot_pos[0] - tracker.track_center[0]
            dy = dot_pos[1] - tracker.track_center[1]
            current_angle = np.degrees(np.arctan2(dy, dx))
        else:
            current_angle = 0
        
        print(f"\n   Frame {frame_num}:")
        print(f"      Red dot: ({dot_pos[0]}, {dot_pos[1]})")
        print(f"      Current angle: {current_angle:.1f}°")
        if tracker.start_position:
            print(f"      Start angle: {np.degrees(tracker.start_angle):.1f}°")
        print(f"      Position: {position:.2f}%")
        
        # Draw visualization
        vis = map_roi.copy()
        
        # Draw track center in yellow
        if tracker.track_center:
            cv2.circle(vis, (int(tracker.track_center[0]), int(tracker.track_center[1])), 5, (0, 255, 255), -1)
        
        # Draw start position in green
        if tracker.start_position:
            cv2.circle(vis, tracker.start_position, 4, (0, 255, 0), -1)
            # Draw line from center to start
            cv2.line(vis, (int(tracker.track_center[0]), int(tracker.track_center[1])), 
                    tracker.start_position, (0, 255, 0), 1)
        
        # Draw red dot detection
        cv2.circle(vis, dot_pos, 5, (0, 0, 255), 2)
        
        # Draw line from center to current position (in cyan)
        cv2.line(vis, (int(tracker.track_center[0]), int(tracker.track_center[1])), 
                dot_pos, (255, 255, 0), 1)
        
        # Add text
        cv2.putText(vis, f"Frame {frame_num}", (5, 15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(vis, f"Pos: {position:.1f}%", (5, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        if tracker.start_position:
            cv2.putText(vis, f"Angle: {current_angle:.1f}deg", (5, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
        
        # Save
        output_path = output_dir / f"frame_{frame_num:05d}_pos_{position:.1f}.png"
        cv2.imwrite(str(output_path), vis)
        print(f"      Saved: {output_path}")
    
    processor.close()
    print(f"\n✅ Debug complete! Check {output_dir}/")

if __name__ == '__main__':
    main()

