"""
Enhanced debug script to test the new gear validation logic.
Shows OCR readings, history, and final gear decision for each frame.
"""

import cv2
import numpy as np
from pathlib import Path
import yaml
from collections import Counter

# Try tesserocr first, fall back to pytesseract
try:
    import tesserocr
    from PIL import Image
    USE_TESSEROCR = True
except ImportError:
    import pytesseract
    USE_TESSEROCR = False


def load_config(config_path: str = 'config/roi_config.yaml'):
    """Load ROI configuration from YAML file."""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def extract_roi(frame: np.ndarray, roi_config: dict) -> np.ndarray:
    """Extract Region of Interest from frame."""
    x = roi_config['x']
    y = roi_config['y']
    w = roi_config['width']
    h = roi_config['height']
    
    return frame[y:y+h, x:x+w]


def get_smoothed_gear(gear_history: list) -> int:
    """Apply majority voting to gear history."""
    if not gear_history:
        return None
    
    gear_counts = Counter(gear_history)
    most_common = gear_counts.most_common(1)[0]
    gear = most_common[0]
    count = most_common[1]
    
    # Require 70% consensus
    if count >= max(len(gear_history) * 0.7, 3):
        return gear
    return None


def validate_gear_change(smoothed_gear: int, last_valid_gear: int, gear_history: list) -> tuple:
    """
    Validate if gear change should be accepted.
    Returns (accepted_gear, reason)
    """
    if last_valid_gear is None:
        return (smoothed_gear, "First detection")
    
    gear_diff = abs(smoothed_gear - last_valid_gear)
    
    if gear_diff == 0:
        return (last_valid_gear, "No change")
    elif gear_diff == 1:
        # Sequential change - check 75% consensus
        gear_counts = Counter(gear_history)
        most_common = gear_counts.most_common(1)[0]
        count = most_common[1]
        consensus = count / len(gear_history) * 100
        
        if count >= max(len(gear_history) * 0.75, 3):
            return (smoothed_gear, f"Sequential ({last_valid_gear}->{smoothed_gear}, {consensus:.0f}%)")
        else:
            return (last_valid_gear, f"Sequential REJECTED ({consensus:.0f}% < 75%)")
    else:
        # Large jump - check 80% consensus
        gear_counts = Counter(gear_history)
        most_common = gear_counts.most_common(1)[0]
        count = most_common[1]
        consensus = count / len(gear_history) * 100
        
        if count >= max(len(gear_history) * 0.80, 3):
            return (smoothed_gear, f"Large jump ({last_valid_gear}->{smoothed_gear}, {consensus:.0f}%)")
        else:
            return (last_valid_gear, f"Large jump REJECTED ({consensus:.0f}% < 80%)")


def main():
    VIDEO_PATH = './input_video.mp4'
    CONFIG_PATH = 'config/roi_config.yaml'
    
    # Time range to debug (31-37 seconds to see full context)
    START_TIME = 31.0
    END_TIME = 37.0
    
    # Load config
    roi_config = load_config(CONFIG_PATH)
    gear_roi = roi_config['gear']
    
    # Open video
    cap = cv2.VideoCapture(VIDEO_PATH)
    if not cap.isOpened():
        print(f"❌ Error: Could not open video '{VIDEO_PATH}'")
        return
    
    fps = cap.get(cv2.CAP_PROP_FPS)
    
    # Calculate frame range
    start_frame = int(START_TIME * fps)
    end_frame = int(END_TIME * fps)
    
    print(f"🎥 Video: {VIDEO_PATH}")
    print(f"   Analyzing frames {start_frame} to {end_frame} ({START_TIME}s to {END_TIME}s)")
    print()
    
    # Initialize tesserocr if available
    tesserocr_api = None
    if USE_TESSEROCR:
        try:
            tesserocr_api = tesserocr.PyTessBaseAPI(
                path='/opt/homebrew/share/tessdata/',
                psm=tesserocr.PSM.SINGLE_WORD,
                oem=tesserocr.OEM.LSTM_ONLY
            )
            tesserocr_api.SetVariable("tessedit_char_whitelist", "123456")
        except:
            tesserocr_api = None
    
    # State tracking
    gear_history = []
    last_valid_gear = None
    history_size = 15
    
    print(f"{'Frame':<7} {'Time':<6} {'OCR':<5} {'Smoothed':<9} {'History (last 5)':<20} {'Final':<6} {'Reason'}")
    print("-" * 100)
    
    for frame_num in range(start_frame, end_frame + 1):
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
        ret, frame = cap.read()
        
        if not ret:
            continue
        
        timestamp = frame_num / fps
        
        # Extract gear ROI
        roi = extract_roi(frame, gear_roi)
        
        # Run OCR
        try:
            if tesserocr_api:
                roi_rgb = cv2.cvtColor(roi, cv2.COLOR_BGR2RGB)
                pil_image = Image.fromarray(roi_rgb)
                tesserocr_api.SetImage(pil_image)
                text_raw = tesserocr_api.GetUTF8Text().strip()
            else:
                tesseract_config = '--psm 8 --oem 3 -c tessedit_char_whitelist=123456'
                text_raw = pytesseract.image_to_string(roi, config=tesseract_config).strip()
            
            # Parse gear
            if text_raw.isdigit():
                ocr_gear = int(text_raw)
            else:
                digits_only = ''.join(filter(str.isdigit, text_raw))
                ocr_gear = int(digits_only) if digits_only else None
            
            # Validate range
            if ocr_gear is not None and not (1 <= ocr_gear <= 6):
                ocr_gear = None
        except:
            ocr_gear = None
        
        ocr_str = str(ocr_gear) if ocr_gear is not None else "None"
        
        # Add to history
        if ocr_gear is not None:
            gear_history.append(ocr_gear)
            if len(gear_history) > history_size:
                gear_history.pop(0)
        
        # Get smoothed gear
        smoothed_gear = get_smoothed_gear(gear_history)
        smoothed_str = str(smoothed_gear) if smoothed_gear is not None else "None"
        
        # Validate gear change
        if smoothed_gear is not None:
            final_gear, reason = validate_gear_change(smoothed_gear, last_valid_gear, gear_history)
            last_valid_gear = final_gear
        else:
            final_gear = last_valid_gear
            reason = "Using last valid"
        
        final_str = str(final_gear) if final_gear is not None else "None"
        
        # Show last 5 items in history
        history_display = str(gear_history[-5:]) if gear_history else "[]"
        
        print(f"{frame_num:<7} {timestamp:<6.2f} {ocr_str:<5} {smoothed_str:<9} {history_display:<20} {final_str:<6} {reason}")
    
    cap.release()
    
    if tesserocr_api:
        tesserocr_api.End()
    
    print()
    print("✅ Analysis complete!")


if __name__ == '__main__':
    main()

