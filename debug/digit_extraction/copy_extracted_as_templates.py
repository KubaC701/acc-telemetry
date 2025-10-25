"""
Copy extracted digit masks directly as templates.
Since the extracted masks are already preprocessed and clean,
we can use them as-is for template matching.
"""

import cv2
import numpy as np
from pathlib import Path


# Manual mapping: which extracted frame contains which digit(s)
# Based on visual inspection of debug/digit_extraction/frame*_mask.png
DIGIT_SOURCES = {
    '0': 'frame240_mask.png',      # Shows "0"
    '1': 'frame5880_mask.png',     # Shows "1" 
    '2': 'frame240_mask.png',      # Shows "22", we'll extract left digit
    '3': 'frame8370_mask.png',     # Shows "3" (if it's actually lap 3)
    '4': 'frame13350_mask.png',    # Shows "4"
    '5': 'frame17190_mask.png',    # Shows "5"
    '6': 'frame20790_mask.png',    # Shows "6"
    '7': 'frame23070_mask.png',    # Shows "7"
    '8': 'frame27120_mask.png',    # Shows "8"
    '9': 'frame29760_mask.png',    # Shows "9" (but might have noise)
}


def extract_single_digit_from_mask(mask: np.ndarray, digit_index: int = 0) -> np.ndarray:
    """
    Extract a single digit from a mask that might contain multiple digits.
    
    Args:
        mask: Binary mask image
        digit_index: Which digit to extract (0=leftmost, 1=second from left, etc.)
    
    Returns:
        Cropped image containing just that digit
    """
    # Find connected components
    _, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    
    # Get all regions sorted left to right
    regions = []
    for i in range(1, len(stats)):
        area = stats[i, cv2.CC_STAT_AREA]
        if area > 20:  # Minimum area
            x = stats[i, cv2.CC_STAT_LEFT]
            y = stats[i, cv2.CC_STAT_TOP]
            w = stats[i, cv2.CC_STAT_WIDTH]
            h = stats[i, cv2.CC_STAT_HEIGHT]
            regions.append((x, y, w, h))
    
    # Sort left to right
    regions.sort(key=lambda r: r[0])
    
    if digit_index >= len(regions):
        return None
    
    # Extract the specified digit
    x, y, w, h = regions[digit_index]
    digit = mask[y:y+h, x:x+w]
    
    return digit


def main():
    """Create templates by copying extracted digits."""
    source_dir = Path('debug/digit_extraction')
    template_dir = Path('templates/lap_digits')
    template_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\n{'='*70}")
    print(f"Creating Templates from Extracted Digits")
    print(f"{'='*70}\n")
    
    created = []
    failed = []
    
    for digit, filename in sorted(DIGIT_SOURCES.items()):
        source_path = source_dir / filename
        
        if not source_path.exists():
            print(f"❌ {digit}: Source not found - {filename}")
            failed.append(digit)
            continue
        
        # Load mask
        mask = cv2.imread(str(source_path), cv2.IMREAD_GRAYSCALE)
        
        if mask is None:
            print(f"❌ {digit}: Failed to load - {filename}")
            failed.append(digit)
            continue
        
        # For "2", extract the first digit from "22" or similar
        if digit == '2' and '240' in filename:
            digit_img = extract_single_digit_from_mask(mask, digit_index=0)
        else:
            # Use the whole mask (single digit)
            digit_img = extract_single_digit_from_mask(mask, digit_index=0)
        
        if digit_img is None or digit_img.size == 0:
            print(f"❌ {digit}: Failed to extract digit from {filename}")
            failed.append(digit)
            continue
        
        # Save as template
        template_path = template_dir / f"{digit}.png"
        cv2.imwrite(str(template_path), digit_img)
        
        print(f"✅ {digit}: Created from {filename} (size: {digit_img.shape[1]}x{digit_img.shape[0]})")
        created.append(digit)
    
    print(f"\n{'='*70}")
    print(f"Template Creation Summary")
    print(f"{'='*70}\n")
    print(f"✅ Created: {len(created)}/10 - {sorted(created)}")
    
    if failed:
        print(f"❌ Failed: {len(failed)}/10 - {sorted(failed)}")
        print(f"\nYou'll need to find frames containing these digits manually.")
    else:
        print(f"🎉 All 10 digit templates created!")
    
    print(f"\n📁 Templates saved to: {template_dir}")


if __name__ == '__main__':
    main()

