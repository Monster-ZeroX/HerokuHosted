"""
Job queue system for managing concurrent downloads.
"""
import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Callable
from uuid import uuid4

logger = logging.getLogger(__name__)


class JobStatus(Enum):
    """Job status enumeration."""
    QUEUED = "queued"
    DOWNLOADING = "downloading"
    UPLOADING = "uploading"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Job:
    """Represents a download job."""
    job_id: str
    user_id: int
    chat_id: int
    torrent_hash: str
    torrent_name: str
    selected_files: Optional[List[int]]
    status: JobStatus = JobStatus.QUEUED
    progress: float = 0.0
    download_speed: float = 0.0
    upload_speed: float = 0.0
    eta: int = -1
    error_message: Optional[str] = None
    gdrive_link: Optional[str] = None
    index_link: Optional[str] = None
    local_path: Optional[str] = None
    remote_path: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class JobQueue:
    """Manages job queue with concurrent execution."""

    def __init__(self, max_concurrent: int = 3):
        self.max_concurrent = max_concurrent
        self.jobs: Dict[str, Job] = {}
        self.active_jobs: List[str] = []
        self.queue: asyncio.Queue = asyncio.Queue()
        self._processing_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()

    async def start(self):
        """Start processing jobs from queue."""
        if self._processing_task is None or self._processing_task.done():
            self._processing_task = asyncio.create_task(self._process_queue())
            logger.info("Job queue processor started")

    async def stop(self):
        """Stop processing jobs."""
        if self._processing_task:
            self._processing_task.cancel()
            try:
                await self._processing_task
            except asyncio.CancelledError:
                pass
            logger.info("Job queue processor stopped")

    async def add_job(
        self,
        user_id: int,
        chat_id: int,
        torrent_hash: str,
        torrent_name: str,
        selected_files: Optional[List[int]] = None
    ) -> Job:
        """
        Add a new job to the queue.

        Args:
            user_id: Telegram user ID
            chat_id: Telegram chat ID
            torrent_hash: Torrent info hash
            torrent_name: Torrent name
            selected_files: List of selected file indices

        Returns:
            Created job
        """
        job_id = str(uuid4())
        job = Job(
            job_id=job_id,
            user_id=user_id,
            chat_id=chat_id,
            torrent_hash=torrent_hash,
            torrent_name=torrent_name,
            selected_files=selected_files
        )

        async with self._lock:
            self.jobs[job_id] = job
            await self.queue.put(job_id)

        logger.info(f"Job {job_id} added to queue (user: {user_id}, torrent: {torrent_name})")
        return job

    async def _process_queue(self):
        """Process jobs from the queue."""
        while True:
            try:
                # Wait for a job
                job_id = await self.queue.get()

                # Wait until we have capacity
                while len(self.active_jobs) >= self.max_concurrent:
                    await asyncio.sleep(1)

                # Start processing
                async with self._lock:
                    if job_id in self.jobs:
                        self.active_jobs.append(job_id)

                # Process in background
                asyncio.create_task(self._execute_job(job_id))

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in queue processor: {e}")

    async def _execute_job(self, job_id: str):
        """
        Execute a job (placeholder - actual execution handled by bot).

        Args:
            job_id: Job ID
        """
        try:
            async with self._lock:
                if job_id in self.jobs:
                    job = self.jobs[job_id]
                    job.status = JobStatus.DOWNLOADING
                    job.started_at = datetime.now()

            # Job execution is handled by the bot's job handler
            # This just maintains the active jobs list

        except Exception as e:
            logger.error(f"Error executing job {job_id}: {e}")
            async with self._lock:
                if job_id in self.jobs:
                    self.jobs[job_id].status = JobStatus.FAILED
                    self.jobs[job_id].error_message = str(e)
        finally:
            async with self._lock:
                if job_id in self.active_jobs:
                    self.active_jobs.remove(job_id)

    async def get_job(self, job_id: str) -> Optional[Job]:
        """Get job by ID."""
        async with self._lock:
            return self.jobs.get(job_id)

    async def update_job(self, job_id: str, **kwargs):
        """Update job fields."""
        async with self._lock:
            if job_id in self.jobs:
                job = self.jobs[job_id]
                for key, value in kwargs.items():
                    if hasattr(job, key):
                        setattr(job, key, value)

    async def complete_job(self, job_id: str, gdrive_link: str = None, index_link: str = None):
        """Mark job as completed."""
        async with self._lock:
            if job_id in self.jobs:
                job = self.jobs[job_id]
                job.status = JobStatus.COMPLETED
                job.completed_at = datetime.now()
                job.gdrive_link = gdrive_link
                job.index_link = index_link
                job.progress = 100.0

                if job_id in self.active_jobs:
                    self.active_jobs.remove(job_id)

                logger.info(f"Job {job_id} completed")

    async def fail_job(self, job_id: str, error_message: str):
        """Mark job as failed."""
        async with self._lock:
            if job_id in self.jobs:
                job = self.jobs[job_id]
                job.status = JobStatus.FAILED
                job.error_message = error_message
                job.completed_at = datetime.now()

                if job_id in self.active_jobs:
                    self.active_jobs.remove(job_id)

                logger.error(f"Job {job_id} failed: {error_message}")

    async def cancel_job(self, job_id: str):
        """Cancel a job."""
        async with self._lock:
            if job_id in self.jobs:
                job = self.jobs[job_id]
                job.status = JobStatus.CANCELLED
                job.completed_at = datetime.now()

                if job_id in self.active_jobs:
                    self.active_jobs.remove(job_id)

                logger.info(f"Job {job_id} cancelled")

    async def get_user_jobs(self, user_id: int) -> List[Job]:
        """Get all jobs for a user."""
        async with self._lock:
            return [job for job in self.jobs.values() if job.user_id == user_id]

    async def get_active_jobs(self) -> List[Job]:
        """Get all active jobs."""
        async with self._lock:
            return [self.jobs[job_id] for job_id in self.active_jobs if job_id in self.jobs]

    async def cleanup_old_jobs(self, max_age_hours: int = 24):
        """Clean up old completed/failed jobs."""
        async with self._lock:
            now = datetime.now()
            to_remove = []

            for job_id, job in self.jobs.items():
                if job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
                    if job.completed_at:
                        age = (now - job.completed_at).total_seconds() / 3600
                        if age > max_age_hours:
                            to_remove.append(job_id)

            for job_id in to_remove:
                del self.jobs[job_id]

            if to_remove:
                logger.info(f"Cleaned up {len(to_remove)} old jobs")
