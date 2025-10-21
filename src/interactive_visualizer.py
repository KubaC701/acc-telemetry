"""
Interactive visualization module using Plotly for telemetry graphs and data export.
Provides interactive zoom, pan, hover tooltips, and multi-lap comparison capabilities.
"""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional


class InteractiveTelemetryVisualizer:
    """Handles interactive telemetry data visualization and export using Plotly."""
    
    def __init__(self, output_dir: str = 'data/output'):
        """
        Initialize interactive visualizer.
        
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
    
    def export_csv(self, df: pd.DataFrame, filename: Optional[str] = None) -> str:
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
    
    def plot_telemetry(self, df: pd.DataFrame, filename: Optional[str] = None, 
                       title: str = 'ACC Telemetry Analysis') -> str:
        """
        Create an interactive multi-panel time-series graph of telemetry data using Plotly.
        
        Features:
        - Interactive zoom (click and drag to zoom into regions)
        - Pan (drag while zoomed)
        - Hover tooltips (exact values at any point)
        - Synchronized x-axis across all three plots
        - Range slider for quick navigation
        - Export controls (download as PNG)
        
        Args:
            df: DataFrame with telemetry data (columns: time, throttle, brake, steering)
            filename: Optional custom filename (will be .html)
            title: Graph title
            
        Returns:
            Path to saved HTML file
        """
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'telemetry_interactive_{timestamp}.html'
        
        # Ensure filename has .html extension
        if not filename.endswith('.html'):
            filename = filename.replace('.png', '.html')
        
        filepath = self.output_dir / filename
        
        # Create figure with 3 subplots (shared x-axis for synchronized zooming)
        fig = make_subplots(
            rows=3, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.08,
            subplot_titles=('Throttle Input', 'Brake Input', 'Steering Input'),
            row_heights=[0.33, 0.33, 0.34]
        )
        
        # ===== THROTTLE PLOT (Row 1) =====
        fig.add_trace(
            go.Scatter(
                x=df['time'],
                y=df['throttle'],
                mode='lines',
                name='Throttle',
                line=dict(color='#00FF00', width=2),
                fill='tozeroy',
                fillcolor='rgba(0, 255, 0, 0.3)',
                hovertemplate='<b>Throttle</b><br>Time: %{x:.2f}s<br>Value: %{y:.1f}%<extra></extra>'
            ),
            row=1, col=1
        )
        
        # ===== BRAKE PLOT (Row 2) =====
        fig.add_trace(
            go.Scatter(
                x=df['time'],
                y=df['brake'],
                mode='lines',
                name='Brake',
                line=dict(color='#FF0000', width=2),
                fill='tozeroy',
                fillcolor='rgba(255, 0, 0, 0.3)',
                hovertemplate='<b>Brake</b><br>Time: %{x:.2f}s<br>Value: %{y:.1f}%<extra></extra>'
            ),
            row=2, col=1
        )
        
        # ===== STEERING PLOT (Row 3) =====
        fig.add_trace(
            go.Scatter(
                x=df['time'],
                y=df['steering'],
                mode='lines',
                name='Steering',
                line=dict(color='#1E90FF', width=2),
                hovertemplate='<b>Steering</b><br>Time: %{x:.2f}s<br>Value: %{y:.3f}<extra></extra>'
            ),
            row=3, col=1
        )
        
        # Add center line (zero) for steering
        fig.add_hline(
            y=0, 
            line_dash="dash", 
            line_color="gray", 
            opacity=0.5,
            row=3, col=1
        )
        
        # ===== UPDATE AXES =====
        # Throttle Y-axis
        fig.update_yaxes(
            title_text="Throttle (%)", 
            range=[-5, 105],
            gridcolor='rgba(128, 128, 128, 0.2)',
            row=1, col=1
        )
        
        # Brake Y-axis
        fig.update_yaxes(
            title_text="Brake (%)", 
            range=[-5, 105],
            gridcolor='rgba(128, 128, 128, 0.2)',
            row=2, col=1
        )
        
        # Steering Y-axis
        fig.update_yaxes(
            title_text="Steering", 
            range=[-1.1, 1.1],
            gridcolor='rgba(128, 128, 128, 0.2)',
            row=3, col=1
        )
        
        # X-axis (only on bottom plot)
        fig.update_xaxes(
            title_text="Time (seconds)",
            gridcolor='rgba(128, 128, 128, 0.2)',
            row=3, col=1
        )
        
        # ===== LAYOUT CONFIGURATION =====
        fig.update_layout(
            title={
                'text': title,
                'x': 0.5,
                'xanchor': 'center',
                'font': {'size': 20, 'family': 'Arial, sans-serif', 'color': '#2C3E50'}
            },
            height=900,
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ),
            hovermode='x unified',  # Show all values at same x-position
            template='plotly_white',
            # Add range slider on bottom plot for easy navigation
            xaxis3=dict(
                rangeslider=dict(visible=True, thickness=0.05),
                type='linear'
            )
        )
        
        # Save as interactive HTML
        fig.write_html(
            filepath,
            config={
                'displayModeBar': True,
                'displaylogo': False,
                'modeBarButtonsToAdd': ['drawline', 'drawopenpath', 'eraseshape'],
                'modeBarButtonsToRemove': ['lasso2d', 'select2d'],
                'toImageButtonOptions': {
                    'format': 'png',
                    'filename': 'telemetry_export',
                    'height': 1080,
                    'width': 1920,
                    'scale': 2
                }
            }
        )
        
        return str(filepath)
    
    def plot_comparison(self, dataframes: List[pd.DataFrame], labels: List[str],
                       filename: Optional[str] = None) -> str:
        """
        Create an interactive comparison graph overlaying multiple laps.
        
        Args:
            dataframes: List of DataFrames, each representing one lap
            labels: List of labels for each lap (e.g., ["Lap 1", "Lap 2", "Best Lap"])
            filename: Optional custom filename
            
        Returns:
            Path to saved HTML file
        """
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'telemetry_comparison_{timestamp}.html'
        
        if not filename.endswith('.html'):
            filename = filename.replace('.png', '.html')
        
        filepath = self.output_dir / filename
        
        # Color palette for different laps
        colors = ['#00FF00', '#FF6B6B', '#4ECDC4', '#FFD93D', '#6C5CE7', '#FD79A8']
        
        # Create figure with 3 subplots
        fig = make_subplots(
            rows=3, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.08,
            subplot_titles=('Throttle Comparison', 'Brake Comparison', 'Steering Comparison'),
            row_heights=[0.33, 0.33, 0.34]
        )
        
        # Add traces for each lap
        for idx, (df, label) in enumerate(zip(dataframes, labels)):
            color = colors[idx % len(colors)]
            
            # Throttle
            fig.add_trace(
                go.Scatter(
                    x=df['time'],
                    y=df['throttle'],
                    mode='lines',
                    name=f'{label} - Throttle',
                    line=dict(color=color, width=2),
                    legendgroup=label,
                    hovertemplate=f'<b>{label}</b><br>Time: %{{x:.2f}}s<br>Throttle: %{{y:.1f}}%<extra></extra>'
                ),
                row=1, col=1
            )
            
            # Brake
            fig.add_trace(
                go.Scatter(
                    x=df['time'],
                    y=df['brake'],
                    mode='lines',
                    name=f'{label} - Brake',
                    line=dict(color=color, width=2, dash='dot'),
                    legendgroup=label,
                    hovertemplate=f'<b>{label}</b><br>Time: %{{x:.2f}}s<br>Brake: %{{y:.1f}}%<extra></extra>'
                ),
                row=2, col=1
            )
            
            # Steering
            fig.add_trace(
                go.Scatter(
                    x=df['time'],
                    y=df['steering'],
                    mode='lines',
                    name=f'{label} - Steering',
                    line=dict(color=color, width=2, dash='dash'),
                    legendgroup=label,
                    hovertemplate=f'<b>{label}</b><br>Time: %{{x:.2f}}s<br>Steering: %{{y:.3f}}<extra></extra>'
                ),
                row=3, col=1
            )
        
        # Add center line for steering
        fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5, row=3, col=1)
        
        # Update axes
        fig.update_yaxes(title_text="Throttle (%)", range=[-5, 105], row=1, col=1)
        fig.update_yaxes(title_text="Brake (%)", range=[-5, 105], row=2, col=1)
        fig.update_yaxes(title_text="Steering", range=[-1.1, 1.1], row=3, col=1)
        fig.update_xaxes(title_text="Time (seconds)", row=3, col=1)
        
        # Layout
        fig.update_layout(
            title={
                'text': 'Lap Comparison Analysis',
                'x': 0.5,
                'xanchor': 'center',
                'font': {'size': 20, 'family': 'Arial, sans-serif'}
            },
            height=900,
            showlegend=True,
            hovermode='x unified',
            template='plotly_white',
            xaxis3=dict(rangeslider=dict(visible=True, thickness=0.05))
        )
        
        fig.write_html(filepath)
        
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

