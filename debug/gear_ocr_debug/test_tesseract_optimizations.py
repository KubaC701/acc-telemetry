"""Test Tesseract optimization techniques from research"""
import cv2
import pytesseract
import time
import os

# Load test frame (lap 22)
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
print("Testing Tesseract Optimization Techniques")
print("="*70)
print(f"ROI size: {roi.shape[1]}x{roi.shape[0]}")
print()

# Test configurations combining OEM, PSM, and threading
configs = [
    # Current implementation
    ("Current (OEM 3, PSM 8)", '--psm 8 --oem 3 -c tessedit_char_whitelist=0123456789', None),
    
    # Try legacy engine (OEM 0) - might be faster
    ("Legacy engine (OEM 0, PSM 8)", '--psm 8 --oem 0 -c tessedit_char_whitelist=0123456789', None),
    ("Legacy engine (OEM 0, PSM 13)", '--psm 13 --oem 0 -c tessedit_char_whitelist=0123456789', None),
    
    # Try LSTM only (OEM 1)
    ("LSTM only (OEM 1, PSM 8)", '--psm 8 --oem 1 -c tessedit_char_whitelist=0123456789', None),
    
    # Try OEM 2 (Legacy + LSTM)
    ("Legacy+LSTM (OEM 2, PSM 8)", '--psm 8 --oem 2 -c tessedit_char_whitelist=0123456789', None),
    
    # Single threading (research suggests this helps)
    ("OEM 3, PSM 8, 1 thread", '--psm 8 --oem 3 -c tessedit_char_whitelist=0123456789', "1"),
    ("OEM 0, PSM 8, 1 thread", '--psm 8 --oem 0 -c tessedit_char_whitelist=0123456789', "1"),
    ("OEM 1, PSM 8, 1 thread", '--psm 8 --oem 1 -c tessedit_char_whitelist=0123456789', "1"),
]

results = []

for test_name, config_str, thread_limit in configs:
    # Set threading
    old_thread_limit = os.environ.get("OMP_THREAD_LIMIT")
    if thread_limit:
        os.environ["OMP_THREAD_LIMIT"] = thread_limit
    
    print(f"{test_name}")
    
    # Warm-up call
    try:
        pytesseract.image_to_string(roi, config=config_str)
    except Exception as e:
        print(f"  ERROR during warmup: {e}")
        continue
    
    # Measure 10 calls to get average
    times = []
    successes = 0
    
    for i in range(10):
        try:
            start = time.time()
            text = pytesseract.image_to_string(roi, config=config_str).strip()
            elapsed = (time.time() - start) * 1000
            times.append(elapsed)
            
            # Parse result
            if text.isdigit():
                detected = int(text)
            else:
                digits_only = ''.join(filter(str.isdigit, text))
                detected = int(digits_only) if digits_only else None
            
            if detected == 22:
                successes += 1
                
        except Exception as e:
            print(f"  ERROR on call {i+1}: {e}")
    
    # Restore threading
    if old_thread_limit is None:
        os.environ.pop("OMP_THREAD_LIMIT", None)
    else:
        os.environ["OMP_THREAD_LIMIT"] = old_thread_limit
    
    if times:
        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)
        accuracy = (successes / len(times)) * 100
        
        status = "✅" if accuracy == 100 else "⚠️" if accuracy >= 80 else "❌"
        
        print(f"  Avg: {avg_time:.1f}ms | Min: {min_time:.1f}ms | Max: {max_time:.1f}ms")
        print(f"  Accuracy: {accuracy:.0f}% {status}")
        
        if accuracy == 100:
            results.append((test_name, avg_time, min_time))
    
    print()

print("="*70)
print("BEST CONFIGURATIONS (100% accuracy)")
print("="*70)

if results:
    # Sort by average time
    results.sort(key=lambda x: x[1])
    
    for i, (name, avg, min_t) in enumerate(results[:5], 1):
        print(f"{i}. {name}")
        print(f"   Avg: {avg:.1f}ms | Best: {min_t:.1f}ms")
    
    print()
    print("="*70)
    print("WINNER:")
    winner = results[0]
    print(f"  {winner[0]}")
    print(f"  Average: {winner[1]:.1f}ms")
    print(f"  Best: {winner[2]:.1f}ms")
    print("="*70)
else:
    print("No configurations achieved 100% accuracy")


