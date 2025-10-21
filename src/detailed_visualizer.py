"""
Enhanced visualization module with detailed, zoomed-in telemetry analysis.
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import numpy as np


class DetailedTelemetryVisualizer:
    """Creates detailed, multi-scale telemetry visualizations for in-depth analysis."""
    
    def __init__(self, output_dir: str = 'data/output'):
        """
        Initialize detailed visualizer.
        
        Args:
            output_dir: Directory to save output files
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def plot_detailed_overview(self, df: pd.DataFrame, filename: str = None) -> str:
        """
        Create a comprehensive overview with multiple detail levels.
        
        Args:
            df: DataFrame with telemetry data
            filename: Optional custom filename
            
        Returns:
            Path to saved graph image
        """
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'telemetry_detailed_{timestamp}.png'
        
        filepath = self.output_dir / filename
        
        # Create figure with custom layout
        fig = plt.figure(figsize=(20, 14))
        gs = gridspec.GridSpec(4, 2, figure=fig, hspace=0.3, wspace=0.3)
        
        fig.suptitle('ACC Telemetry - Detailed Analysis', fontsize=18, fontweight='bold')
        
        # 1. Full lap overview (left column, top)
        ax_overview = fig.add_subplot(gs[0, :])
        self._plot_overview(ax_overview, df)
        
        # 2. Throttle detail (left column, second row)
        ax_throttle = fig.add_subplot(gs[1, 0])
        self._plot_throttle_detail(ax_throttle, df)
        
        # 3. Brake detail (right column, second row)
        ax_brake = fig.add_subplot(gs[1, 1])
        self._plot_brake_detail(ax_brake, df)
        
        # 4. Steering detail (left column, third row)
        ax_steering = fig.add_subplot(gs[2, 0])
        self._plot_steering_detail(ax_steering, df)
        
        # 5. Combined pedals (right column, third row)
        ax_pedals = fig.add_subplot(gs[2, 1])
        self._plot_pedal_overlay(ax_pedals, df)
        
        # 6. Statistics panel (bottom row)
        ax_stats = fig.add_subplot(gs[3, :])
        self._plot_statistics(ax_stats, df)
        
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()
        
        return str(filepath)
    
    def plot_zoomed_sections(self, df: pd.DataFrame, num_sections: int = 6, 
                            filename: str = None) -> str:
        """
        Create zoomed-in views of different sections of the lap.
        
        Args:
            df: DataFrame with telemetry data
            num_sections: Number of sections to create
            filename: Optional custom filename
            
        Returns:
            Path to saved graph image
        """
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'telemetry_sections_{timestamp}.png'
        
        filepath = self.output_dir / filename
        
        # Calculate section boundaries
        total_time = df['time'].iloc[-1]
        section_duration = total_time / num_sections
        
        # Create grid layout
        fig, axes = plt.subplots(num_sections, 1, figsize=(18, 4 * num_sections))
        fig.suptitle('ACC Telemetry - Zoomed Sections', fontsize=18, fontweight='bold')
        
        if num_sections == 1:
            axes = [axes]
        
        for i, ax in enumerate(axes):
            start_time = i * section_duration
            end_time = (i + 1) * section_duration
            
            # Filter data for this section
            mask = (df['time'] >= start_time) & (df['time'] <= end_time)
            section_df = df[mask]
            
            if len(section_df) > 0:
                self._plot_section_detail(ax, section_df, i + 1, start_time, end_time)
        
        plt.tight_layout()
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()
        
        return str(filepath)
    
    def plot_braking_zones(self, df: pd.DataFrame, brake_threshold: float = 10.0,
                          filename: str = None) -> str:
        """
        Identify and visualize all braking zones with detailed analysis.
        
        Args:
            df: DataFrame with telemetry data
            brake_threshold: Minimum brake % to consider as braking
            filename: Optional custom filename
            
        Returns:
            Path to saved graph image
        """
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'telemetry_braking_zones_{timestamp}.png'
        
        filepath = self.output_dir / filename
        
        # Find braking zones
        braking_zones = self._identify_braking_zones(df, brake_threshold)
        
        if not braking_zones:
            print(f"No braking zones found with threshold {brake_threshold}%")
            return None
        
        # Create subplots for each braking zone
        num_zones = len(braking_zones)
        fig, axes = plt.subplots(num_zones, 1, figsize=(18, 5 * num_zones))
        fig.suptitle(f'ACC Telemetry - Braking Zones Analysis ({num_zones} zones found)', 
                    fontsize=18, fontweight='bold')
        
        if num_zones == 1:
            axes = [axes]
        
        for idx, (ax, zone) in enumerate(zip(axes, braking_zones)):
            self._plot_braking_zone_detail(ax, df, zone, idx + 1)
        
        plt.tight_layout()
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()
        
        return str(filepath)
    
    def plot_throttle_application(self, df: pd.DataFrame, filename: str = None) -> str:
        """
        Analyze throttle application patterns - focusing on acceleration phases.
        
        Args:
            df: DataFrame with telemetry data
            filename: Optional custom filename
            
        Returns:
            Path to saved graph image
        """
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'telemetry_throttle_analysis_{timestamp}.png'
        
        filepath = self.output_dir / filename
        
        fig, axes = plt.subplots(3, 1, figsize=(18, 12))
        fig.suptitle('ACC Telemetry - Throttle Application Analysis', 
                    fontsize=18, fontweight='bold')
        
        # 1. Throttle trace with gradient highlighting
        ax1 = axes[0]
        self._plot_throttle_gradient(ax1, df)
        
        # 2. Throttle vs Steering correlation
        ax2 = axes[1]
        self._plot_throttle_steering_correlation(ax2, df)
        
        # 3. Throttle application rate (acceleration)
        ax3 = axes[2]
        self._plot_throttle_rate(ax3, df)
        
        plt.tight_layout()
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()
        
        return str(filepath)
    
    # Helper methods for plotting different visualizations
    
    def _plot_overview(self, ax, df):
        """Plot complete lap overview with all three inputs."""
        ax2 = ax.twinx()
        
        # Plot throttle and brake on primary axis
        ax.fill_between(df['time'], 0, df['throttle'], color='green', alpha=0.4, label='Throttle')
        ax.fill_between(df['time'], 0, df['brake'], color='red', alpha=0.4, label='Brake')
        ax.plot(df['time'], df['throttle'], color='darkgreen', linewidth=1, alpha=0.8)
        ax.plot(df['time'], df['brake'], color='darkred', linewidth=1, alpha=0.8)
        
        # Plot steering on secondary axis
        ax2.plot(df['time'], df['steering'], color='blue', linewidth=1.5, alpha=0.7, label='Steering')
        ax2.axhline(y=0, color='gray', linestyle='--', alpha=0.3)
        
        ax.set_xlabel('Time (seconds)', fontsize=11)
        ax.set_ylabel('Throttle/Brake (%)', fontsize=11)
        ax2.set_ylabel('Steering', fontsize=11)
        ax.set_ylim(-5, 105)
        ax2.set_ylim(-1.1, 1.1)
        ax.set_title('Complete Lap Overview', fontsize=13, fontweight='bold')
        ax.grid(True, alpha=0.3, linewidth=0.5)
        
        # Combine legends
        lines1, labels1 = ax.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax.legend(lines1 + lines2, labels1 + labels2, loc='upper right', fontsize=9)
    
    def _plot_throttle_detail(self, ax, df):
        """Plot detailed throttle analysis."""
        ax.plot(df['time'], df['throttle'], color='green', linewidth=2, alpha=0.8)
        ax.fill_between(df['time'], 0, df['throttle'], color='green', alpha=0.3)
        
        # Add horizontal reference lines
        for pct in [25, 50, 75, 100]:
            ax.axhline(y=pct, color='gray', linestyle=':', alpha=0.4, linewidth=0.8)
            ax.text(df['time'].iloc[0], pct, f'{pct}%', fontsize=8, va='bottom')
        
        ax.set_ylabel('Throttle (%)', fontsize=11)
        ax.set_xlabel('Time (seconds)', fontsize=10)
        ax.set_ylim(-5, 105)
        ax.set_title('Throttle Input Detail', fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3, linewidth=0.5)
        
        # Add stats
        avg_throttle = df['throttle'].mean()
        max_throttle = df['throttle'].max()
        ax.text(0.02, 0.98, f'Avg: {avg_throttle:.1f}%\nMax: {max_throttle:.1f}%',
               transform=ax.transAxes, fontsize=9, va='top',
               bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    def _plot_brake_detail(self, ax, df):
        """Plot detailed brake analysis."""
        ax.plot(df['time'], df['brake'], color='red', linewidth=2, alpha=0.8)
        ax.fill_between(df['time'], 0, df['brake'], color='red', alpha=0.3)
        
        # Add horizontal reference lines
        for pct in [25, 50, 75, 100]:
            ax.axhline(y=pct, color='gray', linestyle=':', alpha=0.4, linewidth=0.8)
            ax.text(df['time'].iloc[0], pct, f'{pct}%', fontsize=8, va='bottom')
        
        ax.set_ylabel('Brake (%)', fontsize=11)
        ax.set_xlabel('Time (seconds)', fontsize=10)
        ax.set_ylim(-5, 105)
        ax.set_title('Brake Input Detail', fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3, linewidth=0.5)
        
        # Add stats
        avg_brake = df['brake'].mean()
        max_brake = df['brake'].max()
        num_braking_events = len(self._identify_braking_zones(df, 10.0))
        ax.text(0.02, 0.98, f'Avg: {avg_brake:.1f}%\nMax: {max_brake:.1f}%\nEvents: {num_braking_events}',
               transform=ax.transAxes, fontsize=9, va='top',
               bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    def _plot_steering_detail(self, ax, df):
        """Plot detailed steering analysis."""
        # Color the line based on direction
        positive_mask = df['steering'] >= 0
        negative_mask = df['steering'] < 0
        
        ax.plot(df['time'][positive_mask], df['steering'][positive_mask], 
               color='royalblue', linewidth=2, alpha=0.8, label='Right')
        ax.plot(df['time'][negative_mask], df['steering'][negative_mask], 
               color='orange', linewidth=2, alpha=0.8, label='Left')
        ax.axhline(y=0, color='black', linestyle='-', alpha=0.5, linewidth=1)
        
        # Add reference lines
        for val in [-1.0, -0.5, 0.5, 1.0]:
            ax.axhline(y=val, color='gray', linestyle=':', alpha=0.4, linewidth=0.8)
        
        ax.set_ylabel('Steering', fontsize=11)
        ax.set_xlabel('Time (seconds)', fontsize=10)
        ax.set_ylim(-1.1, 1.1)
        ax.set_title('Steering Input Detail', fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3, linewidth=0.5)
        ax.legend(loc='upper right', fontsize=9)
        
        # Add stats
        avg_abs_steering = df['steering'].abs().mean()
        max_left = df['steering'].min()
        max_right = df['steering'].max()
        ax.text(0.02, 0.98, f'Avg abs: {avg_abs_steering:.2f}\nMax left: {max_left:.2f}\nMax right: {max_right:.2f}',
               transform=ax.transAxes, fontsize=9, va='top',
               bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    def _plot_pedal_overlay(self, ax, df):
        """Plot throttle and brake overlayed to show transitions."""
        ax.fill_between(df['time'], 0, df['throttle'], color='green', alpha=0.4, label='Throttle')
        ax.fill_between(df['time'], 0, df['brake'], color='red', alpha=0.4, label='Brake')
        ax.plot(df['time'], df['throttle'], color='darkgreen', linewidth=1.5)
        ax.plot(df['time'], df['brake'], color='darkred', linewidth=1.5)
        
        # Highlight areas where both pedals are pressed (trail braking or mistakes)
        both_pressed = (df['throttle'] > 5) & (df['brake'] > 5)
        if both_pressed.any():
            for i in range(len(df)):
                if both_pressed.iloc[i]:
                    ax.axvspan(df['time'].iloc[i], df['time'].iloc[min(i+1, len(df)-1)], 
                             color='yellow', alpha=0.3)
        
        ax.set_ylabel('Pedal Input (%)', fontsize=11)
        ax.set_xlabel('Time (seconds)', fontsize=10)
        ax.set_ylim(-5, 105)
        ax.set_title('Pedal Overlay (Yellow = Both Pressed)', fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3, linewidth=0.5)
        ax.legend(loc='upper right', fontsize=9)
    
    def _plot_statistics(self, ax, df):
        """Plot summary statistics panel."""
        ax.axis('off')
        
        # Calculate comprehensive statistics
        stats_text = self._generate_statistics_text(df)
        
        ax.text(0.5, 0.5, stats_text, transform=ax.transAxes,
               fontsize=10, va='center', ha='center', family='monospace',
               bbox=dict(boxstyle='round', facecolor='lightgray', alpha=0.8))
        
        ax.set_title('Telemetry Statistics', fontsize=12, fontweight='bold')
    
    def _plot_section_detail(self, ax, section_df, section_num, start_time, end_time):
        """Plot detailed view of a specific time section."""
        ax2 = ax.twinx()
        
        # Pedals on primary axis
        ax.fill_between(section_df['time'], 0, section_df['throttle'], 
                       color='green', alpha=0.4, label='Throttle')
        ax.fill_between(section_df['time'], 0, section_df['brake'], 
                       color='red', alpha=0.4, label='Brake')
        ax.plot(section_df['time'], section_df['throttle'], color='darkgreen', linewidth=2)
        ax.plot(section_df['time'], section_df['brake'], color='darkred', linewidth=2)
        
        # Steering on secondary axis
        ax2.plot(section_df['time'], section_df['steering'], 
                color='blue', linewidth=2, alpha=0.7, label='Steering')
        ax2.axhline(y=0, color='gray', linestyle='--', alpha=0.3)
        
        ax.set_ylabel('Throttle/Brake (%)', fontsize=10)
        ax2.set_ylabel('Steering', fontsize=10)
        ax.set_xlabel('Time (seconds)', fontsize=10)
        ax.set_ylim(-5, 105)
        ax2.set_ylim(-1.1, 1.1)
        ax.set_title(f'Section {section_num}: {start_time:.2f}s - {end_time:.2f}s', 
                    fontsize=11, fontweight='bold')
        ax.grid(True, alpha=0.3, linewidth=0.5)
        
        # Combine legends
        lines1, labels1 = ax.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax.legend(lines1 + lines2, labels1 + labels2, loc='upper right', fontsize=8)
    
    def _plot_braking_zone_detail(self, ax, df, zone, zone_num):
        """Plot detailed analysis of a single braking zone."""
        start_idx, end_idx = zone
        
        # Add context before and after
        context_frames = 30
        plot_start = max(0, start_idx - context_frames)
        plot_end = min(len(df), end_idx + context_frames)
        
        plot_df = df.iloc[plot_start:plot_end].copy()
        brake_zone_df = df.iloc[start_idx:end_idx].copy()
        
        ax2 = ax.twinx()
        
        # Plot full context
        ax.fill_between(plot_df['time'], 0, plot_df['throttle'], 
                       color='green', alpha=0.3)
        ax.fill_between(plot_df['time'], 0, plot_df['brake'], 
                       color='red', alpha=0.3)
        ax.plot(plot_df['time'], plot_df['throttle'], color='darkgreen', linewidth=1.5)
        ax.plot(plot_df['time'], plot_df['brake'], color='darkred', linewidth=1.5)
        
        # Highlight braking zone
        ax.axvspan(brake_zone_df['time'].iloc[0], brake_zone_df['time'].iloc[-1],
                  color='yellow', alpha=0.2, label='Braking Zone')
        
        # Plot steering
        ax2.plot(plot_df['time'], plot_df['steering'], 
                color='blue', linewidth=2, alpha=0.7, label='Steering')
        ax2.axhline(y=0, color='gray', linestyle='--', alpha=0.3)
        
        # Calculate braking stats
        duration = brake_zone_df['time'].iloc[-1] - brake_zone_df['time'].iloc[0]
        max_brake = brake_zone_df['brake'].max()
        avg_brake = brake_zone_df['brake'].mean()
        initial_throttle = df.iloc[start_idx - 1]['throttle'] if start_idx > 0 else 0
        
        ax.set_ylabel('Throttle/Brake (%)', fontsize=10)
        ax2.set_ylabel('Steering', fontsize=10)
        ax.set_xlabel('Time (seconds)', fontsize=10)
        ax.set_ylim(-5, 105)
        ax2.set_ylim(-1.1, 1.1)
        ax.set_title(f'Braking Zone {zone_num} | Duration: {duration:.2f}s | Max: {max_brake:.1f}% | Avg: {avg_brake:.1f}%', 
                    fontsize=11, fontweight='bold')
        ax.grid(True, alpha=0.3, linewidth=0.5)
        
        # Add stats box
        stats_text = f'Duration: {duration:.2f}s\nMax brake: {max_brake:.1f}%\nAvg brake: {avg_brake:.1f}%\nFrom throttle: {initial_throttle:.1f}%'
        ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, fontsize=9, va='top',
               bbox=dict(boxstyle='round', facecolor='white', alpha=0.9))
        
        lines1, labels1 = ax.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax.legend(lines1 + lines2, labels1 + labels2, loc='upper right', fontsize=8)
    
    def _plot_throttle_gradient(self, ax, df):
        """Plot throttle with color gradient showing application rate."""
        # Calculate throttle rate of change
        df_copy = df.copy()
        df_copy['throttle_delta'] = df_copy['throttle'].diff()
        
        # Plot with scatter to show gradient
        scatter = ax.scatter(df_copy['time'], df_copy['throttle'], 
                           c=df_copy['throttle_delta'], cmap='RdYlGn',
                           s=10, alpha=0.6, vmin=-50, vmax=50)
        ax.plot(df_copy['time'], df_copy['throttle'], color='green', 
               linewidth=1, alpha=0.3)
        
        plt.colorbar(scatter, ax=ax, label='Throttle Change Rate (%/frame)')
        
        ax.set_ylabel('Throttle (%)', fontsize=11)
        ax.set_xlabel('Time (seconds)', fontsize=10)
        ax.set_ylim(-5, 105)
        ax.set_title('Throttle Application (Color = Rate of Change)', 
                    fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3, linewidth=0.5)
    
    def _plot_throttle_steering_correlation(self, ax, df):
        """Plot throttle and steering together to show correlation."""
        ax2 = ax.twinx()
        
        ax.fill_between(df['time'], 0, df['throttle'], color='green', alpha=0.4)
        ax.plot(df['time'], df['throttle'], color='darkgreen', linewidth=2)
        
        # Plot absolute steering to compare with throttle
        ax2.plot(df['time'], df['steering'].abs(), color='blue', linewidth=2, alpha=0.7)
        
        ax.set_ylabel('Throttle (%)', fontsize=11)
        ax2.set_ylabel('Steering (Absolute)', fontsize=11)
        ax.set_xlabel('Time (seconds)', fontsize=10)
        ax.set_ylim(-5, 105)
        ax2.set_ylim(0, 1.1)
        ax.set_title('Throttle vs Steering Correlation', fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3, linewidth=0.5)
    
    def _plot_throttle_rate(self, ax, df):
        """Plot rate of throttle application."""
        df_copy = df.copy()
        df_copy['throttle_rate'] = df_copy['throttle'].diff() / df_copy['time'].diff()
        
        # Separate into acceleration and deceleration
        acceleration = df_copy[df_copy['throttle_rate'] > 0]
        deceleration = df_copy[df_copy['throttle_rate'] <= 0]
        
        ax.plot(acceleration['time'], acceleration['throttle_rate'], 
               color='green', linewidth=1, alpha=0.7, label='Acceleration')
        ax.plot(deceleration['time'], deceleration['throttle_rate'], 
               color='red', linewidth=1, alpha=0.7, label='Deceleration')
        ax.axhline(y=0, color='black', linestyle='-', alpha=0.5)
        
        ax.set_ylabel('Throttle Rate (%/second)', fontsize=11)
        ax.set_xlabel('Time (seconds)', fontsize=10)
        ax.set_title('Throttle Application Rate', fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3, linewidth=0.5)
        ax.legend(loc='upper right', fontsize=9)
    
    def _identify_braking_zones(self, df, threshold: float) -> List[Tuple[int, int]]:
        """
        Identify continuous braking zones.
        
        Args:
            df: DataFrame with telemetry data
            threshold: Minimum brake % to consider as braking
            
        Returns:
            List of (start_index, end_index) tuples
        """
        zones = []
        in_zone = False
        start_idx = 0
        
        for idx, row in df.iterrows():
            if row['brake'] >= threshold:
                if not in_zone:
                    in_zone = True
                    start_idx = idx
            else:
                if in_zone:
                    in_zone = False
                    zones.append((start_idx, idx))
        
        # Handle case where braking continues to end
        if in_zone:
            zones.append((start_idx, len(df) - 1))
        
        return zones
    
    def _generate_statistics_text(self, df) -> str:
        """Generate formatted statistics text."""
        duration = df['time'].iloc[-1] - df['time'].iloc[0]
        total_frames = len(df)
        fps = total_frames / duration if duration > 0 else 0
        
        # Throttle stats
        avg_throttle = df['throttle'].mean()
        max_throttle = df['throttle'].max()
        time_full_throttle = len(df[df['throttle'] >= 99]) / fps if fps > 0 else 0
        throttle_pct = (time_full_throttle / duration * 100) if duration > 0 else 0
        
        # Brake stats
        avg_brake = df['brake'].mean()
        max_brake = df['brake'].max()
        num_braking_zones = len(self._identify_braking_zones(df, 10.0))
        time_braking = len(df[df['brake'] >= 10]) / fps if fps > 0 else 0
        brake_pct = (time_braking / duration * 100) if duration > 0 else 0
        
        # Steering stats
        avg_abs_steering = df['steering'].abs().mean()
        max_left = df['steering'].min()
        max_right = df['steering'].max()
        
        stats = f"""
╔══════════════════════════════════════════════════════════════════════════════════════════════════╗
║  LAP STATISTICS                                                                                  ║
╠══════════════════════════════════════════════════════════════════════════════════════════════════╣
║  Duration: {duration:.2f}s  |  Frames: {total_frames}  |  FPS: {fps:.1f}                                    ║
║                                                                                                  ║
║  THROTTLE:  Avg: {avg_throttle:5.1f}%  |  Max: {max_throttle:5.1f}%  |  Full throttle: {time_full_throttle:5.2f}s ({throttle_pct:4.1f}%)          ║
║  BRAKE:     Avg: {avg_brake:5.1f}%  |  Max: {max_brake:5.1f}%  |  Braking time: {time_braking:5.2f}s ({brake_pct:4.1f}%)  |  Events: {num_braking_zones:2d}   ║
║  STEERING:  Avg abs: {avg_abs_steering:4.2f}  |  Max left: {max_left:5.2f}  |  Max right: {max_right:5.2f}                         ║
╚══════════════════════════════════════════════════════════════════════════════════════════════════╝
        """
        
        return stats.strip()

