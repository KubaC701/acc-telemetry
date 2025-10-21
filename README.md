# ACC Telemetry Extractor

Extract throttle, brake, and steering telemetry from Assetto Corsa Competizione gameplay videos using computer vision.

## Features

- 🎥 Video processing at 60 FPS
- 🔍 Computer vision-based telemetry extraction
- 📊 Beautiful time-series graphs
- 📁 CSV export for further analysis
- ⚙️ Configurable ROI coordinates

## Requirements

- Python 3.8+
- OpenCV
- NumPy, Pandas, Matplotlib

## Installation

1. Clone or download this repository

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

1. **Place your ACC gameplay video** in the project root directory and name it `input_video.mp4`
   - Or edit the `VIDEO_PATH` variable in `main.py` to point to your video

2. **Run the extractor**:
```bash
python main.py
```

3. **Check the outputs** in `data/output/`:
   - `telemetry_TIMESTAMP.csv` - Raw telemetry data
   - `telemetry_TIMESTAMP.png` - Visualization graph

## ROI Configuration

The extractor uses Region of Interest (ROI) coordinates to locate the telemetry UI elements in your video.

Default configuration is in `config/roi_config.yaml` for 1920x1080 videos:

```yaml
throttle:
  x: 1650      # Left edge position
  y: 1020      # Top edge position
  width: 200   # ROI width
  height: 25   # ROI height

brake:
  x: 1650
  y: 1050
  width: 200
  height: 25

steering:
  x: 1650
  y: 990
  width: 200
  height: 15
```

### Adjusting ROI Coordinates

If the extractor doesn't work correctly with your video:

1. Open your video in a video player or image viewer
2. Note the pixel coordinates of:
   - Throttle bar (green bar in bottom-right)
   - Brake bar (gray bar in bottom-right)
   - Steering indicator (white dot above the bars)
3. Update the coordinates in `config/roi_config.yaml`
4. Re-run `main.py`

**Tips:**
- The ROI should fully contain the UI element with a small margin
- Different video resolutions require different coordinates
- For 4K videos, multiply the default values by 2
- For 720p videos, multiply the default values by 0.67

## Output Format

### CSV Columns:
- `frame` - Frame number
- `time` - Timestamp in seconds
- `throttle` - Throttle percentage (0-100)
- `brake` - Brake percentage (0-100)
- `steering` - Steering position (-1.0 to +1.0, where -1=full left, 0=center, +1=full right)

### Graph:
Three stacked plots showing:
1. Throttle over time (green)
2. Brake over time (red)
3. Steering over time (blue)

## Troubleshooting

**"Video file not found"**
- Ensure your video is at `./input_video.mp4` or update `VIDEO_PATH` in `main.py`

**Incorrect telemetry values (all zeros or wrong percentages)**
- Your ROI coordinates need adjustment
- Open a frame from your video and identify the correct pixel coordinates
- Update `config/roi_config.yaml`

**Video takes too long to process**
- This is normal for long videos (a 10-minute video may take 2-5 minutes)
- Future optimization: reduce sampling rate in `video_processor.py`

**"Could not open video file"**
- Ensure OpenCV supports your video codec
- Try re-encoding with: `ffmpeg -i input.mp4 -c:v libx264 input_video.mp4`

## Future Enhancements

- [ ] Web UI for drag-drop video upload
- [ ] Interactive ROI calibration tool
- [ ] Template matching for auto-detection
- [ ] Multiple video comparison
- [ ] Export to MoTeC i2 format
- [ ] Lap time detection and split analysis
- [ ] Track map overlay

## License

MIT License - Feel free to use and modify!

## Contributing

Found a bug or have a feature request? Open an issue!

---

**Note:** This tool is designed for personal use to analyze your own gameplay footage. Respect copyright when analyzing videos from other sources.

