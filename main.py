"""
ACC Telemetry Extractor - Main entry point
Extracts throttle, brake, and steering telemetry from ACC gameplay videos.
"""

import yaml
from pathlib import Path
from src.video_processor import VideoProcessor
from src.telemetry_extractor import TelemetryExtractor
from src.interactive_visualizer import InteractiveTelemetryVisualizer


def load_config(config_path: str = 'config/roi_config.yaml'):
    """Load ROI configuration from YAML file."""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def main():
    """Main processing pipeline."""
    
    # Configuration
    VIDEO_PATH = './input_video.mp4'  # Place your video here
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
    
    try:
        for frame_num, timestamp, roi_dict in processor.process_frames():
            # Extract telemetry from current frame
            telemetry = extractor.extract_frame_telemetry(roi_dict)
            
            # Store data
            telemetry_data.append({
                'frame': frame_num,
                'time': timestamp,
                'throttle': telemetry['throttle'],
                'brake': telemetry['brake'],
                'steering': telemetry['steering']
            })
            
            # Progress indicator
            progress = int((frame_num / video_info['frame_count']) * 100)
            if progress % 10 == 0 and progress != last_progress:
                print(f"   Progress: {progress}% ({frame_num}/{video_info['frame_count']} frames)")
                last_progress = progress
        
        print(f"   ✅ Processing complete! Extracted {len(telemetry_data)} frames")
        
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
    print(f"   Avg Throttle: {summary['avg_throttle']:.1f}% (max: {summary['max_throttle']:.1f}%)")
    print(f"   Avg Brake: {summary['avg_brake']:.1f}% (max: {summary['max_brake']:.1f}%)")
    print(f"   Avg Steering: {summary['avg_steering_abs']:.2f} (range: {summary['max_steering_left']:.2f} to {summary['max_steering_right']:.2f})")
    
    print("\n" + "=" * 60)
    print("✅ Processing complete!")
    print("=" * 60)


if __name__ == '__main__':
    main()

