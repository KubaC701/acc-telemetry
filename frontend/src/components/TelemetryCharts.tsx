import React, { useState, useMemo } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceArea,
  Legend,
} from 'recharts';
import { Settings2 } from 'lucide-react';

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
  track_position?: number;
}

interface TelemetryChartsProps {
  referenceData: TelemetryDataPoint[];
  comparisonData?: TelemetryDataPoint[];
  height?: number;
}

interface ChartRowProps {
  title: string;
  referenceData: TelemetryDataPoint[];
  comparisonData?: TelemetryDataPoint[];
  dataKey: keyof TelemetryDataPoint;
  color: string;
  comparisonColor: string;
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
  referenceData,
  comparisonData,
  dataKey,
  color,
  comparisonColor,
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
      </div>
      <div className="flex-1 min-h-0 select-none">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart
            data={referenceData}
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
              formatter={(value: number, name: string) => [value.toFixed(2), name]}
              labelFormatter={(label) => `Time: ${Number(label).toFixed(2)}s`}
            />
            <Legend wrapperStyle={{ fontSize: '10px' }} />
            
            {/* Reference Line */}
            <Line
              name="Reference"
              data={referenceData}
              type="monotone"
              dataKey={dataKey}
              stroke={color}
              strokeWidth={2}
              dot={false}
              isAnimationActive={false}
            />

            {/* Comparison Line */}
            {comparisonData && (
              <Line
                name="Comparison"
                data={comparisonData}
                type="monotone"
                dataKey={dataKey}
                stroke={comparisonColor}
                strokeWidth={2}
                strokeDasharray="4 4"
                dot={false}
                isAnimationActive={false}
              />
            )}

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

export const TelemetryCharts: React.FC<TelemetryChartsProps> = ({ referenceData, comparisonData }) => {
  const [xAxisDomain, setXAxisDomain] = useState<[number | 'dataMin', number | 'dataMax']>(['dataMin', 'dataMax']);
  const [refAreaLeft, setRefAreaLeft] = useState<string | number | undefined>(undefined);
  const [refAreaRight, setRefAreaRight] = useState<string | number | undefined>(undefined);
  const [timeOffset, setTimeOffset] = useState<number>(0);

  // Per-chart Y-axis auto state
  const [autoYState, setAutoYState] = useState<Record<string, boolean>>({
    throttle: false,
    brake: false,
    steering: true,
    speed: true,
    gear: false,
    tc_active: false,
    abs_active: false,
  });

  // Shift comparison data based on time offset
  const shiftedComparisonData = useMemo(() => {
    if (!comparisonData) return undefined;
    if (timeOffset === 0) return comparisonData;
    
    return comparisonData.map(point => ({
      ...point,
      time: point.time + timeOffset
    }));
  }, [comparisonData, timeOffset]);

  if (!referenceData || referenceData.length === 0) {
    return <div className="text-center text-slate-500 mt-10">No telemetry data available</div>;
  }

  const zoom = () => {
    if (refAreaLeft === refAreaRight || refAreaRight === undefined || refAreaLeft === undefined) {
      setRefAreaLeft(undefined);
      setRefAreaRight(undefined);
      return;
    }

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
    { key: 'throttle', title: 'Throttle', color: '#22c55e', comparisonColor: '#86efac', defaultDomain: [0, 100] as [number, number] },
    { key: 'brake', title: 'Brake', color: '#ef4444', comparisonColor: '#fca5a5', defaultDomain: [0, 100] as [number, number] },
    { key: 'steering', title: 'Steering', color: '#3b82f6', comparisonColor: '#93c5fd', defaultDomain: ['auto', 'auto'] as ['auto', 'auto'] },
    { key: 'speed', title: 'Speed', color: '#f97316', comparisonColor: '#fdba74', defaultDomain: ['auto', 'auto'] as ['auto', 'auto'] },
    { key: 'gear', title: 'Gear', color: '#a855f7', comparisonColor: '#d8b4fe', defaultDomain: [1, 6] as [number, number] },
    { key: 'tc_active', title: 'TC Active', color: '#eab308', comparisonColor: '#fde047', defaultDomain: [0, 1] as [number, number] },
    { key: 'abs_active', title: 'ABS Active', color: '#f59e0b', comparisonColor: '#fcd34d', defaultDomain: [0, 1] as [number, number] },
  ];

  return (
    <div className="flex flex-col w-full h-full bg-slate-900/50 rounded-lg p-4 space-y-2 overflow-y-auto">
      <div className="flex justify-between items-center mb-2 sticky top-0 z-10 bg-slate-900/90 p-2 rounded backdrop-blur-sm">
        
        {/* Manual Alignment Controls */}
        {comparisonData && (
          <div className="flex items-center gap-4 bg-slate-800/50 px-3 py-1 rounded border border-slate-700">
            <Settings2 size={16} className="text-slate-400" />
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-400 font-medium">Offset:</span>
              <input
                type="range"
                min="-5"
                max="5"
                step="0.01"
                value={timeOffset}
                onChange={(e) => setTimeOffset(parseFloat(e.target.value))}
                className="w-32 h-1 bg-slate-600 rounded-lg appearance-none cursor-pointer accent-blue-500"
              />
              <span className="text-xs font-mono w-12 text-right">{timeOffset > 0 ? '+' : ''}{timeOffset.toFixed(2)}s</span>
            </div>
            <button 
              onClick={() => setTimeOffset(0)}
              className="text-xs text-slate-500 hover:text-slate-300 underline"
            >
              Reset
            </button>
          </div>
        )}

        <div className="flex-1"></div>

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
          referenceData={referenceData}
          comparisonData={shiftedComparisonData}
          dataKey={config.key as keyof TelemetryDataPoint}
          color={config.color}
          comparisonColor={config.comparisonColor}
          defaultDomain={config.defaultDomain}
          height={chartHeight}
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
