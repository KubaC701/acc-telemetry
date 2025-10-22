"""Quick test to see what Tesseract actually reads from preprocessed images"""
import cv2
import pytesseract

# Test on the preprocessed images
test_images = [
    'debug/lap_detection_debug/frame0_preprocessed.png',
    'debug/lap_detection_debug/frame240_preprocessed.png',
    'debug/lap_detection_debug/frame1000_preprocessed.png',
]

configs = [
    ('PSM 7 (line)', '--psm 7 --oem 3 -c tessedit_char_whitelist=0123456789'),
    ('PSM 8 (word)', '--psm 8 --oem 3 -c tessedit_char_whitelist=0123456789'),
    ('PSM 13 (raw)', '--psm 13 --oem 3 -c tessedit_char_whitelist=0123456789'),
    ('PSM 10 (char)', '--psm 10 --oem 3 -c tessedit_char_whitelist=0123456789'),
]

print("="*70)
print("Direct Tesseract OCR Test")
print("="*70)

for img_path in test_images:
    print(f"\n{img_path}:")
    img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
    
    if img is None:
        print("  ❌ Image not found")
        continue
        
    print(f"  Image size: {img.shape[1]}x{img.shape[0]}")
    
    for config_name, config_str in configs:
        try:
            text = pytesseract.image_to_string(img, config=config_str).strip()
            if text:
                print(f"  {config_name}: '{text}'")
            else:
                print(f"  {config_name}: (empty)")
        except Exception as e:
            print(f"  {config_name}: ERROR - {e}")

print("\n" + "="*70)


