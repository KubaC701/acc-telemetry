"""API endpoints for job status tracking."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse
import asyncio
import json

from ..models import JobStatus
from ..services.jobs import job_manager

router = APIRouter()


@router.get("", response_model=list[JobStatus])
async def list_jobs():
    """
    Get all jobs.

    Returns:
        List of all jobs
    """
    return job_manager.list_jobs()


@router.get("/{job_id}/status", response_model=JobStatus)
async def get_job_status(job_id: str):
    """
    Get the status of a processing job.

    Args:
        job_id: Job ID

    Returns:
        JobStatus object
    """
    job = job_manager.get_job(job_id)

    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    return job


@router.get("/{job_id}/progress")
async def get_job_progress_stream(job_id: str):
    """
    Stream job progress updates using Server-Sent Events.

    Args:
        job_id: Job ID

    Returns:
        EventSourceResponse streaming job updates
    """
    async def event_generator():
        """Generate SSE events for job progress."""
        while True:
            job = job_manager.get_job(job_id)

            if job is None:
                yield {
                    "event": "error",
                    "data": json.dumps({"error": "Job not found"})
                }
                break

            # Send current job status
            yield {
                "event": "progress",
                "data": json.dumps(job.model_dump())
            }

            # If job is completed or failed, end the stream
            if job.status in ["completed", "failed"]:
                yield {
                    "event": "done",
                    "data": json.dumps(job.model_dump())
                }
                break

            # Wait before next update
            await asyncio.sleep(1)

    return EventSourceResponse(event_generator())


@router.delete("/{job_id}")
async def delete_job(job_id: str):
    """
    Delete a job from tracking.

    Args:
        job_id: Job ID

    Returns:
        Success message
    """
    job = job_manager.get_job(job_id)

    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    job_manager.delete_job(job_id)

    return {"message": "Job deleted successfully"}
