"""
Create templates by directly using the extracted digit samples.
We'll manually map specific extracted frames to their lap numbers.
"""

import cv2
import numpy as np
from pathlib import Path

# Manual mapping: frame_number -> lap_number
# Based on the extraction log and video timeline
KNOWN_LAP_NUMBERS = {
    240: 22,      # Early in race
    3180: 1,      # Lap 1
    5880: 2,      # Lap 2  
    8370: 3,      # Lap 3
    13350: 4,     # Lap 4
    17190: 5,     # Lap 5
    20790: 6,     # Lap 6
    23070: 7,     # Lap 7
    27120: 8,     # Lap 8
    29760: 9,     # Lap 9
    36510: 10,    # Lap 10 (gives us 1 and 0)
}

def split_and_save_digits(sample_path: Path, lap_number: int, output_dir: Path):
    """
    Split lap number image into individual digit templates.
    """
    img = cv2.imread(str(sample_path), cv2.IMREAD_GRAYSCALE)
    if img is None:
        print(f"❌ Failed to load {sample_path}")
        return False
    
    # Find connected components
    _, labels, stats, _ = cv2.connectedComponentsWithStats(img, connectivity=8)
    
    # Get digit regions
    digit_regions = []
    for i in range(1, len(stats)):
        area = stats[i, cv2.CC_STAT_AREA]
        if area > 20:  # Minimum area
            x = stats[i, cv2.CC_STAT_LEFT]
            y = stats[i, cv2.CC_STAT_TOP]
            w = stats[i, cv2.CC_STAT_WIDTH]
            h = stats[i, cv2.CC_STAT_HEIGHT]
            digit_regions.append((x, y, w, h))
    
    # Sort left to right
    digit_regions.sort(key=lambda r: r[0])
    
    # Convert lap number to string
    lap_str = str(lap_number)
    
    if len(digit_regions) != len(lap_str):
        print(f"⚠️  Frame {sample_path.stem}: found {len(digit_regions)} regions, expected {len(lap_str)} for lap {lap_number}")
        return False
    
    # Save each digit
    saved_any = False
    for (x, y, w, h), digit_char in zip(digit_regions, lap_str):
        digit_img = img[y:y+h, x:x+w]
        
        # Save template
        template_path = output_dir / f"{digit_char}.png"
        
        # Only save if we don't have this digit yet
        if not template_path.exists():
            cv2.imwrite(str(template_path), digit_img)
            print(f"✅ Saved template: {digit_char}.png (from lap {lap_number})")
            saved_any = True
        else:
            print(f"   Skipped: {digit_char}.png (already exists)")
    
    return saved_any


def main():
    """Create templates from known lap numbers."""
    samples_dir = Path('debug/digit_extraction')
    output_dir = Path('templates/lap_digits')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\n{'='*60}")
    print(f"Creating Digit Templates from Extracted Samples")
    print(f"{'='*60}\n")
    
    created_digits = set()
    
    for frame_num, lap_number in sorted(KNOWN_LAP_NUMBERS.items()):
        sample_path = samples_dir / f"frame{frame_num}_mask.png"
        
        if not sample_path.exists():
            print(f"⚠️  Sample not found: {sample_path}")
            continue
        
        print(f"\nProcessing frame {frame_num} (Lap {lap_number})...")
        if split_and_save_digits(sample_path, lap_number, output_dir):
            for digit in str(lap_number):
                created_digits.add(digit)
        
        # Check if we have all digits
        if len(created_digits) == 10:
            print(f"\n🎉 All 10 digits created!")
            break
    
    print(f"\n{'='*60}")
    print(f"Template Creation Complete!")
    print(f"{'='*60}\n")
    print(f"Created digits: {sorted(created_digits)}")
    
    missing = set('0123456789') - created_digits
    if missing:
        print(f"⚠️  Still missing: {sorted(missing)}")
        print(f"   You may need to find more frames or adjust KNOWN_LAP_NUMBERS")
    else:
        print(f"✅ All digits (0-9) have templates!")
    
    print(f"\nTemplates saved to: {output_dir}")


if __name__ == '__main__':
    main()

