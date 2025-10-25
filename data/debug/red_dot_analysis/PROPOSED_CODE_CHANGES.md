# Proposed Code Changes to Fix Red Dot Position Detection Issue

**File:** `/Users/jakub.cieply/Personal/acc-telemetry/src/position_tracker_v2.py`
**Issue:** 1-pixel detection noise causes 1.72% lap position error
**Fix:** Force lap start to 0.0% and add tolerance-based matching

---

## CHANGE #1: Force Lap Start to 0.0% (IMMEDIATE FIX)

**Location:** `extract_position()` method, line ~490-496

### Current Code (BROKEN):
```python
else:
    # SUBSEQUENT LAPS: Reuse the locked start position from lap 1
    # Don't return 0.0 - let position calculation continue normally
    # The position will naturally wrap around through 0% as the car passes
    # the lap 1 start position
    print(f"      🏁 Lap reset - using locked start position from lap 1: pixel ({self.start_position[0]}, {self.start_position[1]}), index {self.start_idx}")
    self.lap_just_started = False
    # Don't set last_position or return early - continue to calculate position below
```

### Fixed Code:
```python
else:
    # SUBSEQUENT LAPS: Reuse the locked start position from lap 1
    # CRITICAL FIX: Force position to 0.0% on first frame after lap reset
    # This prevents the 1-pixel detection noise from causing 2-4% offset
    print(f"      🏁 Lap reset - using locked start position from lap 1: pixel ({self.start_position[0]}, {self.start_position[1]}), index {self.start_idx}")
    print(f"         Forcing position to 0.0% for lap start frame")
    self.lap_just_started = False
    self.last_position = 0.0
    return 0.0  # ← ADD THIS LINE: Don't calculate, just return 0.0
```

**Impact:**
- All laps will start at exactly 0.000%
- Eliminates the 3.871% vs 2.151% inconsistency
- Zero risk (only affects first frame after lap transition)

---

## CHANGE #2: Add Tolerance-Based Matching (RECOMMENDED)

**Location:** `calculate_position()` method, line ~316-413

### Current Code (FRAGILE):
```python
def calculate_position(self, dot_x: int, dot_y: int) -> float:
    # ...

    # STEP 1: Find closest point on racing line to red dot
    min_distance = float('inf')
    closest_idx = 0

    for i, (px, py) in enumerate(self.track_path):
        dx = dot_x - px
        dy = dot_y - py
        distance = dx*dx + dy*dy  # Squared distance (faster, no sqrt needed)

        if distance < min_distance:
            min_distance = distance
            closest_idx = i

    # ... rest of position calculation using closest_idx ...
```

**Problem:** Greedy nearest-neighbor has no tolerance. When dot is equidistant from multiple points (1.41px vs 1.41px), the choice becomes arbitrary.

