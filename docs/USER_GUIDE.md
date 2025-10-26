# ACC Telemetry Extractor - User Guide

## Quick Start

```bash
# 1. Setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Extract telemetry from video
python main.py

# 3. Compare laps by position (recommended)
python compare_laps_by_position.py data/output/telemetry_YYYYMMDD_HHMMSS.csv

# 4. Compare laps by time (for separate videos)
python compare_laps.py lap1.csv lap2.csv
```

## Video Configuration

By default, main.py looks for `./panorama.mp4`. To use a different video:
- Edit the `VIDEO_PATH` variable in [main.py](../main.py:81)
- Or rename your video to `panorama.mp4`

## What You Get

### Output Files (in data/output/)

1. **CSV File**: `telemetry_YYYYMMDD_HHMMSS.csv`
   - Frame-by-frame data: throttle, brake, steering, speed, gear, lap number, track position
   - Import into Excel, Google Sheets, or analysis tools

2. **Interactive HTML**: `telemetry_interactive_YYYYMMDD_HHMMSS.html`
   - Browser-based visualization with zoom, pan, hover tooltips
   - Synchronized plots (throttle, brake, steering, speed)
   - Works offline, shareable

3. **Position-Based Comparison**: `lap_comparison_position_YYYYMMDD_HHMMSS.html`
   - Compare laps by track position (not time)
   - Shows time delta at each position
   - Interactive dropdown to select which laps to compare
   - **This is the gold standard for racing analysis**

## Interactive Visualization

### Features

The HTML visualizations provide professional-grade analysis:

- **Zoom**: Click and drag to zoom into any region
- **Pan**: Drag while zoomed to navigate
- **Hover**: See exact values at any point
- **Synchronized views**: All plots zoom together
- **Range slider**: Quick navigation timeline
- **Export**: Download as PNG from browser

### How to Use

1. **Open HTML file** in any modern browser (Chrome, Firefox, Safari, Edge)
2. **Explore the full lap**: Scroll through time using the range slider
3. **Zoom into sections**: Click-drag to select braking zones, corner entries
4. **Analyze technique**: Compare throttle/brake/steering smoothness

## Position-Based Lap Comparison

### Why Position-Based?

**Problem with time-based comparison:**
- If you brake earlier/later, the rest of the lap is out of sync
- Can't see WHERE on track you gain or lose time

**Solution with position-based:**
- Aligns laps by track position (0% = start/finish, 100% = back to start)
- Shows time delta at each position
- Directly compare inputs at the same corners

### Usage

```bash
python compare_laps_by_position.py data/output/telemetry_YYYYMMDD_HHMMSS.csv
```

### The Visualization

**5 Synchronized Plots:**
1. Throttle overlay (green vs red line)
2. Brake overlay
3. Steering overlay
4. Speed overlay
5. **Time Delta** - where you gain (negative) or lose (positive) time

**Dropdown Menu**: Select which two laps to compare

### Analysis Workflow

1. **Load comparison** - Tool auto-generates all pairwise comparisons
2. **Select laps** from dropdown (e.g., "Lap 22 vs Lap 23")
3. **Check time delta** - Where does it increase (losing time)?
4. **Zoom to problem areas** - Click-drag on the section
5. **Compare inputs** - Are you braking too early? Getting on throttle late?
6. **Repeat** - Try different lap combinations

### Example Analysis

**Time delta plot shows:**
- 0% position: 0.0s (equal start)
- 25% position: -0.5s (Lap A ahead)
- 50% position: -1.2s (Lap A more ahead)
- 75% position: -0.8s (Lap A lost some time)
- 100% position: -1.5s (Lap A 1.5s faster overall)

**Zoom to 50-75%** (where time was lost):
- Brake plot: Lap A braked earlier
- Speed plot: Lap A minimum corner speed lower
- Throttle plot: Lap A got on throttle later
- **Conclusion**: Braking too early, not carrying enough speed

## Understanding the Data

### CSV Columns

| Column | Range | Description |
|--------|-------|-------------|
| `frame` | 0-N | Frame number |
| `time` | 0.0-N.N | Time in seconds |
| `lap_number` | 1-99 | Current lap (from HUD) |
| `track_position` | 0.0-100.0 | Position around track (%) |
| `speed` | 0-300+ | Speed in km/h |
| `gear` | 1-6 | Current gear |
| `throttle` | 0.0-100.0 | Throttle input (%) |
| `brake` | 0.0-100.0 | Brake input (%) |
| `steering` | -1.0 to +1.0 | Steering (-1=full left, +1=full right) |
| `tc_active` | 0 or 1 | Traction control active |
| `abs_active` | 0 or 1 | ABS active |

### What "Good" Looks Like

**Throttle:**
- Long green sections (full throttle on straights)
- Smooth ramps (not jagged)
- Early application on corner exit

**Brake:**
- Sharp initial application
- Smooth trail-off
- No pumping (multiple spikes)

