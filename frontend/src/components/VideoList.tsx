import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { videosApi, telemetryApi } from '../lib/api';
import { useAppStore } from '../store/useAppStore';
import { Button } from './ui/Button';
import { Card, CardHeader, CardTitle, CardContent } from './ui/Card';
import type { VideoListItem } from '../types/api';

export function VideoList() {
  const queryClient = useQueryClient();
  const { selectedVideo, setSelectedVideo } = useAppStore();

  const { data: videos, isLoading, error } = useQuery({
    queryKey: ['videos'],
    queryFn: videosApi.list,
    refetchInterval: 5000, // Poll every 5 seconds
  });

  const deleteMutation = useMutation({
    mutationFn: (videoName: string) => videosApi.delete(videoName),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['videos'] });
      if (selectedVideo) {
        setSelectedVideo(null);
      }
    },
  });

  const formatDuration = (seconds: number): string => {
    const minutes = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${minutes}:${secs.toString().padStart(2, '0')}`;
  };

  const formatDate = (dateString: string): string => {
    const date = new Date(dateString);
    return date.toLocaleString();
  };

  if (isLoading) {
    return (
      <Card>
        <CardContent>
          <div className="flex items-center justify-center py-8">
            <svg className="animate-spin h-8 w-8 text-blue-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardContent>
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <p className="text-sm text-red-800">Failed to load videos</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!videos || videos.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Processed Videos</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-gray-500 text-center py-8">
            No videos processed yet. Upload a video to get started.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Processed Videos ({videos.length})</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {videos.map((video) => (
            <div
              key={video.video_name}
              className={`border rounded-lg p-4 transition-all ${
                selectedVideo?.video_name === video.video_name
                  ? 'border-blue-500 bg-blue-50'
                  : 'border-gray-200 hover:border-gray-300'
              }`}
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <h4 className="font-semibold text-gray-900 mb-1">
                    {video.video_name}
                  </h4>
                  <div className="space-y-1 text-sm text-gray-600">
                    <p>Duration: {formatDuration(video.duration)}</p>
                    <p>Processed: {formatDate(video.processed_at)}</p>
                    <p>Laps: {video.total_laps}</p>
                    <p>FPS: {video.fps.toFixed(2)}</p>
                  </div>
                </div>

                <div className="flex flex-col gap-2 ml-4">
                  <Button
                    size="sm"
                    variant={selectedVideo?.video_name === video.video_name ? 'secondary' : 'primary'}
                    onClick={() => setSelectedVideo(
                      selectedVideo?.video_name === video.video_name ? null : video
                    )}
                  >
                    {selectedVideo?.video_name === video.video_name ? 'Deselect' : 'View'}
                  </Button>

                  <a
                    href={telemetryApi.downloadCsv(video.video_name)}
                    download
                    className="text-center"
                  >
                    <Button size="sm" variant="secondary">
                      Download CSV
                    </Button>
                  </a>

                  <Button
                    size="sm"
                    variant="danger"
                    onClick={() => {
                      if (confirm(`Delete ${video.video_name}?`)) {
                        deleteMutation.mutate(video.video_name);
                      }
                    }}
                    isLoading={deleteMutation.isPending}
                  >
                    Delete
                  </Button>
                </div>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