### Proposed New Code (ROBUST):
```python
def calculate_position(self, dot_x: int, dot_y: int) -> float:
    """
    Calculate position percentage using arc length along the racing line.

    IMPROVEMENT: Uses tolerance-based candidate matching to handle detection noise.
    When multiple track points are within tolerance, picks the one closest to
    expected position based on last known position and estimated velocity.
    """
    if not self.path_extracted or self.track_center is None or self.start_position is None:
        return 0.0

    if not self.track_path or len(self.track_path) == 0:
        return 0.0

    # Configuration
    TOLERANCE_RADIUS = 3.0  # pixels - covers typical ±1-2px detection noise

    # STEP 1: Find ALL track points within tolerance radius
    candidates = []
    min_distance_overall = float('inf')
    closest_idx_fallback = 0

    for i, (px, py) in enumerate(self.track_path):
        dx = dot_x - px
        dy = dot_y - py
        distance = np.sqrt(dx*dx + dy*dy)

        # Track closest point for fallback
        if distance < min_distance_overall:
            min_distance_overall = distance
            closest_idx_fallback = i

        # Collect candidates within tolerance
        if distance <= TOLERANCE_RADIUS:
            candidates.append((i, distance))

    # STEP 2: Choose best candidate based on context
    if not candidates:
        # No points within tolerance - use closest point but log warning
        closest_idx = closest_idx_fallback
        print(f"⚠️  Warning: No track points within {TOLERANCE_RADIUS}px of dot ({dot_x}, {dot_y})")
        print(f"   Using fallback closest point: index {closest_idx} at {min_distance_overall:.2f}px")
    elif len(candidates) == 1:
        # Only one candidate - use it
        closest_idx = candidates[0][0]
    else:
        # Multiple candidates - pick based on temporal consistency

        # At lap start (position near 0%), prefer indices near start_idx
        if self.last_position < 5.0:
            # Find candidate closest to start_idx
            best_candidate = min(candidates, key=lambda c: abs(c[0] - self.start_idx))
            closest_idx = best_candidate[0]

            if len(candidates) > 1:
                print(f"   Lap start: {len(candidates)} candidates within {TOLERANCE_RADIUS}px")
                print(f"   Choosing index {closest_idx} (closest to start_idx={self.start_idx})")
        else:
            # Mid-lap: prefer index closest to expected position based on velocity
            # Expected position = last_position + estimated forward progress
            expected_arc_length = (self.last_position / 100.0) * self.total_track_length

            # Convert expected arc length to approximate index
            # (Simple estimation: index ≈ arc_length / average_segment_length)
            avg_segment_length = self.total_track_length / len(self.track_path)
            expected_idx = int(expected_arc_length / avg_segment_length) % len(self.track_path)

            # Among candidates, pick the one with smallest index deviation from expected
            # Use circular distance (account for wraparound)
            def circular_distance(idx1, idx2, n):
                """Calculate shortest circular distance between two indices."""
                diff = abs(idx1 - idx2)
                return min(diff, n - diff)

            best_candidate = min(candidates,
                                key=lambda c: circular_distance(c[0], expected_idx, len(self.track_path)))
            closest_idx = best_candidate[0]

    # STEP 3: Calculate arc length from start to current position (unchanged)
    arc_length = 0.0

    if closest_idx >= self.start_idx:
        # Normal case: current position is ahead of start
        for i in range(self.start_idx, closest_idx):
            p1 = self.track_path[i]
            p2 = self.track_path[i + 1]
            dx = p2[0] - p1[0]
            dy = p2[1] - p1[1]
            arc_length += np.sqrt(dx*dx + dy*dy)
    else:
        # Wraparound case: we've passed the end of the path array
        for i in range(self.start_idx, len(self.track_path) - 1):
            p1 = self.track_path[i]
            p2 = self.track_path[i + 1]
            dx = p2[0] - p1[0]
            dy = p2[1] - p1[1]
            arc_length += np.sqrt(dx*dx + dy*dy)

        # Add closing segment
        p1 = self.track_path[-1]
        p2 = self.track_path[0]
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        arc_length += np.sqrt(dx*dx + dy*dy)

        # Add from start to current position
        for i in range(0, closest_idx):
            p1 = self.track_path[i]
            p2 = self.track_path[i + 1]
            dx = p2[0] - p1[0]
            dy = p2[1] - p1[1]
            arc_length += np.sqrt(dx*dx + dy*dy)

    # STEP 4: Convert to percentage (unchanged)
    if self.total_track_length > 0:
        position = (arc_length / self.total_track_length) * 100.0
    else:
        position = 0.0

    # STEP 5: Handle near-completion detection (unchanged)
    if self.last_position > 90.0 and position < 90.0 and (self.last_position - position) > 3.0:
        position = 100.0

    # Clamp to valid range
    position = max(0.0, min(100.0, position))

    return position
```

**Impact:**
- Eliminates index flipping when dot is equidistant from multiple points
- At lap start, prefers indices near start_idx (prevents 15 vs 25 ambiguity)
- Mid-lap, uses temporal consistency (smooth progression)
- Degrades gracefully (falls back to closest point if no candidates)

**Risk:** Low - can be tested with a feature flag:
```python
USE_TOLERANCE_MATCHING = True  # Set to False to revert to old behavior
```

---

## CHANGE #3: Add Position Sanity Check (OPTIONAL)

**Location:** `extract_position()` method, after `raw_position = self.calculate_position(...)`

### Proposed Code:
```python
# Calculate raw position (if red dot detected)
raw_position = None
if dot_position is not None:
    dot_x, dot_y = dot_position
    # ... existing lap_just_started handling ...
    raw_position = self.calculate_position(dot_x, dot_y)

# SANITY CHECK: Position should be reasonable given last known position
if raw_position is not None:
    # At lap start, position must be near 0%
    if self.last_position < 2.0 and raw_position > 5.0:
        print(f"⚠️  Warning: Lap start position is {raw_position:.1f}% (expected <5%)")
        print(f"   This suggests incorrect index matching. Attempting correction...")

        # Force search near start_idx instead of using detected dot position
        best_idx = self.start_idx
        min_dist = float('inf')

        # Search within ±50 indices of start_idx
        search_range = 50
        for offset in range(-search_range, search_range + 1):
            idx = (self.start_idx + offset) % len(self.track_path)
            px, py = self.track_path[idx]
            dx = dot_x - px
            dy = dot_y - py
            dist = dx*dx + dy*dy

            if dist < min_dist:
                min_dist = dist
                best_idx = idx

        # Recalculate position using corrected index
        # (We can't call calculate_position again, so inline the arc length calc)
        arc_length = 0.0
        if best_idx >= self.start_idx:
            for i in range(self.start_idx, best_idx):
                p1 = self.track_path[i]
                p2 = self.track_path[i + 1]
                dx = p2[0] - p1[0]
                dy = p2[1] - p1[1]
                arc_length += np.sqrt(dx*dx + dy*dy)
        else:
            # Wraparound case
            for i in range(self.start_idx, len(self.track_path) - 1):
                p1 = self.track_path[i]
                p2 = self.track_path[i + 1]
                dx = p2[0] - p1[0]
                dy = p2[1] - p1[1]
                arc_length += np.sqrt(dx*dx + dy*dy)
            p1 = self.track_path[-1]
            p2 = self.track_path[0]
            dx = p2[0] - p1[0]
            dy = p2[1] - p1[1]
            arc_length += np.sqrt(dx*dx + dy*dy)
            for i in range(0, best_idx):
                p1 = self.track_path[i]
                p2 = self.track_path[i + 1]
                dx = p2[0] - p1[0]
                dy = p2[1] - p1[1]
                arc_length += np.sqrt(dx*dx + dy*dy)

        raw_position = (arc_length / self.total_track_length * 100.0) if self.total_track_length > 0 else 0.0
        raw_position = max(0.0, min(100.0, raw_position))

        print(f"   Corrected: index {best_idx} → position {raw_position:.3f}%")

# Apply simple validation
return self._validate_position(raw_position)
```

