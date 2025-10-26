import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import Plot from 'react-plotly.js';
import { telemetryApi } from '../lib/api';
import { useAppStore } from '../store/useAppStore';
import { Card, CardHeader, CardTitle, CardContent } from './ui/Card';
import type { TelemetryData } from '../types/api';

export function TelemetryVisualization() {
  const { selectedVideo, selectedLap, setSelectedLap } = useAppStore();
  const [viewMode, setViewMode] = useState<'all' | 'lap'>('all');

  const { data: allTelemetry, isLoading: isLoadingAll } = useQuery({
    queryKey: ['telemetry', selectedVideo?.video_name],
    queryFn: () => telemetryApi.getData(selectedVideo!.video_name),
    enabled: !!selectedVideo && viewMode === 'all',
  });

  const { data: laps, isLoading: isLoadingLaps } = useQuery({
    queryKey: ['laps', selectedVideo?.video_name],
    queryFn: () => telemetryApi.getLaps(selectedVideo!.video_name),
    enabled: !!selectedVideo,
  });

  const { data: lapData, isLoading: isLoadingLap } = useQuery({
    queryKey: ['lap', selectedVideo?.video_name, selectedLap],
    queryFn: () => telemetryApi.getLapData(selectedVideo!.video_name, selectedLap!),
    enabled: !!selectedVideo && !!selectedLap && viewMode === 'lap',
  });

  const telemetryData = useMemo(() => {
    if (viewMode === 'all') return allTelemetry || [];
    return lapData || [];
  }, [viewMode, allTelemetry, lapData]);

  if (!selectedVideo) {
    return (
      <Card>
        <CardContent>
          <p className="text-gray-500 text-center py-8">
            Select a video to view telemetry data
          </p>
        </CardContent>
      </Card>
    );
  }

  const isLoading = isLoadingAll || isLoadingLaps || isLoadingLap;

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

  if (!telemetryData || telemetryData.length === 0) {
    return (
      <Card>
        <CardContent>
          <p className="text-gray-500 text-center py-8">
            No telemetry data available
          </p>
        </CardContent>
      </Card>
    );
  }

  const timestamps = telemetryData.map((d) => d.time);

  // Calculate subplot domains (8 subplots with equal spacing)
  const subplotHeight = 0.11; // 11% height per subplot
  const subplotGap = 0.01; // 1% gap between subplots

  const getSubplotDomain = (index: number): [number, number] => {
    const bottom = index * (subplotHeight + subplotGap);
    return [bottom, bottom + subplotHeight];
  };

  // Prepare all traces with their respective y-axis assignments
  const plotData = [
    // Speed (y-axis 1)
    {
      x: timestamps,
      y: telemetryData.map((d: TelemetryData) => d.speed),
      type: 'scatter' as const,
      mode: 'lines' as const,
      name: 'Speed (km/h)',
      line: { color: '#3b82f6', width: 2 },
      yaxis: 'y',
      hovertemplate: 'Speed: %{y:.1f} km/h<extra></extra>',
    },
    // Gear (y-axis 2)
    {
      x: timestamps,
      y: telemetryData.map((d: TelemetryData) => d.gear),
      type: 'scatter' as const,
      mode: 'lines' as const,
      name: 'Gear',
      line: { color: '#9b59b6', width: 2, shape: 'hv' as const },
      yaxis: 'y2',
      hovertemplate: 'Gear: %{y}<extra></extra>',
    },
    // Throttle (y-axis 3)
    {
      x: timestamps,
      y: telemetryData.map((d: TelemetryData) => d.throttle),
      type: 'scatter' as const,
      mode: 'lines' as const,
      name: 'Throttle (%)',
      line: { color: '#22c55e', width: 2 },
      fill: 'tozeroy' as const,
      yaxis: 'y3',
      hovertemplate: 'Throttle: %{y:.1f}%<extra></extra>',
    },
    // Brake (y-axis 3, shared with throttle)
    {
      x: timestamps,
      y: telemetryData.map((d: TelemetryData) => -d.brake),
      type: 'scatter' as const,
      mode: 'lines' as const,
      name: 'Brake (%)',
      line: { color: '#ef4444', width: 2 },
      fill: 'tozeroy' as const,
      yaxis: 'y3',
      hovertemplate: 'Brake: %{y:.1f}%<extra></extra>',
    },
    // Steering (y-axis 4)
    {
      x: timestamps,
      y: telemetryData.map((d: TelemetryData) => d.steering),
      type: 'scatter' as const,
      mode: 'lines' as const,
      name: 'Steering',
      line: { color: '#8b5cf6', width: 2 },
      yaxis: 'y4',
      hovertemplate: 'Steering: %{y:.2f}<extra></extra>',
    },
    // Track Position (y-axis 5)
    {
      x: timestamps,
      y: telemetryData.map((d: TelemetryData) => d.track_position),
      type: 'scatter' as const,
      mode: 'lines' as const,
      name: 'Track Position (%)',
      line: { color: '#f59e0b', width: 2 },
      yaxis: 'y5',
      hovertemplate: 'Position: %{y:.1f}%<extra></extra>',
    },
    // TC Active (y-axis 6)
    {
      x: timestamps,
      y: telemetryData.map((d: TelemetryData) => d.tc_active ? 1 : 0),
      type: 'scatter' as const,
      mode: 'lines' as const,
      name: 'TC Active',
      line: { color: '#ffa500', width: 2, shape: 'hv' as const },
      fill: 'tozeroy' as const,
      fillcolor: 'rgba(255, 165, 0, 0.3)',
      yaxis: 'y6',
      hovertemplate: 'TC: %{y}<extra></extra>',
    },
    // ABS Active (y-axis 7)
    {
      x: timestamps,
      y: telemetryData.map((d: TelemetryData) => d.abs_active ? 1 : 0),
      type: 'scatter' as const,
      mode: 'lines' as const,
      name: 'ABS Active',
      line: { color: '#ff8c00', width: 2, shape: 'hv' as const },
      fill: 'tozeroy' as const,
      fillcolor: 'rgba(255, 140, 0, 0.3)',
      yaxis: 'y7',
      hovertemplate: 'ABS: %{y}<extra></extra>',
    },
  ];

  // Configure the layout with 8 subplots
  const layout = {
    height: 2400,
    hovermode: 'x unified' as const,
    showlegend: true,
    legend: {
      orientation: 'h' as const,
      y: 1.02,
      x: 0,
      xanchor: 'left' as const,
      yanchor: 'bottom' as const,
    },
    margin: { l: 60, r: 60, t: 100, b: 50 },

    // Main x-axis (bottom)
    xaxis: {
      title: 'Time (s)',
      domain: [0, 1],
      anchor: 'y' as const,
      showspikes: true,
      spikemode: 'across',
      spikesnap: 'cursor',
      spikecolor: 'rgba(200, 200, 200, 0.8)',
      spikethickness: 1,
      spikedash: 'solid',
    },

    // Y-axis 1: Speed
    yaxis: {
      title: 'Speed (km/h)',
      domain: getSubplotDomain(7), // Top subplot
      anchor: 'x' as const,
      showspikes: true,
      spikecolor: 'rgba(200, 200, 200, 0.5)',
      spikethickness: 1,
    },

    // Y-axis 2: Gear
    yaxis2: {
      title: 'Gear',
      domain: getSubplotDomain(6),
      anchor: 'x' as const,
      range: [0, 7],
      showspikes: true,
      spikecolor: 'rgba(200, 200, 200, 0.5)',
      spikethickness: 1,
    },

    // Y-axis 3: Throttle & Brake
    yaxis3: {
      title: 'Throttle/Brake (%)',
      domain: getSubplotDomain(5),
      anchor: 'x' as const,
      range: [-100, 100],
      showspikes: true,
      spikecolor: 'rgba(200, 200, 200, 0.5)',
      spikethickness: 1,
    },

    // Y-axis 4: Steering
    yaxis4: {
      title: 'Steering',
      domain: getSubplotDomain(4),
      anchor: 'x' as const,
      range: [-1.1, 1.1],
      showspikes: true,
      spikecolor: 'rgba(200, 200, 200, 0.5)',
      spikethickness: 1,
    },

    // Y-axis 5: Track Position
    yaxis5: {
      title: 'Track Position (%)',
      domain: getSubplotDomain(3),
      anchor: 'x' as const,
      range: [0, 100],
      showspikes: true,
      spikecolor: 'rgba(200, 200, 200, 0.5)',
      spikethickness: 1,
    },

    // Y-axis 6: TC Active
    yaxis6: {
      title: 'TC',
      domain: getSubplotDomain(2),
      anchor: 'x' as const,
      range: [-0.1, 1.2],
      tickvals: [0, 1],
      ticktext: ['Off', 'On'],
      showspikes: true,
      spikecolor: 'rgba(200, 200, 200, 0.5)',
      spikethickness: 1,
    },

    // Y-axis 7: ABS Active
    yaxis7: {
      title: 'ABS',
      domain: getSubplotDomain(1),
      anchor: 'x' as const,
      range: [-0.1, 1.2],
      tickvals: [0, 1],
      ticktext: ['Off', 'On'],
      showspikes: true,
      spikecolor: 'rgba(200, 200, 200, 0.5)',
      spikethickness: 1,
    },

    
    // Enable unified hover across all subplots
    spikedistance: -1,
    hoverdistance: 100,
  };

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Telemetry: {selectedVideo.video_name}</CardTitle>
            <div className="flex gap-2">
              <button
                className={`px-3 py-1 rounded text-sm font-medium ${
                  viewMode === 'all'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-200 text-gray-700'
                }`}
                onClick={() => {
                  setViewMode('all');
                  setSelectedLap(null);
                }}
              >
                All Laps
              </button>
              <button
                className={`px-3 py-1 rounded text-sm font-medium ${
                  viewMode === 'lap'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-200 text-gray-700'
                }`}
                onClick={() => setViewMode('lap')}
                disabled={!laps || laps.length === 0}
              >
                Single Lap
              </button>
            </div>
          </div>
        </CardHeader>

        {viewMode === 'lap' && laps && laps.length > 0 && (
          <CardContent className="border-t">
            <div className="flex items-center gap-4">
              <label className="text-sm font-medium text-gray-700">
                Select Lap:
              </label>
              <select
                className="px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                value={selectedLap || ''}
                onChange={(e) => setSelectedLap(Number(e.target.value))}
              >
                <option value="">Choose a lap...</option>
                {laps.map((lap) => (
                  <option key={lap.lap_number} value={lap.lap_number}>
                    Lap {lap.lap_number} - {lap.lap_time}
                  </option>
                ))}
              </select>
            </div>
          </CardContent>
        )}
      </Card>

      {viewMode === 'lap' && !selectedLap ? (
        <Card>
          <CardContent>
            <p className="text-gray-500 text-center py-8">
              Select a lap to view detailed telemetry
            </p>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Synchronized Telemetry View</CardTitle>
          </CardHeader>
          <CardContent>
            <Plot
              data={plotData}
              layout={layout}
              config={{
                responsive: true,
                displayModeBar: true,
                displaylogo: false,
                modeBarButtonsToRemove: ['lasso2d', 'select2d'],
              }}
              style={{ width: '100%', height: '2400px' }}
            />
          </CardContent>
        </Card>
      )}
    </div>
  );
}
