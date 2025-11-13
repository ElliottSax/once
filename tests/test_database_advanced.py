"""
Comprehensive tests for database models and services.

Tests cover:
- Content caching and deduplication
- Rate limiting and throttling
- Job queue management
- Database models
"""

import pytest
import uuid
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.database.models import (
    Base, User, Video, VideoStatusEnum, ContentCache,
    RateLimit, JobQueue, VideoAnalytics
)
from src.database.caching import ContentCacheService, ScriptCacheService, ImagePromptCacheService
from src.database.rate_limiting import RateLimitService, JobQueueService


# Test database setup
@pytest.fixture(scope="function")
def db_session():
    """Create a test database session"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    yield session

    session.close()


@pytest.fixture
def test_user(db_session):
    """Create a test user"""
    user = User(
        id=str(uuid.uuid4()),
        email="test@example.com",
        api_key="test_key_" + str(uuid.uuid4()),
        daily_budget_limit=50.0,
        monthly_budget_limit=500.0
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def test_video(db_session, test_user):
    """Create a test video"""
    video = Video(
        id=str(uuid.uuid4()),
        user_id=test_user.id,
        topic="Test video about AI",
        status=VideoStatusEnum.PENDING,
        target_duration=300,
        max_cost=12.0
    )
    db_session.add(video)
    db_session.commit()
    return video


# =====================
# Content Cache Tests
# =====================

class TestContentCacheService:
    """Test content caching functionality"""

    @pytest.mark.asyncio
    async def test_cache_miss(self, db_session):
        """Test cache miss returns None"""
        cache_service = ContentCacheService(db_session)

        result = await cache_service.check_cache(
            content_type='script_segment',
            content='Tell me about artificial intelligence',
            params={'model': 'gpt-4', 'temperature': 0.7}
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_cache_hit(self, db_session):
        """Test cache hit returns cached data"""
        cache_service = ContentCacheService(db_session)

        # Store content
        test_data = {'script': 'AI is amazing...', 'metadata': {}}
        cache_id = await cache_service.store_cache(
            content_type='script_segment',
            content='Tell me about artificial intelligence',
            content_data=test_data,
            params={'model': 'gpt-4', 'temperature': 0.7},
            generation_cost=0.05
        )

        assert cache_id is not None

        # Retrieve content
        result = await cache_service.check_cache(
            content_type='script_segment',
            content='Tell me about artificial intelligence',
            params={'model': 'gpt-4', 'temperature': 0.7}
        )

        assert result is not None
        assert result['content_data']['script'] == 'AI is amazing...'
        assert result['hit_count'] == 1

    @pytest.mark.asyncio
    async def test_cache_normalization(self, db_session):
        """Test content normalization improves hit rate"""
        cache_service = ContentCacheService(db_session)

        # Store with one format
        await cache_service.store_cache(
            content_type='script_segment',
            content='Tell   me about   AI!',
            content_data={'script': 'Test'},
            generation_cost=0.05
        )

        # Retrieve with different formatting
        result = await cache_service.check_cache(
            content_type='script_segment',
            content='tell me about ai?',  # Different case and punctuation
        )

        assert result is not None  # Should hit due to normalization

    @pytest.mark.asyncio
    async def test_cache_hit_tracking(self, db_session):
        """Test hit count increments correctly"""
        cache_service = ContentCacheService(db_session)

        # Store content
        await cache_service.store_cache(
            content_type='visual_concept',
            content='A modern office',
            content_data={'image_url': 'http://example.com/image.png'},
            generation_cost=0.50
        )

        # Hit cache multiple times
        for _ in range(5):
            result = await cache_service.check_cache(
                content_type='visual_concept',
                content='A modern office'
            )
            assert result is not None

        # Check final hit count
        result = await cache_service.check_cache(
            content_type='visual_concept',
            content='A modern office'
        )
        assert result['hit_count'] == 6  # 5 + 1

    @pytest.mark.asyncio
    async def test_cache_stats(self, db_session):
        """Test cache statistics calculation"""
        cache_service = ContentCacheService(db_session)

        # Add some cache entries
        await cache_service.store_cache(
            content_type='script_segment',
            content='Test 1',
            content_data={'data': 'test'},
            generation_cost=0.05
        )

        await cache_service.store_cache(
            content_type='visual_concept',
            content='Test 2',
            content_data={'data': 'test'},
            generation_cost=0.50
        )

        # Hit one of them
        await cache_service.check_cache('script_segment', 'Test 1')

        # Get stats
        stats = await cache_service.get_cache_stats(days=30)

        assert stats['total_entries'] == 2
        assert stats['total_hits'] == 1
        assert stats['total_cost_saved'] > 0


class TestScriptCacheService:
    """Test script-specific caching"""

    @pytest.mark.asyncio
    async def test_script_cache(self, db_session):
        """Test script caching"""
        cache_service = ContentCacheService(db_session)
        script_cache = ScriptCacheService(cache_service)

        # Cache a script
        await script_cache.cache_script_segment(
            prompt='Explain quantum computing',
            generated_script='Quantum computing uses qubits...',
            metadata={'model': 'gpt-4', 'cost': 0.03}
        )

        # Retrieve script
        cached_script = await script_cache.get_cached_script(
            prompt='Explain quantum computing',
            model='gpt-4'
        )

        assert cached_script == 'Quantum computing uses qubits...'


class TestImagePromptCacheService:
    """Test image prompt caching"""

    @pytest.mark.asyncio
    async def test_image_cache(self, db_session):
        """Test image prompt caching"""
        cache_service = ContentCacheService(db_session)
        image_cache = ImagePromptCacheService(cache_service)

        # Cache an image
        await image_cache.cache_image_prompt(
            prompt='A futuristic cityscape',
            image_url='http://example.com/city.png',
            asset_id='asset_123',
            provider='dalle3',
            cost=0.50
        )

        # Retrieve image
        cached_image = await image_cache.get_cached_image(
            prompt='A futuristic cityscape',
            provider='dalle3'
        )

        assert cached_image is not None
        assert cached_image['image_url'] == 'http://example.com/city.png'
        assert cached_image['asset_id'] == 'asset_123'
        assert cached_image['cache_hit'] is True


# =====================
# Rate Limiting Tests
# =====================

class TestRateLimitService:
    """Test rate limiting functionality"""

    @pytest.mark.asyncio
    async def test_create_default_rate_limit(self, db_session, test_user):
        """Test default rate limit creation"""
        rate_limit_service = RateLimitService(db_session)
        rate_limit = rate_limit_service.get_or_create_rate_limit(test_user.id)

        assert rate_limit.user_id == test_user.id
        assert rate_limit.tier == 'free'
        assert rate_limit.videos_per_hour == 2
        assert rate_limit.videos_per_day == 10
        assert rate_limit.current_hour_count == 0

    @pytest.mark.asyncio
    async def test_rate_limit_check_allowed(self, db_session, test_user):
        """Test rate limit check when under limits"""
        rate_limit_service = RateLimitService(db_session)

        result = await rate_limit_service.check_rate_limit(
            user_id=test_user.id,
            video_duration=120
        )

        assert result['allowed'] is True
        assert 'current_usage' in result

    @pytest.mark.asyncio
    async def test_rate_limit_hourly_exceeded(self, db_session, test_user):
        """Test rate limit when hourly limit exceeded"""
        rate_limit_service = RateLimitService(db_session)

        # Set up rate limit at max
        rate_limit = rate_limit_service.get_or_create_rate_limit(test_user.id)
        rate_limit.current_hour_count = rate_limit.videos_per_hour
        db_session.commit()

        result = await rate_limit_service.check_rate_limit(test_user.id)

        assert result['allowed'] is False
        assert 'Hourly limit' in result['reason']
        assert 'retry_after' in result

    @pytest.mark.asyncio
    async def test_rate_limit_increment(self, db_session, test_user):
        """Test usage increment"""
        rate_limit_service = RateLimitService(db_session)

        # Initial state
        rate_limit = rate_limit_service.get_or_create_rate_limit(test_user.id)
        initial_hour = rate_limit.current_hour_count
        initial_day = rate_limit.current_day_count
        initial_month = rate_limit.current_month_count

        # Increment
        await rate_limit_service.increment_usage(test_user.id)

        # Check increments
        rate_limit = rate_limit_service.get_or_create_rate_limit(test_user.id)
        assert rate_limit.current_hour_count == initial_hour + 1
        assert rate_limit.current_day_count == initial_day + 1
        assert rate_limit.current_month_count == initial_month + 1
        assert rate_limit.active_jobs == 1

    @pytest.mark.asyncio
    async def test_rate_limit_decrement_active_jobs(self, db_session, test_user):
        """Test decrementing active jobs"""
        rate_limit_service = RateLimitService(db_session)

        # Increment first
        await rate_limit_service.increment_usage(test_user.id)

        rate_limit = rate_limit_service.get_or_create_rate_limit(test_user.id)
        assert rate_limit.active_jobs == 1

        # Decrement
        await rate_limit_service.decrement_active_jobs(test_user.id)

        rate_limit = rate_limit_service.get_or_create_rate_limit(test_user.id)
        assert rate_limit.active_jobs == 0

    @pytest.mark.asyncio
    async def test_rate_limit_concurrent_jobs_exceeded(self, db_session, test_user):
        """Test concurrent job limit"""
        rate_limit_service = RateLimitService(db_session)

        # Set active jobs to max
        rate_limit = rate_limit_service.get_or_create_rate_limit(test_user.id)
        rate_limit.active_jobs = rate_limit.max_concurrent_jobs
        db_session.commit()

        result = await rate_limit_service.check_rate_limit(test_user.id)

        assert result['allowed'] is False
        assert 'concurrent' in result['reason'].lower()

    @pytest.mark.asyncio
    async def test_rate_limit_video_duration_exceeded(self, db_session, test_user):
        """Test video duration limit"""
        rate_limit_service = RateLimitService(db_session)

        result = await rate_limit_service.check_rate_limit(
            user_id=test_user.id,
            video_duration=300  # Exceeds free tier 180s limit
        )

        assert result['allowed'] is False
        assert 'duration' in result['reason'].lower()


# =====================
# Job Queue Tests
# =====================

class TestJobQueueService:
    """Test job queue functionality"""

    @pytest.mark.asyncio
    async def test_enqueue_job(self, db_session, test_user, test_video):
        """Test enqueueing a job"""
        queue_service = JobQueueService(db_session)

        job = await queue_service.enqueue_job(
            video_id=test_video.id,
            user_id=test_user.id,
            estimated_cost=5.0,
            estimated_duration=300
        )

        assert job.id is not None
        assert job.video_id == test_video.id
        assert job.status == 'queued'
        assert job.priority == 5  # Default normal priority

    @pytest.mark.asyncio
    async def test_queue_position(self, db_session, test_user):
        """Test queue position calculation"""
        queue_service = JobQueueService(db_session)

        # Create videos for jobs
        video_ids = []
        for i in range(3):
            video = Video(
                id=str(uuid.uuid4()),
                user_id=test_user.id,
                topic=f"Test video {i}",
                status=VideoStatusEnum.PENDING
            )
            db_session.add(video)
            db_session.commit()
            video_ids.append(video.id)

        # Enqueue jobs with different priorities
        job1 = await queue_service.enqueue_job(
            video_id=video_ids[0],
            user_id=test_user.id,
            estimated_cost=5.0,
            estimated_duration=300,
            priority_override=5  # Normal
        )

        job2 = await queue_service.enqueue_job(
            video_id=video_ids[1],
            user_id=test_user.id,
            estimated_cost=5.0,
            estimated_duration=300,
            priority_override=1  # High
        )

        job3 = await queue_service.enqueue_job(
            video_id=video_ids[2],
            user_id=test_user.id,
            estimated_cost=5.0,
            estimated_duration=300,
            priority_override=10  # Low
        )

        # Check positions
        pos1 = queue_service.get_queue_position(job1.id)
        pos2 = queue_service.get_queue_position(job2.id)
        pos3 = queue_service.get_queue_position(job3.id)

        assert pos2 == 1  # High priority first
        assert pos1 == 2  # Normal priority second
        assert pos3 == 3  # Low priority last

    @pytest.mark.asyncio
    async def test_get_next_job(self, db_session, test_user):
        """Test getting next job from queue"""
        queue_service = JobQueueService(db_session)

        # Create and enqueue multiple jobs
        video_ids = []
        for i in range(3):
            video = Video(
                id=str(uuid.uuid4()),
                user_id=test_user.id,
                topic=f"Test video {i}",
                status=VideoStatusEnum.PENDING
            )
            db_session.add(video)
            db_session.commit()
            video_ids.append(video.id)

        # Enqueue with different priorities
        await queue_service.enqueue_job(video_ids[0], test_user.id, 5.0, 300, priority_override=10)
        await queue_service.enqueue_job(video_ids[1], test_user.id, 5.0, 300, priority_override=1)
        await queue_service.enqueue_job(video_ids[2], test_user.id, 5.0, 300, priority_override=5)

        # Get next job
        next_job = await queue_service.get_next_job()

        assert next_job is not None
        assert next_job.priority == 1  # Should get highest priority
        assert next_job.status == 'processing'
        assert next_job.started_at is not None

    @pytest.mark.asyncio
    async def test_complete_job(self, db_session, test_user, test_video):
        """Test completing a job"""
        queue_service = JobQueueService(db_session)

        # Enqueue job
        job = await queue_service.enqueue_job(
            video_id=test_video.id,
            user_id=test_user.id,
            estimated_cost=5.0,
            estimated_duration=300
        )

        # Mark as started
        await queue_service.get_next_job()

        # Complete job
        await queue_service.complete_job(job.id, success=True)

        # Check status
        completed_job = db_session.query(JobQueue).filter(JobQueue.id == job.id).first()
        assert completed_job.status == 'completed'
        assert completed_job.completed_at is not None

    @pytest.mark.asyncio
    async def test_queue_stats(self, db_session, test_user):
        """Test queue statistics"""
        queue_service = JobQueueService(db_session)

        # Create videos and enqueue jobs
        for i in range(5):
            video = Video(
                id=str(uuid.uuid4()),
                user_id=test_user.id,
                topic=f"Test video {i}",
                status=VideoStatusEnum.PENDING
            )
            db_session.add(video)
            db_session.commit()

            await queue_service.enqueue_job(
                video_id=video.id,
                user_id=test_user.id,
                estimated_cost=5.0,
                estimated_duration=300
            )

        # Get stats
        stats = await queue_service.get_queue_stats()

        assert stats['total_queued'] == 5
        assert stats['processing'] == 0
        assert len(stats['by_priority']) > 0


# =====================
# Model Tests
# =====================

class TestDatabaseModels:
    """Test database model creation and relationships"""

    def test_user_creation(self, db_session):
        """Test creating a user"""
        user = User(
            id=str(uuid.uuid4()),
            email="newuser@example.com",
            api_key="api_key_123"
        )
        db_session.add(user)
        db_session.commit()

        retrieved = db_session.query(User).filter(User.email == "newuser@example.com").first()
        assert retrieved is not None
        assert retrieved.email == "newuser@example.com"

    def test_video_user_relationship(self, db_session, test_user):
        """Test video-user relationship"""
        video = Video(
            id=str(uuid.uuid4()),
            user_id=test_user.id,
            topic="Test relationship",
            status=VideoStatusEnum.PENDING
        )
        db_session.add(video)
        db_session.commit()

        # Check relationship
        assert video.user.email == test_user.email
        assert len(test_user.videos) > 0

    def test_content_cache_creation(self, db_session):
        """Test creating content cache entry"""
        cache = ContentCache(
            id=str(uuid.uuid4()),
            content_type='script_segment',
            content_hash='abc123',
            content_data={'test': 'data'},
            hit_count=0
        )
        db_session.add(cache)
        db_session.commit()

        retrieved = db_session.query(ContentCache).filter(
            ContentCache.content_hash == 'abc123'
        ).first()
        assert retrieved is not None

    def test_rate_limit_creation(self, db_session, test_user):
        """Test creating rate limit entry"""
        rate_limit = RateLimit(
            id=str(uuid.uuid4()),
            user_id=test_user.id,
            tier='pro',
            videos_per_hour=10
        )
        db_session.add(rate_limit)
        db_session.commit()

        retrieved = db_session.query(RateLimit).filter(
            RateLimit.user_id == test_user.id
        ).first()
        assert retrieved is not None
        assert retrieved.tier == 'pro'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
