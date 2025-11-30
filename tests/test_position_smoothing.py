import sys
import unittest
from unittest.mock import MagicMock

# Mock cv2 before importing PositionTrackerV2
sys.modules['cv2'] = MagicMock()
sys.modules['cv2'].getStructuringElement = MagicMock()
sys.modules['cv2'].MORPH_ELLIPSE = 1

from src.position_tracker_v2 import PositionTrackerV2

class TestPositionSmoothing(unittest.TestCase):
    def setUp(self):
        self.tracker = PositionTrackerV2()
        # Mock path extraction state
        self.tracker.path_extracted = True
        self.tracker.validation_passed = True
        self.tracker.track_path = [(0,0)] # Dummy
        self.tracker.track_center = (0,0)
        self.tracker.start_position = (0,0)
        
    def test_smoothing_reduces_jitter(self):
        """Test that small fluctuations are smoothed out."""
        # Simulate noisy input: 10.0 -> 10.2 -> 10.1 -> 10.3
        
        # Initial state
        self.tracker.last_position = 10.0
        
        # Input 10.2 (jump of 0.2)
        # Smoothed = 0.3 * 10.2 + 0.7 * 10.0 = 3.06 + 7.0 = 10.06
        pos1 = self.tracker._validate_position(10.2)
        self.assertLess(pos1, 10.2)
        self.assertGreater(pos1, 10.0)
        print(f"10.0 -> 10.2 smoothed to {pos1:.4f}")
        
        # Input 10.1 (backward fluctuation relative to 10.2, but forward relative to smoothed 10.06)
        # Smoothed = 0.3 * 10.1 + 0.7 * 10.06 = 3.03 + 7.042 = 10.072
        pos2 = self.tracker._validate_position(10.1)
        self.assertGreater(pos2, pos1) # Should still increase monotonically
        print(f"10.2 -> 10.1 smoothed to {pos2:.4f}")
        
    def test_monotonicity(self):
        """Test that position never decreases (except wrap-around)."""
        self.tracker.last_position = 20.0
        
        # Input 19.9 (backward noise)
        pos = self.tracker._validate_position(19.9)
        self.assertEqual(pos, 20.0) # Should hold
        
    def test_catch_up_logic(self):
        """Test that it catches up if lag is too large."""
        self.tracker.last_position = 30.0
        
        # Input 30.8 (large jump, but < max_jump 1.0)
        # Normal smooth: 0.3*30.8 + 0.7*30.0 = 9.24 + 21.0 = 30.24
        # Lag = 30.8 - 30.24 = 0.56 > 0.5
        # Catch up: 30.8 - 0.2 = 30.6
        pos = self.tracker._validate_position(30.8)
        self.assertAlmostEqual(pos, 30.6)
        print(f"30.0 -> 30.8 caught up to {pos:.4f}")

if __name__ == '__main__':
    unittest.main()
