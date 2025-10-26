import axios from 'axios';
import type {
  VideoListItem,
  VideoMetadata,
  TelemetryData,
  LapData,
  Job,
  VideoProcessRequest,
  ProcessResponse,
  DeleteResponse,
  LapIdentifier,
  ComparisonRequest,
  LapComparisonData,
} from '../types/api';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const videosApi = {
  list: async (): Promise<VideoListItem[]> => {
    const response = await api.get('/api/videos');
    return response.data;
  },

  getMetadata: async (videoName: string): Promise<VideoMetadata> => {
    const response = await api.get(`/api/videos/${videoName}`);
    return response.data;
  },

  process: async (videoPath: string): Promise<ProcessResponse> => {
    const response = await api.post<ProcessResponse>('/api/videos/process', {
      video_path: videoPath,
    } as VideoProcessRequest);
    return response.data;
  },

  delete: async (videoName: string): Promise<DeleteResponse> => {
    const response = await api.delete(`/api/videos/${videoName}`);
    return response.data;
  },
};

export const telemetryApi = {
  getData: async (videoName: string): Promise<TelemetryData[]> => {
    const response = await api.get(`/api/telemetry/${videoName}/data`);
    return response.data;
  },

  getLapData: async (videoName: string, lapNumber: number): Promise<TelemetryData[]> => {
    const response = await api.get(`/api/telemetry/${videoName}/laps/${lapNumber}`);
    return response.data;
  },

  getLaps: async (videoName: string): Promise<LapData[]> => {
    const response = await api.get(`/api/telemetry/${videoName}/laps`);
    return response.data;
  },

  downloadCsv: (videoName: string): string => {
    return `${API_BASE_URL}/api/telemetry/${videoName}/csv`;
  },

  compareLaps: async (lapIdentifiers: LapIdentifier[]): Promise<LapComparisonData[]> => {
    const response = await api.post<LapComparisonData[]>('/api/telemetry/compare', {
      laps: lapIdentifiers,
    } as ComparisonRequest);
    return response.data;
  },
};

export const jobsApi = {
  getStatus: async (jobId: string): Promise<Job> => {
    const response = await api.get(`/api/jobs/${jobId}`);
    return response.data;
  },

  list: async (): Promise<Job[]> => {
    const response = await api.get('/api/jobs');
    return response.data;
  },
};

export default api;
