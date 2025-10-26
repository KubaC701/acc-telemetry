"""API endpoints for video management."""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import List
from pathlib import Path

from ..models import VideoProcessRequest, VideoMetadata, VideoListItem
from ..services.storage import StorageService
from ..services.processing import VideoProcessingService
from ..services.jobs import job_manager

router = APIRouter()
storage = StorageService()
processing = VideoProcessingService()


@router.get("", response_model=List[VideoListItem])
async def list_videos():
    """
    Get a list of all processed videos.

    Returns:
        List of VideoListItem objects
    """
    videos = storage.list_videos()
    return videos


@router.get("/{video_name}", response_model=VideoMetadata)
async def get_video_metadata(video_name: str):
    """
    Get metadata for a specific video.

    Args:
        video_name: Name of the video

    Returns:
        VideoMetadata object
    """
    metadata = storage.load_metadata(video_name)

    if metadata is None:
        raise HTTPException(status_code=404, detail="Video not found")

    return metadata


@router.post("/process")
async def process_video(request: VideoProcessRequest, background_tasks: BackgroundTasks):
    """
    Start processing a video file.

    Args:
        request: VideoProcessRequest with video_path
        background_tasks: FastAPI background tasks

    Returns:
        Job ID for tracking progress
    """
    video_path = Path(request.video_path)

    # Validate video file exists
    if not video_path.exists():
        raise HTTPException(status_code=404, detail=f"Video file not found: {request.video_path}")

    # Sanitize video name
    video_name = storage.sanitize_filename(video_path.name)

    # Check if already processed
    if storage.video_exists(video_name):
        raise HTTPException(
            status_code=409,
            detail=f"Video '{video_name}' has already been processed. Delete it first to reprocess."
        )

    # Create job
    job_id = job_manager.create_job(video_name)

    # Define progress callback
    def progress_callback(progress: int, message: str):
        job_manager.update_job(
            job_id=job_id,
            status="processing",
            progress=progress,
            message=message
        )

    # Define background task
    async def process_task():
        try:
            job_manager.update_job(job_id, status="processing", progress=0, message="Starting processing...")

            metadata = await processing.process_video(
                video_path=str(video_path),
                video_name=video_name,
                progress_callback=progress_callback
            )

            job_manager.complete_job(job_id, message=f"Video '{video_name}' processed successfully")

        except Exception as e:
            job_manager.fail_job(job_id, error=str(e))

    # Add to background tasks
    background_tasks.add_task(process_task)

    return {
        "job_id": job_id,
        "video_name": video_name,
        "message": "Processing started"
    }


@router.delete("/{video_name}")
async def delete_video(video_name: str):
    """
    Delete all data for a video.

    Args:
        video_name: Name of the video

    Returns:
        Success message
    """
    if not storage.video_exists(video_name):
        raise HTTPException(status_code=404, detail="Video not found")

    success = storage.delete_video(video_name)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete video")

    return {"message": f"Video '{video_name}' deleted successfully"}
