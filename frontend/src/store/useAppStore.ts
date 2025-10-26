import { create } from 'zustand';
import type { VideoListItem, ComparisonCartItem } from '../types/api';

interface AppState {
  selectedVideo: VideoListItem | null;
  selectedLap: number | null;
  comparisonCart: ComparisonCartItem[];
  setSelectedVideo: (video: VideoListItem | null) => void;
  setSelectedLap: (lap: number | null) => void;
  addToComparison: (item: ComparisonCartItem) => void;
  removeFromComparison: (videoName: string, lapNumber: number) => void;
  clearComparison: () => void;
  isInComparison: (videoName: string, lapNumber: number) => boolean;
}

export const useAppStore = create<AppState>((set, get) => ({
  selectedVideo: null,
  selectedLap: null,
  comparisonCart: [],

  setSelectedVideo: (video) => set({ selectedVideo: video, selectedLap: null }),
  setSelectedLap: (lap) => set({ selectedLap: lap }),

  addToComparison: (item) => set((state) => {
    // Check if already in cart
    const exists = state.comparisonCart.some(
      (cartItem) =>
        cartItem.videoName === item.videoName &&
        cartItem.lapNumber === item.lapNumber
    );

    if (exists) {
      return state;
    }

    // Limit to 10 laps
    if (state.comparisonCart.length >= 10) {
      console.warn('Maximum 10 laps allowed in comparison cart');
      return state;
    }

    return {
      comparisonCart: [...state.comparisonCart, item],
    };
  }),

  removeFromComparison: (videoName, lapNumber) => set((state) => ({
    comparisonCart: state.comparisonCart.filter(
      (item) => !(item.videoName === videoName && item.lapNumber === lapNumber)
    ),
  })),

  clearComparison: () => set({ comparisonCart: [] }),

  isInComparison: (videoName, lapNumber) => {
    const state = get();
    return state.comparisonCart.some(
      (item) => item.videoName === videoName && item.lapNumber === lapNumber
    );
  },
}));