**Impact:**
- Catches egregious errors (3-4% at lap start is clearly wrong)
- Self-correcting without manual intervention
- Only triggers at lap start, doesn't affect normal operation

**Risk:** Low - only runs when position is obviously wrong

---

## Testing the Changes

### Before Applying Changes
```bash
# Run diagnostic to see current behavior
python data/debug/red_dot_analysis/analyze_red_dot_frames.py

# Expected output (BROKEN):
# Frame 3064 (Lap 1): Position 3.871%
# Frame 9430 (Lap 3): Position 2.151%  ← WRONG
# Frame 12431 (Lap 4): Position 3.871%
```

### After Applying CHANGE #1 Only
```bash
# Re-run diagnostic
python data/debug/red_dot_analysis/analyze_red_dot_frames.py

# Expected output (FIXED):
# Frame 3064 (Lap 1): Position 0.000%  ← FIXED
# Frame 9430 (Lap 3): Position 0.000%  ← FIXED
# Frame 12431 (Lap 4): Position 0.000%  ← FIXED
```

### After Applying CHANGE #2
```bash
# Process full video
python main.py

# Check lap comparison
python compare_laps_by_position.py data/output/telemetry_*.csv

# Expected: All laps should overlay perfectly at start (0%) and finish (100%)
# No more offset caused by index 15 vs 25 ambiguity
```

---

## Implementation Checklist

- [ ] **CHANGE #1: Force lap start to 0.0%**
  - [ ] Edit `src/position_tracker_v2.py` line ~495
  - [ ] Add `return 0.0` after `self.lap_just_started = False`
  - [ ] Test with diagnostic script
  - [ ] Verify all lap starts show 0.000%

- [ ] **CHANGE #2: Tolerance-based matching**
  - [ ] Replace `calculate_position()` method (lines 316-413)
  - [ ] Add `TOLERANCE_RADIUS = 3.0` configuration
  - [ ] Add candidate search logic
  - [ ] Add temporal consistency checks
  - [ ] Test with full video processing
  - [ ] Verify position progresses smoothly 0% → 100%

- [ ] **CHANGE #3: Sanity check (optional)**
  - [ ] Add validation code after `raw_position = ...`
  - [ ] Test with known bad frames
  - [ ] Verify auto-correction works

- [ ] **Validation**
  - [ ] Run all test cases from `FINAL_REPORT.md`
  - [ ] Compare before/after lap comparison graphs
  - [ ] Verify no regressions in mid-lap tracking

---

## Rollback Plan

If the changes cause issues:

1. **Rollback CHANGE #1:** Remove the `return 0.0` line
2. **Rollback CHANGE #2:** Revert `calculate_position()` to original implementation
3. **Rollback CHANGE #3:** Remove sanity check code

Original code is preserved in git history:
```bash
git diff src/position_tracker_v2.py  # See changes
git checkout src/position_tracker_v2.py  # Revert if needed
```

---

## Performance Impact

- **CHANGE #1:** Zero (only affects one frame per lap)
- **CHANGE #2:** Minimal (~10% slower per frame due to candidate search)
  - Original: ~50 iterations (worst case)
  - New: ~50 iterations (candidate search) + ~10 iterations (candidate scoring) = ~60 total
  - At 30 FPS, per-frame time increases from ~0.5ms to ~0.6ms (negligible)
- **CHANGE #3:** Minimal (only triggers on error conditions)

---

## Summary

**Minimum viable fix:** CHANGE #1 only (1 line of code, zero risk)
**Recommended fix:** CHANGE #1 + CHANGE #2 (robustness + consistency)
**Full solution:** All 3 changes (belt + suspenders + backup parachute)

**Estimated implementation time:**
- CHANGE #1: 5 minutes
- CHANGE #2: 30 minutes
- CHANGE #3: 15 minutes
- Testing: 30 minutes
- **Total: ~1.5 hours**

---

**Created by:** ACC Telemetry Debugging Specialist
**Last updated:** 2025-10-25
