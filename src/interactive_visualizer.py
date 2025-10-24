"""
Interactive visualization module using Plotly for telemetry graphs and data export.
Provides interactive zoom, pan, hover tooltips, and multi-lap comparison capabilities.
"""

import pandas as pd
import numpy as np
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
                       title: str = 'ACC Telemetry Analysis', use_subplots: bool = False) -> str:
        """
        Create an interactive multi-panel time-series graph of telemetry data using Plotly.
        
        Features:
        - Interactive zoom (click and drag to zoom into regions)
        - Pan (drag while zoomed)
        - Unified hover tooltips showing ALL values at cursor position
        - Synchronized x-axis across all plots
        - Range slider for quick navigation
        - Export controls (download as PNG)
        
        Args:
            df: DataFrame with telemetry data (columns: time, throttle, brake, steering)
            filename: Optional custom filename (will be .html)
            title: Graph title
            use_subplots: If True, use traditional subplots (separate panels). 
                         If False (default), use single plot with multiple y-axes for unified tooltips.
            
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
        
        if use_subplots:
            # Traditional subplot approach (separate panels, no unified tooltip)
            return self._plot_telemetry_subplots(df, filepath, title)
        else:
            # Single plot with multiple y-axes (unified tooltip showing all values)
            return self._plot_telemetry_unified(df, filepath, title)
    
    def _plot_telemetry_subplots(self, df: pd.DataFrame, filepath: Path, title: str) -> str:
        """Create telemetry visualization using traditional subplots (separate panels)."""
        # Create figure with 7 subplots (shared x-axis for synchronized zooming)
        fig = make_subplots(
            rows=7, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.03,
            subplot_titles=('Throttle Input', 'Brake Input', 'Steering Input', 'Speed', 'Gear', 'Traction Control (TC)', 'ABS'),
            row_heights=[0.14, 0.14, 0.14, 0.14, 0.14, 0.14, 0.14]
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
        
        # ===== SPEED PLOT (Row 4) =====
        fig.add_trace(
            go.Scatter(
                x=df['time'],
                y=df['speed'],
                mode='lines',
                name='Speed',
                line=dict(color='#FF8C00', width=2),
                hovertemplate='<b>Speed</b><br>Time: %{x:.2f}s<br>Value: %{y:.0f} km/h<extra></extra>'
            ),
            row=4, col=1
        )
        
        # ===== GEAR PLOT (Row 5) =====
        # Use step plot for gear (gears change discretely, not continuously)
        fig.add_trace(
            go.Scatter(
                x=df['time'],
                y=df['gear'],
                mode='lines',
                name='Gear',
                line=dict(color='#9B59B6', width=2, shape='hv'),  # 'hv' creates step effect
                hovertemplate='<b>Gear</b><br>Time: %{x:.2f}s<br>Gear: %{y:.0f}<extra></extra>'
            ),
            row=5, col=1
        )
        
        # ===== TC PLOT (Row 6) =====
        # Binary indicator for traction control activation
        fig.add_trace(
            go.Scatter(
                x=df['time'],
                y=df['tc_active'],
                mode='lines',
                name='TC Active',
                line=dict(color='#FFA500', width=2, shape='hv'),  # Orange color, step effect
                fill='tozeroy',
                fillcolor='rgba(255, 165, 0, 0.3)',
                hovertemplate='<b>TC Active</b><br>Time: %{x:.2f}s<br>Status: %{y:.0f}<extra></extra>'
            ),
            row=6, col=1
        )
        
        # ===== ABS PLOT (Row 7) =====
        # Binary indicator for ABS activation
        fig.add_trace(
            go.Scatter(
                x=df['time'],
                y=df['abs_active'],
                mode='lines',
                name='ABS Active',
                line=dict(color='#FF8C00', width=2, shape='hv'),  # Dark orange color, step effect
                fill='tozeroy',
                fillcolor='rgba(255, 140, 0, 0.3)',
                hovertemplate='<b>ABS Active</b><br>Time: %{x:.2f}s<br>Status: %{y:.0f}<extra></extra>'
            ),
            row=7, col=1
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
        
        # Speed Y-axis
        fig.update_yaxes(
            title_text="Speed (km/h)", 
            range=[0, 350],
            gridcolor='rgba(128, 128, 128, 0.2)',
            row=4, col=1
        )
        
        # Gear Y-axis
        fig.update_yaxes(
            title_text="Gear", 
            range=[0, 7],
            gridcolor='rgba(128, 128, 128, 0.2)',
            row=5, col=1
        )
        
        # TC Y-axis
        fig.update_yaxes(
            title_text="TC", 
            range=[-0.1, 1.2],
            gridcolor='rgba(128, 128, 128, 0.2)',
            row=6, col=1
        )
        
        # ABS Y-axis
        fig.update_yaxes(
            title_text="ABS", 
            range=[-0.1, 1.2],
            gridcolor='rgba(128, 128, 128, 0.2)',
            row=7, col=1
        )
        
        # X-axis (only on bottom plot)
        fig.update_xaxes(
            title_text="Time (seconds)",
            gridcolor='rgba(128, 128, 128, 0.2)',
            row=7, col=1
        )
        
        # ===== LAP VISUALIZATION FEATURES =====
                # Add vertical lap separators if lap_number column exists
        if 'lap_number' in df.columns:
            valid_laps_df = df[df['lap_number'].notna()]
            
            if not valid_laps_df.empty:
                # Find lap transition points (where lap number changes)
                lap_transitions = valid_laps_df[
                    valid_laps_df['lap_number'] != valid_laps_df['lap_number'].shift()
                ]
                
                # Add vertical lines and annotations at transitions
                for idx, row in lap_transitions.iterrows():
                    transition_time = row['time']
                    lap_num = int(row['lap_number'])
                    
                    # Add vertical line on all seven subplots
                    for subplot_row in [1, 2, 3, 4, 5, 6, 7]:
                        fig.add_vline(
                            x=transition_time,
                            line_dash="dash",
                            line_color="rgba(128, 128, 128, 0.5)",
                            line_width=1,
                            row=subplot_row, col=1
                        )
                    
                    # Add lap annotation on top plot
                    fig.add_annotation(
                        x=transition_time,
                        y=100,
                        text=f"Lap {lap_num}",
                        showarrow=False,
                        font=dict(size=10, color='#34495E'),
                        bgcolor='rgba(255, 255, 255, 0.7)',
                        bordercolor='rgba(128, 128, 128, 0.3)',
                        borderwidth=1,
                        borderpad=3,
                        row=1, col=1,
                        yref='y1'
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
            hovermode='x',  # Show all values at same x-position
            template='plotly_white',
            # Add range slider on bottom plot for easy navigation
            xaxis7=dict(
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
    
    def _plot_telemetry_unified(self, df: pd.DataFrame, filepath: Path, title: str) -> str:
        """
        Create telemetry visualization using single plot with multiple y-axes.
        This enables TRUE unified hover tooltip showing ALL values at once.
        """
        # Create a single figure (not subplots)
        fig = go.Figure()
        
        # Add all traces to the same plot, each with its own y-axis
        # The key is using yaxis='y', yaxis2='y2', etc. and positioning them vertically
        
        # ===== THROTTLE (primary y-axis, domain: top 20%) =====
        fig.add_trace(go.Scatter(
            x=df['time'],
            y=df['throttle'],
            mode='lines',
            name='Throttle',
            line=dict(color='#00FF00', width=2),
            fill='tozeroy',
            fillcolor='rgba(0, 255, 0, 0.3)',
            yaxis='y1',
            hovertemplate='Throttle: %{y:.1f}%<extra></extra>'
        ))
        
        # ===== BRAKE (y-axis 2, domain: 20-40%) =====
        fig.add_trace(go.Scatter(
            x=df['time'],
            y=df['brake'],
            mode='lines',
            name='Brake',
            line=dict(color='#FF0000', width=2),
            fill='tozeroy',
            fillcolor='rgba(255, 0, 0, 0.3)',
            yaxis='y2',
            hovertemplate='Brake: %{y:.1f}%<extra></extra>'
        ))
        
        # ===== STEERING (y-axis 3, domain: 40-60%) =====
        fig.add_trace(go.Scatter(
            x=df['time'],
            y=df['steering'],
            mode='lines',
            name='Steering',
            line=dict(color='#1E90FF', width=2),
            yaxis='y3',
            hovertemplate='Steering: %{y:.3f}<extra></extra>'
        ))
        
        # Add zero line for steering
        fig.add_hline(
            y=0, 
            line_dash="dash", 
            line_color="gray", 
            opacity=0.5,
            yref='y3'
        )
        
        # ===== SPEED (y-axis 4, domain: 60-80%) =====
        fig.add_trace(go.Scatter(
            x=df['time'],
            y=df['speed'],
            mode='lines',
            name='Speed',
            line=dict(color='#FF8C00', width=2),
            yaxis='y4',
            hovertemplate='Speed: %{y:.0f} km/h<extra></extra>'
        ))
        
        # ===== GEAR (y-axis 5, domain: to be adjusted) =====
        fig.add_trace(go.Scatter(
            x=df['time'],
            y=df['gear'],
            mode='lines',
            name='Gear',
            line=dict(color='#9B59B6', width=2, shape='hv'),
            yaxis='y5',
            hovertemplate='Gear: %{y:.0f}<extra></extra>'
        ))
        
        # ===== TC (y-axis 6, domain: to be adjusted) =====
        fig.add_trace(go.Scatter(
            x=df['time'],
            y=df['tc_active'],
            mode='lines',
            name='TC Active',
            line=dict(color='#FFA500', width=2, shape='hv'),
            fill='tozeroy',
            fillcolor='rgba(255, 165, 0, 0.3)',
            yaxis='y6',
            hovertemplate='TC: %{y:.0f}<extra></extra>'
        ))
        
        # ===== ABS (y-axis 7, domain: to be adjusted) =====
        fig.add_trace(go.Scatter(
            x=df['time'],
            y=df['abs_active'],
            mode='lines',
            name='ABS Active',
            line=dict(color='#FF8C00', width=2, shape='hv'),
            fill='tozeroy',
            fillcolor='rgba(255, 140, 0, 0.3)',
            yaxis='y7',
            hovertemplate='ABS: %{y:.0f}<extra></extra>'
        ))
        
        # ===== ADD LAP SEPARATORS =====
        if 'lap_number' in df.columns:
            valid_laps_df = df[df['lap_number'].notna()]
            
            if not valid_laps_df.empty:
                lap_transitions = valid_laps_df[
                    valid_laps_df['lap_number'] != valid_laps_df['lap_number'].shift()
                ]
                
                for idx, row in lap_transitions.iterrows():
                    transition_time = row['time']
                    lap_num = int(row['lap_number'])
                    
                    # Add vertical line (will span entire plot)
                    fig.add_vline(
                        x=transition_time,
                        line_dash="dash",
                        line_color="rgba(128, 128, 128, 0.5)",
                        line_width=1
                    )
                    
                    # Add lap annotation at top
                    fig.add_annotation(
                        x=transition_time,
                        y=1.0,
                        yref='paper',  # Use paper coordinates (0-1 range)
                        text=f"Lap {lap_num}",
                        showarrow=False,
                        font=dict(size=10, color='#34495E'),
                        bgcolor='rgba(255, 255, 255, 0.7)',
                        bordercolor='rgba(128, 128, 128, 0.3)',
                        borderwidth=1,
                        borderpad=3
                    )
        
        # ===== CONFIGURE LAYOUT WITH MULTIPLE Y-AXES =====
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
            hovermode='x unified',  # THIS IS THE KEY! Works with single plot + multiple y-axes
            template='plotly_white',
            
            # Configure the main x-axis with range slider
            xaxis=dict(
                title='Time (seconds)',
                domain=[0, 1],
                rangeslider=dict(visible=True, thickness=0.05),
                gridcolor='rgba(128, 128, 128, 0.2)'
            ),
            
            # Configure 7 separate y-axes, each with its own vertical domain
            # Domain format: [bottom, top] as fraction of plot height (0-1)
            # Each subplot gets ~13% of space with ~1% gap
            
            # Y1 - Throttle (top 13% of plot)
            yaxis1=dict(
                title='Throttle (%)',
                range=[-5, 105],
                domain=[0.87, 1.0],
                gridcolor='rgba(128, 128, 128, 0.2)',
                anchor='x'
            ),
            
            # Y2 - Brake (73-86% of plot)
            yaxis2=dict(
                title='Brake (%)',
                range=[-5, 105],
                domain=[0.73, 0.86],
                gridcolor='rgba(128, 128, 128, 0.2)',
                anchor='x'
            ),
            
            # Y3 - Steering (59-72% of plot)
            yaxis3=dict(
                title='Steering',
                range=[-1.1, 1.1],
                domain=[0.59, 0.72],
                gridcolor='rgba(128, 128, 128, 0.2)',
                anchor='x'
            ),
            
            # Y4 - Speed (45-58% of plot)
            yaxis4=dict(
                title='Speed (km/h)',
                range=[0, 350],
                domain=[0.45, 0.58],
                gridcolor='rgba(128, 128, 128, 0.2)',
                anchor='x'
            ),
            
            # Y5 - Gear (31-44% of plot)
            yaxis5=dict(
                title='Gear',
                range=[0, 7],
                domain=[0.31, 0.44],
                gridcolor='rgba(128, 128, 128, 0.2)',
                anchor='x'
            ),
            
            # Y6 - TC (17-30% of plot)
            yaxis6=dict(
                title='TC',
                range=[-0.1, 1.2],
                domain=[0.17, 0.30],
                gridcolor='rgba(128, 128, 128, 0.2)',
                anchor='x'
            ),
            
            # Y7 - ABS (bottom 3-16% of plot, leaving space for x-axis and range slider)
            yaxis7=dict(
                title='ABS',
                range=[-0.1, 1.2],
                domain=[0.03, 0.16],
                gridcolor='rgba(128, 128, 128, 0.2)',
                anchor='x'
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
            Dictionary with summary statistics including per-lap data if available
        """
        summary = {
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
        
        # Add speed statistics if speed column exists
        if 'speed' in df.columns:
            # Filter out None/NaN speeds
            valid_speeds = df[df['speed'].notna()]
            if not valid_speeds.empty:
                summary['avg_speed'] = valid_speeds['speed'].mean()
                summary['max_speed'] = valid_speeds['speed'].max()
            else:
                summary['avg_speed'] = 0.0
                summary['max_speed'] = 0.0
        else:
            summary['avg_speed'] = 0.0
            summary['max_speed'] = 0.0
        
        # Add TC and ABS statistics if columns exist
        if 'tc_active' in df.columns:
            tc_frames = df['tc_active'].sum()
            summary['tc_active_frames'] = int(tc_frames)
            summary['tc_active_percentage'] = (tc_frames / len(df)) * 100 if len(df) > 0 else 0.0
        else:
            summary['tc_active_frames'] = 0
            summary['tc_active_percentage'] = 0.0
        
        if 'abs_active' in df.columns:
            abs_frames = df['abs_active'].sum()
            summary['abs_active_frames'] = int(abs_frames)
            summary['abs_active_percentage'] = (abs_frames / len(df)) * 100 if len(df) > 0 else 0.0
        else:
            summary['abs_active_frames'] = 0
            summary['abs_active_percentage'] = 0.0
        
        # Add track position statistics if column exists
        if 'track_position' in df.columns:
            valid_positions = df[df['track_position'].notna()]
            if not valid_positions.empty:
                summary['min_track_position'] = valid_positions['track_position'].min()
                summary['max_track_position'] = valid_positions['track_position'].max()
                summary['track_position_tracked'] = True
            else:
                summary['track_position_tracked'] = False
        else:
            summary['track_position_tracked'] = False
        
        # Add lap-based statistics if lap_number column exists
        if 'lap_number' in df.columns:
            # Filter out None/NaN lap numbers
            valid_laps_df = df[df['lap_number'].notna()]
            
            if not valid_laps_df.empty:
                summary['total_laps'] = int(valid_laps_df['lap_number'].nunique())
                summary['laps'] = []
                
                # Generate per-lap statistics
                for lap_num in sorted(valid_laps_df['lap_number'].unique()):
                    lap_df = valid_laps_df[valid_laps_df['lap_number'] == lap_num]
                    
                    if not lap_df.empty:
                        lap_duration = lap_df['time'].iloc[-1] - lap_df['time'].iloc[0]
                        
                        lap_stats = {
                            'lap_number': int(lap_num),
                            'duration': lap_duration,
                            'frames': len(lap_df),
                            'avg_throttle': lap_df['throttle'].mean(),
                            'avg_brake': lap_df['brake'].mean(),
                            'max_throttle': lap_df['throttle'].max(),
                            'max_brake': lap_df['brake'].max(),
                            'avg_steering_abs': lap_df['steering'].abs().mean()
                        }
                        
                        # Add speed statistics if available
                        if 'speed' in lap_df.columns:
                            valid_lap_speeds = lap_df[lap_df['speed'].notna()]
                            if not valid_lap_speeds.empty:
                                lap_stats['avg_speed'] = valid_lap_speeds['speed'].mean()
                                lap_stats['max_speed'] = valid_lap_speeds['speed'].max()
                        
                        summary['laps'].append(lap_stats)
            else:
                summary['total_laps'] = 0
                summary['laps'] = []
        else:
            summary['total_laps'] = 0
            summary['laps'] = []
        
        return summary
    
    def plot_lap_comparison(self, df: pd.DataFrame, lap_numbers: List[int],
                           filename: Optional[str] = None) -> str:
        """
        Create an interactive comparison graph overlaying multiple laps.
        Each lap is normalized to start at time=0 for direct comparison.
        
        Args:
            df: DataFrame with telemetry data including lap_number column
            lap_numbers: List of lap numbers to compare (e.g., [22, 23, 24])
            filename: Optional custom filename
            
        Returns:
            Path to saved HTML file
        """
        if 'lap_number' not in df.columns:
            raise ValueError("DataFrame must contain 'lap_number' column for lap comparison")
        
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            laps_str = '_'.join(map(str, lap_numbers))
            filename = f'telemetry_lap_comparison_{laps_str}_{timestamp}.html'
        
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
        
        # Process each lap
        for idx, lap_num in enumerate(lap_numbers):
            # Filter data for this lap
            lap_df = df[df['lap_number'] == lap_num].copy()
            
            if lap_df.empty:
                print(f"Warning: No data found for lap {lap_num}")
                continue
            
            # Normalize time to start at 0 for this lap
            lap_start_time = lap_df['time'].iloc[0]
            lap_df['normalized_time'] = lap_df['time'] - lap_start_time
            
            # Get lap time if available
            lap_time = lap_df['lap_time'].iloc[0] if 'lap_time' in lap_df.columns else None
            lap_duration = lap_df['normalized_time'].iloc[-1]
            
            # Create label with lap time
            if lap_time:
                label = f"Lap {lap_num} ({lap_time})"
            else:
                label = f"Lap {lap_num} ({lap_duration:.2f}s)"
            
            color = colors[idx % len(colors)]
            
            # Throttle trace
            fig.add_trace(
                go.Scatter(
                    x=lap_df['normalized_time'],
                    y=lap_df['throttle'],
                    mode='lines',
                    name=label,
                    line=dict(color=color, width=2),
                    legendgroup=f'lap{lap_num}',
                    showlegend=True,
                    hovertemplate=f'<b>{label}</b><br>Time: %{{x:.2f}}s<br>Throttle: %{{y:.1f}}%<extra></extra>'
                ),
                row=1, col=1
            )
            
            # Brake trace
            fig.add_trace(
                go.Scatter(
                    x=lap_df['normalized_time'],
                    y=lap_df['brake'],
                    mode='lines',
                    name=label,
                    line=dict(color=color, width=2),
                    legendgroup=f'lap{lap_num}',
                    showlegend=False,
                    hovertemplate=f'<b>{label}</b><br>Time: %{{x:.2f}}s<br>Brake: %{{y:.1f}}%<extra></extra>'
                ),
                row=2, col=1
            )
            
            # Steering trace
            fig.add_trace(
                go.Scatter(
                    x=lap_df['normalized_time'],
                    y=lap_df['steering'],
                    mode='lines',
                    name=label,
                    line=dict(color=color, width=2),
                    legendgroup=f'lap{lap_num}',
                    showlegend=False,
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
        fig.update_xaxes(title_text="Lap Time (seconds)", row=3, col=1)
        
        # Layout
        fig.update_layout(
            title={
                'text': f'Lap Comparison: Laps {", ".join(map(str, lap_numbers))}',
                'x': 0.5,
                'xanchor': 'center',
                'font': {'size': 20, 'family': 'Arial, sans-serif'}
            },
            height=900,
            showlegend=True,
            legend=dict(
                orientation="v",
                yanchor="top",
                y=0.99,
                xanchor="right",
                x=0.99
            ),
            hovermode='x unified',
            template='plotly_white',
            xaxis3=dict(rangeslider=dict(visible=True, thickness=0.05))
        )
        
        fig.write_html(filepath)
        
        return str(filepath)
    
    def _resample_lap_by_position(self, lap_df: pd.DataFrame, position_step: float = 0.5) -> pd.DataFrame:
        """
        Resample a single lap's telemetry data at fixed track position intervals.
        
        This allows position-based comparison between laps by ensuring both laps
        have data points at the same track positions (e.g., 0%, 0.5%, 1.0%, ..., 100%).
        
        Args:
            lap_df: DataFrame for a single lap with track_position column
            position_step: Interval between position samples (default: 0.5% = 200 samples per lap)
        
        Returns:
            Resampled DataFrame with columns: position, throttle, brake, steering, speed, time, frame
        """
        # Filter out rows with missing track_position
        valid_df = lap_df[lap_df['track_position'].notna()].copy()
        
        if valid_df.empty:
            return pd.DataFrame()
        
        # Sort by track_position to ensure interpolation works correctly
        valid_df = valid_df.sort_values('track_position')
        
        # Create target positions from 0 to 100% at fixed intervals
        target_positions = np.arange(0.0, 100.0 + position_step, position_step)
        
        # Interpolate each telemetry channel at target positions
        resampled_data = {
            'position': target_positions,
            'throttle': np.interp(target_positions, valid_df['track_position'], valid_df['throttle']),
            'brake': np.interp(target_positions, valid_df['track_position'], valid_df['brake']),
            'steering': np.interp(target_positions, valid_df['track_position'], valid_df['steering']),
            'time': np.interp(target_positions, valid_df['track_position'], valid_df['time']),
            'frame': np.interp(target_positions, valid_df['track_position'], valid_df['frame'])
        }
        
        # Add speed if available
        if 'speed' in valid_df.columns:
            resampled_data['speed'] = np.interp(target_positions, valid_df['track_position'], valid_df['speed'])
        
        return pd.DataFrame(resampled_data)
    
    def _calculate_time_delta(self, lap_a_df: pd.DataFrame, lap_b_df: pd.DataFrame, fps: float = 30.0) -> np.ndarray:
        """
        Calculate time delta between two laps at each track position.
        
        Delta = time_lap_a - time_lap_b
        - Positive delta: Lap A is slower (behind) at this position
        - Negative delta: Lap A is faster (ahead) at this position
        
        Args:
            lap_a_df: Resampled DataFrame for lap A (baseline)
            lap_b_df: Resampled DataFrame for lap B (comparison)
            fps: Video frames per second (for frame-based calculation)
        
        Returns:
            Array of time deltas in seconds at each position point
        """
        # Use time-based calculation (more accurate than frame-based)
        # Subtract the starting time to get relative lap times
        lap_a_relative_time = lap_a_df['time'].values - lap_a_df['time'].values[0]
        lap_b_relative_time = lap_b_df['time'].values - lap_b_df['time'].values[0]
        
        # Delta = how much slower lap A is compared to lap B at each position
        time_delta = lap_a_relative_time - lap_b_relative_time
        
        return time_delta
    
    def plot_position_based_comparison(self, df: pd.DataFrame, filename: Optional[str] = None,
                                      position_step: float = 0.5, fps: float = 30.0) -> str:
        """
        Create an interactive position-based lap comparison with dropdown selector.
        
        This visualization aligns laps by track position (not time) to enable
        direct comparison of driving technique at each point around the track.
        
        Features:
        - Dropdown menu to select which two laps to compare
        - 5 synchronized plots (x-axis = Track Position %):
          1. Throttle overlay
          2. Brake overlay
          3. Steering overlay
          4. Speed overlay
          5. Time Delta (shows where time is gained/lost)
        - Interactive zoom/pan
        - Unified hover tooltips
        
        Args:
            df: DataFrame with telemetry data including lap_number and track_position columns
            filename: Optional custom filename
            position_step: Interval between position samples (default: 0.5%)
            fps: Video frames per second for time delta calculation
        
        Returns:
            Path to saved HTML file
        """
        # Validate required columns
        required_cols = ['lap_number', 'track_position', 'throttle', 'brake', 'steering', 'time', 'frame']
        missing_cols = [col for col in required_cols if col not in df.columns]
        
        if missing_cols:
            raise ValueError(f"DataFrame missing required columns: {missing_cols}")
        
        # Filter to only rows with valid lap_number and track_position
        valid_df = df[(df['lap_number'].notna()) & (df['track_position'].notna())].copy()
        
        if valid_df.empty:
            raise ValueError("No valid data with both lap_number and track_position")
        
        # Get unique laps
        unique_laps = sorted(valid_df['lap_number'].unique())
        
        if len(unique_laps) < 2:
            raise ValueError(f"Need at least 2 laps for comparison, found {len(unique_laps)}")
        
        print(f"\n📊 Generating position-based lap comparison...")
        print(f"   Found {len(unique_laps)} laps: {unique_laps}")
        
        # Generate all pairwise comparisons (lap_a vs lap_b where a < b)
        comparison_pairs = []
        for i, lap_a in enumerate(unique_laps):
            for lap_b in unique_laps[i+1:]:
                comparison_pairs.append((int(lap_a), int(lap_b)))
        
        print(f"   Generating {len(comparison_pairs)} pairwise comparisons...")
        
        # Resample all laps by position
        print(f"   Resampling laps at {position_step}% intervals...")
        resampled_laps = {}
        for lap_num in unique_laps:
            lap_df = valid_df[valid_df['lap_number'] == lap_num]
            resampled = self._resample_lap_by_position(lap_df, position_step)
            
            if not resampled.empty:
                resampled_laps[int(lap_num)] = resampled
                print(f"      Lap {int(lap_num)}: {len(resampled)} position points")
        
        # Create figure with 5 subplots
        fig = make_subplots(
            rows=5, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.03,
            subplot_titles=('Throttle Input', 'Brake Input', 'Steering Input', 'Speed', 'Time Delta'),
            row_heights=[0.18, 0.18, 0.18, 0.18, 0.28]
        )
        
        # Color palette for laps
        colors = ['#00FF00', '#FF6B6B', '#4ECDC4', '#FFD93D', '#6C5CE7', '#FD79A8']
        
        # Track which traces belong to which comparison (for dropdown visibility control)
        trace_visibility_map = []  # List of lists: [[comparison_0_traces], [comparison_1_traces], ...]
        
        # Generate traces for all comparisons
        for comparison_idx, (lap_a, lap_b) in enumerate(comparison_pairs):
            if lap_a not in resampled_laps or lap_b not in resampled_laps:
                print(f"   ⚠️  Skipping comparison Lap {lap_a} vs {lap_b} (missing data)")
                continue
            
            lap_a_data = resampled_laps[lap_a]
            lap_b_data = resampled_laps[lap_b]
            
            # Calculate time delta
            time_delta = self._calculate_time_delta(lap_a_data, lap_b_data, fps)
            
            # Determine colors
            color_a = colors[0]  # Green for first lap
            color_b = colors[1]  # Red for second lap
            
            # Track trace indices for this comparison
            comparison_traces = []
            
            # Determine if these traces should be visible initially (only first comparison)
            is_visible = (comparison_idx == 0)
            
            # === THROTTLE TRACES (Row 1) ===
            # Lap A throttle
            fig.add_trace(
                go.Scatter(
                    x=lap_a_data['position'],
                    y=lap_a_data['throttle'],
                    mode='lines',
                    name=f'Lap {lap_a}',
                    line=dict(color=color_a, width=2),
                    legendgroup=f'comparison_{comparison_idx}',
                    showlegend=True,
                    visible=is_visible,
                    hovertemplate=f'<b>Lap {lap_a}</b><br>Position: %{{x:.1f}}%<br>Throttle: %{{y:.1f}}%<extra></extra>'
                ),
                row=1, col=1
            )
            comparison_traces.append(len(fig.data) - 1)
            
            # Lap B throttle
            fig.add_trace(
                go.Scatter(
                    x=lap_b_data['position'],
                    y=lap_b_data['throttle'],
                    mode='lines',
                    name=f'Lap {lap_b}',
                    line=dict(color=color_b, width=2),
                    legendgroup=f'comparison_{comparison_idx}',
                    showlegend=True,
                    visible=is_visible,
                    hovertemplate=f'<b>Lap {lap_b}</b><br>Position: %{{x:.1f}}%<br>Throttle: %{{y:.1f}}%<extra></extra>'
                ),
                row=1, col=1
            )
            comparison_traces.append(len(fig.data) - 1)
            
            # === BRAKE TRACES (Row 2) ===
            fig.add_trace(
                go.Scatter(
                    x=lap_a_data['position'],
                    y=lap_a_data['brake'],
                    mode='lines',
                    name=f'Lap {lap_a}',
                    line=dict(color=color_a, width=2),
                    legendgroup=f'comparison_{comparison_idx}',
                    showlegend=False,
                    visible=is_visible,
                    hovertemplate=f'<b>Lap {lap_a}</b><br>Position: %{{x:.1f}}%<br>Brake: %{{y:.1f}}%<extra></extra>'
                ),
                row=2, col=1
            )
            comparison_traces.append(len(fig.data) - 1)
            
            fig.add_trace(
                go.Scatter(
                    x=lap_b_data['position'],
                    y=lap_b_data['brake'],
                    mode='lines',
                    name=f'Lap {lap_b}',
                    line=dict(color=color_b, width=2),
                    legendgroup=f'comparison_{comparison_idx}',
                    showlegend=False,
                    visible=is_visible,
                    hovertemplate=f'<b>Lap {lap_b}</b><br>Position: %{{x:.1f}}%<br>Brake: %{{y:.1f}}%<extra></extra>'
                ),
                row=2, col=1
            )
            comparison_traces.append(len(fig.data) - 1)
            
            # === STEERING TRACES (Row 3) ===
            fig.add_trace(
                go.Scatter(
                    x=lap_a_data['position'],
                    y=lap_a_data['steering'],
                    mode='lines',
                    name=f'Lap {lap_a}',
                    line=dict(color=color_a, width=2),
                    legendgroup=f'comparison_{comparison_idx}',
                    showlegend=False,
                    visible=is_visible,
                    hovertemplate=f'<b>Lap {lap_a}</b><br>Position: %{{x:.1f}}%<br>Steering: %{{y:.3f}}<extra></extra>'
                ),
                row=3, col=1
            )
            comparison_traces.append(len(fig.data) - 1)
            
            fig.add_trace(
                go.Scatter(
                    x=lap_b_data['position'],
                    y=lap_b_data['steering'],
                    mode='lines',
                    name=f'Lap {lap_b}',
                    line=dict(color=color_b, width=2),
                    legendgroup=f'comparison_{comparison_idx}',
                    showlegend=False,
                    visible=is_visible,
                    hovertemplate=f'<b>Lap {lap_b}</b><br>Position: %{{x:.1f}}%<br>Steering: %{{y:.3f}}<extra></extra>'
                ),
                row=3, col=1
            )
            comparison_traces.append(len(fig.data) - 1)
            
            # === SPEED TRACES (Row 4) ===
            if 'speed' in lap_a_data.columns and 'speed' in lap_b_data.columns:
                fig.add_trace(
                    go.Scatter(
                        x=lap_a_data['position'],
                        y=lap_a_data['speed'],
                        mode='lines',
                        name=f'Lap {lap_a}',
                        line=dict(color=color_a, width=2),
                        legendgroup=f'comparison_{comparison_idx}',
                        showlegend=False,
                        visible=is_visible,
                        hovertemplate=f'<b>Lap {lap_a}</b><br>Position: %{{x:.1f}}%<br>Speed: %{{y:.0f}} km/h<extra></extra>'
                    ),
                    row=4, col=1
                )
                comparison_traces.append(len(fig.data) - 1)
                
                fig.add_trace(
                    go.Scatter(
                        x=lap_b_data['position'],
                        y=lap_b_data['speed'],
                        mode='lines',
                        name=f'Lap {lap_b}',
                        line=dict(color=color_b, width=2),
                        legendgroup=f'comparison_{comparison_idx}',
                        showlegend=False,
                        visible=is_visible,
                        hovertemplate=f'<b>Lap {lap_b}</b><br>Position: %{{x:.1f}}%<br>Speed: %{{y:.0f}} km/h<extra></extra>'
                    ),
                    row=4, col=1
                )
                comparison_traces.append(len(fig.data) - 1)
            
            # === TIME DELTA TRACE (Row 5) ===
            # Color: green where lap A is faster (negative delta), red where lap A is slower (positive delta)
            fig.add_trace(
                go.Scatter(
                    x=lap_a_data['position'],
                    y=time_delta,
                    mode='lines',
                    name=f'Delta (Lap {lap_a} - Lap {lap_b})',
                    line=dict(color='#9B59B6', width=2),
                    fill='tozeroy',
                    fillcolor='rgba(155, 89, 182, 0.3)',
                    legendgroup=f'comparison_{comparison_idx}',
                    showlegend=False,
                    visible=is_visible,
                    hovertemplate=f'<b>Time Delta</b><br>Position: %{{x:.1f}}%<br>Delta: %{{y:.3f}}s<br>(Lap {lap_a} - Lap {lap_b})<extra></extra>'
                ),
                row=5, col=1
            )
            comparison_traces.append(len(fig.data) - 1)
            
            # Store trace indices for this comparison
            trace_visibility_map.append(comparison_traces)
        
        # Add zero line for steering and time delta
        fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5, row=3, col=1)
        fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5, row=5, col=1)
        
        # Update axes labels
        fig.update_yaxes(title_text="Throttle (%)", range=[-5, 105], row=1, col=1)
        fig.update_yaxes(title_text="Brake (%)", range=[-5, 105], row=2, col=1)
        fig.update_yaxes(title_text="Steering", range=[-1.1, 1.1], row=3, col=1)
        fig.update_yaxes(title_text="Speed (km/h)", range=[0, 350], row=4, col=1)
        fig.update_yaxes(title_text="Time Delta (s)", row=5, col=1)
        fig.update_xaxes(title_text="Track Position (%)", row=5, col=1)
        
        # Create dropdown menu buttons
        dropdown_buttons = []
        for comparison_idx, (lap_a, lap_b) in enumerate(comparison_pairs):
            if lap_a not in resampled_laps or lap_b not in resampled_laps:
                continue
            
            # Create visibility array: all False except for traces of this comparison
            visibility = [False] * len(fig.data)
            for trace_idx in trace_visibility_map[comparison_idx]:
                visibility[trace_idx] = True
            
            dropdown_buttons.append({
                'label': f'Lap {lap_a} vs Lap {lap_b}',
                'method': 'update',
                'args': [
                    {'visible': visibility},
                    {'title': f'Position-Based Lap Comparison: Lap {lap_a} vs Lap {lap_b}'}
                ]
            })
        
        # Update layout with dropdown
        fig.update_layout(
            title={
                'text': f'Position-Based Lap Comparison: Lap {comparison_pairs[0][0]} vs Lap {comparison_pairs[0][1]}',
                'x': 0.5,
                'xanchor': 'center',
                'font': {'size': 20, 'family': 'Arial, sans-serif', 'color': '#2C3E50'}
            },
            updatemenus=[{
                'buttons': dropdown_buttons,
                'direction': 'down',
                'showactive': True,
                'x': 0.02,
                'xanchor': 'left',
                'y': 1.15,
                'yanchor': 'top',
                'bgcolor': '#FFFFFF',
                'bordercolor': '#CCCCCC',
                'borderwidth': 1
            }],
            height=1100,
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.08,
                xanchor="right",
                x=0.98
            ),
            hovermode='x unified',
            template='plotly_white',
            xaxis5=dict(rangeslider=dict(visible=True, thickness=0.05))
        )
        
        # Generate filename
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'lap_comparison_position_{timestamp}.html'
        
        if not filename.endswith('.html'):
            filename = filename.replace('.png', '.html')
        
        filepath = self.output_dir / filename
        
        # Save HTML
        fig.write_html(
            filepath,
            config={
                'displayModeBar': True,
                'displaylogo': False,
                'modeBarButtonsToAdd': ['drawline', 'drawopenpath', 'eraseshape'],
                'modeBarButtonsToRemove': ['lasso2d', 'select2d'],
                'toImageButtonOptions': {
                    'format': 'png',
                    'filename': 'lap_comparison_position',
                    'height': 1200,
                    'width': 1920,
                    'scale': 2
                }
            }
        )
        
        print(f"   ✅ Position-based comparison saved: {filepath}")
        
        return str(filepath)

