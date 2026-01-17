"""
Background tasks and async job queue for VoltWay.

Handles:
- Scheduled cache refresh
- Periodic data synchronization
- Email notifications
- Analytics aggregation
- Cleanup operations
"""

import asyncio
import logging
from typing import Callable, List, Optional, Dict, Any
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
import uuid

logger = logging.getLogger(__name__)


class JobStatus(str, Enum):
    """Job execution status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Job:
    """Represents a background job."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    status: JobStatus = JobStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    result: Optional[Any] = None
    retry_count: int = 0
    max_retries: int = 3

    @property
    def duration(self) -> Optional[timedelta]:
        """Get job execution duration."""
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        return None

    @property
    def is_running(self) -> bool:
        """Check if job is running."""
        return self.status == JobStatus.RUNNING

    @property
    def is_completed(self) -> bool:
        """Check if job is completed."""
        return self.status in (JobStatus.COMPLETED, JobStatus.FAILED)


class JobQueue:
    """Simple in-memory job queue for background tasks."""

    def __init__(self, max_workers: int = 5):
        """
        Initialize job queue.

        Args:
            max_workers: Maximum concurrent workers
        """
        self.max_workers = max_workers
        self.jobs: Dict[str, Job] = {}
        self.queue: asyncio.Queue = asyncio.Queue()
        self.active_workers = 0
        self.workers: List[asyncio.Task] = []

    async def submit(
        self,
        func: Callable,
        name: str = "",
        *args,
        **kwargs,
    ) -> str:
        """
        Submit job to queue.

        Args:
            func: Async function to execute
            name: Job name for identification
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Job ID
        """
        job = Job(name=name or func.__name__)
        self.jobs[job.id] = job
        await self.queue.put((job, func, args, kwargs))
        logger.info(f"Job {job.id} ({name}) submitted")
        return job.id

    async def start(self) -> None:
        """Start queue worker tasks."""
        for _ in range(self.max_workers):
            worker = asyncio.create_task(self._worker())
            self.workers.append(worker)
        logger.info(f"Job queue started with {self.max_workers} workers")

    async def stop(self) -> None:
        """Stop all workers."""
        for worker in self.workers:
            if not worker.done():
                worker.cancel()
        await asyncio.gather(*self.workers, return_exceptions=True)
        logger.info("Job queue stopped")

    async def _worker(self) -> None:
        """Worker task for processing jobs."""
        try:
            while True:
                job, func, args, kwargs = await self.queue.get()
                await self._execute_job(job, func, args, kwargs)
                self.queue.task_done()
        except asyncio.CancelledError:
            pass

    async def _execute_job(
        self,
        job: Job,
        func: Callable,
        args: tuple,
        kwargs: dict,
    ) -> None:
        """Execute a single job with retry logic."""
        job.status = JobStatus.RUNNING
        job.started_at = datetime.utcnow()

        try:
            logger.info(f"Job {job.id} started")
            if asyncio.iscoroutinefunction(func):
                job.result = await func(*args, **kwargs)
            else:
                job.result = func(*args, **kwargs)

            job.status = JobStatus.COMPLETED
            job.completed_at = datetime.utcnow()
            logger.info(
                f"Job {job.id} completed in {job.duration.total_seconds():.2f}s"
            )

        except Exception as e:
            logger.error(f"Job {job.id} failed: {str(e)}")
            job.retry_count += 1

            if job.retry_count < job.max_retries:
                job.status = JobStatus.PENDING
                job.started_at = None
                job.completed_at = None
                logger.info(f"Job {job.id} queued for retry {job.retry_count}")
                await self.queue.put((job, func, args, kwargs))
            else:
                job.status = JobStatus.FAILED
                job.error = str(e)
                job.completed_at = datetime.utcnow()
                logger.error(f"Job {job.id} failed after {job.max_retries} retries")

    def get_job(self, job_id: str) -> Optional[Job]:
        """Get job by ID."""
        return self.jobs.get(job_id)

    def get_jobs(self, status: Optional[JobStatus] = None) -> List[Job]:
        """Get jobs by status."""
        if status:
            return [j for j in self.jobs.values() if j.status == status]
        return list(self.jobs.values())

    def get_stats(self) -> Dict[str, Any]:
        """Get queue statistics."""
        completed = len([j for j in self.jobs.values() if j.status == JobStatus.COMPLETED])
        failed = len([j for j in self.jobs.values() if j.status == JobStatus.FAILED])
        pending = len([j for j in self.jobs.values() if j.status == JobStatus.PENDING])
        running = len([j for j in self.jobs.values() if j.status == JobStatus.RUNNING])

        return {
            "total_jobs": len(self.jobs),
            "completed": completed,
            "failed": failed,
            "pending": pending,
            "running": running,
            "active_workers": self.active_workers,
            "queue_size": self.queue.qsize(),
        }


