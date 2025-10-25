# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ACC Telemetry Extractor is a **computer vision tool** that extracts detailed telemetry data from Assetto Corsa Competizione gameplay videos. Designed for **console players (PS5/Xbox)** who lack native telemetry export, it analyzes on-screen HUD elements frame-by-frame to extract:

- Throttle/brake inputs (0-100%)
- Steering position (-1.0 to +1.0)
- Speed (km/h) and gear (1-6)
- Lap numbers and lap times
- Track position (0-100% via minimap analysis with Kalman filtering)
- TC/ABS activation status

**Core principle**: If you can see it on screen, we can extract it.

## Essential Commands

### Setup and Running
```bash
# Initial setup
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
pip install -r requirements.txt

# Extract telemetry (generates CSV + interactive HTML)
python main.py

# Optional: Generate detailed static analysis
python generate_detailed_analysis.py

# Compare laps by position (gold standard - shows where time is gained/lost)
python compare_laps_by_position.py data/output/telemetry_YYYYMMDD_HHMMSS.csv

# Compare laps by time (separate lap files)
python compare_laps.py lap1.csv lap2.csv
```

### Video Configuration
By default, main.py looks for `./panorama.mp4`. To use a different video, edit the `VIDEO_PATH` variable in [main.py](main.py:81).

## Architecture Overview

### Processing Pipeline
```
main.py (orchestrator)
  └─> VideoProcessor: Extract frames and ROI regions
  └─> TelemetryExtractor: Analyze ROI images using HSV color detection
  └─> LapDetector: Extract lap numbers, speed, gear, lap times
  └─> PositionTrackerV2: Track position on minimap (with Kalman filtering)
  └─> InteractiveTelemetryVisualizer: Generate CSV + interactive HTML graphs
```

### Core Modules

#### [src/telemetry_extractor.py](src/telemetry_extractor.py)
**Computer vision engine** for throttle/brake/steering detection:
- Uses **HSV color space** (more robust than RGB for varying lighting)
- `extract_bar_percentage()`: Detects filled portion of horizontal/vertical bars
- Multi-color detection: Handles TC/ABS color changes (green→yellow, red→orange)
- Noise filtering: Median-based measurements, minimum pixel thresholds
- See HSV ranges: Green (35-85°), Yellow (15-35°), Red (0-10° + 170-180°), Orange (10-40°)

#### [src/position_tracker_v2.py](src/position_tracker_v2.py)
**Minimap-based track position tracking**:
- Extracts white racing line from minimap using multi-frame frequency voting
- Detects red position dot and calculates track position (0-100%)
- **Kalman filtering**: Smooths position, rejects outliers (>10% jumps)
- State vector: `[position, velocity]` with constant velocity model
- Resets on lap transitions to maintain accuracy

#### [src/lap_detector.py](src/lap_detector.py)
**Fast lap number and OCR detection**:
- **Template matching** for lap numbers: 100-500x faster than OCR (~2ms vs ~50-250ms)
- **tesserocr** for speed/gear: Direct C++ API, ~2ms per frame
- **pytesseract** fallback for lap times: Used only at lap transitions (~50ms)
- Temporal smoothing: Majority voting across recent frames to filter noise

#### [src/interactive_visualizer.py](src/interactive_visualizer.py)
**Interactive Plotly visualizations**:
- Browser-based graphs with zoom, pan, hover tooltips
- Multi-lap overlay with dropdown selector
- Synchronized plots (throttle, brake, steering, speed, position)

### Configuration System

#### [config/roi_config.yaml](config/roi_config.yaml)
**ROI (Region of Interest) coordinates** for all HUD elements:
- Currently configured for **1280×720 (720p)** videos
- Each ROI defined as: `{x, y, width, height}` in pixels
- **Resolution dependency**: Coordinates must be recalibrated for different resolutions
  - 1080p: multiply by 1.5
  - 1440p: multiply by 2.0
  - 4K: multiply by 3.0

ROI regions defined:
- `throttle`: Horizontal green/yellow bar (bottom-right)
- `brake`: Horizontal red/orange bar (below throttle)
- `steering`: White dot indicator (above throttle)
- `speed`: Speed display (inside rev meter)
- `gear`: Gear number (center of rev meter)
- `lap_number`: Lap flag with number (top-left)
- `last_lap_time`: Completed lap time (top-left)
- `track_map`: Circular minimap (top-left, 269×183px)

## Key Technical Patterns

### 1. HSV Color Detection
All telemetry extraction uses **HSV color space** instead of BGR:
```python
hsv = cv2.cvtColor(roi_image, cv2.COLOR_BGR2HSV)
mask = cv2.inRange(hsv, lower_bound, upper_bound)
```

**Why HSV?** Separates color (hue) from brightness (value), making detection robust to lighting variations.

### 2. Multi-Color Detection for TC/ABS
Bars change color when driver aids activate:
- **Throttle**: Green normally → Yellow when TC active
- **Brake**: Red normally → Orange when ABS active

Handled by combining color masks:
```python
mask_green = cv2.inRange(hsv, lower_green, upper_green)
mask_yellow = cv2.inRange(hsv, lower_yellow, upper_yellow)
combined_mask = cv2.bitwise_or(mask_green, mask_yellow)
```

### 3. Template Matching for Performance
Lap number detection uses **template matching** instead of OCR:
- 100-500x faster (~2ms vs ~50-250ms per frame)
- Pre-extracted digit templates matched against ROI
- Falls back to OCR if confidence low
- See [src/lap_detector.py](src/lap_detector.py) `extract_lap_number()`

