"""
Compare pytesseract (spawns process each call) vs tesserocr (direct API).
tesserocr should be 2-3x faster by avoiding process spawn overhead.
"""
import cv2
import time

# Load test frame
cap = cv2.VideoCapture('./input_video.mp4')
cap.set(cv2.CAP_PROP_POS_FRAMES, 1000)
ret, frame = cap.read()
cap.release()

if not ret:
    print("Failed to load frame")
    exit(1)

roi = frame[71:71+37, 237:237+47]

print("="*70)
print("Performance Comparison: pytesseract vs tesserocr")
print("="*70)
print()

# Test 1: pytesseract (current approach)
print("1. Testing pytesseract (spawns new process each call):")
import pytesseract

config = '--psm 8 --oem 3 -c tessedit_char_whitelist=0123456789'

# Warmup
pytesseract.image_to_string(roi, config=config)

# Benchmark
times = []
for i in range(20):
    start = time.time()
    result = pytesseract.image_to_string(roi, config=config).strip()
    elapsed = (time.time() - start) * 1000
    times.append(elapsed)

avg_time = sum(times) / len(times)
min_time = min(times)
print(f"   Average: {avg_time:.2f}ms")
print(f"   Best: {min_time:.2f}ms")
print(f"   Result: '{result}'")
print()

# Test 2: Try tesserocr (direct API)
print("2. Testing tesserocr (direct C++ API, keeps engine warm):")
try:
    import tesserocr
    from PIL import Image
    
    # Convert OpenCV image to PIL
    roi_rgb = cv2.cvtColor(roi, cv2.COLOR_BGR2RGB)
    pil_image = Image.fromarray(roi_rgb)
    
    # Create API instance (reusable!)
    # Specify path to tessdata
    api = tesserocr.PyTessBaseAPI(
        path='/opt/homebrew/share/tessdata/',
        psm=tesserocr.PSM.SINGLE_WORD,
        oem=tesserocr.OEM.LSTM_ONLY
    )
    api.SetVariable("tessedit_char_whitelist", "0123456789")
    
    # Warmup
    api.SetImage(pil_image)
    api.GetUTF8Text()
    
    # Benchmark
    times = []
    for i in range(20):
        start = time.time()
        api.SetImage(pil_image)
        result = api.GetUTF8Text().strip()
        elapsed = (time.time() - start) * 1000
        times.append(elapsed)
    
    avg_time = sum(times) / len(times)
    min_time = min(times)
    print(f"   Average: {avg_time:.2f}ms")
    print(f"   Best: {min_time:.2f}ms")
    print(f"   Result: '{result}'")
    
    api.End()
    
    print()
    print("="*70)
    print("✅ tesserocr is available and working!")
    print("   Consider switching to tesserocr for 2-3x speedup")
    print("="*70)
    
except ImportError:
    print("   ❌ tesserocr not installed")
    print()
    print("="*70)
    print("To install tesserocr (faster OCR):")
    print("="*70)
    print("macOS:")
    print("  brew install tesseract")
    print("  pip install tesserocr")
    print()
    print("Linux:")
    print("  sudo apt-get install tesseract-ocr libtesseract-dev")
    print("  pip install tesserocr")
    print()
    print("Expected speedup: 50ms → 15-25ms (2-3x faster)")
    print("="*70)


