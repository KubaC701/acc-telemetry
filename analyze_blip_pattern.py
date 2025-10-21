"""
Analyze the throttle blip pattern during the first braking zone.
User reports 3 downshifts (6→5→4→3) but sees 6 throttle spikes.
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# Load telemetry
df = pd.read_csv('/Users/jakub.cieply/Personal/acc-telemetry/data/output/telemetry_20251022_001554.csv')

# Find first major braking event
brake_start_idx = None
for i in range(1, len(df)):
    if df.loc[i-1, 'brake'] < 10 and df.loc[i, 'brake'] > 20:
        brake_start_idx = i
        break

print("="*80)
print("ANALYZING FIRST BRAKING ZONE - THROTTLE BLIP PATTERN")
print("="*80)
print(f"\nBraking starts at frame {brake_start_idx} (time: {df.loc[brake_start_idx, 'time']:.2f}s)")

# Analyze 60 frames after brake start (should cover entire braking zone)
start_frame = brake_start_idx
end_frame = min(len(df), brake_start_idx + 60)

segment = df.iloc[start_frame:end_frame].copy()
segment['relative_frame'] = segment['frame'] - brake_start_idx

print(f"\nAnalyzing frames {start_frame} to {end_frame-1}")
print("Looking for throttle blips during heavy braking (brake > 50%)...\n")

# Find throttle blips: throttle goes above 20% while brake is above 50%
blips = []
in_blip = False
blip_start = None

for idx, row in segment.iterrows():
    if row['brake'] > 50:  # During heavy braking
        if row['throttle'] > 20 and not in_blip:
            # Start of a blip
            in_blip = True
            blip_start = idx
        elif row['throttle'] <= 20 and in_blip:
            # End of a blip
            in_blip = False
            blip_segment = segment.loc[blip_start:idx-1]
            blip_info = {
                'start_frame': int(blip_segment.iloc[0]['frame']),
                'end_frame': int(blip_segment.iloc[-1]['frame']),
                'start_time': blip_segment.iloc[0]['time'],
                'end_time': blip_segment.iloc[-1]['time'],
                'duration_frames': len(blip_segment),
                'duration_sec': blip_segment.iloc[-1]['time'] - blip_segment.iloc[0]['time'],
                'peak_throttle': blip_segment['throttle'].max(),
                'avg_throttle': blip_segment['throttle'].mean(),
                'brake_level': blip_segment['brake'].mean()
            }
            blips.append(blip_info)

print(f"{'='*80}")
print(f"FOUND {len(blips)} THROTTLE BLIPS")
print(f"{'='*80}\n")

for i, blip in enumerate(blips, 1):
    print(f"Blip #{i}:")
    print(f"  Frames: {blip['start_frame']} → {blip['end_frame']} ({blip['duration_frames']} frames)")
    print(f"  Time: {blip['start_time']:.3f}s → {blip['end_time']:.3f}s ({blip['duration_sec']:.3f}s)")
    print(f"  Throttle: avg={blip['avg_throttle']:.1f}%, peak={blip['peak_throttle']:.1f}%")
    print(f"  Brake level: {blip['brake_level']:.1f}%")
    
    # Calculate time since previous blip
    if i > 1:
        time_since_prev = blip['start_time'] - blips[i-2]['end_time']
        print(f"  Time since previous blip: {time_since_prev:.3f}s")
    print()

# Analyze the pattern
print(f"{'='*80}")
print("PATTERN ANALYSIS")
print(f"{'='*80}\n")

if len(blips) >= 2:
    # Calculate inter-blip intervals
    intervals = []
    for i in range(1, len(blips)):
        interval = blips[i]['start_time'] - blips[i-1]['end_time']
        intervals.append(interval)
    
    print(f"Inter-blip intervals: {[f'{x:.3f}s' for x in intervals]}")
    print(f"Average interval: {np.mean(intervals):.3f}s")
    print(f"Std deviation: {np.std(intervals):.3f}s")
    
    # Check for pattern of pairs
    short_intervals = [x for x in intervals if x < 0.15]
    long_intervals = [x for x in intervals if x >= 0.15]
    
    print(f"\nShort intervals (<0.15s): {len(short_intervals)} - {[f'{x:.3f}s' for x in short_intervals]}")
    print(f"Long intervals (≥0.15s): {len(long_intervals)} - {[f'{x:.3f}s' for x in long_intervals]}")
    
    if len(short_intervals) > 0 and len(long_intervals) > 0:
        print("\n⚠️  PATTERN DETECTED: Mix of short and long intervals!")
        print("This suggests some blips might be false detections or the throttle")
        print("is being applied twice per downshift.")

# Visualize in detail
fig, axes = plt.subplots(3, 1, figsize=(16, 12))

# Plot 1: Full view of braking zone
ax1 = axes[0]
ax1.plot(segment['relative_frame'], segment['throttle'], 'g-', linewidth=2, label='Throttle', marker='o', markersize=4)
ax1.plot(segment['relative_frame'], segment['brake'], 'r-', linewidth=2, label='Brake', marker='s', markersize=4)

# Mark each blip
for i, blip in enumerate(blips, 1):
    blip_frames = segment[
        (segment['frame'] >= blip['start_frame']) & 
        (segment['frame'] <= blip['end_frame'])
    ]
    ax1.axvspan(blip_frames.iloc[0]['relative_frame'], 
                blip_frames.iloc[-1]['relative_frame'],
                alpha=0.3, color='yellow')
    ax1.text(blip_frames.iloc[0]['relative_frame'], 105, f'{i}', 
             fontsize=12, fontweight='bold', ha='center')

ax1.set_xlabel('Frames from brake start', fontsize=11)
ax1.set_ylabel('Percentage (%)', fontsize=11)
ax1.set_title(f'First Braking Zone - Found {len(blips)} Throttle Blips (Expected: 3)', 
              fontsize=13, fontweight='bold')
ax1.legend(loc='best')
ax1.grid(True, alpha=0.3)
ax1.set_ylim(-5, 110)

# Plot 2: Zoomed on throttle with frame numbers
ax2 = axes[1]
ax2.plot(segment['frame'], segment['throttle'], 'g-', linewidth=2, marker='o', markersize=5, label='Throttle')
ax2.axhline(y=20, color='orange', linestyle='--', linewidth=1, alpha=0.7, label='Blip threshold (20%)')

# Mark blip boundaries
for i, blip in enumerate(blips, 1):
    ax2.axvspan(blip['start_frame'], blip['end_frame'], alpha=0.2, color='yellow')
    mid_frame = (blip['start_frame'] + blip['end_frame']) / 2
    ax2.text(mid_frame, blip['peak_throttle'] + 5, f'Blip {i}\n{blip["peak_throttle"]:.0f}%', 
             fontsize=9, ha='center', fontweight='bold',
             bbox=dict(boxstyle='round,pad=0.3', facecolor='yellow', alpha=0.7))

ax2.set_xlabel('Frame Number', fontsize=11)
ax2.set_ylabel('Throttle (%)', fontsize=11)
ax2.set_title('Throttle Detail - Yellow = Blip Detection', fontsize=12, fontweight='bold')
ax2.legend(loc='best')
ax2.grid(True, alpha=0.3)
ax2.set_ylim(-5, 110)

# Plot 3: Frame-by-frame data table view
ax3 = axes[2]
ax3.axis('off')

# Create table data
table_data = []
table_data.append(['Frame', 'Time (s)', 'Throttle (%)', 'Brake (%)', 'Status'])

for idx, row in segment.iterrows():
    frame = int(row['frame'])
    time = row['time']
    throttle = row['throttle']
    brake = row['brake']
    
    # Determine status
    status = ''
    for i, blip in enumerate(blips, 1):
        if blip['start_frame'] <= frame <= blip['end_frame']:
            status = f'BLIP {i}'
            break
    
    # Only show frames with throttle > 0 or in braking
    if throttle > 5 or brake > 80 or status:
        table_data.append([
            f'{frame}',
            f'{time:.2f}',
            f'{throttle:.1f}',
            f'{brake:.1f}',
            status
        ])

# Show first 40 rows
table_data_display = table_data[:min(41, len(table_data))]
table = ax3.table(cellText=table_data_display, cellLoc='left', loc='center',
                  colWidths=[0.15, 0.2, 0.2, 0.2, 0.25])
table.auto_set_font_size(False)
table.set_fontsize(9)
table.scale(1, 1.5)

# Color header row
for i in range(5):
    table[(0, i)].set_facecolor('#4CAF50')
    table[(0, i)].set_text_props(weight='bold', color='white')

# Color blip rows
for i in range(1, len(table_data_display)):
    if 'BLIP' in table_data_display[i][4]:
        for j in range(5):
            table[(i, j)].set_facecolor('#FFEB3B')

ax3.set_title('Frame-by-Frame Data (First 40 relevant frames)', fontsize=12, fontweight='bold', pad=20)

plt.tight_layout()
plt.savefig('analyze_blip_pattern.png', dpi=150, bbox_inches='tight')
print(f"\n{'='*80}")
print("✅ Visualization saved: analyze_blip_pattern.png")
print(f"{'='*80}\n")

print("\n" + "="*80)
print("HYPOTHESIS:")
print("="*80)
print("""
If you see 6 blips but only shifted 3 times, possible causes:

1. **Double detection per shift**: The throttle blip might have multiple peaks
   due to how the game applies throttle (ramp up + hold + release), causing
   two separate detections per downshift.

2. **Detection threshold too sensitive**: The 20% threshold might be catching
   partial throttle applications that aren't actual blips.

3. **Pixel noise**: Small amounts of green pixels being detected between real
   blips, creating false spikes.

4. **Actual double-blipping**: Some racing games apply throttle twice per
   downshift for smoother rev matching.

RECOMMENDED FIXES:
- Increase throttle threshold for blip detection (e.g., 30-40% instead of 20%)
- Require minimum blip duration (e.g., 3+ frames)
- Merge blips that are very close together (<0.1s apart)
- Increase pixel threshold from 50 to 100+ for more confidence
""")

plt.show()

