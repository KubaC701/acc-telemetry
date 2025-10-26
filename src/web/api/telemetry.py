"""API endpoints for telemetry data retrieval."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse, FileResponse
from typing import List, Optional
import pandas as pd
import numpy as np
import io

from ..models import (
    LapMetadata,
    TelemetryDataPoint,
    ComparisonRequest,
    LapComparisonData,
    LapIdentifier
)
from ..services.storage import StorageService

router = APIRouter()
storage = StorageService()


def clean_telemetry_for_json(df: pd.DataFrame) -> list:
    """
    Clean telemetry DataFrame for JSON serialization.

    Replaces NaN and Infinity values with None to ensure JSON compliance.

    Args:
        df: Telemetry DataFrame

    Returns:
        List of dictionaries ready for JSON serialization
    """
    # Replace inf/-inf with None
    df = df.replace([np.inf, -np.inf], None)

    # Replace NaN with None
    df = df.where(pd.notna(df), None)

    # Convert to dict
    data = df.to_dict(orient='records')

    # Additional pass to clean any remaining problematic values
    def clean_value(val):
        if isinstance(val, float):
            if np.isnan(val) or np.isinf(val):
                return None
        return val

    return [{k: clean_value(v) for k, v in record.items()} for record in data]


@router.get("/{video_name}/laps", response_model=List[LapMetadata])
async def get_laps(video_name: str):
    """
    Get list of laps for a video.

    Args:
        video_name: Name of the video

    Returns:
        List of LapMetadata objects
    """
    metadata = storage.load_metadata(video_name)

    if metadata is None:
        raise HTTPException(status_code=404, detail="Video not found")

    return metadata.laps


@router.get("/{video_name}/laps/{lap_number}")
async def get_lap_data(video_name: str, lap_number: int):
    """
    Get telemetry data for a specific lap.

    Args:
        video_name: Name of the video
        lap_number: Lap number

    Returns:
        CSV data for the lap
    """
    lap_df = storage.get_lap_data(video_name, lap_number)

    if lap_df is None:
        raise HTTPException(status_code=404, detail=f"Lap {lap_number} not found")

    # Clean data for JSON serialization
    return clean_telemetry_for_json(lap_df)


@router.get("/{video_name}/csv")
async def get_telemetry_csv(video_name: str):
    """
    Download the full telemetry CSV file.

    Args:
        video_name: Name of the video

    Returns:
        CSV file download
    """
    csv_path = storage.get_telemetry_csv_path(video_name)

    if not csv_path.exists():
        raise HTTPException(status_code=404, detail="Telemetry data not found")

    return FileResponse(
        path=csv_path,
        media_type="text/csv",
        filename=f"{video_name}_telemetry.csv"
    )


@router.get("/{video_name}/data")
async def get_telemetry_data(
    video_name: str,
    lap_numbers: Optional[str] = None,
    start_frame: Optional[int] = None,
    end_frame: Optional[int] = None
):
    """
    Get telemetry data as JSON with optional filtering.

    Args:
        video_name: Name of the video
        lap_numbers: Comma-separated lap numbers to include (e.g., "1,2,3")
        start_frame: Starting frame number
        end_frame: Ending frame number

    Returns:
        JSON array of telemetry data points
    """
    df = storage.load_telemetry_data(video_name)

    if df is None:
        raise HTTPException(status_code=404, detail="Telemetry data not found")

    # Apply filters
    if lap_numbers:
        lap_list = [int(lap.strip()) for lap in lap_numbers.split(',')]
        df = df[df['lap_number'].isin(lap_list)]

    if start_frame is not None:
        df = df[df['frame'] >= start_frame]

    if end_frame is not None:
        df = df[df['frame'] <= end_frame]

    # Clean data for JSON serialization
    return clean_telemetry_for_json(df)


@router.get("/{video_name}/summary")
async def get_telemetry_summary(video_name: str):
    """
    Get summary statistics for telemetry data.

    Args:
        video_name: Name of the video

    Returns:
        Summary statistics
    """
    df = storage.load_telemetry_data(video_name)

    if df is None:
        raise HTTPException(status_code=404, detail="Telemetry data not found")

    # Generate summary using visualizer
    from ...interactive_visualizer import InteractiveTelemetryVisualizer
    visualizer = InteractiveTelemetryVisualizer()
    summary = visualizer.generate_summary(df)

    return summary


@router.post("/compare", response_model=List[LapComparisonData])
async def compare_laps(request: ComparisonRequest):
    """
    Compare multiple laps across sessions.

    Args:
        request: ComparisonRequest with list of lap identifiers

    Returns:
        List of LapComparisonData with telemetry for each lap

    Raises:
        HTTPException: If fewer than 2 laps provided or laps not found
    """
    if len(request.laps) < 2:
        raise HTTPException(
            status_code=400,
            detail="At least 2 laps required for comparison"
        )

    if len(request.laps) > 10:
        raise HTTPException(
            status_code=400,
            detail="Maximum 10 laps allowed for comparison"
        )

    # Convert Pydantic models to dicts for storage service
    lap_identifiers = [
        {'video_name': lap.video_name, 'lap_number': lap.lap_number}
        for lap in request.laps
    ]

    # Get lap data
    laps_data = storage.get_multiple_laps_data(lap_identifiers)

    if len(laps_data) < 2:
        raise HTTPException(
            status_code=404,
            detail=f"Could not find enough laps. Found {len(laps_data)} of {len(request.laps)} requested laps."
        )

    # Clean and convert to response format
    result = []
    for lap_data in laps_data:
        # Clean telemetry data
        cleaned_data = clean_telemetry_for_json(pd.DataFrame(lap_data['data']))

        result.append(LapComparisonData(
            video_name=lap_data['video_name'],
            lap_number=lap_data['lap_number'],
            lap_time=lap_data['lap_time'],
            data=cleaned_data
        ))

    return result
