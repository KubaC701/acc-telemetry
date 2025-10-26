# Quick Start Guide - Web Application

This guide will help you quickly get the ACC Telemetry Extractor web application up and running.

## Prerequisites

- Python 3.8+ with virtual environment
- Node.js 18+ and npm
- All dependencies from [requirements.txt](requirements.txt)

## Start Both Servers

### Option 1: Using Separate Terminals

**Terminal 1 - Backend:**
```bash
# Activate virtual environment
source venv/bin/activate  # macOS/Linux
# or
venv\Scripts\activate     # Windows

# Start backend API
python run_server.py
```

The backend will run on [http://localhost:8000](http://localhost:8000)

**Terminal 2 - Frontend:**
```bash
# Navigate to frontend directory
cd frontend

# Install dependencies (first time only)
npm install

# Start development server
npm run dev
```

The frontend will run on [http://localhost:5173](http://localhost:5173)

### Option 2: Using Background Processes (macOS/Linux)

```bash
# Start backend in background
source venv/bin/activate && python run_server.py &

# Start frontend in background
cd frontend && npm run dev &

# View running processes
jobs

# Bring a process to foreground if needed
fg %1  # or %2
```

## Using the Web Interface

1. **Open your browser** to [http://localhost:5173](http://localhost:5173)

2. **Process a video:**
   - Enter the full path to your video file (e.g., `/Users/you/videos/acc-gameplay.mp4`)
   - Click "Process Video"
   - Watch the real-time progress bar

3. **View telemetry:**
   - Once processing completes, the video appears in the "Processed Videos" list
   - Click "View" to select the video
   - Interactive charts will appear on the right side

4. **Analyze laps:**
   - Click "Single Lap" to view individual lap data
   - Select a lap from the dropdown
   - Charts will update to show only that lap's telemetry

5. **Download data:**
   - Click "Download CSV" to export raw telemetry data
   - Use this data with external tools like MoTeC or your own analysis scripts

## API Documentation

Once the backend is running, visit [http://localhost:8000/docs](http://localhost:8000/docs) for interactive API documentation (Swagger UI).

## Default Video Paths

For testing, you can use these example paths (adjust to your system):
- macOS: `/Users/yourname/Videos/acc-gameplay.mp4`
- Linux: `/home/yourname/videos/acc-gameplay.mp4`
- Windows: `C:\Users\YourName\Videos\acc-gameplay.mp4`

## Stopping the Servers

**If running in terminals:**
- Press `Ctrl+C` in each terminal

**If running in background:**
```bash
# Find process IDs
ps aux | grep python
ps aux | grep node

# Kill by PID
kill <PID>

# Or use pkill
pkill -f "python run_server.py"
pkill -f "npm run dev"
```

## Troubleshooting

### Backend won't start
- Check Python version: `python --version` (should be 3.8+)
- Install missing dependencies: `pip install -r requirements.txt`
- Check port 8000 isn't already in use: `lsof -i :8000` (macOS/Linux)

### Frontend won't start
- Check Node version: `node --version` (should be 18+)
- Install dependencies: `cd frontend && npm install`
- Check port 5173 isn't already in use: `lsof -i :5173` (macOS/Linux)

### "Failed to load videos" in browser
- Ensure backend is running on port 8000
- Check browser console for CORS errors
- Verify `.env` file in `frontend/` contains `VITE_API_URL=http://localhost:8000`

### Video processing fails
- Ensure video file exists at the provided path
- Check video format is supported (MP4, AVI, MOV)
- Verify video has ACC HUD visible
- Check backend logs for detailed error messages

## Configuration

### Change Backend Port

Edit [src/web/config.py](src/web/config.py):
```python
api_port = 8001  # Change to desired port
```

Then update [frontend/.env](frontend/.env):
```
VITE_API_URL=http://localhost:8001
```

### Change Frontend Port

Edit [frontend/vite.config.ts](frontend/vite.config.ts):
```typescript
export default defineConfig({
  server: {
    port: 3000  // Change to desired port
  }
})
```

## Next Steps

- Read [frontend/README.md](frontend/README.md) for detailed frontend documentation
- Check [CLAUDE.md](CLAUDE.md) for computer vision implementation details
- See [compare_laps_by_position.py](compare_laps_by_position.py) for lap comparison tools
- Explore the API at [http://localhost:8000/docs](http://localhost:8000/docs)

## Production Deployment

For production deployment:

1. **Backend:** Use Gunicorn or Uvicorn with multiple workers
   ```bash
   uvicorn src.web.main:app --host 0.0.0.0 --port 8000 --workers 4
   ```

2. **Frontend:** Build and deploy static files
   ```bash
   cd frontend
   npm run build
   # Deploy the dist/ folder to your hosting service
   ```

See [frontend/README.md](frontend/README.md) for deployment options.
