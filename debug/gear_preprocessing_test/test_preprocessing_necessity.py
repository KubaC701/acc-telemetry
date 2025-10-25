"""Test which preprocessing steps are actually necessary for OCR accuracy"""
import cv2
import pytesseract
import time

# Load a test image we know works (frame 1000 = lap 22)
cap = cv2.VideoCapture('./input_video.mp4')
cap.set(cv2.CAP_PROP_POS_FRAMES, 1000)
ret, frame = cap.read()
cap.release()

if not ret:
    print("Failed to load frame")
    exit(1)

# Extract ROI
roi = frame[71:71+37, 237:237+47]

print("="*70)
print("Testing What Preprocessing is Actually Necessary")
print("="*70)
print(f"Original ROI: {roi.shape[1]}x{roi.shape[0]} pixels")
print()

# Test configurations
configs = [
    ('PSM 7', '--psm 7 --oem 3 -c tessedit_char_whitelist=0123456789'),
    ('PSM 8', '--psm 8 --oem 3 -c tessedit_char_whitelist=0123456789'),
    ('PSM 13', '--psm 13 --oem 3 -c tessedit_char_whitelist=0123456789'),
]

tests = [
    ("1. Raw BGR ROI (no processing)", roi),
    ("2. Grayscale only", cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)),
    ("3. Grayscale + 2x upscale LINEAR", 
     cv2.resize(cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY), (94, 74), interpolation=cv2.INTER_LINEAR)),
    ("4. Grayscale + 3x upscale LINEAR", 
     cv2.resize(cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY), (141, 111), interpolation=cv2.INTER_LINEAR)),
    ("5. Grayscale + threshold + 2x",
     lambda: cv2.resize(cv2.threshold(cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY), 180, 255, cv2.THRESH_BINARY)[1], (94, 74), interpolation=cv2.INTER_LINEAR)),
    ("6. Grayscale + threshold + 3x",
     lambda: cv2.resize(cv2.threshold(cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY), 180, 255, cv2.THRESH_BINARY)[1], (141, 111), interpolation=cv2.INTER_LINEAR)),
    ("7. Grayscale + threshold + invert + 2x",
     lambda: cv2.resize(cv2.bitwise_not(cv2.threshold(cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY), 180, 255, cv2.THRESH_BINARY)[1]), (94, 74), interpolation=cv2.INTER_LINEAR)),
    ("8. Grayscale + threshold + invert + 3x (CURRENT)",
     lambda: cv2.resize(cv2.bitwise_not(cv2.threshold(cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY), 180, 255, cv2.THRESH_BINARY)[1]), (141, 111), interpolation=cv2.INTER_LINEAR)),
]

results = []

for test_name, test_image in tests:
    # Handle lazy evaluation (lambda functions)
    if callable(test_image):
        test_image = test_image()
    
    print(f"\n{test_name}")
    print(f"  Image size: {test_image.shape[1]}x{test_image.shape[0] if len(test_image.shape) == 2 else test_image.shape[0]}")
    
    best_result = None
    best_config = None
    best_time = float('inf')
    
    for config_name, config_str in configs:
        try:
            start = time.time()
            text = pytesseract.image_to_string(test_image, config=config_str).strip()
            elapsed = (time.time() - start) * 1000
            
            # Parse result
            if text.isdigit():
                detected = int(text)
            else:
                digits_only = ''.join(filter(str.isdigit, text))
                detected = int(digits_only) if digits_only else None
            
            is_correct = detected == 22
            
            if is_correct and elapsed < best_time:
                best_result = detected
                best_config = config_name
                best_time = elapsed
            
            status = "✅" if is_correct else "❌"
            print(f"    {config_name}: '{text}' → {detected} {status} ({elapsed:.1f}ms)")
            
        except Exception as e:
            print(f"    {config_name}: ERROR - {e}")
    
    if best_result:
        results.append((test_name, best_config, best_time))

print("\n" + "="*70)
print("SUMMARY: Best Performing Configurations")
print("="*70)
for test_name, config, time_ms in results:
    print(f"{test_name}")
    print(f"  Best: {config} in {time_ms:.1f}ms")

print("\n" + "="*70)
print("CONCLUSION")
print("="*70)
if results:
    fastest = min(results, key=lambda x: x[2])
    print(f"Fastest accurate method: {fastest[0]}")
    print(f"  Config: {fastest[1]}")
    print(f"  Time: {fastest[2]:.1f}ms")
else:
    print("No configurations successfully detected lap 22")


