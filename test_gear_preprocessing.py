"""
Test script to compare OCR accuracy with and without preprocessing.
"""

import cv2
import numpy as np
import yaml
from pathlib import Path

try:
    import tesserocr
    from PIL import Image
    USE_TESSEROCR = True
except ImportError:
    import pytesseract
    USE_TESSEROCR = False


def load_config(config_path: str = 'config/roi_config.yaml'):
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def extract_roi(frame: np.ndarray, roi_config: dict) -> np.ndarray:
    x = roi_config['x']
    y = roi_config['y']
    w = roi_config['width']
    h = roi_config['height']
    return frame[y:y+h, x:x+w]


def preprocess_gear_roi(roi: np.ndarray) -> np.ndarray:
    """Preprocess gear ROI for better OCR."""
    # Convert to grayscale
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    
    # Threshold to isolate white digits
    _, thresh = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY)
    
    # Resize for better OCR (upscale 2x)
    height, width = thresh.shape
    preprocessed = cv2.resize(thresh, (width * 2, height * 2), interpolation=cv2.INTER_CUBIC)
    
    return preprocessed


def run_ocr(image: np.ndarray, tesserocr_api) -> str:
    """Run OCR on image."""
    try:
        if tesserocr_api:
            # Convert to RGB for PIL
            if len(image.shape) == 2:  # grayscale
                image_rgb = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
            else:  # BGR
                image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(image_rgb)
            tesserocr_api.SetImage(pil_image)
            return tesserocr_api.GetUTF8Text().strip()
        else:
            import pytesseract
            config = '--psm 8 --oem 3 -c tessedit_char_whitelist=123456'
            return pytesseract.image_to_string(image, config=config).strip()
    except Exception as e:
        return f"ERROR: {e}"


def main():
    VIDEO_PATH = './input_video.mp4'
    roi_config = load_config()['gear']
    
    # Initialize tesserocr
    tesserocr_api = None
    if USE_TESSEROCR:
        try:
            tesserocr_api = tesserocr.PyTessBaseAPI(
                path='/opt/homebrew/share/tessdata/',
                psm=tesserocr.PSM.SINGLE_WORD,
                oem=tesserocr.OEM.LSTM_ONLY
            )
            tesserocr_api.SetVariable("tessedit_char_whitelist", "123456")
            print("✅ Using tesserocr")
        except:
            tesserocr_api = None
    
    # Open video
    cap = cv2.VideoCapture(VIDEO_PATH)
    fps = cap.get(cv2.CAP_PROP_FPS)
    
    # Test frames where OCR was failing (32-33s)
    test_frames = [960, 963, 968, 973, 978, 983, 988, 1008, 1013]
    
    print("\n🔬 Testing OCR with and without preprocessing:\n")
    print(f"{'Frame':<7} {'Time':<7} {'Raw OCR':<10} {'Preprocessed OCR':<18} {'Improvement'}")
    print("-" * 70)
    
    debug_dir = Path('debug/gear_preprocessing_test')
    debug_dir.mkdir(parents=True, exist_ok=True)
    
    for frame_num in test_frames:
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
        ret, frame = cap.read()
        if not ret:
            continue
        
        timestamp = frame_num / fps
        
        # Extract ROI
        roi = extract_roi(frame, roi_config)
        
        # Run OCR on raw ROI
        raw_result = run_ocr(roi, tesserocr_api)
        
        # Preprocess ROI
        preprocessed = preprocess_gear_roi(roi)
        
        # Run OCR on preprocessed ROI
        preprocessed_result = run_ocr(preprocessed, tesserocr_api)
        
        # Compare
        if raw_result != preprocessed_result:
            improvement = "✅ BETTER" if preprocessed_result in ['1', '2', '3', '4', '5', '6'] else "⚠️ DIFFERENT"
        else:
            improvement = "Same"
        
        print(f"{frame_num:<7} {timestamp:<7.2f} {repr(raw_result):<10} {repr(preprocessed_result):<18} {improvement}")
        
        # Save preprocessed image
        cv2.imwrite(str(debug_dir / f'frame{frame_num:05d}_preprocessed.png'), preprocessed)
    
    cap.release()
    if tesserocr_api:
        tesserocr_api.End()
    
    print(f"\n✅ Preprocessed images saved to: {debug_dir}")
    print("   Compare these with debug/gear_ocr_debug/ to see the difference!")


if __name__ == '__main__':
    main()

