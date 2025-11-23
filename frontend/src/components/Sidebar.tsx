import React, { useRef } from 'react';
import { Upload, FileVideo, ChevronLeft, ChevronRight } from 'lucide-react';
import type { VideoListItem } from '../services/api';
import clsx from 'clsx';

interface SidebarProps {
  videos: VideoListItem[];
  selectedVideo: string | null;
  onSelectVideo: (videoName: string) => void;
  onUpload: (file: File) => void;
  isOpen: boolean;
  onToggle: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  videos,
  selectedVideo,
  onSelectVideo,
  onUpload,
  isOpen,
  onToggle,
}) => {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      onUpload(file);
    }
  };

  return (
    <div
      className={clsx(
        "fixed left-0 top-0 h-full bg-slate-900 border-r border-slate-800 transition-all duration-300 flex flex-col z-20",
        isOpen ? "w-64" : "w-16"
      )}
    >
      <div className="p-4 flex items-center justify-between border-b border-slate-800">
        {isOpen && <h1 className="text-xl font-bold text-slate-100 truncate">Telemetry</h1>}
        <button
          onClick={onToggle}
          className="p-1 rounded hover:bg-slate-800 text-slate-400 hover:text-slate-100 transition-colors"
        >
          {isOpen ? <ChevronLeft size={20} /> : <ChevronRight size={20} />}
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-2 space-y-2">
        {videos.map((video) => (
          <button
            key={video.video_name}
            onClick={() => onSelectVideo(video.video_name)}
            className={clsx(
              "w-full text-left p-2 rounded flex items-center gap-3 transition-colors group",
              selectedVideo === video.video_name
                ? "bg-blue-600 text-white"
                : "hover:bg-slate-800 text-slate-400 hover:text-slate-100"
            )}
            title={video.video_name}
          >
            <FileVideo size={20} className="shrink-0" />
            {isOpen && <span className="truncate text-sm">{video.video_name}</span>}
          </button>
        ))}
      </div>

      <div className="p-4 border-t border-slate-800">
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
            "w-full flex items-center justify-center gap-2 bg-slate-800 hover:bg-slate-700 text-slate-200 py-2 px-4 rounded transition-colors",
            !isOpen && "px-0"
          )}
          title="Upload Video"
        >
          <Upload size={20} />
          {isOpen && <span>Upload Video</span>}
        </button>
      </div>
    </div>
  );
};
