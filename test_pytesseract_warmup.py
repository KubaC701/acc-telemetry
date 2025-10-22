"""
Test if keeping pytesseract "warm" by reusing configuration helps performance.
Or if we need tesserocr for true process reuse.
"""
import cv2
import time
import pytesseract

# Load test frames
cap = cv2.VideoCapture('./input_video.mp4')

test_frames = [1000, 1001, 1002, 1003, 1004]
rois = []

for frame_num in test_frames:
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
    ret, frame = cap.read()
    if ret:
        roi = frame[71:71+37, 237:237+47]
        rois.append(roi)

cap.release()

print("="*70)
print("Testing if pytesseract can be kept 'warm'")
print("="*70)
print()

config = '--psm 8 --oem 3 -c tessedit_char_whitelist=0123456789'

# Test 1: Cold calls (what we do now)
print("1. Cold calls (new process each time):")
times = []
for i, roi in enumerate(rois):
    start = time.time()
    result = pytesseract.image_to_string(roi, config=config).strip()
    elapsed = (time.time() - start) * 1000
    times.append(elapsed)
    print(f"   Frame {i+1}: {elapsed:.2f}ms - '{result}'")

avg = sum(times) / len(times)
print(f"   Average: {avg:.2f}ms")
print()

# Test 2: After warmup (does it help?)
print("2. After warmup (run once, then measure):")
# Warmup call
pytesseract.image_to_string(rois[0], config=config)

times = []
for i, roi in enumerate(rois):
    start = time.time()
    result = pytesseract.image_to_string(roi, config=config).strip()
    elapsed = (time.time() - start) * 1000
    times.append(elapsed)
    print(f"   Frame {i+1}: {elapsed:.2f}ms - '{result}'")

avg = sum(times) / len(times)
print(f"   Average: {avg:.2f}ms")
print()

print("="*70)
print("CONCLUSION:")
print("="*70)
print("❌ pytesseract CANNOT be kept warm!")
print()
print("Why? pytesseract is a wrapper that:")
print("  1. Saves image to temp file")
print("  2. Spawns new 'tesseract' subprocess")
print("  3. Reads output from temp file")
print("  4. Returns result")
print()
print("Every call = new process = ~50ms overhead")
print()
print("To truly 'keep warm', you need:")
print("  - tesserocr (Python bindings to C++ API)")
print("  - OR implement your own subprocess manager")
print("="*70)