### 4. Kalman Filtering for Position Tracking
Position tracking includes outlier rejection:
- 1D Kalman filter tracks `[position, velocity]`
- Rejects measurements with >10% innovation (likely detection errors)
- Prevents false spikes in lap comparison graphs
- Enabled by default in [PositionTrackerV2](src/position_tracker_v2.py:33)

### 5. Temporal Smoothing
OCR results smoothed using majority voting:
```python
# Track last 5 detections
lap_number_history = [20, 21, 20, 21, 21]

# Use most common value if ≥40% agreement
most_common = Counter(lap_number_history).most_common(1)[0]
if most_common[1] >= max(2, len(history) * 0.4):
    return most_common[0]
```

## Common Development Tasks

### Debugging Incorrect Telemetry Values
1. **Extract ROI images** to verify correct regions are captured:
   ```python
   cv2.imwrite(f'debug_throttle_frame{frame_num}.png', roi_dict['throttle'])
   ```
2. **Save color masks** to check HSV detection:
   ```python
   cv2.imwrite(f'debug_mask.png', mask)
   ```
3. **Visualize ROI coordinates** on original frame:
   ```python
   cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
   cv2.imwrite('debug_frame_with_roi.png', frame)
   ```

### Calibrating for Different Video Resolutions
1. Extract sample frame: `python find_minimap_roi.py` (or similar helper script)
2. Open frame in image viewer with pixel coordinates (GIMP, Photoshop)
3. Locate HUD elements (throttle/brake bars usually bottom-right)
4. Measure coordinates and update [config/roi_config.yaml](config/roi_config.yaml)
5. Test with short clip first

### Tuning HSV Color Ranges
Edit ranges in [src/telemetry_extractor.py](src/telemetry_extractor.py):
```python
# Make green detection more permissive
lower_green = np.array([30, 40, 40])  # Lower saturation threshold
upper_green = np.array([90, 255, 255])  # Wider hue range
```

Print color statistics for debugging:
```python
print(f"Min HSV: {hsv.min(axis=(0,1))}")
print(f"Max HSV: {hsv.max(axis=(0,1))}")
```

### Adding New Telemetry Channel
1. Add ROI coordinates to [config/roi_config.yaml](config/roi_config.yaml)
2. Update `VideoProcessor.extract_roi()` to include new ROI
3. Add extraction method in [src/telemetry_extractor.py](src/telemetry_extractor.py)
4. Update `extract_frame_telemetry()` to call new method
5. Modify visualizer to plot new channel

## Important Notes

### ROI Extraction Strategy
- Keep ROIs **tight around UI elements** with 1-3px margin
- Sample **middle portions** of bars to avoid edge artifacts
- Use **median** instead of mean for robustness against outliers

### Red Color Detection Gotcha
Red wraps around in HSV (0° and 180° are both red). Must detect in **two ranges**:
```python
lower_red1 = np.array([0, 100, 100])    # Lower red
upper_red1 = np.array([10, 255, 255])
lower_red2 = np.array([170, 100, 100])  # Upper red
upper_red2 = np.array([180, 255, 255])
mask = cv2.bitwise_or(mask_red1, mask_red2)
```

### OCR Performance
- **Template matching** (lap numbers): ~2ms per frame
- **tesserocr** (speed/gear): ~2ms per frame
- **pytesseract** (lap times): ~50ms per transition (only when lap changes)
- Total per-frame processing: ~5-10ms (100-200 FPS capable)

### Position Tracking
- Requires `track_map` ROI in config
- Extracts white racing line from multiple frames (avoids red dot occlusion)
- Samples frames: [0, 50, 100, 150, 200, 250, 500, 750, 1000, 1250, 1500]
- Resets Kalman filter on lap transitions for accuracy

### File Outputs
All outputs in `data/output/`:
- `telemetry_YYYYMMDD_HHMMSS.csv` - Frame-by-frame raw data
- `telemetry_interactive_YYYYMMDD_HHMMSS.html` - Interactive Plotly graphs
- `lap_comparison_position_YYYYMMDD_HHMMSS.html` - Position-based comparison
- `telemetry_analysis_YYYYMMDD_HHMMSS.png` - Detailed static graphs (if using generate_detailed_analysis.py)

## Performance Considerations

### Bottlenecks
1. **Video I/O**: Reading frames from disk (OpenCV handles efficiently)
2. **OCR**: Lap time extraction (~50ms) - only runs at lap transitions
3. **Visualization**: Plotly graph generation (~2-5s) - only at end

### Optimization Notes
- Template matching eliminated 100-500x OCR slowdown for lap numbers
- Kalman filter adds <1ms overhead per frame
- Multi-frame track path extraction runs once at startup (not per-frame)

## Testing and Validation

### Quick Test Workflow
```bash
# Extract 10-second clip for fast iteration
ffmpeg -i input_video.mp4 -t 10 test_clip.mp4

# Update VIDEO_PATH in main.py to point to test_clip.mp4
python main.py
```

### Verification Checklist
- [ ] All telemetry values in expected ranges (0-100%, -1.0 to +1.0)
- [ ] No sustained 0% or 100% values (indicates ROI misconfiguration)
- [ ] Lap transitions detected correctly
- [ ] Position tracking shows smooth progression (0% → 100%)
- [ ] TC/ABS activation correlates with visible HUD color changes

## Known Limitations

1. **Resolution-dependent**: ROI coordinates must be recalibrated for different video resolutions
2. **HUD-dependent**: Requires default ACC HUD to be visible (custom HUDs unsupported)
3. **Post-processing only**: Not real-time (but console players record first anyway)
4. **Console-focused**: PC players have native telemetry export options
