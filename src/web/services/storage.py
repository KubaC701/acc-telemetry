"""File storage and management service."""

import json
import re
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime
import pandas as pd

from ..config import settings
from ..models import VideoMetadata, LapMetadata, VideoListItem


class StorageService:
    """Manages file storage and retrieval for processed videos."""

    def __init__(self):
        self.output_dir = settings.data_output_dir
        self.videos_dir = settings.videos_dir

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """
        Sanitize a filename to be filesystem-safe.

        Args:
            filename: Original filename

        Returns:
            Sanitized filename
        """
        # Remove extension if present
        filename = Path(filename).stem

        # Replace spaces with underscores
        filename = filename.replace(' ', '_')

        # Remove special characters
        filename = re.sub(r'[^a-zA-Z0-9_-]', '', filename)

        # Limit length
        filename = filename[:100]

        return filename

    def get_video_directory(self, video_name: str) -> Path:
        """
        Get the directory path for a video.

        Args:
            video_name: Name of the video (sanitized)

        Returns:
            Path to the video directory
        """
        return self.output_dir / video_name

    def get_video_path(self, video_name: str) -> Path:
        """
        Get the path for the raw video file.

        Args:
            video_name: Name of the video (sanitized)

        Returns:
            Path to the video file
        """
        return self.videos_dir / f"{video_name}.mp4"

    def video_exists(self, video_name: str) -> bool:
        """
        Check if a video has been processed.

        Args:
            video_name: Name of the video

        Returns:
            True if video data exists
        """
        video_dir = self.get_video_directory(video_name)
        metadata_path = video_dir / "metadata.json"
        csv_path = video_dir / "telemetry.csv"

        return metadata_path.exists() and csv_path.exists()

    def save_metadata(self, video_name: str, metadata: VideoMetadata) -> None:
        """
        Save video metadata to JSON file.

        Args:
            video_name: Name of the video
            metadata: VideoMetadata object
        """
        video_dir = self.get_video_directory(video_name)
        video_dir.mkdir(parents=True, exist_ok=True)

        metadata_path = video_dir / "metadata.json"

        with open(metadata_path, 'w') as f:
            json.dump(metadata.model_dump(), f, indent=2)

    def load_metadata(self, video_name: str) -> Optional[VideoMetadata]:
        """
        Load video metadata from JSON file.

        Args:
            video_name: Name of the video

        Returns:
            VideoMetadata object or None if not found
        """
        metadata_path = self.get_video_directory(video_name) / "metadata.json"

        if not metadata_path.exists():
            return None

        with open(metadata_path, 'r') as f:
            data = json.load(f)

        return VideoMetadata(**data)

    def get_telemetry_csv_path(self, video_name: str) -> Path:
        """
        Get the path to the telemetry CSV file.

        Args:
            video_name: Name of the video

        Returns:
            Path to the CSV file
        """
        return self.get_video_directory(video_name) / "telemetry.csv"

    def load_telemetry_data(self, video_name: str) -> Optional[pd.DataFrame]:
        """
        Load telemetry data from CSV file.

        Args:
            video_name: Name of the video

        Returns:
            DataFrame with telemetry data or None if not found
        """
        csv_path = self.get_telemetry_csv_path(video_name)

        if not csv_path.exists():
            return None

        return pd.read_csv(csv_path)

    def list_videos(self) -> List[VideoListItem]:
        """
        List all processed videos.

        Returns:
            List of VideoListItem objects
        """
        videos = []

        # Iterate through directories in output folder
        for video_dir in self.output_dir.iterdir():
            if not video_dir.is_dir():
                continue

            metadata_path = video_dir / "metadata.json"
            if not metadata_path.exists():
                continue

            try:
                metadata = self.load_metadata(video_dir.name)
                if metadata:
                    videos.append(VideoListItem(
                        video_name=metadata.video_name,
                        total_laps=metadata.total_laps,
                        duration=metadata.duration,
                        processed_at=metadata.processed_at,
                        fps=metadata.fps
                    ))
            except Exception as e:
                print(f"Error loading metadata for {video_dir.name}: {e}")
                continue

        # Sort by processed_at (most recent first)
        videos.sort(key=lambda x: x.processed_at, reverse=True)

        return videos

    def delete_video(self, video_name: str) -> bool:
        """
        Delete all data for a video.

        Args:
            video_name: Name of the video

        Returns:
            True if deletion successful
        """
        video_dir = self.get_video_directory(video_name)

        if not video_dir.exists():
            return False

        import shutil
        shutil.rmtree(video_dir)

        return True

    def get_lap_data(self, video_name: str, lap_number: int) -> Optional[pd.DataFrame]:
        """
        Get telemetry data for a specific lap.

        Args:
            video_name: Name of the video
            lap_number: Lap number to retrieve

        Returns:
            DataFrame with lap data or None if not found
        """
        df = self.load_telemetry_data(video_name)

        if df is None:
            return None

        # Filter for specific lap
        lap_df = df[df['lap_number'] == lap_number]

        if lap_df.empty:
            return None

        return lap_df

    def get_multiple_laps_data(
        self,
        lap_identifiers: List[Dict[str, any]]
    ) -> List[Dict[str, any]]:
        """
        Get telemetry data for multiple laps across sessions.

        Args:
            lap_identifiers: List of dicts with 'video_name' and 'lap_number'
                Example: [{'video_name': 'video1', 'lap_number': 3}, ...]

        Returns:
            List of dicts with lap data including metadata
            Example: [
                {
                    'video_name': 'video1',
                    'lap_number': 3,
                    'lap_time': '1:45.23',
                    'data': [...telemetry data points...]
                },
                ...
            ]
        """
        result = []

        for identifier in lap_identifiers:
            video_name = identifier.get('video_name')
            lap_number = identifier.get('lap_number')

            if not video_name or lap_number is None:
                continue

            # Get lap data
            lap_df = self.get_lap_data(video_name, lap_number)
            if lap_df is None:
                continue

            # Get metadata for lap time
            metadata = self.load_metadata(video_name)
            lap_time = None
            if metadata:
                for lap_meta in metadata.laps:
                    if lap_meta.lap_number == lap_number:
                        lap_time = lap_meta.lap_time
                        break

            # Convert DataFrame to list of dicts
            lap_data_list = lap_df.to_dict(orient='records')

            result.append({
                'video_name': video_name,
                'lap_number': lap_number,
                'lap_time': lap_time,
                'data': lap_data_list
            })

        return result
