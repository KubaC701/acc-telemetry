# ACC Telemetry Web App - Progress Report

## ✅ Completed Backend (FastAPI)

### 1. Project Structure
```
src/web/
├── __init__.py
├── main.py                  # FastAPI app entry point
├── config.py                # Settings and configuration
├── models.py                # Pydantic models for API
├── api/
│   ├── __init__.py
│   ├── videos.py            # Video management endpoints
│   ├── telemetry.py         # Telemetry data endpoints
│   └── jobs.py              # Job status tracking endpoints
└── services/
    ├── __init__.py
    ├── storage.py           # File management service
    ├── processing.py        # Video processing service
    └── jobs.py              # Job tracking service
```

### 2. API Endpoints Implemented

#### Video Management (`/api/videos`)
- `GET /api/videos` - List all processed videos
- `GET /api/videos/{video_name}` - Get video metadata
- `POST /api/videos/process` - Start video processing (background task)
- `DELETE /api/videos/{video_name}` - Delete video data

#### Telemetry Data (`/api/telemetry`)
- `GET /api/telemetry/{video_name}/laps` - Get lap list
- `GET /api/telemetry/{video_name}/laps/{lap_number}` - Get single lap data
- `GET /api/telemetry/{video_name}/csv` - Download full CSV
- `GET /api/telemetry/{video_name}/data` - Get filtered JSON data
- `GET /api/telemetry/{video_name}/summary` - Get summary statistics

#### Job Tracking (`/api/jobs`)
- `GET /api/jobs/{job_id}/status` - Get job status
- `GET /api/jobs/{job_id}/progress` - Stream progress updates (SSE)
- `DELETE /api/jobs/{job_id}` - Delete job

### 3. Key Features
- ✅ CORS enabled for local development
- ✅ Background task processing
- ✅ Server-Sent Events for real-time progress
- ✅ File-based storage organized by video name
- ✅ Automatic video name sanitization
- ✅ Comprehensive error handling

### 4. Data Organization
Videos are now organized as:
```
data/output/
├── panorama/
│   ├── telemetry.csv
│   └── metadata.json
└── silverstone_race/
    ├── telemetry.csv
    └── metadata.json
```

## 🚧 In Progress - Frontend (React + Vite + TypeScript)

### 1. Setup Complete
- ✅ React + Vite + TypeScript project created
- ✅ Dependencies installed:
  - react-plotly.js & plotly.js (charts)
  - @tanstack/react-query (server state)
  - axios (HTTP client)
  - zustand (UI state)
  - tailwindcss (styling)

### 2. Next Steps for Frontend

#### Components to Create
1. **VideoList.tsx** - Display processed videos, select one to view
2. **VideoProcessForm.tsx** - Form to process new video (input video path)
3. **LapSelector.tsx** - Lap checkboxes + "See All" toggle
4. **TelemetryChart.tsx** - Main Plotly chart with 7 subplots
5. **SyncedCursor.tsx** - Vertical line that follows cursor
6. **UnifiedTooltip.tsx** - Custom tooltip showing all frame data
7. **ProcessingProgress.tsx** - Progress bar with SSE updates

#### Services/Hooks to Create
1. **src/services/api.ts** - Axios client with typed endpoints
2. **src/hooks/useVideoList.ts** - Fetch videos list
3. **src/hooks/useTelemetry.ts** - Fetch telemetry data
4. **src/hooks/useProcessing.ts** - Handle video processing + progress
5. **src/types/index.ts** - TypeScript interfaces matching Pydantic models

#### Features to Implement
1. **Synced Vertical Cursor**
   - Use Plotly `hovermode: 'x unified'`
   - Add custom vertical line via `shapes` array
   - Update on `plotly_hover` event

2. **Unified Tooltip**
   - Floating div positioned at cursor
   - Shows all telemetry for current frame
   - Formatted: Frame | Time | Lap | Throttle | Brake | etc.

3. **Lap Comparison**
   - "See All" mode (default) - overlay all laps
   - Checkbox mode - select specific laps
   - Position-based alignment using existing backend logic
   - Delta plot when comparing 2 laps

## 📝 Usage Instructions (When Complete)

### Starting the Application

1. **Start Backend Server**
   ```bash
   python run_server.py
   # API will be available at http://localhost:8000
   # API docs at http://localhost:8000/docs
   ```

2. **Start Frontend Dev Server**
   ```bash
   cd frontend
   npm run dev
   # UI will be available at http://localhost:5173
   ```

### Processing a Video

1. Open frontend at `http://localhost:5173`
2. Click "Process New Video"
3. Enter video path (e.g., `/path/to/panorama.mp4`)
4. Watch progress bar update in real-time
5. Once complete, video appears in list

### Viewing Telemetry

1. Click on a video from the list
2. See all laps overlaid by default ("See All" mode)
3. Use checkboxes to select specific laps
4. Hover over any chart to see:
   - Synced vertical cursor across all plots
   - Unified tooltip with all data at that frame
5. Click and drag to zoom
6. Pan while zoomed

### Comparing Laps

1. Uncheck "See All"
2. Check 2 or more laps
3. Charts update to show only selected laps
4. If 2 laps: delta plot appears showing time gained/lost
5. Position-based alignment ensures accurate comparison

## 🔧 Technical Details

### Backend Technology Stack
- **FastAPI** - Modern async web framework
- **Pydantic** - Data validation and serialization
- **SSE (Server-Sent Events)** - Real-time progress updates
- **Background Tasks** - Non-blocking video processing
- **Pandas** - Telemetry data manipulation

### Frontend Technology Stack
- **React 18** - UI framework
- **TypeScript** - Type safety
- **Vite** - Fast build tool and dev server
- **Plotly.js** - Interactive charts
- **React Query** - Server state management
- **Zustand** - Lightweight UI state
- **TailwindCSS** - Utility-first styling
- **Axios** - HTTP client

### API Communication
- REST API for data fetching
- SSE for progress streaming
- JSON for telemetry data (not CSV)
- CORS enabled for cross-origin requests

## 🎯 Remaining Work

### High Priority
1. Create frontend components (VideoList, LapSelector, TelemetryChart)
2. Implement synced cursor and unified tooltip
3. Set up API service and React Query hooks
4. Configure TailwindCSS
5. Build main App.tsx layout

### Medium Priority
1. Add lap comparison features
2. Implement position-based alignment
3. Add delta plot for 2-lap comparison
4. Style with TailwindCSS
5. Add responsive design

### Low Priority (Future Enhancements)
1. Docker deployment configuration
2. User authentication (if multi-user needed)
3. Video upload (vs local file path)
4. Export features (PNG screenshots, filtered CSV)
5. ROI configuration UI
6. Track/car detection (auto-identify track)

## 📚 API Documentation

Once the server is running, visit:
- **Interactive Docs**: http://localhost:8000/docs
- **Alternative Docs**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/api/health

## 🚀 Next Session TODO

1. Create TailwindCSS config
2. Create TypeScript types matching Pydantic models
3. Build API service with typed Axios client
4. Create VideoList component
5. Create TelemetryChart with basic Plotly integration
6. Test end-to-end: process video → view in UI

---

**Note**: All existing CLI tools (`main.py`, `compare_laps_by_position.py`) still work independently. The web UI is an additional interface to the same underlying processing engine.
