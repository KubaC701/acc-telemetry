export interface VideoListItem {
  video_name: string;
  total_laps: number;
  duration: number;
  processed_at: string;
  fps: number;
}

export interface LapMetadata {
  lap_number: number;
  duration: number;
  frames: number;
  avg_speed?: number;
  max_speed?: number;
  avg_throttle?: number;
  avg_brake?: number;
  lap_time?: string;
}

export interface VideoMetadata {
  video_name: string;
  video_path: string;
  fps: number;
  duration: number;
  frame_count: number;
  total_laps: number;
  laps: LapMetadata[];
  processed_at: string;
  csv_path: string;
  track_position_available: boolean;
}

export interface TelemetryData {
  frame: number;
  time: number;
  lap_number: number | null;
  lap_time: string | null;
  track_position: number | null;
  speed: number | null;
  gear: number | null;
  throttle: number;
  brake: number;
  steering: number;
  tc_active: boolean;
  abs_active: boolean;
}

// LapData = LapMetadata (same structure for /laps endpoint)
export type LapData = LapMetadata;

export interface Job {
  job_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress: number;
  message: string;
  video_name: string;
  created_at: string;
  completed_at?: string;
  error?: string;
}

export interface VideoProcessRequest {
  video_path: string;
}

export interface ProcessResponse {
  job_id: string;
  video_name: string;
  message: string;
}

export interface DeleteResponse {
  message: string;
}

export interface LapIdentifier {
  video_name: string;
  lap_number: number;
}

export interface ComparisonRequest {
  laps: LapIdentifier[];
}

export interface LapComparisonData {
  video_name: string;
  lap_number: number;
  lap_time: string | null;
  data: TelemetryData[];
}

export interface ComparisonCartItem {
  videoName: string;
  lapNumber: number;
  lapTime: string | null;
}
