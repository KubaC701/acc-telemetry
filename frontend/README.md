# ACC Telemetry Extractor - Frontend

Modern React-based web interface for the ACC Telemetry Extractor, providing an intuitive way to upload, process, and visualize telemetry data from Assetto Corsa Competizione gameplay videos.

## Features

- **Video Upload & Processing**: Submit video files for telemetry extraction with real-time progress tracking
- **Interactive Visualizations**: View telemetry data with interactive Plotly charts including:
  - Throttle & Brake inputs
  - Steering position
  - Speed and gear
  - Track position
  - Combined multi-metric views
- **Lap-by-Lap Analysis**: View complete sessions or analyze individual laps
- **Job Management**: Track processing jobs with live progress updates
- **Video Library**: Browse and manage processed videos
- **CSV Export**: Download raw telemetry data for external analysis

## Tech Stack

- **Framework**: React 19 + TypeScript
- **Build Tool**: Vite
- **Styling**: Tailwind CSS 4
- **State Management**: Zustand
- **Data Fetching**: TanStack Query (React Query)
- **Visualization**: Plotly.js via react-plotly.js
- **HTTP Client**: Axios

## Getting Started

### Prerequisites

- Node.js 18+ and npm
- Backend API running (see main project README)

### Installation

```bash
# Install dependencies
npm install

# Create environment file (or copy .env.example to .env)
echo "VITE_API_URL=http://localhost:8000" > .env

# Start development server
npm run dev
```

The frontend will be available at [http://localhost:5173](http://localhost:5173)

### Building for Production

```bash
# Build optimized production bundle
npm run build

# Preview production build locally
npm run preview
```

The build output will be in the `dist/` directory.

## Project Structure

```
frontend/
├── src/
│   ├── components/          # React components
│   │   ├── ui/             # Reusable UI components (Button, Card, Input, etc.)
│   │   ├── VideoUpload.tsx # Video file upload form
│   │   ├── VideoList.tsx   # List of processed videos
│   │   ├── JobStatus.tsx   # Job progress tracking
│   │   └── TelemetryVisualization.tsx  # Plotly charts
│   ├── lib/
│   │   └── api.ts          # API client functions
│   ├── store/
│   │   └── useAppStore.ts  # Zustand state management
│   ├── types/
│   │   └── api.ts          # TypeScript type definitions
│   ├── App.tsx             # Main application component
│   ├── main.tsx            # Application entry point
│   └── index.css           # Global styles with Tailwind
├── public/                 # Static assets
└── index.html              # HTML template
```

## Component Overview

### VideoUpload
Form for submitting video file paths to the backend for processing. Displays success/error messages and triggers job creation.

### VideoList
Displays all processed videos with metadata (file size, creation date, lap count). Provides actions to view telemetry, download CSV, or delete videos.

### JobStatus & JobsList
Real-time job monitoring with progress bars and status updates. Automatically polls the backend for updates while jobs are processing.

### TelemetryVisualization
Interactive Plotly charts for visualizing extracted telemetry data. Supports two modes:
- **All Laps**: View complete session data
- **Single Lap**: Analyze individual lap performance

Charts include:
- Speed & Gear
- Throttle & Brake (filled area chart)
- Steering Input
- Track Position
- Combined Overview (multi-axis)

## API Integration

The frontend communicates with the backend API running on port 8000 (configurable via `VITE_API_URL`).

### Endpoints Used

- `GET /api/videos` - List processed videos
- `GET /api/videos/{name}` - Get video metadata
- `POST /api/videos/process` - Start video processing
- `DELETE /api/videos/{name}` - Delete video and data
- `GET /api/telemetry/{name}` - Get all telemetry data
- `GET /api/telemetry/{name}/lap/{lap}` - Get single lap data
- `GET /api/telemetry/{name}/laps` - Get all laps metadata
- `GET /api/telemetry/{name}/csv` - Download CSV export
- `GET /api/jobs` - List all jobs
- `GET /api/jobs/{id}` - Get job status

## Configuration

### Environment Variables

- `VITE_API_URL`: Backend API base URL (default: `http://localhost:8000`)

### Polling Intervals

- Video list: 5 seconds
- Jobs list: 2 seconds
- Active job status: 1 second

These can be adjusted in the respective components.

## Development

### Available Scripts

- `npm run dev` - Start development server with HMR
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run lint` - Run ESLint

### Code Style

This project uses ESLint with TypeScript rules. Run `npm run lint` before committing.

## Deployment

The frontend is a static SPA that can be deployed to any static hosting service:

1. Build the project: `npm run build`
2. Deploy the `dist/` folder to your hosting provider
3. Configure the `VITE_API_URL` environment variable to point to your production API

Popular hosting options:
- Vercel
- Netlify
- GitHub Pages
- AWS S3 + CloudFront
- Azure Static Web Apps

## Troubleshooting

### "Failed to load videos" error
- Ensure the backend API is running on the configured port
- Check CORS settings in the backend
- Verify `VITE_API_URL` in `.env` is correct

### Charts not rendering
- Check browser console for errors
- Ensure telemetry data is being fetched successfully
- Verify Plotly.js is installed correctly

### Slow performance
- Check network tab for slow API responses
- Consider adjusting polling intervals
- Ensure backend is not overloaded with processing jobs

## License

This project is part of the ACC Telemetry Extractor and shares the same license.
