"""
ACC Telemetry Extractor - Main entry point
Extracts throttle, brake, and steering telemetry from ACC gameplay videos.
"""

import yaml
import time
from pathlib import Path
from src.video_processor import VideoProcessor
from src.telemetry_extractor import TelemetryExtractor
from src.lap_detector import LapDetector
from src.interactive_visualizer import InteractiveTelemetryVisualizer


class PerformanceTracker:
    """Tracks timing statistics for each processing step."""
    
    def __init__(self):
        self.timings = {
            'frame_processing': [],
            'telemetry_extraction': [],
            'lap_number_detection': [],
            'speed_extraction': [],
            'gear_extraction': [],
            'lap_transition_detection': [],
            'lap_time_extraction': [],
            'data_storage': []
        }
        self.total_frames = 0
    
    def record(self, step: str, duration: float):
        """Record timing for a specific step (in milliseconds)."""
        if step in self.timings:
            self.timings[step].append(duration * 1000)  # Convert to ms
    
    def print_summary(self):
        """Print detailed performance summary."""
        print(f"\n⏱️  Performance Breakdown:")
        print(f"   {'Operation':<30} {'Total (s)':<12} {'Avg (ms)':<12} {'Min (ms)':<12} {'Max (ms)':<12} {'% of Total':<12}")
        print(f"   {'-'*100}")
        
        total_time = sum(sum(times) for times in self.timings.values())
        
        for step, times in self.timings.items():
            if times:
                total_s = sum(times) / 1000
                avg_ms = sum(times) / len(times)
                min_ms = min(times)
                max_ms = max(times)
                percentage = (sum(times) / total_time) * 100 if total_time > 0 else 0
                
                # Format step name (remove underscores, capitalize)
                step_name = step.replace('_', ' ').title()
                
                print(f"   {step_name:<30} {total_s:<12.2f} {avg_ms:<12.2f} {min_ms:<12.2f} {max_ms:<12.2f} {percentage:<12.1f}%")
        
        print(f"   {'-'*100}")
        print(f"   {'TOTAL':<30} {total_time/1000:<12.2f}")
        print(f"\n   Per-frame average: {(total_time/len(self.timings['frame_processing']) if self.timings['frame_processing'] else 0):.2f}ms")
        print(f"   Frames processed: {self.total_frames}")
        if self.total_frames > 0:
            print(f"   Actual FPS: {self.total_frames / (total_time/1000):.2f}")


def load_config(config_path: str = 'config/roi_config.yaml'):
    """Load ROI configuration from YAML file."""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def main():
    """Main processing pipeline."""
    
    # Track total execution time
    total_start_time = time.time()
    
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
    
    # Initialize performance tracker
    perf_tracker = PerformanceTracker()
    
    telemetry_data = []
    last_progress = -1
    previous_lap = None
    lap_transitions = []  # Track lap transition frames
    completed_lap_times = {}  # Map lap_number -> lap_time for completed laps
    frames_since_transition = 0  # Counter to capture lap time on first frame after transition
    
    try:
        for frame_num, timestamp, roi_dict in processor.process_frames():
            frame_start = time.time()
            
            # Extract telemetry from current frame
            telemetry_start = time.time()
            telemetry = extractor.extract_frame_telemetry(roi_dict)
            perf_tracker.record('telemetry_extraction', time.time() - telemetry_start)
            
            # Extract lap number
            lap_start = time.time()
            lap_number = lap_detector.extract_lap_number(processor.current_frame)
            perf_tracker.record('lap_number_detection', time.time() - lap_start)
            
            # Extract speed
            speed_start = time.time()
            speed = lap_detector.extract_speed(processor.current_frame)
            perf_tracker.record('speed_extraction', time.time() - speed_start)
            
            # Extract gear
            gear_start = time.time()
            gear = lap_detector.extract_gear(processor.current_frame)
            perf_tracker.record('gear_extraction', time.time() - gear_start)
            
            # Detect lap transitions
            transition_start = time.time()
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
                lap_time_start = time.time()
                completed_lap_time = lap_detector.extract_last_lap_time(processor.current_frame)
                perf_tracker.record('lap_time_extraction', time.time() - lap_time_start)
                
                if completed_lap_time and previous_lap is not None:
                    completed_lap_times[previous_lap] = completed_lap_time
                    
                    # Update the last transition record with the lap time
                    if lap_transitions:
                        lap_transitions[-1]['completed_lap_time'] = completed_lap_time
                
                frames_since_transition = 0  # Reset counter
            perf_tracker.record('lap_transition_detection', time.time() - transition_start)
            
            # Store data (lap_time will be filled in post-processing)
            storage_start = time.time()
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
            perf_tracker.record('data_storage', time.time() - storage_start)
            
            previous_lap = lap_number
            perf_tracker.total_frames += 1
            
            # Record total frame processing time
            perf_tracker.record('frame_processing', time.time() - frame_start)
            
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
        
        # Display detailed performance breakdown
        perf_tracker.print_summary()
        
    finally:
        processor.close()
    
    # Create DataFrame
    print(f"\n📈 Generating outputs...")
    
    df_start = time.time()
    df = visualizer.create_dataframe(telemetry_data)
    df_time = time.time() - df_start
    
    # Export CSV
    csv_start = time.time()
    csv_path = visualizer.export_csv(df)
    csv_time = time.time() - csv_start
    print(f"   ✅ CSV saved: {csv_path} (took {csv_time*1000:.1f}ms)")
    
    # Generate interactive HTML graph
    graph_start = time.time()
    graph_path = visualizer.plot_telemetry(df)
    graph_time = time.time() - graph_start
    print(f"   ✅ Interactive graph saved: {graph_path} (took {graph_time:.2f}s)")
    print(f"      💡 Open this HTML file in your browser for interactive zoom/pan/hover!")
    
    print(f"\n   Output Generation Summary:")
    print(f"      DataFrame creation: {df_time*1000:.1f}ms")
    print(f"      CSV export: {csv_time*1000:.1f}ms")
    print(f"      Graph generation: {graph_time:.2f}s")
    print(f"      Total: {(df_time + csv_time + graph_time):.2f}s")
    
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
    
    # Display total execution time
    total_time = time.time() - total_start_time
    print(f"\n⏱️  Total Execution Time: {total_time:.2f}s ({total_time/60:.1f} minutes)")


if __name__ == '__main__':
    main()

