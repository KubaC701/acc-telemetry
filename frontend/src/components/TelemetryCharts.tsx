import React, { useState } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceArea,
} from 'recharts';

interface TelemetryDataPoint {
  time: number;
  throttle: number;
  brake: number;
  steering: number;
  speed: number;
  gear: number;
  tc_active: number;
  abs_active: number;
  lap_number: number;
}

interface TelemetryChartsProps {
  data: TelemetryDataPoint[];
  height?: number;
}

interface ChartRowProps {
  title: string;
  data: TelemetryDataPoint[];
  dataKey: keyof TelemetryDataPoint;
  color: string;
  defaultDomain: [number, number] | ['auto', 'auto'];
  height: number;
  syncId: string;
  showXAxis?: boolean;
  xAxisDomain: [number | 'dataMin', number | 'dataMax'];
  yAxisDomain: [number | 'auto', number | 'auto'];
  onMouseDown: (e: any) => void;
  onMouseMove: (e: any) => void;
  onMouseUp: (e: any) => void;
  refAreaLeft?: string | number;
  refAreaRight?: string | number;
  onToggleYAxis: () => void;
  isAutoY: boolean;
}

const ChartRow: React.FC<ChartRowProps> = ({
  title,
  data,
  dataKey,
  color,
  height,
  syncId,
  showXAxis = false,
  xAxisDomain,
  yAxisDomain,
  onMouseDown,
  onMouseMove,
  onMouseUp,
  refAreaLeft,
  refAreaRight,
  onToggleYAxis,
  isAutoY,
}) => {
  return (
    <div className="w-full flex flex-col" style={{ height }}>
      <div className="flex justify-between items-center pl-2 mb-1 pr-4">
        <div className="text-xs font-semibold text-slate-400">{title}</div>
        <button
          onClick={onToggleYAxis}
          className={`text-[10px] px-2 py-0.5 rounded border transition-colors ${
            isAutoY
              ? 'bg-blue-500/20 text-blue-400 border-blue-500/50 hover:bg-blue-500/30'
              : 'bg-slate-800 text-slate-400 border-slate-700 hover:bg-slate-700'
          }`}
        >
          Auto Y
        </button>
      </div>
      <div className="flex-1 min-h-0 select-none">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart
            data={data}
            syncId={syncId}
            margin={{ top: 5, right: 30, left: 0, bottom: 5 }}
            onMouseDown={onMouseDown}
            onMouseMove={onMouseMove}
            onMouseUp={onMouseUp}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
            <XAxis
              dataKey="time"
              type="number"
              domain={xAxisDomain}
              allowDataOverflow
              hide={!showXAxis}
              tick={{ fill: '#94a3b8', fontSize: 12 }}
            />
            <YAxis
              domain={yAxisDomain}
              allowDataOverflow={true}
              tick={{ fill: '#94a3b8', fontSize: 12 }}
              width={40}
            />
            <Tooltip
              trigger="hover"
              contentStyle={{ backgroundColor: '#1e293b', borderColor: '#334155', color: '#f8fafc' }}
              itemStyle={{ color: '#f8fafc' }}
              labelStyle={{ color: '#94a3b8' }}
              formatter={(value: number) => [value.toFixed(2), title]}
              labelFormatter={(label) => `Time: ${Number(label).toFixed(2)}s`}
            />
            <Line
              type="monotone"
              dataKey={dataKey}
              stroke={color}
              strokeWidth={2}
              dot={false}
              isAnimationActive={false}
            />
            {refAreaLeft && refAreaRight ? (
              <ReferenceArea
                x1={refAreaLeft}
                x2={refAreaRight}
                strokeOpacity={0.3}
                fill="#3b82f6"
                fillOpacity={0.3}
              />
            ) : null}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

export const TelemetryCharts: React.FC<TelemetryChartsProps> = ({ data }) => {
  const [xAxisDomain, setXAxisDomain] = useState<[number | 'dataMin', number | 'dataMax']>(['dataMin', 'dataMax']);
  const [refAreaLeft, setRefAreaLeft] = useState<string | number | undefined>(undefined);
  const [refAreaRight, setRefAreaRight] = useState<string | number | undefined>(undefined);

  // Per-chart Y-axis auto state
  const [autoYState, setAutoYState] = useState<Record<string, boolean>>({
    throttle: false,
    brake: false,
    steering: true, // Default to auto as per original code
    speed: true,    // Default to auto as per original code
    gear: false,
    tc_active: false,
    abs_active: false,
  });

  if (!data || data.length === 0) {
    return <div className="text-center text-slate-500 mt-10">No telemetry data available</div>;
  }

  const zoom = () => {
    if (refAreaLeft === refAreaRight || refAreaRight === undefined || refAreaLeft === undefined) {
      setRefAreaLeft(undefined);
      setRefAreaRight(undefined);
      return;
    }

    // Ensure left is smaller than right
    let left = Number(refAreaLeft);
    let right = Number(refAreaRight);

    if (left > right) [left, right] = [right, left];

    setRefAreaLeft(undefined);
    setRefAreaRight(undefined);
    setXAxisDomain([left, right]);
  };

  const zoomOut = () => {
    setXAxisDomain(['dataMin', 'dataMax']);
    setRefAreaLeft(undefined);
    setRefAreaRight(undefined);
  };

  const toggleYAxis = (key: string) => {
    setAutoYState(prev => ({ ...prev, [key]: !prev[key] }));
  };

  const setGlobalAutoY = (enabled: boolean) => {
    const newState = Object.keys(autoYState).reduce((acc, key) => {
      acc[key] = enabled;
      return acc;
    }, {} as Record<string, boolean>);
    setAutoYState(newState);
  };

  const handleMouseDown = (e: any) => {
    if (e && e.activeLabel) setRefAreaLeft(e.activeLabel);
  };

  const handleMouseMove = (e: any) => {
    if (refAreaLeft && e && e.activeLabel) setRefAreaRight(e.activeLabel);
  };

  const handleMouseUp = () => {
    zoom();
  };

  const chartHeight = 150;

  const chartConfigs = [
    { key: 'throttle', title: 'Throttle', color: '#22c55e', defaultDomain: [0, 100] as [number, number] },
    { key: 'brake', title: 'Brake', color: '#ef4444', defaultDomain: [0, 100] as [number, number] },
    { key: 'steering', title: 'Steering', color: '#3b82f6', defaultDomain: ['auto', 'auto'] as ['auto', 'auto'] },
    { key: 'speed', title: 'Speed', color: '#f97316', defaultDomain: ['auto', 'auto'] as ['auto', 'auto'] },
        { key: 'gear', title: 'Gear', color: '#a855f7', defaultDomain: [1, 6] as [number, number] },
        { key: 'tc_active', title: 'TC Active', color: '#eab308', defaultDomain: [0, 1] as [number, number] },
    { key: 'abs_active', title: 'ABS Active', color: '#f59e0b', defaultDomain: [0, 1] as [number, number] },
  ];

  return (
    <div className="flex flex-col w-full h-full bg-slate-900/50 rounded-lg p-4 space-y-2 overflow-y-auto">
      <div className="flex justify-end space-x-2 mb-2 sticky top-0 z-10 bg-slate-900/90 p-2 rounded backdrop-blur-sm">
        <button
          onClick={() => setGlobalAutoY(true)}
          className="px-3 py-1 text-xs bg-slate-800 hover:bg-slate-700 text-slate-300 rounded border border-slate-700 transition-colors"
        >
          All Auto Y
        </button>
        <button
          onClick={() => setGlobalAutoY(false)}
          className="px-3 py-1 text-xs bg-slate-800 hover:bg-slate-700 text-slate-300 rounded border border-slate-700 transition-colors"
        >
          Reset Y
        </button>
        <button
          onClick={zoomOut}
          className="px-3 py-1 text-xs bg-blue-600 hover:bg-blue-500 text-white rounded shadow-sm transition-colors"
        >
          Reset Zoom
        </button>
      </div>

      {chartConfigs.map((config, index) => (
        <ChartRow
          key={config.key}
          title={config.title}
          data={data}
          dataKey={config.key as keyof TelemetryDataPoint}
          color={config.color}
          defaultDomain={config.defaultDomain}
          height={config.height || chartHeight}
          syncId="telemetry"
          showXAxis={index === chartConfigs.length - 1}
          xAxisDomain={xAxisDomain}
          yAxisDomain={autoYState[config.key] ? ['auto', 'auto'] : config.defaultDomain}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          refAreaLeft={refAreaLeft}
          refAreaRight={refAreaRight}
          onToggleYAxis={() => toggleYAxis(config.key)}
          isAutoY={autoYState[config.key]}
        />
      ))}
    </div>
  );
};
