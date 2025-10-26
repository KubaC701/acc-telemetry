import { useState } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { VideoUpload } from './components/VideoUpload';
import { VideoList } from './components/VideoList';
import { JobStatus, JobsList } from './components/JobStatus';
import { TelemetryVisualization } from './components/TelemetryVisualization';
import { LapComparison } from './components/LapComparison';
import { ComparisonCart } from './components/ComparisonCart';
import { useAppStore } from './store/useAppStore';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

function TelemetryView() {
  const { selectedVideo } = useAppStore();
  const [currentJobId, setCurrentJobId] = useState<string | null>(null);

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">
                ACC Telemetry Extractor
              </h1>
              <p className="mt-1 text-sm text-gray-600">
                Extract and visualize telemetry from Assetto Corsa Competizione gameplay videos
              </p>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-green-500 rounded-full animate-pulse"></div>
              <span className="text-sm text-gray-600">API Connected</span>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-1 space-y-6">
            <VideoUpload
              onProcessStarted={(jobId) => setCurrentJobId(jobId)}
            />

            {currentJobId && (
              <JobStatus
                jobId={currentJobId}
                onComplete={() => {
                  setCurrentJobId(null);
                  queryClient.invalidateQueries({ queryKey: ['videos'] });
                }}
              />
            )}

            <JobsList />

            <VideoList />
          </div>

          <div className="lg:col-span-2">
            {selectedVideo ? (
              <TelemetryVisualization />
            ) : (
              <div className="bg-white rounded-lg shadow-md p-12 text-center">
                <svg
                  className="mx-auto h-16 w-16 text-gray-400 mb-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
                  />
                </svg>
                <h3 className="text-xl font-semibold text-gray-900 mb-2">
                  No Video Selected
                </h3>
                <p className="text-gray-600 max-w-md mx-auto">
                  Upload and process a video, then select it from the list to view
                  interactive telemetry visualizations including throttle, brake,
                  steering, speed, and track position data.
                </p>
              </div>
            )}
          </div>
        </div>
      </main>

      <footer className="bg-white border-t border-gray-200 mt-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="text-center text-sm text-gray-600">
            <p>
              ACC Telemetry Extractor - Computer vision-based telemetry extraction
              for console players
            </p>
            <p className="mt-1">
              Designed for PS5/Xbox players who lack native telemetry export
            </p>
          </div>
        </div>
      </footer>

      <ComparisonCart />
    </div>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<TelemetryView />} />
          <Route path="/compare" element={<LapComparison />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
