import React, { useRef, useState } from 'react';
import { Upload, FileVideo, ChevronLeft, ChevronRight, ChevronDown, ChevronUp } from 'lucide-react';
import type { VideoListItem, VideoMetadata } from '../services/api';
import clsx from 'clsx';

interface SidebarProps {
  videos: VideoListItem[];
  videoMetadata: Record<string, VideoMetadata>;
  selectedReference: { video: string; lap: number } | null;
  selectedComparison: { video: string; lap: number } | null;
  onSelectReference: (video: string, lap: number) => void;
  onSelectComparison: (video: string, lap: number) => void;
  onExpandVideo: (videoName: string) => void;
  onUpload: (file: File) => void;
  isOpen: boolean;
  onToggle: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  videos,
  videoMetadata,
  selectedReference,
  selectedComparison,
  onSelectReference,
  onSelectComparison,
  onExpandVideo,
  onUpload,
  isOpen,
  onToggle,
}) => {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [expandedVideos, setExpandedVideos] = useState<Set<string>>(new Set());

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      onUpload(file);
    }
  };

  const toggleVideo = (videoName: string) => {
    const newExpanded = new Set(expandedVideos);
    if (newExpanded.has(videoName)) {
      newExpanded.delete(videoName);
    } else {
      newExpanded.add(videoName);
      onExpandVideo(videoName);
    }
    setExpandedVideos(newExpanded);
  };

  const formatTime = (seconds: number) => {
    const m = Math.floor(seconds / 60);
    const s = (seconds % 60).toFixed(3);
    return `${m}:${s.padStart(6, '0')}`;
  };

  return (
    <div
      className={clsx(
        "fixed left-0 top-0 h-full bg-slate-900/95 backdrop-blur-md border-r border-slate-800/50 transition-all duration-300 ease-in-out flex flex-col z-20 shadow-xl",
        isOpen ? "w-80" : "w-16"
      )}
    >
      <div className="h-16 flex items-center justify-between px-4 border-b border-slate-800/50 shrink-0">
        <div className={clsx("overflow-hidden transition-all duration-300", isOpen ? "w-full opacity-100" : "w-0 opacity-0")}>
           <h1 className="text-lg font-bold bg-gradient-to-r from-blue-400 to-indigo-400 bg-clip-text text-transparent truncate">
            Telemetry
          </h1>
        </div>
        <button
          onClick={onToggle}
          className="p-2 rounded-lg hover:bg-slate-800/50 text-slate-400 hover:text-slate-100 transition-colors shrink-0"
        >
          {isOpen ? <ChevronLeft size={20} /> : <ChevronRight size={20} />}
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-2 scrollbar-thin scrollbar-thumb-slate-700 scrollbar-track-transparent">
        {videos.map((video) => {
          const isExpanded = expandedVideos.has(video.video_name);
          const metadata = videoMetadata[video.video_name];
          
          return (
            <div key={video.video_name} className="flex flex-col gap-1">
              <button
                onClick={() => toggleVideo(video.video_name)}
                className={clsx(
                  "w-full text-left p-2.5 rounded-lg flex items-center gap-3 transition-all duration-200 group relative overflow-hidden",
                  isExpanded
                    ? "bg-slate-800/80 text-slate-200"
                    : "hover:bg-slate-800/50 text-slate-400 hover:text-slate-200"
                )}
                title={video.video_name}
              >
                <FileVideo size={20} className="shrink-0 text-slate-500 group-hover:text-slate-300" />
                <span className={clsx(
                  "truncate text-sm font-medium transition-all duration-300 flex-1",
                  isOpen ? "opacity-100 translate-x-0" : "opacity-0 -translate-x-4 absolute"
                )}>
                  {video.video_name}
                </span>
                {isOpen && (
                  isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />
                )}
              </button>

              {/* Laps List */}
              {isExpanded && isOpen && metadata && (
                <div className="pl-4 pr-1 space-y-1 animate-in slide-in-from-top-2 duration-200">
                  {metadata.laps.map((lap) => {
                    const isRef = selectedReference?.video === video.video_name && selectedReference?.lap === lap.lap_number;
                    const isComp = selectedComparison?.video === video.video_name && selectedComparison?.lap === lap.lap_number;

                    return (
                      <div 
                        key={lap.lap_number}
                        className={clsx(
                          "flex items-center justify-between p-2 rounded text-xs transition-colors",
                          (isRef || isComp) ? "bg-slate-800" : "hover:bg-slate-800/30"
                        )}
                      >
                        <div className="flex items-center gap-2 text-slate-300">
                          <span className="font-mono text-slate-500 w-4">{lap.lap_number}</span>
                          <span className="font-mono">{formatTime(lap.lap_time)}</span>
                        </div>
                        
                        <div className="flex gap-1">
                          <button
                            onClick={(e) => { e.stopPropagation(); onSelectReference(video.video_name, lap.lap_number); }}
                            className={clsx(
                              "px-2 py-0.5 rounded text-[10px] font-bold transition-colors border",
                              isRef 
                                ? "bg-blue-600 border-blue-500 text-white" 
                                : "bg-slate-900 border-slate-700 text-slate-500 hover:border-blue-500/50 hover:text-blue-400"
                            )}
                            title="Set as Reference"
                          >
                            R
                          </button>
                          <button
                            onClick={(e) => { e.stopPropagation(); onSelectComparison(video.video_name, lap.lap_number); }}
                            className={clsx(
                              "px-2 py-0.5 rounded text-[10px] font-bold transition-colors border",
                              isComp
                                ? "bg-purple-600 border-purple-500 text-white"
                                : "bg-slate-900 border-slate-700 text-slate-500 hover:border-purple-500/50 hover:text-purple-400"
                            )}
                            title="Set as Comparison"
                          >
                            C
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
              
              {isExpanded && isOpen && !metadata && (
                <div className="pl-8 py-2 text-xs text-slate-500 animate-pulse">
                  Loading laps...
                </div>
              )}
            </div>
          );
        })}
      </div>

      <div className="p-4 border-t border-slate-800/50 bg-slate-900/50 backdrop-blur-sm">
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleFileChange}
          accept="video/*"
          className="hidden"
        />
        <button
          onClick={() => fileInputRef.current?.click()}
          className={clsx(
            "w-full flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-500 text-white py-2.5 px-4 rounded-lg transition-all duration-200 shadow-lg shadow-blue-900/20 hover:shadow-blue-900/40 active:scale-[0.98]",
            !isOpen && "px-0"
          )}
          title="Upload Video"
        >
          <Upload size={20} />
          {isOpen && <span className="font-medium">Upload Video</span>}
        </button>
      </div>
    </div>
  );
};
