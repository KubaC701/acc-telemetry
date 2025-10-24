# ACC Telemetry Extractor (Console Edition)

Extract detailed telemetry data from Assetto Corsa Competizione gameplay videos using computer vision. Designed for **console players (PS5/Xbox)** who can't access native telemetry export.

## 🎯 What It Does

This tool analyzes ACC gameplay videos frame-by-frame to extract:
- **Throttle input** (0-100%)
- **Brake input** (0-100%)
- **Steering input** (-1.0 to +1.0)
- **Speed** (km/h via OCR)
- **Gear** (1-6 via OCR)
- **Lap numbers** (via template matching)
- **Track position** (0-100% via minimap analysis) 🆕

And generates:
- CSV data files for analysis
- **Interactive HTML visualizations** with zoom, pan, and hover tooltips
- **Position-based lap comparison** - see exactly where you gain/lose time 🆕
- High-resolution graphs with multiple detail levels
- Braking zone analysis
- Throttle application analysis
- Time-based lap comparison
- Lap statistics

## 🚀 Quick Start

```bash
# 1. Set up Python environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Place your gameplay video as input_video.mp4

# 3. Extract telemetry (generates interactive HTML + CSV)
python main.py

# 4. Generate detailed static analysis (optional)
python generate_detailed_analysis.py

# 5. Compare laps by time (optional - separate lap files)
python compare_laps.py lap1.csv lap2.csv

# 6. Compare laps by position (optional - single file with multiple laps)
python compare_laps_by_position.py data/output/telemetry_YYYYMMDD_HHMMSS.csv
```

## 📊 Output Examples

### Interactive Visualization (NEW!)
**Browser-based interactive graphs with Plotly** - [See full guide](docs/INTERACTIVE_VISUALIZATION_GUIDE.md)

Features:
- 🔍 **Interactive zoom**: Click and drag to zoom into any region
- 🖱️ **Pan navigation**: Explore your lap in detail
- 📊 **Hover tooltips**: See exact values at any point
- 📈 **Synchronized views**: All plots zoom together
- 🏁 **Lap comparison**: Overlay multiple laps to compare performance
- 💾 **Export controls**: Download as high-res PNG
- 🌐 **Shareable**: Just send the HTML file - works in any browser

**Output**: `telemetry_interactive_YYYYMMDD_HHMMSS.html` (open in browser)

---

### Position-Based Lap Comparison (NEW! 🆕)
**Gold standard for racing analysis** - [See full guide](docs/POSITION_BASED_LAP_COMPARISON.md)

Compare laps by **track position** instead of time to see exactly where you gain or lose time around the track!

Features:
- 🎯 **Position alignment**: Compare inputs at the same corners (not same time)
- 📉 **Time delta plot**: Shows exactly where time is gained/lost
- 🔽 **Dropdown selector**: Switch between lap comparisons instantly
- 🗺️ **Track position axis**: 0% = start/finish, 50% = halfway around
- 📊 **5 synchronized plots**: Throttle, Brake, Steering, Speed, Time Delta

**Why it's better than time-based comparison:**
- See EXACTLY which corner is costing you time
- Compare braking points at the same position
- Identify problem sections immediately
- Direct comparison of driving technique

**Usage**:
```bash
python compare_laps_by_position.py data/output/telemetry_YYYYMMDD_HHMMSS.csv
```

**Output**: `lap_comparison_position_YYYYMMDD_HHMMSS.html` (open in browser)

---

### Detailed Static Analysis
The tool also generates **4 types of detailed static visualizations** (all at 300 DPI for printing/annotation):

### 1. Comprehensive Overview
6-panel layout with:
- Complete lap overview
- Throttle detail with reference lines
- Brake detail with statistics
- Steering detail (color-coded)
- Pedal overlay (shows when both pedals are pressed)
- Complete lap statistics

![Example Overview](docs/example_overview.png)

### 2. Zoomed Sections
Your lap divided into sections (default: 6) for detailed analysis of specific areas.

