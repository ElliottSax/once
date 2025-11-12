"""
Rate limiting and queue management for fair resource allocation.

Implements tier-based rate limiting, priority queues, and job scheduling
to ensure fair resource allocation and prevent abuse.
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, List
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from loguru import logger

from src.database.models import RateLimit, JobQueue, User


class RateLimitService:
    """Service for managing user rate limits."""

    TIER_LIMITS = {
        'free': {
            'videos_per_hour': 2,
            'videos_per_day': 10,
            'videos_per_month': 50,
            'max_concurrent_jobs': 1,
            'max_video_duration': 180,  # 3 minutes
        },
        'pro': {
            'videos_per_hour': 10,
            'videos_per_day': 100,
            'videos_per_month': 500,
            'max_concurrent_jobs': 3,
            'max_video_duration': 600,  # 10 minutes
        },
        'enterprise': {
            'videos_per_hour': 50,
            'videos_per_day': 500,
            'videos_per_month': 5000,
            'max_concurrent_jobs': 10,
            'max_video_duration': 1800,  # 30 minutes
        }
    }

    def __init__(self, db: Session):
        self.db = db

    def get_or_create_rate_limit(self, user_id: str) -> RateLimit:
        """Get or create rate limit entry for user."""
        rate_limit = self.db.query(RateLimit).filter(
            RateLimit.user_id == user_id
        ).first()

        if not rate_limit:
            # Get user tier
            user = self.db.query(User).filter(User.id == user_id).first()
            tier = 'free'  # Default tier

            limits = self.TIER_LIMITS[tier]

            rate_limit = RateLimit(
                user_id=user_id,
                tier=tier,
                videos_per_hour=limits['videos_per_hour'],
                videos_per_day=limits['videos_per_day'],
                videos_per_month=limits['videos_per_month'],
                max_concurrent_jobs=limits['max_concurrent_jobs'],
                max_video_duration=limits['max_video_duration'],
                current_hour_count=0,
                current_day_count=0,
                current_month_count=0,
                active_jobs=0,
                hour_reset_at=datetime.utcnow() + timedelta(hours=1),
                day_reset_at=datetime.utcnow() + timedelta(days=1),
                month_reset_at=datetime.utcnow() + timedelta(days=30),
                created_at=datetime.utcnow()
            )
            self.db.add(rate_limit)
            self.db.commit()

        # Reset counters if time periods have passed
        self._reset_counters_if_needed(rate_limit)

        return rate_limit

    def _reset_counters_if_needed(self, rate_limit: RateLimit) -> None:
        """Reset counters for expired time periods."""
        now = datetime.utcnow()
        updated = False

        if rate_limit.hour_reset_at <= now:
            rate_limit.current_hour_count = 0
            rate_limit.hour_reset_at = now + timedelta(hours=1)
            updated = True

        if rate_limit.day_reset_at <= now:
            rate_limit.current_day_count = 0
            rate_limit.day_reset_at = now + timedelta(days=1)
            updated = True

        if rate_limit.month_reset_at <= now:
            rate_limit.current_month_count = 0
            rate_limit.month_reset_at = now + timedelta(days=30)
            updated = True

        if updated:
            rate_limit.updated_at = now
            self.db.commit()

    async def check_rate_limit(
        self,
        user_id: str,
        video_duration: Optional[int] = None
    ) -> Dict[str, any]:
        """
        Check if user can generate a video.

        Args:
            user_id: User ID
            video_duration: Requested video duration in seconds

        Returns:
            Dict with 'allowed' boolean and 'reason' if not allowed
        """
        rate_limit = self.get_or_create_rate_limit(user_id)

        # Check concurrent jobs
        if rate_limit.active_jobs >= rate_limit.max_concurrent_jobs:
            return {
                'allowed': False,
                'reason': f'Maximum concurrent jobs reached ({rate_limit.max_concurrent_jobs})',
                'retry_after': 'Wait for a job to complete',
                'current_usage': {
                    'active_jobs': rate_limit.active_jobs,
                    'max_concurrent': rate_limit.max_concurrent_jobs
                }
            }

        # Check hourly limit
        if rate_limit.current_hour_count >= rate_limit.videos_per_hour:
            seconds_until_reset = (rate_limit.hour_reset_at - datetime.utcnow()).total_seconds()
            return {
                'allowed': False,
                'reason': f'Hourly limit reached ({rate_limit.videos_per_hour} videos/hour)',
                'retry_after': f'{int(seconds_until_reset)} seconds',
                'current_usage': {
                    'hour': rate_limit.current_hour_count,
                    'day': rate_limit.current_day_count,
                    'month': rate_limit.current_month_count
                }
            }

        # Check daily limit
        if rate_limit.current_day_count >= rate_limit.videos_per_day:
            seconds_until_reset = (rate_limit.day_reset_at - datetime.utcnow()).total_seconds()
            return {
                'allowed': False,
                'reason': f'Daily limit reached ({rate_limit.videos_per_day} videos/day)',
                'retry_after': f'{int(seconds_until_reset / 3600)} hours',
                'current_usage': {
                    'hour': rate_limit.current_hour_count,
                    'day': rate_limit.current_day_count,
                    'month': rate_limit.current_month_count
                }
            }

        # Check monthly limit
        if rate_limit.current_month_count >= rate_limit.videos_per_month:
            seconds_until_reset = (rate_limit.month_reset_at - datetime.utcnow()).total_seconds()
            return {
                'allowed': False,
                'reason': f'Monthly limit reached ({rate_limit.videos_per_month} videos/month)',
                'retry_after': f'{int(seconds_until_reset / 86400)} days',
                'current_usage': {
                    'hour': rate_limit.current_hour_count,
                    'day': rate_limit.current_day_count,
                    'month': rate_limit.current_month_count
                }
            }

        # Check video duration
        if video_duration and video_duration > rate_limit.max_video_duration:
            return {
                'allowed': False,
                'reason': f'Video duration exceeds limit ({rate_limit.max_video_duration}s for {rate_limit.tier} tier)',
                'max_duration': rate_limit.max_video_duration,
                'requested_duration': video_duration
            }

        # All checks passed
        return {
            'allowed': True,
            'current_usage': {
                'hour': rate_limit.current_hour_count,
                'day': rate_limit.current_day_count,
                'month': rate_limit.current_month_count,
                'active_jobs': rate_limit.active_jobs
            }
        }

    async def increment_usage(self, user_id: str) -> None:
        """Increment usage counters and active jobs."""
        rate_limit = self.get_or_create_rate_limit(user_id)

        rate_limit.current_hour_count += 1
        rate_limit.current_day_count += 1
        rate_limit.current_month_count += 1
        rate_limit.active_jobs += 1
        rate_limit.updated_at = datetime.utcnow()

        self.db.commit()

        logger.info(
            f"Rate limit updated for user {user_id}: "
            f"hour={rate_limit.current_hour_count}/{rate_limit.videos_per_hour}, "
            f"day={rate_limit.current_day_count}/{rate_limit.videos_per_day}, "
            f"active={rate_limit.active_jobs}/{rate_limit.max_concurrent_jobs}"
        )

    async def decrement_active_jobs(self, user_id: str) -> None:
        """Decrement active jobs counter."""
        rate_limit = self.get_or_create_rate_limit(user_id)

        if rate_limit.active_jobs > 0:
            rate_limit.active_jobs -= 1
            rate_limit.updated_at = datetime.utcnow()
            self.db.commit()


class JobQueueService:
    """Service for managing priority job queue."""

    PRIORITY_LEVELS = {
        'critical': 1,
        'high': 3,
        'normal': 5,
        'low': 7,
        'batch': 10
    }

    def __init__(self, db: Session):
        self.db = db

    def get_user_priority(self, user_id: str) -> int:
        """Get priority level for user based on tier."""
        user = self.db.query(User).filter(User.id == user_id).first()

        # Enterprise users get high priority, pro gets normal, free gets low
        # This is a simplified example
        return self.PRIORITY_LEVELS['normal']

    async def enqueue_job(
        self,
        video_id: str,
        user_id: str,
        estimated_cost: float,
        estimated_duration: int,
        priority_override: Optional[int] = None
    ) -> JobQueue:
        """
        Add a job to the queue.

        Args:
            video_id: Video ID
            user_id: User ID
            estimated_cost: Estimated generation cost
            estimated_duration: Estimated duration in seconds
            priority_override: Override default priority

        Returns:
            JobQueue entry
        """
        priority = priority_override or self.get_user_priority(user_id)

        job = JobQueue(
            video_id=video_id,
            user_id=user_id,
            priority=priority,
            estimated_cost=estimated_cost,
            estimated_duration=estimated_duration,
            queued_at=datetime.utcnow(),
            status='queued',
            retry_count=0
        )

        self.db.add(job)
        self.db.commit()

        # Get queue position
        position = self.get_queue_position(job.id)

        logger.info(
            f"Job {job.id} enqueued for video {video_id} "
            f"(priority={priority}, position={position})"
        )

        return job

    def get_queue_position(self, job_id: str) -> int:
        """Get position of job in queue."""
        job = self.db.query(JobQueue).filter(JobQueue.id == job_id).first()
        if not job:
            return -1

        # Count jobs ahead of this one
        count = self.db.query(JobQueue).filter(
            and_(
                JobQueue.status == 'queued',
                JobQueue.started_at.is_(None),
                # Higher priority (lower number) OR same priority but earlier
                (
                    (JobQueue.priority < job.priority) |
                    (
                        (JobQueue.priority == job.priority) &
                        (JobQueue.queued_at < job.queued_at)
                    )
                )
            )
        ).count()

        return count + 1

    async def get_next_job(self, max_cost: Optional[float] = None) -> Optional[JobQueue]:
        """
        Get next job to process from queue.

        Args:
            max_cost: Maximum cost limit for job selection

        Returns:
            Next job to process, or None if queue is empty
        """
        query = self.db.query(JobQueue).filter(
            and_(
                JobQueue.status == 'queued',
                JobQueue.started_at.is_(None)
            )
        )

        if max_cost:
            query = query.filter(JobQueue.estimated_cost <= max_cost)

        # Order by priority (ascending) then queued_at (ascending)
        job = query.order_by(
            JobQueue.priority,
            JobQueue.queued_at
        ).first()

        if job:
            # Mark as started
            job.status = 'processing'
            job.started_at = datetime.utcnow()
            self.db.commit()

            logger.info(f"Dequeued job {job.id} (priority={job.priority})")

        return job

    async def complete_job(self, job_id: str, success: bool = True) -> None:
        """Mark job as completed."""
        job = self.db.query(JobQueue).filter(JobQueue.id == job_id).first()
        if job:
            job.status = 'completed' if success else 'failed'
            job.completed_at = datetime.utcnow()
            self.db.commit()

            logger.info(f"Job {job_id} completed (success={success})")

    async def get_queue_stats(self) -> Dict[str, any]:
        """Get queue statistics."""
        total_queued = self.db.query(JobQueue).filter(
            JobQueue.status == 'queued'
        ).count()

        processing = self.db.query(JobQueue).filter(
            JobQueue.status == 'processing'
        ).count()

        # Average wait time for completed jobs today
        today = datetime.utcnow().date()
        avg_wait = self.db.query(
            func.avg(
                func.extract('epoch', JobQueue.started_at - JobQueue.queued_at)
            )
        ).filter(
            and_(
                JobQueue.started_at.isnot(None),
                func.date(JobQueue.queued_at) == today
            )
        ).scalar() or 0

        # Queue by priority
        by_priority = self.db.query(
            JobQueue.priority,
            func.count(JobQueue.id).label('count')
        ).filter(
            JobQueue.status == 'queued'
        ).group_by(JobQueue.priority).all()

        return {
            'total_queued': total_queued,
            'processing': processing,
            'avg_wait_time_seconds': round(avg_wait, 2),
            'by_priority': [
                {'priority': p, 'count': c}
                for p, c in by_priority
            ]
        }


# Example usage in API:
"""
# In main_db.py

