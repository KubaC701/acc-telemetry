
import sys
import os
import numpy as np
import unittest
from unittest.mock import MagicMock

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from position_tracker_v2 import PositionTrackerV2

class TestPositionTrackerV2(unittest.TestCase):
    def setUp(self):
        self.tracker = PositionTrackerV2(fps=30.0, max_jump_per_frame=5.0)
        
        # Manually set up a simple square track path
        # 0,0 -> 100,0 -> 100,100 -> 0,100 -> 0,0
        # Total length = 400
        self.tracker.track_path = []
        # Bottom edge
        for x in range(0, 100): self.tracker.track_path.append((x, 0))
        # Right edge
        for y in range(0, 100): self.tracker.track_path.append((100, y))
        # Top edge
        for x in range(100, 0, -1): self.tracker.track_path.append((x, 100))
        # Left edge
        for y in range(100, 0, -1): self.tracker.track_path.append((0, y))
        
        self.tracker.total_path_pixels = len(self.tracker.track_path)
        self.tracker.total_track_length = 400.0 # Approx
        self.tracker.track_center = (50.0, 50.0)
        self.tracker.path_extracted = True
        self.tracker.validation_passed = True
        
        # Mock detect_red_dot to return values we control
        self.tracker.detect_red_dot = MagicMock()

    def test_lap_reset_logic(self):
        """Test that reset_for_new_lap forces 0% and resets start anchor."""
        # 1. Start a lap
        self.tracker.reset_for_new_lap()
        self.assertTrue(self.tracker.lap_just_started)
        
        # 2. First frame: dot at (10, 0) - should be 0%
        self.tracker.detect_red_dot.return_value = (10, 0)
        pos = self.tracker.extract_position(np.zeros((100,100,3), dtype=np.uint8))
        
        self.assertEqual(pos, 0.0)
        self.assertFalse(self.tracker.lap_just_started)
        self.assertEqual(self.tracker.start_position, (10, 0))
        
        # 3. Second frame: dot at (20, 0) - moved 10 pixels = 2.5% of 400
        self.tracker.detect_red_dot.return_value = (20, 0)
        pos = self.tracker.extract_position(np.zeros((100,100,3), dtype=np.uint8))
        
        self.assertAlmostEqual(pos, 2.5, delta=0.1)
        
        # 4. Trigger lap reset
        self.tracker.reset_for_new_lap()
        self.assertTrue(self.tracker.lap_just_started)
        self.assertEqual(self.tracker.last_position, 0.0)
        
        # 5. Next frame: dot at (20, 0) - this is the NEW start line
        # Even though it's physically at the same spot, it should be 0% now
        self.tracker.detect_red_dot.return_value = (20, 0)
        pos = self.tracker.extract_position(np.zeros((100,100,3), dtype=np.uint8))
        
        self.assertEqual(pos, 0.0)
        self.assertEqual(self.tracker.start_position, (20, 0))

    def test_validation_smoothing(self):
        """Test that validation smooths jumps and ignores backward movement."""
        self.tracker.max_jump_per_frame = 1.0
        # Setup start
        self.tracker.reset_for_new_lap()
        self.tracker.detect_red_dot.return_value = (0, 0)
        self.tracker.extract_position(np.zeros((1,1), dtype=np.uint8)) # Init at 0%
        
        # 1. Normal move: 0 -> 0.5% (2 pixels)
        self.tracker.detect_red_dot.return_value = (2, 0)
        pos = self.tracker.extract_position(np.zeros((1,1), dtype=np.uint8))
        self.assertAlmostEqual(pos, 0.5, delta=0.1)
        
        # 2. Backward move: 0.5% -> 0.25% (1 pixel) - should be ignored
        self.tracker.detect_red_dot.return_value = (1, 0)
        pos = self.tracker.extract_position(np.zeros((1,1), dtype=np.uint8))
        self.assertAlmostEqual(pos, 0.5, delta=0.1) # Should stay at 0.5
        
        # 3. Huge forward jump: 0.5% -> 5.0% (20 pixels) - should be clamped
        # Max jump is 1.0%
        self.tracker.detect_red_dot.return_value = (20, 0)
        pos = self.tracker.extract_position(np.zeros((1,1), dtype=np.uint8))
        self.assertAlmostEqual(pos, 1.5, delta=0.1) # 0.5 + 1.0 = 1.5
        
    def test_wraparound(self):
        """Test 99% -> 1% wraparound logic."""
        # Manually set last position to 99.5%
        self.tracker.last_position = 99.5
        
        # Mock a raw position of 0.5% (wrapped around)
        # We need to bypass calculate_position logic for this test or set up the dots correctly
        # Let's just test _validate_position directly
        
        val_pos = self.tracker._validate_position(0.5)
        self.assertEqual(val_pos, 0.5) # Should accept it
        self.assertEqual(self.tracker.last_position, 0.5)

    def test_spike_removal(self):
        """Test that sharp spikes (start/finish line artifacts) are removed."""
        # Create a path with a spike
        # 0,0 -> 50,0 -> 50,20 (spike tip) -> 50,0 -> 100,0
        path = []
        for x in range(0, 50): path.append((x, 0))
        # Spike out
        for y in range(0, 20): path.append((50, y))
        # Spike back
        for y in range(20, 0, -1): path.append((50, y))
        # Continue
        for x in range(50, 100): path.append((x, 0))
        
        # Clean path
        cleaned = self.tracker._remove_path_spikes(path, window=5, angle_threshold=60.0)
        
        # Verify spike is gone
        # The path should be roughly 0,0 -> 100,0
        # Length should be much smaller than original
        original_len = len(path)
        cleaned_len = len(cleaned)
        
        self.assertLess(cleaned_len, original_len - 30) # Should remove at least 30 points (spike is 40 total)
        
        # Verify no points have y > 5 (spike went to y=20)
        max_y = 0
        for p in cleaned:
            if p[1] > max_y: max_y = p[1]
            
        self.assertLess(max_y, 5)

if __name__ == '__main__':
    unittest.main()
