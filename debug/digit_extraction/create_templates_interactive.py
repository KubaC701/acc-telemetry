"""
Interactive tool to create digit templates from extracted samples.
Shows each sample and lets you label it with keyboard input.
Much faster than manual cropping!
"""

import cv2
import numpy as np
from pathlib import Path
import sys


class InteractiveTemplateCreator:
    """
    Interactive tool to quickly label extracted digit samples.
    """
    
    def __init__(self, samples_dir: str = 'debug/digit_extraction', 
                 template_dir: str = 'templates/lap_digits'):
        self.samples_dir = Path(samples_dir)
        self.template_dir = Path(template_dir)
        self.template_dir.mkdir(parents=True, exist_ok=True)
        
        # Track which digits we have templates for
        self.completed_digits = set()
        self._check_existing_templates()
    
    def _check_existing_templates(self):
        """Check which digit templates already exist."""
        for digit in range(10):
            template_path = self.template_dir / f"{digit}.png"
            if template_path.exists():
                self.completed_digits.add(str(digit))
    
    def show_sample_and_label(self, sample_path: Path) -> bool:
        """
        Show sample image and get user input for what digit(s) it contains.
        
        Returns:
            True to continue, False to quit
        """
        # Load image
        img = cv2.imread(str(sample_path), cv2.IMREAD_GRAYSCALE)
        if img is None:
            return True
        
        # Scale up for better visibility (3x)
        h, w = img.shape
        display = cv2.resize(img, (w * 3, h * 3), interpolation=cv2.INTER_NEAREST)
        
        # Add info text
        info_panel = np.zeros((100, display.shape[1]), dtype=np.uint8)
        frame_num = sample_path.stem.split('_')[0].replace('frame', '')
        cv2.putText(info_panel, f"Frame: {frame_num}", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, 255, 2)
        cv2.putText(info_panel, "Enter digit(s) you see, or:", (10, 60), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, 255, 1)
        cv2.putText(info_panel, "s=skip, q=quit, d=done", (10, 85), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, 255, 1)
        
        # Combine display with info panel
        combined = np.vstack([info_panel, display])
        
        # Show image
        cv2.imshow('Digit Template Creator', combined)
        cv2.waitKey(1)  # Small wait to ensure window updates
        
        # Get user input from console
        print(f"\n{'='*50}")
        print(f"Frame {frame_num}")
        print(f"Missing digits: {sorted(set('0123456789') - self.completed_digits)}")
        user_input = input("What lap number is this? (or s=skip, q=quit, d=done): ").strip()
        
        if user_input.lower() == 'q':
            return False
        elif user_input.lower() == 'd':
            return False
        elif user_input.lower() == 's':
            return True
        elif user_input.isdigit():
            # User entered a lap number - split into individual digits and save templates
            lap_number = user_input
            self._save_templates_from_sample(img, lap_number)
            return True
        else:
            print("Invalid input, skipping...")
            return True
    
    def _save_templates_from_sample(self, img: np.ndarray, lap_number: str):
        """
        Split lap number image into individual digits and save as templates.
        """
        # Find connected components (individual digits)
        _, labels, stats, _ = cv2.connectedComponentsWithStats(img, connectivity=8)
        
        # Filter and sort digit regions left to right
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
        
        # Check if number of regions matches number of digits in lap_number
        if len(digit_regions) != len(lap_number):
            print(f"⚠️  Warning: Found {len(digit_regions)} regions but lap number has {len(lap_number)} digits")
            print(f"   Skipping this sample. Try another frame with clearer digits.")
            return
        
        # Save each digit
        for (x, y, w, h), digit_char in zip(digit_regions, lap_number):
            digit_img = img[y:y+h, x:x+w]
            
            # Normalize size
            target_height = 35
            aspect_ratio = w / h
            target_width = int(target_height * aspect_ratio)
            resized = cv2.resize(digit_img, (target_width, target_height), 
                                interpolation=cv2.INTER_AREA)
            
            # Save template
            template_path = self.template_dir / f"{digit_char}.png"
            cv2.imwrite(str(template_path), resized)
            
            self.completed_digits.add(digit_char)
            print(f"✅ Saved template: {digit_char}.png")
        
        # Show progress
        missing = set('0123456789') - self.completed_digits
        if missing:
            print(f"📊 Progress: {len(self.completed_digits)}/10 digits")
            print(f"   Still need: {sorted(missing)}")
        else:
            print(f"🎉 All digits complete! (10/10)")
    
    def run(self):
        """
        Main interactive loop.
        """
        print(f"\n{'='*60}")
        print(f"Interactive Digit Template Creator")
        print(f"{'='*60}\n")
        print(f"Samples directory: {self.samples_dir}")
        print(f"Templates directory: {self.template_dir}")
        print(f"\nExisting templates: {sorted(self.completed_digits)}")
        print(f"Missing digits: {sorted(set('0123456789') - self.completed_digits)}\n")
        
        if len(self.completed_digits) == 10:
            print("✅ All templates already exist!")
            print("   Delete templates/lap_digits/*.png if you want to recreate them.\n")
            return
        
        # Get all sample images
        sample_files = sorted(self.samples_dir.glob('frame*_mask.png'))
        
        if not sample_files:
            print(f"❌ No sample images found in {self.samples_dir}")
            print(f"   Run extract_lap_digit_templates.py first!")
            return
        
        print(f"Found {len(sample_files)} samples to process\n")
        print("Instructions:")
        print("  • Look at the image in the window")
        print("  • Type the lap number you see (e.g., '1', '22', '5')")
        print("  • Press ENTER to save that digit's template")
        print("  • Or type 's' to skip, 'q' to quit\n")
        print("Starting in 3 seconds...")
        cv2.namedWindow('Digit Template Creator')
        cv2.waitKey(3000)
        
        processed = 0
        for sample_file in sample_files:
            # Check if we're done
            if len(self.completed_digits) == 10:
                print(f"\n🎉 All 10 digits complete!")
                break
            
            # Show sample and get label
            should_continue = self.show_sample_and_label(sample_file)
            processed += 1
            
            if not should_continue:
                print(f"\nStopped after processing {processed} samples.")
                break
        
        cv2.destroyAllWindows()
        
        # Final summary
        print(f"\n{'='*60}")
        print(f"Template Creation Complete!")
        print(f"{'='*60}\n")
        print(f"Created templates for: {sorted(self.completed_digits)}")
        
        missing = set('0123456789') - self.completed_digits
        if missing:
            print(f"Still missing: {sorted(missing)}")
            print(f"\nRun this script again to create the missing templates.")
        else:
            print(f"✅ All digits (0-9) have templates!")
            print(f"\nYou can now run main.py to test template-based lap detection.")
        
        print(f"\nTemplates saved to: {self.template_dir}")


def main():
    """Run interactive template creator."""
    creator = InteractiveTemplateCreator()
    
    try:
        creator.run()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        cv2.destroyAllWindows()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        cv2.destroyAllWindows()


if __name__ == '__main__':
    main()