from src.database.rate_limiting import RateLimitService, JobQueueService

@app.post("/api/videos/generate")
async def generate_video(
    request: GenerateVideoRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    # Check rate limits
    rate_limit_service = RateLimitService(db)
    rate_check = await rate_limit_service.check_rate_limit(
        user_id=request.user_id,
        video_duration=request.target_duration
    )

    if not rate_check['allowed']:
        raise HTTPException(
            status_code=429,
            detail=rate_check['reason'],
            headers={'Retry-After': str(rate_check.get('retry_after', '3600'))}
        )

    # Create video job
    video_id = create_video_job(...)

    # Enqueue job
    queue_service = JobQueueService(db)
    job = await queue_service.enqueue_job(
        video_id=video_id,
        user_id=request.user_id,
        estimated_cost=5.0,
        estimated_duration=request.target_duration
    )

    # Increment rate limit
    await rate_limit_service.increment_usage(request.user_id)

    # Get queue position
    position = queue_service.get_queue_position(job.id)

    return {
        'video_id': video_id,
        'status': 'queued',
        'queue_position': position,
        'estimated_wait_time': position * 120  # Rough estimate
    }


# Worker process
async def worker_loop():
    while True:
        queue_service = JobQueueService(db)
        job = await queue_service.get_next_job()

        if job:
            try:
                # Process video
                await process_video(job.video_id)
                await queue_service.complete_job(job.id, success=True)

                # Decrement active jobs for user
                rate_limit_service = RateLimitService(db)
                await rate_limit_service.decrement_active_jobs(job.user_id)

            except Exception as e:
                logger.error(f"Job {job.id} failed: {e}")
                await queue_service.complete_job(job.id, success=False)

        else:
            await asyncio.sleep(5)  # Wait if queue is empty
"""
