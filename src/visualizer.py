"""
Visualization module for generating telemetry graphs and exporting data.
"""

import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
from pathlib import Path
from typing import List, Dict


class TelemetryVisualizer:
    """Handles telemetry data visualization and export."""
    
    def __init__(self, output_dir: str = 'data/output'):
        """
        Initialize visualizer.
        
        Args:
            output_dir: Directory to save output files
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def create_dataframe(self, telemetry_data: List[Dict]) -> pd.DataFrame:
        """
        Convert telemetry data list to pandas DataFrame.
        
        Args:
            telemetry_data: List of dicts with frame, time, throttle, brake, steering
            
        Returns:
            pandas DataFrame
        """
        return pd.DataFrame(telemetry_data)
    
    def export_csv(self, df: pd.DataFrame, filename: str = None) -> str:
        """
        Export telemetry data to CSV.
        
        Args:
            df: DataFrame with telemetry data
            filename: Optional custom filename
            
        Returns:
            Path to saved CSV file
        """
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'telemetry_{timestamp}.csv'
        
        filepath = self.output_dir / filename
        df.to_csv(filepath, index=False)
        
        return str(filepath)
    
    def plot_telemetry(self, df: pd.DataFrame, filename: str = None) -> str:
        """
        Create a multi-panel time-series graph of telemetry data.
        
        Args:
            df: DataFrame with telemetry data
            filename: Optional custom filename
            
        Returns:
            Path to saved graph image
        """
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'telemetry_{timestamp}.png'
        
        filepath = self.output_dir / filename
        
        # Create figure with 3 subplots
        fig, axes = plt.subplots(3, 1, figsize=(14, 10), sharex=True)
        fig.suptitle('ACC Telemetry Analysis', fontsize=16, fontweight='bold')
        
        # Throttle plot
        axes[0].plot(df['time'], df['throttle'], color='green', linewidth=1.5, label='Throttle')
        axes[0].set_ylabel('Throttle (%)', fontsize=12)
        axes[0].set_ylim(-5, 105)
        axes[0].grid(True, alpha=0.3)
        axes[0].legend(loc='upper right')
        axes[0].fill_between(df['time'], 0, df['throttle'], color='green', alpha=0.3)
        
        # Brake plot
        axes[1].plot(df['time'], df['brake'], color='red', linewidth=1.5, label='Brake')
        axes[1].set_ylabel('Brake (%)', fontsize=12)
        axes[1].set_ylim(-5, 105)
        axes[1].grid(True, alpha=0.3)
        axes[1].legend(loc='upper right')
        axes[1].fill_between(df['time'], 0, df['brake'], color='red', alpha=0.3)
        
        # Steering plot
        axes[2].plot(df['time'], df['steering'], color='blue', linewidth=1.5, label='Steering')
        axes[2].set_ylabel('Steering', fontsize=12)
        axes[2].set_xlabel('Time (seconds)', fontsize=12)
        axes[2].set_ylim(-1.1, 1.1)
        axes[2].axhline(y=0, color='gray', linestyle='--', alpha=0.5)
        axes[2].grid(True, alpha=0.3)
        axes[2].legend(loc='upper right')
        
        # Add steering labels
        axes[2].text(df['time'].iloc[0], -1.05, 'Left', fontsize=9, ha='left')
        axes[2].text(df['time'].iloc[-1], 1.05, 'Right', fontsize=9, ha='right')
        
        plt.tight_layout()
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        
        return str(filepath)
    
    def generate_summary(self, df: pd.DataFrame) -> Dict:
        """
        Generate summary statistics from telemetry data.
        
        Args:
            df: DataFrame with telemetry data
            
        Returns:
            Dictionary with summary statistics
        """
        return {
            'duration': df['time'].iloc[-1] - df['time'].iloc[0],
            'total_frames': len(df),
            'avg_throttle': df['throttle'].mean(),
            'max_throttle': df['throttle'].max(),
            'avg_brake': df['brake'].mean(),
            'max_brake': df['brake'].max(),
            'avg_steering_abs': df['steering'].abs().mean(),
            'max_steering_left': df['steering'].min(),
            'max_steering_right': df['steering'].max()
        }

