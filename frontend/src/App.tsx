import { useState, useEffect } from 'react';
import { Sidebar } from './components/Sidebar';
import { TelemetryChartsECharts } from './components/TelemetryChartsECharts';
import { fetchVideos, uploadVideo, fetchTelemetryData, fetchVideoMetadata } from './services/api';
import type { VideoListItem, VideoMetadata } from './services/api';
import clsx from 'clsx';

interface LapSelection {
  video: string;
  lap: number;
}

function App() {
  const [videos, setVideos] = useState<VideoListItem[]>([]);
  const [videoMetadata, setVideoMetadata] = useState<Record<string, VideoMetadata>>({});
  
  const [referenceLap, setReferenceLap] = useState<LapSelection | null>(null);
  const [comparisonLap, setComparisonLap] = useState<LapSelection | null>(null);
  
  const [referenceData, setReferenceData] = useState<any[]>([]);
  const [comparisonData, setComparisonData] = useState<any[]>([]);
  
  const [isLoading, setIsLoading] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);

  useEffect(() => {
    loadVideos();
  }, []);

  useEffect(() => {
    if (referenceLap) {
      loadTelemetry(referenceLap, setReferenceData);
    } else {
      setReferenceData([]);
    }
  }, [referenceLap]);

  useEffect(() => {
    if (comparisonLap) {
      loadTelemetry(comparisonLap, setComparisonData);
    } else {
      setComparisonData([]);
    }
  }, [comparisonLap]);

  const loadVideos = async () => {
    try {
      const data = await fetchVideos();
      setVideos(data);
    } catch (error) {
      console.error('Failed to load videos:', error);
    }
  };

  const handleExpandVideo = async (videoName: string) => {
    if (videoMetadata[videoName]) return;

    try {
      const metadata = await fetchVideoMetadata(videoName);
      setVideoMetadata(prev => ({ ...prev, [videoName]: metadata }));
    } catch (error) {
      console.error(`Failed to load metadata for ${videoName}:`, error);
    }
  };

  const loadTelemetry = async (selection: LapSelection, setData: (data: any[]) => void) => {
    setIsLoading(true);
    try {
      // We request data for the specific lap
      // Note: The backend API currently filters by lap_numbers if provided
      const rawData = await fetchTelemetryData(selection.video, [selection.lap]);
      
      // Normalize time to start from 0
      if (rawData.length > 0) {
        const startTime = rawData[0].time;
        const normalizedData = rawData.map((point: any) => ({
          ...point,
          time: point.time - startTime
        }));
        setData(normalizedData);
      } else {
        setData([]);
      }
    } catch (error) {
      console.error('Failed to load telemetry:', error);
      setData([]);
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
        videoMetadata={videoMetadata}
        selectedReference={referenceLap}
        selectedComparison={comparisonLap}
        onSelectReference={(video, lap) => {
          if (referenceLap?.video === video && referenceLap?.lap === lap) {
            setReferenceLap(null);
          } else {
            setReferenceLap({ video, lap });
          }
        }}
        onSelectComparison={(video, lap) => {
          if (comparisonLap?.video === video && comparisonLap?.lap === lap) {
            setComparisonLap(null);
          } else {
            setComparisonLap({ video, lap });
          }
        }}
        onExpandVideo={handleExpandVideo}
        onUpload={handleUpload}
        isOpen={isSidebarOpen}
        onToggle={() => setIsSidebarOpen(!isSidebarOpen)}
      />

      <main
        className={clsx(
          "flex-1 transition-all duration-300 flex flex-col h-full overflow-hidden",
          isSidebarOpen ? "ml-80" : "ml-16"
        )}
      >
        {referenceLap ? (
          <div className="flex flex-col h-full overflow-hidden">
            <div className="p-4 border-b border-slate-800 bg-slate-900/50 flex justify-between items-center">
              <div className="flex items-center gap-4">
                <div>
                  <div className="text-xs text-slate-400 uppercase tracking-wider font-bold">Reference</div>
                  <div className="text-lg font-bold text-blue-400">
                    {referenceLap.video} <span className="text-slate-500">Lap {referenceLap.lap}</span>
                  </div>
                </div>
                
                {comparisonLap && (
                  <>
                    <div className="h-8 w-px bg-slate-700"></div>
                    <div>
                      <div className="text-xs text-slate-400 uppercase tracking-wider font-bold">Comparison</div>
                      <div className="text-lg font-bold text-purple-400">
                        {comparisonLap.video} <span className="text-slate-500">Lap {comparisonLap.lap}</span>
                      </div>
                    </div>
                  </>
                )}
              </div>
              
              <div className="text-sm text-slate-400">
                {referenceData.length > 0 ? `${referenceData.length} frames` : 'No data'}
              </div>
            </div>
            
            <div className="flex-1 p-4 overflow-hidden relative">
              {isLoading && (referenceData.length === 0 && comparisonData.length === 0) ? (
                <div className="absolute inset-0 flex items-center justify-center bg-slate-900/50 z-10">
                  <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
                </div>
              ) : (
                <TelemetryChartsECharts 
                  referenceData={referenceData} 
                  comparisonData={comparisonData.length > 0 ? comparisonData : undefined} 
                />
              )}
            </div>
          </div>
        ) : (
          <div className="flex-1 flex items-center justify-center text-slate-500">
            <div className="text-center">
              <h2 className="text-2xl font-bold mb-2">Welcome to Telemetry Visualizer</h2>
              <p>Select a lap from the sidebar to start analyzing.</p>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
