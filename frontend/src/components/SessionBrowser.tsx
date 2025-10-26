import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { videosApi, telemetryApi } from '../lib/api';
import { useAppStore } from '../store/useAppStore';
import { Modal } from './ui/Modal';
import { Checkbox } from './ui/Checkbox';
import type { VideoListItem, LapData } from '../types/api';

interface SessionBrowserProps {
  isOpen: boolean;
  onClose: () => void;
}

export function SessionBrowser({ isOpen, onClose }: SessionBrowserProps) {
  const [expandedVideo, setExpandedVideo] = useState<string | null>(null);
  const { addToComparison, isInComparison, comparisonCart } = useAppStore();

  const { data: videos, isLoading: isLoadingVideos } = useQuery({
    queryKey: ['videos'],
    queryFn: () => videosApi.list(),
    enabled: isOpen,
  });

  const { data: laps, isLoading: isLoadingLaps } = useQuery({
    queryKey: ['laps', expandedVideo],
    queryFn: () => telemetryApi.getLaps(expandedVideo!),
    enabled: !!expandedVideo,
  });

  const handleToggleVideo = (videoName: string) => {
    setExpandedVideo(expandedVideo === videoName ? null : videoName);
  };

  const handleToggleLap = (video: VideoListItem, lap: LapData) => {
    const inCart = isInComparison(video.video_name, lap.lap_number);

    if (inCart) {
      // Remove from cart - handled in parent
      return;
    }

    // Check cart limit
    if (comparisonCart.length >= 10) {
      alert('Maximum 10 laps allowed in comparison cart');
      return;
    }

    addToComparison({
      videoName: video.video_name,
      lapNumber: lap.lap_number,
      lapTime: lap.lap_time || null,
    });
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Browse Sessions" size="xl">
      {isLoadingVideos ? (
        <div className="flex items-center justify-center py-12">
          <svg
            className="animate-spin h-8 w-8 text-blue-600"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            ></circle>
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            ></path>
          </svg>
        </div>
      ) : !videos || videos.length === 0 ? (
        <div className="text-center py-12 text-gray-500">
          No sessions found. Process a video first.
        </div>
      ) : (
        <div className="space-y-3">
          {videos.map((video) => (
            <div
              key={video.video_name}
              className="border border-gray-200 rounded-lg overflow-hidden"
            >
              {/* Video Header */}
              <button
                onClick={() => handleToggleVideo(video.video_name)}
                className="w-full p-4 flex items-center justify-between bg-gray-50 hover:bg-gray-100 transition-colors"
              >
                <div className="flex-1 text-left">
                  <h4 className="font-semibold text-gray-900">
                    {video.video_name}
                  </h4>
                  <p className="text-sm text-gray-600">
                    {video.total_laps} laps • {Math.floor(video.duration / 60)}:
                    {String(Math.floor(video.duration % 60)).padStart(2, '0')}
                  </p>
                </div>
                <svg
                  className={`w-5 h-5 text-gray-500 transition-transform ${
                    expandedVideo === video.video_name ? 'rotate-180' : ''
                  }`}
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M19 9l-7 7-7-7"
                  />
                </svg>
              </button>

              {/* Lap List */}
              {expandedVideo === video.video_name && (
                <div className="p-4 bg-white border-t border-gray-200">
                  {isLoadingLaps ? (
                    <div className="flex justify-center py-4">
                      <svg
                        className="animate-spin h-6 w-6 text-blue-600"
                        xmlns="http://www.w3.org/2000/svg"
                        fill="none"
                        viewBox="0 0 24 24"
                      >
                        <circle
                          className="opacity-25"
                          cx="12"
                          cy="12"
                          r="10"
                          stroke="currentColor"
                          strokeWidth="4"
                        ></circle>
                        <path
                          className="opacity-75"
                          fill="currentColor"
                          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                        ></path>
                      </svg>
                    </div>
                  ) : !laps || laps.length === 0 ? (
                    <p className="text-sm text-gray-500 text-center py-4">
                      No laps found
                    </p>
                  ) : (
                    <div className="space-y-2">
                      {laps.map((lap) => (
                        <div
                          key={lap.lap_number}
                          className="flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
                        >
                          <div className="flex-1">
                            <p className="text-sm font-medium text-gray-900">
                              Lap {lap.lap_number}
                              {lap.lap_time && ` - ${lap.lap_time}`}
                            </p>
                            {lap.avg_speed && (
                              <p className="text-xs text-gray-600">
                                Avg Speed: {lap.avg_speed.toFixed(1)} km/h
                              </p>
                            )}
                          </div>
                          <Checkbox
                            checked={isInComparison(
                              video.video_name,
                              lap.lap_number
                            )}
                            onChange={() => handleToggleLap(video, lap)}
                            label="Add to comparison"
                          />
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </Modal>
  );
}
