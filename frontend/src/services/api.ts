import axios from 'axios';

const API_URL = 'http://localhost:8000/api';

export const api = axios.create({
  baseURL: API_URL,
});

export interface VideoListItem {
  video_name: string;
  total_laps: number;
  duration: number;
  processed_at: string;
  fps: number;
}

export interface VideoMetadata {
  name: string;
  duration: number;
  fps: number;
  frame_count: number;
  resolution: [number, number];
  laps: LapMetadata[];
}

export interface LapMetadata {
  lap_number: number;
  lap_time: number;
  start_frame: number;
  end_frame: number;
}

export const fetchVideos = async (): Promise<VideoListItem[]> => {
  const response = await api.get('/videos');
  return response.data;
};

export const fetchVideoMetadata = async (videoName: string): Promise<VideoMetadata> => {
  const response = await api.get(`/videos/${videoName}`);
  return response.data;
};

export const uploadVideo = async (file: File, hasOverlay: boolean = false): Promise<VideoMetadata> => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('has_overlay', String(hasOverlay));
  const response = await api.post('/videos/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

export const fetchTelemetryData = async (videoName: string, lapNumbers?: number[]) => {
    const params = new URLSearchParams();
    if (lapNumbers) {
        params.append('lap_numbers', lapNumbers.join(','));
    }
    const response = await api.get(`/telemetry/${videoName}/data`, { params });
    return response.data;
}
