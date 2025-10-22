"""
Debug script to visualize what OCR sees in the gear ROI.
Shows the actual ROI images and OCR results for frames in the 32-33s range.
"""

import cv2
import numpy as np
from pathlib import Path
import yaml

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


def main():
    VIDEO_PATH = './input_video.mp4'
    CONFIG_PATH = 'config/roi_config.yaml'
    
    # Time range to debug (32-34 seconds)
    START_TIME = 32.0
    END_TIME = 34.0
    
    # Load config
    roi_config = load_config(CONFIG_PATH)
    gear_roi = roi_config['gear']
    
    # Open video
    cap = cv2.VideoCapture(VIDEO_PATH)
    if not cap.isOpened():
        print(f"❌ Error: Could not open video '{VIDEO_PATH}'")
        return
    
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    # Calculate frame range
    start_frame = int(START_TIME * fps)
    end_frame = int(END_TIME * fps)
    
    print(f"🎥 Video: {VIDEO_PATH}")
    print(f"   FPS: {fps:.2f}")
    print(f"   Analyzing frames {start_frame} to {end_frame} ({START_TIME}s to {END_TIME}s)")
    print(f"   Gear ROI: x={gear_roi['x']}, y={gear_roi['y']}, w={gear_roi['width']}, h={gear_roi['height']}")
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
            print("✅ Using tesserocr for OCR")
        except Exception as e:
            print(f"⚠️  tesserocr init failed: {e}, falling back to pytesseract")
            tesserocr_api = None
    else:
        print("ℹ️  Using pytesseract for OCR")
    
    print()
    
    # Create debug output directory
    debug_dir = Path('debug/gear_ocr_debug')
    debug_dir.mkdir(parents=True, exist_ok=True)
    
    # Sample every 5 frames to avoid too much output
    sample_interval = 5
    
    print(f"{'Frame':<8} {'Time':<8} {'OCR Raw':<12} {'OCR Clean':<12} {'Valid?':<8} {'Image Saved'}")
    print("-" * 70)
    
    for frame_num in range(start_frame, end_frame + 1, sample_interval):
        # Seek to frame
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
                # Fast path: tesserocr
                roi_rgb = cv2.cvtColor(roi, cv2.COLOR_BGR2RGB)
                pil_image = Image.fromarray(roi_rgb)
                tesserocr_api.SetImage(pil_image)
                text_raw = tesserocr_api.GetUTF8Text()
            else:
                # Slow path: pytesseract
                tesseract_config = '--psm 8 --oem 3 -c tessedit_char_whitelist=123456'
                text_raw = pytesseract.image_to_string(roi, config=tesseract_config)
            
            text_raw = text_raw.strip()
            
            # Parse gear (same logic as in lap_detector.py)
            if text_raw.isdigit():
                gear = int(text_raw)
            else:
                # Try to extract digits
                digits_only = ''.join(filter(str.isdigit, text_raw))
                if digits_only:
                    gear = int(digits_only)
                else:
                    gear = None
            
            # Validate
            is_valid = gear is not None and 1 <= gear <= 6
            gear_str = str(gear) if gear is not None else "None"
            
        except Exception as e:
            text_raw = f"ERROR: {e}"
            gear_str = "None"
            is_valid = False
        
        # Save ROI image
        img_filename = f'frame{frame_num:05d}_t{timestamp:.2f}s_gear{gear_str}.png'
        cv2.imwrite(str(debug_dir / img_filename), roi)
        
        # Print result
        print(f"{frame_num:<8} {timestamp:<8.2f} {repr(text_raw):<12} {gear_str:<12} {str(is_valid):<8} {img_filename}")
    
    cap.release()
    
    if tesserocr_api:
        tesserocr_api.End()
    
    print()
    print(f"✅ Debug images saved to: {debug_dir}")
    print(f"   Open these images to see exactly what the OCR is reading!")
    print()
    print("🔍 Analysis:")
    print("   1. Check if the gear digit is clearly visible in the ROI")
    print("   2. Look for image artifacts, compression, or blur")
    print("   3. Check if ROI is correctly positioned (not cutting off digits)")
    print("   4. Compare frames where OCR fails vs succeeds")


if __name__ == '__main__':
    main()