### 3. Braking Zones Analysis
Every braking event isolated with:
- Context before/after
- Duration, max brake, average brake
- Steering overlay to see trail braking

### 4. Throttle Application Analysis
3-panel analysis showing:
- Throttle with color gradient (rate of change)
- Throttle vs steering correlation
- Throttle application rate (smoothness)

## 📁 Project Structure

```
acc-telemetry/
├── main.py                           # Main telemetry extraction
├── compare_laps.py                   # Time-based lap comparison
├── compare_laps_by_position.py       # Position-based lap comparison 🆕
├── generate_detailed_analysis.py     # Generate detailed static graphs
├── config/
│   └── roi_config.yaml              # ROI coordinates (resolution-specific)
├── src/
│   ├── video_processor.py           # Video frame extraction
│   ├── telemetry_extractor.py       # Computer vision analysis
│   ├── lap_detector.py              # Lap number detection (OCR/template matching)
│   ├── position_tracker_v2.py       # Track position tracking (minimap analysis) 🆕
│   ├── interactive_visualizer.py    # Interactive Plotly visualizations
│   ├── visualizer.py                # Basic matplotlib visualization
│   └── detailed_visualizer.py       # Detailed multi-scale visualization
├── data/
│   └── output/                      # Generated CSV and HTML files
└── docs/
    ├── POSITION_BASED_LAP_COMPARISON.md  # Position-based comparison guide 🆕
    ├── INTERACTIVE_VISUALIZATION_GUIDE.md # Interactive visualization guide
    ├── DETAILED_ANALYSIS_GUIDE.md   # Detailed static visualizations guide
    ├── TRACK_POSITION_TRACKING.md   # Track position tracking guide 🆕
    └── PROJECT_SUMMARY.md           # Technical overview
```

## 🎮 Supported Setup

Currently configured for:
- **Game**: Assetto Corsa Competizione (Console)
- **Resolution**: 1280×720 (720p)
- **HUD**: Default ACC HUD with visible throttle/brake bars

**Other resolutions?** You'll need to recalibrate ROI coordinates using the helper scripts (see docs).

## 🔧 Calibration Helper Scripts

If your video resolution differs:
- `find_throttle_brake_bars.py` - Find ROI coordinates for your resolution
- `visualize_rois.py` - Verify ROI placement
- `debug_braking.py` - Debug brake detection issues

## 📖 Documentation

### User Guides
- **[POSITION_BASED_LAP_COMPARISON.md](docs/POSITION_BASED_LAP_COMPARISON.md)** - Position-based lap comparison (where you gain/lose time) 🆕 ⭐ START HERE
- **[INTERACTIVE_VISUALIZATION_GUIDE.md](docs/INTERACTIVE_VISUALIZATION_GUIDE.md)** - Interactive HTML graphs and basic lap comparison
- **[DETAILED_ANALYSIS_GUIDE.md](docs/DETAILED_ANALYSIS_GUIDE.md)** - Detailed static visualizations guide

### Technical Guides
- **[TRACK_POSITION_TRACKING.md](docs/TRACK_POSITION_TRACKING.md)** - How minimap-based position tracking works 🆕
- **[PROJECT_SUMMARY.md](docs/PROJECT_SUMMARY.md)** - Technical overview and architecture

## 🛠️ Technical Stack

- **Python 3.10+**
- **OpenCV** - Video processing and computer vision
- **NumPy** - Array operations
- **Pandas** - Data handling and CSV export
- **Plotly** - Interactive web-based visualizations
- **Matplotlib** - Static high-resolution graphs
- **PyYAML** - Configuration

## 💡 How It Works

1. **Video Processing**: Extract frames from gameplay video
2. **ROI Extraction**: Crop specific regions (throttle bar, brake bar, steering indicator)
3. **Color Detection**: Use HSV color space to detect:
   - Green/yellow pixels (throttle - changes with TC activation)
   - Red/orange pixels (brake - changes with ABS activation)
   - White pixels (steering indicator dot)
