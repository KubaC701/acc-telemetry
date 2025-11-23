import { useState, useEffect } from 'react';
import { Sidebar } from './components/Sidebar';
import { TelemetryCharts } from './components/TelemetryCharts';
import { fetchVideos, uploadVideo, fetchTelemetryData } from './services/api';
import type { VideoListItem } from './services/api';
import clsx from 'clsx';

function App() {
  const [videos, setVideos] = useState<VideoListItem[]>([]);
  const [selectedVideo, setSelectedVideo] = useState<string | null>(null);
  const [telemetryData, setTelemetryData] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);

  useEffect(() => {
    loadVideos();
  }, []);

  useEffect(() => {
    if (selectedVideo) {
      loadTelemetry(selectedVideo);
    }
  }, [selectedVideo]);

  const loadVideos = async () => {
    try {
      const data = await fetchVideos();
      setVideos(data);
    } catch (error) {
      console.error('Failed to load videos:', error);
    }
  };

  const loadTelemetry = async (videoName: string) => {
    setIsLoading(true);
    try {
      const data = await fetchTelemetryData(videoName);
      setTelemetryData(data);
    } catch (error) {
      console.error('Failed to load telemetry:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleUpload = async (file: File) => {
    try {
      await uploadVideo(file);
      await loadVideos(); // Refresh list
    } catch (error) {
      console.error('Failed to upload video:', error);
    }
  };

  return (
    <div className="flex h-screen bg-slate-950 text-slate-100 overflow-hidden">
      <Sidebar
        videos={videos}
        selectedVideo={selectedVideo}
        onSelectVideo={setSelectedVideo}
        onUpload={handleUpload}
        isOpen={isSidebarOpen}
        onToggle={() => setIsSidebarOpen(!isSidebarOpen)}
      />

      <main
        className={clsx(
          "flex-1 transition-all duration-300 flex flex-col h-full overflow-hidden",
          isSidebarOpen ? "ml-64" : "ml-16"
        )}
      >
        {selectedVideo ? (
          <div className="flex flex-col h-full overflow-hidden">
            <div className="p-4 border-b border-slate-800 bg-slate-900/50 flex justify-between items-center">
              <h2 className="text-xl font-bold">{selectedVideo}</h2>
              <div className="text-sm text-slate-400">
                {telemetryData.length > 0 ? `${telemetryData.length} frames` : 'No data'}
              </div>
            </div>
            
            <div className="flex-1 p-4 overflow-hidden relative">
              {isLoading ? (
                <div className="absolute inset-0 flex items-center justify-center bg-slate-900/50 z-10">
                  <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
                </div>
              ) : (
                <TelemetryCharts data={telemetryData} />
              )}
            </div>
          </div>
        ) : (
          <div className="flex-1 flex items-center justify-center text-slate-500">
            <div className="text-center">
              <h2 className="text-2xl font-bold mb-2">Welcome to Telemetry Visualizer</h2>
              <p>Select a video from the sidebar or upload a new one to get started.</p>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
