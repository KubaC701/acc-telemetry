import React, { useState, useMemo, useEffect, useRef } from 'react';
import ReactECharts from 'echarts-for-react';
import * as echarts from 'echarts';
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

interface ChartConfig {
  key: keyof TelemetryDataPoint;
  title: string;
  color: string;
  comparisonColor: string;
  yAxis?: {
    min?: number;
    max?: number;
    type?: 'value' | 'category';
    splitNumber?: number;
    interval?: number;
  };
}

const CHART_CONFIGS: ChartConfig[] = [
  { key: 'throttle', title: 'Throttle', color: '#22c55e', comparisonColor: '#86efac', yAxis: { min: 0, max: 100, splitNumber: 2 } },
  { key: 'brake', title: 'Brake', color: '#ef4444', comparisonColor: '#fca5a5', yAxis: { min: 0, max: 100, splitNumber: 2 } },
  { key: 'steering', title: 'Steering', color: '#3b82f6', comparisonColor: '#93c5fd', yAxis: { splitNumber: 2 } },
  { key: 'speed', title: 'Speed', color: '#f97316', comparisonColor: '#fdba74', yAxis: { splitNumber: 4 } },
  { key: 'gear', title: 'Gear', color: '#a855f7', comparisonColor: '#d8b4fe', yAxis: { min: 0, max: 6, splitNumber: 2 } }, // Assuming max gear 8
  { key: 'tc_active', title: 'TC Active', color: '#eab308', comparisonColor: '#fde047', yAxis: { min: 0, max: 1, interval: 1 } },
  { key: 'abs_active', title: 'ABS Active', color: '#f59e0b', comparisonColor: '#fcd34d', yAxis: { min: 0, max: 1, interval: 1 } },
];

const ChartRow: React.FC<{
  config: ChartConfig;
  referenceData: any[];
  comparisonData?: any[];
  group: string;
  showXAxis: boolean;
  height: number;
  minTime: number;
  maxTime: number;
  onChartReady: (instance: echarts.ECharts) => void;
}> = ({ config, referenceData, comparisonData, group, showXAxis, height, minTime, maxTime, onChartReady }) => {
  
  const option = useMemo(() => {
    const series = [
      {
        name: 'Reference',
        type: 'line',
        data: referenceData,
        showSymbol: false,
        itemStyle: { color: config.color },
        lineStyle: { width: 2 },
        emphasis: { focus: 'series' },
        sampling: 'lttb', // Downsampling for performance
      },
      {
        name: 'Comparison',
        type: 'line',
        data: comparisonData || [],
        showSymbol: false,
        itemStyle: { color: config.comparisonColor },
        lineStyle: { width: 2, type: 'dashed' } as any,
        emphasis: { focus: 'series' },
        sampling: 'lttb',
      }
    ];

    return {
      title: {
        text: config.title,
        left: 5,
        top: 5,
        textStyle: {
          fontSize: 12,
          color: '#94a3b8'
        }
      },
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'line',
          label: {
            backgroundColor: '#6a7985'
          }
        },
        backgroundColor: 'rgba(30, 41, 59, 0.9)',
        borderColor: '#334155',
        textStyle: {
          color: '#f8fafc'
        },
        formatter: (params: any) => {
          let result = `Time: ${params[0].axisValueLabel}s<br/>`;
          params.forEach((param: any) => {
            const val = param.value[1];
            result += `${param.marker} ${param.seriesName}: ${typeof val === 'number' ? val.toFixed(2) : val}<br/>`;
          });
          return result;
        }
      },
      toolbox: {
        feature: {
          dataZoom: {
            yAxisIndex: 'none',
            title: {
              zoom: 'Zoom',
              back: 'Reset Zoom'
            }
          }
        },
        iconStyle: {
          borderColor: '#94a3b8'
        },
        right: 20,
        top: 0
      },
      grid: {
        left: 50,
        right: 20,
        top: 30,
        bottom: showXAxis ? 25 : 5,
        containLabel: false
      },
      xAxis: {
        type: 'value',
        min: minTime,
        max: maxTime,
        boundaryGap: false,
        axisLabel: {
          show: showXAxis,
          color: '#94a3b8',
          formatter: (value: number) => value.toFixed(1) + 's'
        },
        axisLine: {
          show: showXAxis,
          lineStyle: { color: '#475569' }
        },
        splitLine: {
          show: true,
          lineStyle: { color: '#334155', type: 'dashed' }
        }
      },
      yAxis: {
        type: 'value',
        min: config.yAxis?.min,
        max: config.yAxis?.max,
        splitNumber: config.yAxis?.splitNumber,
        interval: config.yAxis?.interval,
        splitLine: {
          lineStyle: { color: '#334155' }
        },
        axisLabel: {
          color: '#94a3b8'
        }
      },
      dataZoom: [
        {
          type: 'inside',
          xAxisIndex: 0,
          filterMode: 'filter'
        },
        {
          type: 'slider',
          xAxisIndex: 0,
          show: showXAxis,
          height: 20,
          bottom: 5,
          borderColor: '#334155',
          fillerColor: 'rgba(59, 130, 246, 0.2)',
          handleStyle: {
            color: '#3b82f6'
          },
          textStyle: {
            color: '#94a3b8'
          }
        }
      ],
      series: series,
      animation: false, // Disable animation for performance
    };
  }, [config, referenceData, comparisonData, showXAxis]);

  return (
    <ReactECharts
      option={option}
      style={{ height: height, width: '100%' }}
      onChartReady={(instance) => {
        instance.group = group;
        onChartReady(instance);
      }}
      opts={{ renderer: 'canvas' }}
    />
  );
};