class ScheduledTask:
    """Represents a scheduled recurring task."""

    def __init__(
        self,
        func: Callable,
        interval_seconds: int,
        name: str = "",
    ):
        """
        Initialize scheduled task.

        Args:
            func: Async function to execute
            interval_seconds: Interval between executions
            name: Task name
        """
        self.func = func
        self.interval_seconds = interval_seconds
        self.name = name or func.__name__
        self.task: Optional[asyncio.Task] = None
        self.last_execution: Optional[datetime] = None
        self.execution_count = 0
        self.errors_count = 0

    async def start(self) -> None:
        """Start scheduled task."""
        self.task = asyncio.create_task(self._run())
        logger.info(f"Scheduled task '{self.name}' started")

    async def stop(self) -> None:
        """Stop scheduled task."""
        if self.task and not self.task.done():
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        logger.info(f"Scheduled task '{self.name}' stopped")

    async def _run(self) -> None:
        """Run scheduled task loop."""
        try:
            while True:
                try:
                    logger.debug(f"Executing scheduled task '{self.name}'")
                    await self.func()
                    self.execution_count += 1
                    self.last_execution = datetime.utcnow()
                except Exception as e:
                    self.errors_count += 1
                    logger.error(f"Error in scheduled task '{self.name}': {str(e)}")

                await asyncio.sleep(self.interval_seconds)
        except asyncio.CancelledError:
            pass

    def get_info(self) -> Dict[str, Any]:
        """Get task information."""
        return {
            "name": self.name,
            "interval_seconds": self.interval_seconds,
            "execution_count": self.execution_count,
            "errors_count": self.errors_count,
            "last_execution": self.last_execution,
            "is_running": self.task and not self.task.done(),
        }


class TaskScheduler:
    """Manages multiple scheduled tasks."""

    def __init__(self):
        """Initialize task scheduler."""
        self.tasks: Dict[str, ScheduledTask] = {}

    def add_task(
        self,
        func: Callable,
        interval_seconds: int,
        name: str = "",
    ) -> str:
        """
        Add scheduled task.

        Args:
            func: Async function to execute
            interval_seconds: Interval in seconds
            name: Task name

        Returns:
            Task ID
        """
        task_name = name or func.__name__
        task = ScheduledTask(func, interval_seconds, task_name)
        self.tasks[task_name] = task
        return task_name

    async def start(self) -> None:
        """Start all scheduled tasks."""
        for task in self.tasks.values():
            await task.start()
        logger.info(f"Task scheduler started with {len(self.tasks)} tasks")

    async def stop(self) -> None:
        """Stop all scheduled tasks."""
        for task in self.tasks.values():
            await task.stop()
        logger.info("Task scheduler stopped")

    def get_task_stats(self) -> Dict[str, Any]:
        """Get statistics for all tasks."""
        return {task_name: task.get_info() for task_name, task in self.tasks.items()}


# Common background tasks

async def refresh_cache() -> None:
    """Refresh application cache."""
    logger.info("Refreshing cache...")
    # Implementation: Clear old cache entries, reload frequently used data


async def sync_external_data() -> None:
    """Sync with external APIs."""
    logger.info("Syncing external data...")
    # Implementation: Update station data from external sources


async def cleanup_old_jobs() -> None:
    """Clean up old completed jobs."""
    logger.info("Cleaning up old jobs...")
    # Implementation: Remove jobs older than 7 days


async def aggregate_analytics() -> None:
    """Aggregate usage analytics."""
    logger.info("Aggregating analytics...")
    # Implementation: Generate daily/weekly reports


async def send_pending_notifications() -> None:
    """Send pending notifications."""
    logger.info("Sending pending notifications...")
    # Implementation: Send batched notifications to users


__all__ = [
    "Job",
    "JobStatus",
    "JobQueue",
    "ScheduledTask",
    "TaskScheduler",
    "refresh_cache",
    "sync_external_data",
    "cleanup_old_jobs",
    "aggregate_analytics",
    "send_pending_notifications",
]
