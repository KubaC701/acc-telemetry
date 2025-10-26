import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import Plot from 'react-plotly.js';
import { telemetryApi } from '../lib/api';
import { useAppStore } from '../store/useAppStore';
import { Card, CardHeader, CardTitle, CardContent } from './ui/Card';
import { Button } from './ui/Button';
import type { TelemetryData } from '../types/api';

export function LapComparison() {
  const navigate = useNavigate();
  const { comparisonCart } = useAppStore();
  const [lap1Index, setLap1Index] = useState(0);
  const [lap2Index, setLap2Index] = useState(1);

  // Fetch comparison data for all laps in cart
  const { data: comparisonData, isLoading } = useQuery({
    queryKey: ['comparison', comparisonCart],
    queryFn: () => {
      const lapIdentifiers = comparisonCart.map(item => ({
        video_name: item.videoName,
        lap_number: item.lapNumber,
      }));
      return telemetryApi.compareLaps(lapIdentifiers);
    },
    enabled: comparisonCart.length >= 2,
  });

  // Get the two selected laps for comparison
  const lap1Data = useMemo(() => {
    if (!comparisonData || lap1Index >= comparisonData.length) return null;
    return comparisonData[lap1Index];
  }, [comparisonData, lap1Index]);

  const lap2Data = useMemo(() => {
    if (!comparisonData || lap2Index >= comparisonData.length) return null;
    return comparisonData[lap2Index];
  }, [comparisonData, lap2Index]);

  // Align data by track position
  const alignedData = useMemo(() => {
    if (!lap1Data || !lap2Data) return null;

    // Filter for valid position data
    const lap1Valid = lap1Data.data.filter(d => d.track_position !== null);
    const lap2Valid = lap2Data.data.filter(d => d.track_position !== null);

    if (lap1Valid.length === 0 || lap2Valid.length === 0) {
      return null;
    }

    // Create position grid (0-100% in 0.5% steps)
    const positionStep = 0.5;
    const positions: number[] = [];
    for (let p = 0; p <= 100; p += positionStep) {
      positions.push(p);
    }

    // Interpolate data for each position
    const interpolate = (data: TelemetryData[], targetPosition: number, field: keyof TelemetryData): number | null => {
      // Find surrounding data points
      let before = null;
      let after = null;

      for (let i = 0; i < data.length; i++) {
        const pos = data[i].track_position;
        if (pos === null) continue;

        if (pos <= targetPosition) {
          before = data[i];
        }
        if (pos >= targetPosition && after === null) {
          after = data[i];
          break;
        }
      }

      if (!before && !after) return null;
      if (!before) return after![field] as number;
      if (!after) return before[field] as number;

      // Linear interpolation
      const beforePos = before.track_position!;
      const afterPos = after.track_position!;
      const beforeVal = before[field] as number;
      const afterVal = after[field] as number;

      if (beforePos === afterPos) return beforeVal;

      const ratio = (targetPosition - beforePos) / (afterPos - beforePos);
      return beforeVal + ratio * (afterVal - beforeVal);
    };

    // Build aligned datasets
    const aligned = {
      positions,
      lap1: {
        throttle: [] as (number | null)[],
        brake: [] as (number | null)[],
        steering: [] as (number | null)[],
        speed: [] as (number | null)[],
        time: [] as (number | null)[],
      },
      lap2: {
        throttle: [] as (number | null)[],
        brake: [] as (number | null)[],
        steering: [] as (number | null)[],
        speed: [] as (number | null)[],
        time: [] as (number | null)[],
      },
    };

    positions.forEach(pos => {
      aligned.lap1.throttle.push(interpolate(lap1Valid, pos, 'throttle'));
      aligned.lap1.brake.push(interpolate(lap1Valid, pos, 'brake'));
      aligned.lap1.steering.push(interpolate(lap1Valid, pos, 'steering'));
      aligned.lap1.speed.push(interpolate(lap1Valid, pos, 'speed'));
      aligned.lap1.time.push(interpolate(lap1Valid, pos, 'time'));

      aligned.lap2.throttle.push(interpolate(lap2Valid, pos, 'throttle'));
      aligned.lap2.brake.push(interpolate(lap2Valid, pos, 'brake'));
      aligned.lap2.steering.push(interpolate(lap2Valid, pos, 'steering'));
      aligned.lap2.speed.push(interpolate(lap2Valid, pos, 'speed'));
      aligned.lap2.time.push(interpolate(lap2Valid, pos, 'time'));
    });

    return aligned;
  }, [lap1Data, lap2Data]);

  // Calculate time delta
  const timeDelta = useMemo(() => {
    if (!alignedData) return null;

    return alignedData.positions.map((_, i) => {
      const t1 = alignedData.lap1.time[i];
      const t2 = alignedData.lap2.time[i];
      if (t1 === null || t2 === null) return null;
      return t1 - t2; // Positive = lap1 is slower, negative = lap1 is faster
    });
  }, [alignedData]);

  if (comparisonCart.length < 2) {
    return (
      <div className="min-h-screen bg-gray-50 p-8">
        <Card>
          <CardContent>
            <div className="text-center py-12">
              <h3 className="text-xl font-semibold text-gray-900 mb-4">
                No Laps to Compare
              </h3>
              <p className="text-gray-600 mb-6">
                Add at least 2 laps to your comparison cart to get started.
              </p>
              <Button onClick={() => navigate('/')}>
                Go to Telemetry View
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 p-8">
        <Card>
          <CardContent>
            <div className="flex items-center justify-center py-12">
              <svg
                className="animate-spin h-12 w-12 text-blue-600"
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
          </CardContent>
        </Card>
      </div>
    );
  }

  if (!alignedData || !timeDelta) {
    return (
      <div className="min-h-screen bg-gray-50 p-8">
        <Card>
          <CardContent>
            <div className="text-center py-12">
              <h3 className="text-xl font-semibold text-gray-900 mb-4">
                No Track Position Data
              </h3>
              <p className="text-gray-600 mb-6">
                The selected laps don't have track position data available.
                Position-based comparison requires minimap tracking to be enabled.
              </p>
              <Button onClick={() => navigate('/')}>
                Go Back
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  const lap1Name = `${comparisonCart[lap1Index].videoName} - Lap ${comparisonCart[lap1Index].lapNumber}`;
  const lap2Name = `${comparisonCart[lap2Index].videoName} - Lap ${comparisonCart[lap2Index].lapNumber}`;

  // Create plot data
  const plotData = [
    // Speed comparison
    {
      x: alignedData.positions,
      y: alignedData.lap1.speed,
      type: 'scatter' as const,
      mode: 'lines' as const,
      name: `${lap1Name} Speed`,
      line: { color: '#3b82f6', width: 2 },
      yaxis: 'y',
    },
    {
      x: alignedData.positions,
      y: alignedData.lap2.speed,
      type: 'scatter' as const,
      mode: 'lines' as const,
      name: `${lap2Name} Speed`,
      line: { color: '#ef4444', width: 2 },
      yaxis: 'y',
    },
    // Throttle comparison
    {
      x: alignedData.positions,
      y: alignedData.lap1.throttle,
      type: 'scatter' as const,
      mode: 'lines' as const,
      name: `${lap1Name} Throttle`,
      line: { color: '#3b82f6', width: 2 },
      yaxis: 'y2',
    },
    {
      x: alignedData.positions,
      y: alignedData.lap2.throttle,
      type: 'scatter' as const,
      mode: 'lines' as const,
      name: `${lap2Name} Throttle`,
      line: { color: '#ef4444', width: 2 },
      yaxis: 'y2',
    },
    // Brake comparison
    {
      x: alignedData.positions,
      y: alignedData.lap1.brake.map(v => v ? -v : v),
      type: 'scatter' as const,
      mode: 'lines' as const,
      name: `${lap1Name} Brake`,
      line: { color: '#60a5fa', width: 2 },
      yaxis: 'y2',
    },
    {
      x: alignedData.positions,
      y: alignedData.lap2.brake.map(v => v ? -v : v),
      type: 'scatter' as const,
      mode: 'lines' as const,
      name: `${lap2Name} Brake`,
      line: { color: '#f87171', width: 2 },
      yaxis: 'y2',
    },
    // Steering comparison
    {
      x: alignedData.positions,
      y: alignedData.lap1.steering,
      type: 'scatter' as const,
      mode: 'lines' as const,
      name: `${lap1Name} Steering`,
      line: { color: '#3b82f6', width: 2 },
      yaxis: 'y3',
    },
    {
      x: alignedData.positions,
      y: alignedData.lap2.steering,
      type: 'scatter' as const,
      mode: 'lines' as const,
      name: `${lap2Name} Steering`,
      line: { color: '#ef4444', width: 2 },
      yaxis: 'y3',
    },
    // Time delta
    {
      x: alignedData.positions,
      y: timeDelta,
      type: 'scatter' as const,
      mode: 'lines' as const,
      name: 'Time Delta (Lap1 - Lap2)',
      line: { color: '#8b5cf6', width: 3 },
      fill: 'tozeroy' as const,
      fillcolor: 'rgba(139, 92, 246, 0.2)',
      yaxis: 'y4',
    },
  ];

  const layout = {
    height: 1600,
    hovermode: 'x unified' as const,
    showlegend: true,
    legend: {
      orientation: 'h' as const,
      y: 1.02,
      x: 0,
    },
    xaxis: {
      title: 'Track Position (%)',
      domain: [0, 1],
    },
    yaxis: {
      title: 'Speed (km/h)',
      domain: [0.78, 0.98],
    },
    yaxis2: {
      title: 'Throttle/Brake (%)',
      domain: [0.53, 0.73],
      range: [-100, 100],
    },
    yaxis3: {
      title: 'Steering',
      domain: [0.28, 0.48],
      range: [-1.1, 1.1],
    },
    yaxis4: {
      title: 'Time Delta (s)',
      domain: [0, 0.23],
    },
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-6 flex items-center justify-between">
          <h1 className="text-3xl font-bold text-gray-900">Lap Comparison</h1>
          <Button onClick={() => navigate('/')}>
            Back to Telemetry
          </Button>
        </div>

        <Card className="mb-6">
          <CardHeader>
            <CardTitle>Select Laps to Compare</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Lap 1 (Blue)
                </label>
                <select
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  value={lap1Index}
                  onChange={(e) => setLap1Index(Number(e.target.value))}
                >
                  {comparisonCart.map((item, index) => (
                    <option key={index} value={index}>
                      {item.videoName} - Lap {item.lapNumber}
                      {item.lapTime && ` (${item.lapTime})`}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Lap 2 (Red)
                </label>
                <select
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  value={lap2Index}
                  onChange={(e) => setLap2Index(Number(e.target.value))}
                >
                  {comparisonCart.map((item, index) => (
                    <option key={index} value={index}>
                      {item.videoName} - Lap {item.lapNumber}
                      {item.lapTime && ` (${item.lapTime})`}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Position-Based Comparison</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="mb-4 p-4 bg-blue-50 rounded-lg">
              <p className="text-sm text-gray-700">
                <strong>How to read:</strong> Time delta shows where time is gained/lost.
                Negative values (below zero) mean Lap 1 (blue) is faster at that point.
                Positive values mean Lap 2 (red) is faster.
              </p>
            </div>
            <Plot
              data={plotData}
              layout={layout}
              config={{
                responsive: true,
                displayModeBar: true,
                displaylogo: false,
              }}
              style={{ width: '100%' }}
            />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
