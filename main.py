"""
ACC Telemetry Extractor - Main entry point
Extracts throttle, brake, and steering telemetry from ACC gameplay videos.
"""

import yaml
from pathlib import Path
from src.video_processor import VideoProcessor
from src.telemetry_extractor import TelemetryExtractor
from src.lap_detector import LapDetector
from src.interactive_visualizer import InteractiveTelemetryVisualizer


def load_config(config_path: str = 'config/roi_config.yaml'):
    """Load ROI configuration from YAML file."""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def main():
    """Main processing pipeline."""
    
    # Configuration
    VIDEO_PATH = './test-acc.mp4'  # Full race video for testing
    CONFIG_PATH = 'config/roi_config.yaml'
    
    print("=" * 60)
    print("ACC Telemetry Extractor")
    print("=" * 60)
    
    # Check if video exists
    if not Path(VIDEO_PATH).exists():
        print(f"\n❌ Error: Video file not found at '{VIDEO_PATH}'")
        print("\nPlease place your ACC gameplay video in the project root directory")
        print("and name it 'input_video.mp4' (or update VIDEO_PATH in main.py)")
        return
    
    # Load configuration
    print(f"\n📋 Loading ROI configuration from '{CONFIG_PATH}'...")
    roi_config = load_config(CONFIG_PATH)
    
    # Initialize components
    print(f"🎥 Opening video: {VIDEO_PATH}")
    processor = VideoProcessor(VIDEO_PATH, roi_config)
    extractor = TelemetryExtractor()
    # Use template matching for lap numbers (100-500x faster than OCR)
    lap_detector = LapDetector(roi_config, enable_performance_stats=True)
    visualizer = InteractiveTelemetryVisualizer()
    
    if not processor.open_video():
        print("❌ Error: Could not open video file")
        return
    
    # Display video info
    video_info = processor.get_video_info()
    print(f"\n📊 Video Info:")
    print(f"   FPS: {video_info['fps']:.2f}")
    print(f"   Frames: {video_info['frame_count']}")
    print(f"   Duration: {video_info['duration']:.2f} seconds")
    
    # Process video
    print(f"\n⚙️  Processing frames and extracting telemetry...")
    print("   (This may take a few minutes depending on video length)")
    
    telemetry_data = []
    last_progress = -1
    previous_lap = None
    lap_transitions = []  # Track lap transition frames
    completed_lap_times = {}  # Map lap_number -> lap_time for completed laps
    frames_since_transition = 0  # Counter to capture lap time on first frame after transition
    
    try:
        for frame_num, timestamp, roi_dict in processor.process_frames():
            # Extract telemetry from current frame
            telemetry = extractor.extract_frame_telemetry(roi_dict)
            
            # Extract lap number, speed, and gear (using full frame from processor)
            lap_number = lap_detector.extract_lap_number(processor.current_frame)
            speed = lap_detector.extract_speed(processor.current_frame)
            gear = lap_detector.extract_gear(processor.current_frame)
            
            # Detect lap transitions
            if lap_detector.detect_lap_transition(lap_number, previous_lap):
                # Lap transition detected - mark to read lap time on NEXT frame
                frames_since_transition = 1  # Will trigger lap time read on next iteration
                
                lap_transitions.append({
                    'frame': frame_num,
                    'time': timestamp,
                    'from_lap': previous_lap,
                    'to_lap': lap_number,
                    'completed_lap_time': None  # Will be filled on next frame
                })
            elif frames_since_transition == 1:
                # This is the FIRST frame after lap transition - read LAST lap time
                completed_lap_time = lap_detector.extract_last_lap_time(processor.current_frame)
                
                if completed_lap_time and previous_lap is not None:
                    completed_lap_times[previous_lap] = completed_lap_time
                    
                    # Update the last transition record with the lap time
                    if lap_transitions:
                        lap_transitions[-1]['completed_lap_time'] = completed_lap_time
                
                frames_since_transition = 0  # Reset counter
            
            # Store data (lap_time will be filled in post-processing)
            telemetry_data.append({
                'frame': frame_num,
                'time': timestamp,
                'lap_number': lap_number,
                'lap_time': None,  # Will be filled from completed_lap_times
                'speed': speed,
                'gear': gear,
                'throttle': telemetry['throttle'],
                'brake': telemetry['brake'],
                'steering': telemetry['steering']
            })
            
            previous_lap = lap_number
            
            # Progress indicator
            progress = int((frame_num / video_info['frame_count']) * 100)
            if progress % 10 == 0 and progress != last_progress:
                print(f"   Progress: {progress}% ({frame_num}/{video_info['frame_count']} frames)")
                last_progress = progress
        
        print(f"   ✅ Processing complete! Extracted {len(telemetry_data)} frames")
        
        # Display lap transition info
        if lap_transitions:
            print(f"\n🏁 Detected {len(lap_transitions)} lap transitions:")
            for transition in lap_transitions[:5]:  # Show first 5
                time_str = f" (time: {transition['completed_lap_time']})" if transition['completed_lap_time'] else ""
                print(f"   Lap {transition['from_lap']} → {transition['to_lap']} at {transition['time']:.1f}s{time_str}")
            if len(lap_transitions) > 5:
                print(f"   ... and {len(lap_transitions) - 5} more")
        
        # Add lap times to telemetry data (map completed lap times to their respective lap entries)
        for entry in telemetry_data:
            lap_num = entry['lap_number']
            entry['lap_time'] = completed_lap_times.get(lap_num, None)
        
        # Display lap detection performance statistics
        perf_stats = lap_detector.get_performance_stats()
        if 'error' not in perf_stats:
            print(f"\n⚡ Lap Detection Performance:")
            print(f"   Method: {perf_stats['method']}")
            print(f"   Total frames: {perf_stats['total_frames']}")
            print(f"   Recognition calls: {perf_stats['recognition_calls']}")
            print(f"   Avg time per frame: {perf_stats['avg_time_per_frame_ms']:.1f}ms")
            print(f"   Speedup vs OCR: {perf_stats['estimated_speedup_vs_ocr']:.0f}x faster")
        
    finally:
        processor.close()
    
    # Create DataFrame
    print(f"\n📈 Generating outputs...")
    df = visualizer.create_dataframe(telemetry_data)
    
    # Export CSV
    csv_path = visualizer.export_csv(df)
    print(f"   ✅ CSV saved: {csv_path}")
    
    # Generate interactive HTML graph
    graph_path = visualizer.plot_telemetry(df)
    print(f"   ✅ Interactive graph saved: {graph_path}")
    print(f"      💡 Open this HTML file in your browser for interactive zoom/pan/hover!")
    
    # Display summary
    summary = visualizer.generate_summary(df)
    print(f"\n📊 Telemetry Summary:")
    print(f"   Duration: {summary['duration']:.2f} seconds")
    print(f"   Total frames: {summary['total_frames']}")
    print(f"   Avg Speed: {summary['avg_speed']:.1f} km/h (max: {summary['max_speed']:.1f} km/h)")
    print(f"   Avg Throttle: {summary['avg_throttle']:.1f}% (max: {summary['max_throttle']:.1f}%)")
    print(f"   Avg Brake: {summary['avg_brake']:.1f}% (max: {summary['max_brake']:.1f}%)")
    print(f"   Avg Steering: {summary['avg_steering_abs']:.2f} (range: {summary['max_steering_left']:.2f} to {summary['max_steering_right']:.2f})")
    
    # Display lap summary if available
    if summary.get('total_laps', 0) > 0:
        print(f"\n🏁 Lap Summary:")
        print(f"   Total laps detected: {summary['total_laps']}")
        if summary.get('laps'):
            print(f"   Lap details:")
            for lap_info in summary['laps'][:5]:  # Show first 5 laps
                lap_num = lap_info['lap_number']
                duration = lap_info['duration']
                print(f"      Lap {lap_num}: {duration:.2f}s")
            if len(summary['laps']) > 5:
                print(f"      ... and {len(summary['laps']) - 5} more laps")
    
    print("\n" + "=" * 60)
    print("✅ Processing complete!")
    print("=" * 60)


if __name__ == '__main__':
    main()

