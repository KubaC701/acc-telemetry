import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { videosApi } from '../lib/api';
import { Button } from './ui/Button';
import { Input } from './ui/Input';
import { Card, CardHeader, CardTitle, CardContent } from './ui/Card';

interface VideoUploadProps {
  onProcessStarted?: (jobId: string) => void;
}

export function VideoUpload({ onProcessStarted }: VideoUploadProps) {
  const [videoPath, setVideoPath] = useState('');

  const processMutation = useMutation({
    mutationFn: (path: string) => videosApi.process(path),
    onSuccess: (data) => {
      setVideoPath('');
      onProcessStarted?.(data.job_id);
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (videoPath.trim()) {
      processMutation.mutate(videoPath.trim());
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Process New Video</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <Input
              label="Video File Path"
              type="text"
              value={videoPath}
              onChange={(e) => setVideoPath(e.target.value)}
              placeholder="/path/to/your/video.mp4"
              error={processMutation.isError ? 'Failed to process video' : undefined}
              disabled={processMutation.isPending}
            />
            <p className="mt-2 text-sm text-gray-600">
              Enter the absolute path to your ACC gameplay video file
            </p>
          </div>

          {processMutation.isError && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4">
              <p className="text-sm text-red-800">
                {processMutation.error instanceof Error
                  ? processMutation.error.message
                  : 'Failed to start processing'}
              </p>
            </div>
          )}

          {processMutation.isSuccess && (
            <div className="bg-green-50 border border-green-200 rounded-lg p-4">
              <p className="text-sm text-green-800">
                Processing started! Job ID: {processMutation.data.job_id}
              </p>
            </div>
          )}

          <Button
            type="submit"
            variant="primary"
            isLoading={processMutation.isPending}
            disabled={!videoPath.trim() || processMutation.isPending}
          >
            {processMutation.isPending ? 'Starting...' : 'Process Video'}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