export const TelemetryChartsECharts: React.FC<TelemetryChartsProps> = ({ referenceData, comparisonData }) => {
  const [timeOffset, setTimeOffset] = useState<number>(0);
  const chartInstances = useRef<echarts.ECharts[]>([]);

  // Prepare data for ECharts (array of [x, y])
  // Memoize this to avoid expensive recalculations
  const processedRefData = useMemo(() => {
    if (!referenceData) return {};
    const result: Record<string, number[][]> = {};
    
    CHART_CONFIGS.forEach(config => {
      result[config.key] = referenceData.map(d => [d.time, d[config.key] as number]);
    });
    
    return result;
  }, [referenceData]);

  const processedCompData = useMemo(() => {
    if (!comparisonData) return undefined;
    const result: Record<string, number[][]> = {};
    
    CHART_CONFIGS.forEach(config => {
      result[config.key] = comparisonData.map(d => [d.time + timeOffset, d[config.key] as number]);
    });
    
    return result;
  }, [comparisonData, timeOffset]);

  // Calculate global min/max time for X-axis scaling
  const { minTime, maxTime } = useMemo(() => {
    if (!referenceData || referenceData.length === 0) return { minTime: 0, maxTime: 100 };
    
    let min = referenceData[0].time;
    let max = referenceData[referenceData.length - 1].time;
    
    if (comparisonData && comparisonData.length > 0) {
      const compMin = comparisonData[0].time + timeOffset;
      const compMax = comparisonData[comparisonData.length - 1].time + timeOffset;
      
      min = Math.min(min, compMin);
      max = Math.max(max, compMax);
    }
    
    return { minTime: min, maxTime: max };
  }, [referenceData, comparisonData, timeOffset]);

  // Connect charts when they are all ready
  useEffect(() => {
    // We need to wait a bit for all instances to be registered
    const timer = setTimeout(() => {
      if (chartInstances.current.length > 0) {
        echarts.connect(chartInstances.current);
      }
    }, 100);
    return () => clearTimeout(timer);
  }, [referenceData, comparisonData]); // Re-connect if data changes (charts might re-mount)

  const handleChartReady = (instance: echarts.ECharts) => {
    if (!chartInstances.current.includes(instance)) {
      chartInstances.current.push(instance);
    }
  };

  if (!referenceData || referenceData.length === 0) {
    return <div className="text-center text-slate-500 mt-10">No telemetry data available</div>;
  }

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
          onClick={() => {
             chartInstances.current.forEach(chart => {
                 chart.dispatchAction({
                     type: 'dataZoom',
                     start: 0,
                     end: 100
                 });
             });
          }}
          className="px-3 py-1 text-xs bg-blue-600 hover:bg-blue-500 text-white rounded shadow-sm transition-colors"
        >
          Reset Zoom
        </button>
      </div>

      {CHART_CONFIGS.map((config, index) => (
        <ChartRow
          key={config.key}
          config={config}
          referenceData={processedRefData[config.key]}
          comparisonData={processedCompData ? processedCompData[config.key] : undefined}
          group="telemetry_group"
          showXAxis={index === CHART_CONFIGS.length - 1}
          height={150}
          minTime={minTime}
          maxTime={maxTime}
          onChartReady={handleChartReady}
        />
      ))}
    </div>
  );
};