4. **Measurement**: Calculate percentage of bar filled or position of indicator
5. **Export**: Generate CSV data and high-resolution visualizations

## 🎯 Use Cases

### Personal Improvement
- Compare your laps to find where you're losing time
- Analyze braking points consistency
- Study throttle application technique
- Identify problem corners

### Lap Comparison
- **Position-based**: See exactly where you gain/lose time around the track 🆕
- **Time-based**: Compare overall lap progression
- Track improvement over practice sessions
- Find which corners have the most variation
- Identify your weakest sections

### Learn from Others
- Download fast laps from YouTube
- Extract their telemetry
- Compare your technique to theirs
- Identify specific differences in inputs

## 🔬 Key Features

### Multi-Color Detection
- Handles TC/ABS activation color changes
- Throttle: Green → Yellow when TC active
- Brake: Red → Orange when ABS active

### High-Resolution Output
- 300 DPI graphs for detailed analysis
- Suitable for printing and annotation
- Frame-by-frame accuracy

### Comprehensive Statistics
- Lap duration and frame count
- Average and max values for all inputs
- Full throttle percentage and time
- Braking event count and duration
- Steering angle statistics

### Intelligent Analysis
- Automatic braking zone detection
- Context frames before/after events
- Trail braking identification
- Throttle smoothness analysis
- Pedal overlap detection (both pedals pressed)

## 🐛 Known Limitations

1. **Resolution-dependent**: ROI coordinates need recalibration for different video resolutions
2. **HUD-dependent**: Requires default ACC HUD to be visible
3. **Console-focused**: Designed for console gameplay footage (PC players have native telemetry export)
4. **Post-processing only**: Not real-time (but console players record first, analyze later anyway)

## 🚧 Roadmap

### Phase 2: Enhanced Features (Planned)
- [ ] Automatic ROI detection (no manual calibration needed)
- [ ] Lap time extraction using OCR
- [ ] Gear detection
- [ ] Batch processing multiple videos
- [ ] Resolution-independent ROI scaling

### Phase 3: Advanced Analysis (In Progress)
- [x] Multi-lap overlay comparison (✅ COMPLETE - see `compare_laps.py`)
- [x] Interactive zoom/pan visualization (✅ COMPLETE - Plotly integration)
- [x] Track position tracking (✅ COMPLETE - minimap analysis)
- [x] Position-based lap comparison (✅ COMPLETE - see `compare_laps_by_position.py`) 🆕
- [x] Time delta analysis (✅ COMPLETE - integrated in position comparison) 🆕
- [ ] Track map overlay visualization
- [ ] Sector-by-sector analysis with automatic sector detection
- [ ] AI-powered driving feedback

### Phase 4: Community Platform (Aspirational)
- [ ] Web UI for video upload
- [ ] Cloud processing
- [ ] Shared telemetry database
- [ ] YouTube integration

## 🤝 Contributing

This is a learning project, but contributions are welcome! Areas where help would be appreciated:
- Support for more video resolutions
- Automatic ROI detection algorithms
- OCR integration for lap times
- Additional visualization types
- Performance optimization

## 📄 License

MIT License - Feel free to use, modify, and share!

## 🙏 Acknowledgments

Built by a console sim racer frustrated by the lack of telemetry tools. Inspired by professional telemetry software like MoTeC i2 and RaceStudio, but adapted for the constraint of console gaming: **if you can see it on screen, we can extract it**.

## 📬 Questions?

Check the documentation:
- **User guide**: [DETAILED_ANALYSIS_GUIDE.md](DETAILED_ANALYSIS_GUIDE.md)
- **Technical details**: [docs/PROJECT_SUMMARY.md](docs/PROJECT_SUMMARY.md)

---

**Happy racing! 🏁**

*Remember: The fastest drivers aren't necessarily the most talented - they're the ones who analyze and improve systematically.*
