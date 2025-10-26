"""Job management service for tracking background tasks."""

import uuid
from typing import Dict, Optional
from datetime import datetime
from ..models import JobStatus


class JobManager:
    """Manages background processing jobs."""

    def __init__(self):
        self._jobs: Dict[str, JobStatus] = {}

    def create_job(self, video_name: str) -> str:
        """
        Create a new job.

        Args:
            video_name: Name of the video being processed

        Returns:
            Job ID
        """
        job_id = str(uuid.uuid4())

        self._jobs[job_id] = JobStatus(
            job_id=job_id,
            status="pending",
            progress=0,
            message="Job created",
            video_name=video_name
        )

        return job_id

    def update_job(
        self,
        job_id: str,
        status: Optional[str] = None,
        progress: Optional[int] = None,
        message: Optional[str] = None,
        error: Optional[str] = None
    ) -> None:
        """
        Update a job's status.

        Args:
            job_id: Job ID
            status: New status
            progress: Progress percentage (0-100)
            message: Status message
            error: Error message if failed
        """
        if job_id not in self._jobs:
            return

        job = self._jobs[job_id]

        if status is not None:
            job.status = status

        if progress is not None:
            job.progress = progress

        if message is not None:
            job.message = message

        if error is not None:
            job.error = error

    def get_job(self, job_id: str) -> Optional[JobStatus]:
        """
        Get a job's status.

        Args:
            job_id: Job ID

        Returns:
            JobStatus or None if not found
        """
        return self._jobs.get(job_id)

    def complete_job(self, job_id: str, message: str = "Processing complete") -> None:
        """
        Mark a job as completed.

        Args:
            job_id: Job ID
            message: Completion message
        """
        self.update_job(job_id, status="completed", progress=100, message=message)

    def fail_job(self, job_id: str, error: str) -> None:
        """
        Mark a job as failed.

        Args:
            job_id: Job ID
            error: Error message
        """
        self.update_job(job_id, status="failed", error=error, message="Processing failed")

    def delete_job(self, job_id: str) -> None:
        """
        Delete a job from tracking.

        Args:
            job_id: Job ID
        """
        if job_id in self._jobs:
            del self._jobs[job_id]

    def list_jobs(self) -> list[JobStatus]:
        """
        Get all jobs.

        Returns:
            List of all JobStatus objects
        """
        return list(self._jobs.values())


# Global job manager instance
job_manager = JobManager()