**Steering:**
- Smooth curves
- No sudden changes
- Minimal corrections (jagged = corrections = instability)

**Speed:**
- High minimum corner speeds
- Smooth acceleration/deceleration

## Common Use Cases

### 1. Find Your Braking Points

**Goal**: Understand where you brake at each corner

1. Open interactive HTML
2. Zoom into brake plot (red)
3. Note where brake spikes occur (track position %)
4. Use these as reference points for next session

### 2. Improve Consistency

**Goal**: Make sure you're doing the same thing every lap

1. Extract telemetry from 5 laps
2. Use position-based comparison to overlay all laps
3. Look for variations in:
   - Braking points (should be within 1% position)
   - Minimum corner speed (should vary <5 km/h)
   - Throttle application points
4. Focus on corners with most variation

### 3. Compare vs Faster Drivers

**Goal**: Learn from aliens

1. Download YouTube video of fast lap
2. Extract their telemetry
3. Extract your lap telemetry
4. Compare using position-based tool
5. Identify where they're different:
   - Braking later?
   - Carrying more speed?
   - On throttle earlier?

### 4. Analyze Driving Style

**Goal**: Understand your tendencies

1. Check full throttle % in statistics (should be 55-70% depending on track)
2. Look for trail braking (throttle overlay yellow = both pedals pressed)
3. Check steering smoothness (smooth = confident, jagged = corrections)
4. Analyze TC/ABS activation frequency

## Resolution Configuration

### Default: 1280×720 (720p)

ROI coordinates in `config/roi_config.yaml` are calibrated for 720p videos.

### Other Resolutions

**1920×1080 (1080p)**: Multiply all coordinates by 1.5
**2560×1440 (1440p)**: Multiply by 2.0
**3840×2160 (4K)**: Multiply by 3.0

**To recalibrate:**
1. Extract a frame: `python -c "import cv2; cap=cv2.VideoCapture('video.mp4'); ret,f=cap.read(); cv2.imwrite('frame.png',f)"`
2. Open in image viewer with pixel coordinates (GIMP, Photoshop)
3. Locate HUD elements and measure coordinates
4. Update `config/roi_config.yaml`

## Performance Expectations

### Processing Speed

**Typical performance on modern CPU (M1/M2, recent Intel i7/i9):**
- ~5-10ms per frame
- 30 FPS video = 100-200 FPS processing speed
- 10-minute video processes in ~1-2 minutes
- 30-minute video processes in ~5-8 minutes

**OCR Performance:**
- Template matching (lap numbers): ~2ms per frame
- tesserocr (speed/gear): ~2ms per frame
- pytesseract fallback: ~50ms per frame (if tesserocr unavailable)

### File Sizes

- CSV: ~1-2MB per 10 minutes of video
- Interactive HTML: ~4-5MB (includes Plotly library + data)
- Position comparison HTML: ~500KB per lap comparison

## Tips & Best Practices

### Recording Tips

1. **Keep HUD visible** - Tool requires default ACC HUD to be on screen
2. **Stable camera** - Minimize camera shake (use cockpit/bumper view)
3. **Good lighting** - Ensure HUD is clearly visible
4. **Full laps** - Record complete laps for best results
5. **High quality** - 1080p or higher recommended for OCR accuracy

### Analysis Tips

1. **Compare adjacent laps first** (22 vs 23, 23 vs 24) - easier to remember what changed
2. **Use position percentages as reference** - Learn which % = which corner
3. **Focus on one corner per session** - Don't try to fix everything at once
4. **Look for patterns** - If you always lose time in the same section, that's your weak point
5. **Share HTML files** - Send to coaches/teammates for feedback (they can zoom/analyze themselves)

### Data Quality

- **Full laps only**: Incomplete laps may have gaps
- **Clean laps**: Avoid laps with incidents or off-track
- **Multiple laps**: More data = better insights
- **Consistent conditions**: Compare laps from similar track/weather conditions

## Troubleshooting

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for detailed solutions to common issues.

**Quick fixes:**

- **No data extracted**: Check ROI coordinates match your video resolution
- **Wrong values**: Verify HUD is visible and not obscured
- **No lap numbers**: Ensure lap indicator is visible in top-left of screen
- **No position data**: Configure `track_map` ROI and ensure minimap is visible
- **Slow processing**: Normal for OCR - template matching is faster (requires calibration)

## Next Steps

1. **Extract your first lap**: Run `python main.py`
2. **Explore the HTML**: Open the interactive visualization
3. **Compare laps**: Use position-based comparison
4. **Analyze and improve**: Identify weak points and practice
5. **Track progress**: Re-analyze after practice to measure improvement

Remember: The goal isn't just to be faster - it's to understand WHY you're faster (or slower). This tool gives you the data to make informed improvements!

## Related Documentation

- [FEATURES.md](FEATURES.md) - Detailed feature descriptions
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Common issues and solutions
- [ARCHITECTURE.md](ARCHITECTURE.md) - Technical implementation details
- [README.md](../README.md) - Project overview
