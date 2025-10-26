import { create } from 'zustand';
import type { VideoListItem } from '../types/api';

interface AppState {
  selectedVideo: VideoListItem | null;
  selectedLap: number | null;
  setSelectedVideo: (video: VideoListItem | null) => void;
  setSelectedLap: (lap: number | null) => void;
}

export const useAppStore = create<AppState>((set) => ({
  selectedVideo: null,
  selectedLap: null,
  setSelectedVideo: (video) => set({ selectedVideo: video, selectedLap: null }),
  setSelectedLap: (lap) => set({ selectedLap: lap }),
}));
