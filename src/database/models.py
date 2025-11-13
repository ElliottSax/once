"""
Database models using SQLAlchemy.

Provides persistent storage for video generation requests, jobs, and users.
"""

from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, DateTime, Text, Boolean, JSON, ForeignKey, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import enum

Base = declarative_base()


class VideoStatusEnum(str, enum.Enum):
    """Video generation status"""
    PENDING = "pending"
    PROCESSING_SCRIPT = "processing_script"
    GENERATING_NARRATION = "generating_narration"
    GENERATING_IMAGES = "generating_images"
    RENDERING_VIDEO = "rendering_video"
    COMPLETED = "completed"
    FAILED = "failed"


class AssetTypeEnum(str, enum.Enum):
    """Asset type classification"""
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    DATA = "data"


class User(Base):
    """User account"""
    __tablename__ = "users"

    id = Column(String(36), primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255))
    api_key = Column(String(64), unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)

    # Limits
    daily_budget_limit = Column(Float, default=50.0)
    monthly_budget_limit = Column(Float, default=500.0)

    # Usage tracking
    total_videos_generated = Column(Integer, default=0)
    total_cost = Column(Float, default=0.0)

    # Relationships
    videos = relationship("Video", back_populates="user", cascade="all, delete-orphan")


class Video(Base):
    """Video generation job"""
    __tablename__ = "videos"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # Request details
    topic = Column(String(500), nullable=False)
    script_text = Column(Text)
    target_duration = Column(Integer, default=300)

    # Configuration
    quality = Column(String(20), default="standard")
    image_provider = Column(String(50), default="dalle3_standard")
    voice_provider = Column(String(50), default="elevenlabs_turbo")
    max_cost = Column(Float, default=12.0)

    # Status
    status = Column(SQLEnum(VideoStatusEnum), default=VideoStatusEnum.PENDING, nullable=False, index=True)
    progress = Column(Float, default=0.0)
    current_step = Column(String(200))

    # Results
    video_path = Column(String(500))
    thumbnail_path = Column(String(500))
    duration_seconds = Column(Float)

    # Costs
    narration_cost = Column(Float, default=0.0)
    image_cost = Column(Float, default=0.0)
    rendering_cost = Column(Float, default=0.0)
    total_cost = Column(Float, default=0.0)

    # Metadata
    script_data = Column(JSON)  # Full VideoScript as JSON
    error_message = Column(Text)
    warnings = Column(JSON)

    # Temporal workflow
    workflow_id = Column(String(100), index=True)
    workflow_run_id = Column(String(100))

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    processing_time_seconds = Column(Float)

    # Relationships
    user = relationship("User", back_populates="videos")
    assets = relationship("Asset", back_populates="video", cascade="all, delete-orphan")
    metrics = relationship("VideoMetrics", back_populates="video", uselist=False, cascade="all, delete-orphan")


class Asset(Base):
    """Generated assets (images, audio files)"""
    __tablename__ = "assets"

    id = Column(String(36), primary_key=True)
    video_id = Column(String(36), ForeignKey("videos.id"), nullable=False, index=True)

    # Asset details
    asset_type = Column(String(50), nullable=False)  # narration, image, thumbnail
    file_path = Column(String(500), nullable=False)
    file_size_bytes = Column(Integer)
    mime_type = Column(String(100))

    # Metadata
    scene_id = Column(String(100))
    provider = Column(String(50))
    generation_time_seconds = Column(Float)
    cost = Column(Float, default=0.0)

    # Cache info
    cache_key = Column(String(64), index=True)
    was_cached = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    video = relationship("Video", back_populates="assets")


class VideoMetrics(Base):
    """Performance metrics for video generation"""
    __tablename__ = "video_metrics"

    id = Column(String(36), primary_key=True)
    video_id = Column(String(36), ForeignKey("videos.id"), nullable=False, unique=True)

    # Timing breakdown
    script_processing_time = Column(Float, default=0.0)
    narration_generation_time = Column(Float, default=0.0)
    image_generation_time = Column(Float, default=0.0)
    video_rendering_time = Column(Float, default=0.0)
    total_time = Column(Float, default=0.0)

    # Asset counts
    scenes_generated = Column(Integer, default=0)
    images_generated = Column(Integer, default=0)
    audio_clips_generated = Column(Integer, default=0)

    # Cache efficiency
    cache_hits = Column(Integer, default=0)
    cache_misses = Column(Integer, default=0)
    cache_hit_rate = Column(Float, default=0.0)

    # Quality metrics
    average_image_quality_score = Column(Float)
    narration_wpm = Column(Float)

    # Cost efficiency
    cost_per_second = Column(Float, default=0.0)
    cost_per_scene = Column(Float, default=0.0)

    # Created
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    video = relationship("Video", back_populates="metrics")


class UsageLog(Base):
    """Daily usage tracking for billing/analytics"""
    __tablename__ = "usage_logs"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    date = Column(DateTime, nullable=False, index=True)

    # Daily totals
    videos_generated = Column(Integer, default=0)
    total_cost = Column(Float, default=0.0)
    total_duration_seconds = Column(Float, default=0.0)

    # Breakdown
    narration_cost = Column(Float, default=0.0)
    image_cost = Column(Float, default=0.0)
    rendering_cost = Column(Float, default=0.0)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ApiKey(Base):
    """API key management"""
    __tablename__ = "api_keys"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    key = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(255))

    # Permissions
    scopes = Column(JSON)  # List of allowed scopes

    # Rate limiting
    rate_limit_per_hour = Column(Integer, default=100)
    rate_limit_per_day = Column(Integer, default=1000)

    # Status
    is_active = Column(Boolean, default=True)
    last_used_at = Column(DateTime)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime)


class ContentCache(Base):
    """Content cache for deduplication and cost savings"""
    __tablename__ = "content_cache"

    id = Column(String(36), primary_key=True)
    content_type = Column(String(50), nullable=False, index=True)  # script_segment, visual_concept, etc.
    content_hash = Column(String(64), nullable=False, index=True)
    content_data = Column(JSON)
    generation_params = Column(JSON)
    asset_ids = Column(JSON)  # Array of asset IDs stored as JSON
    hit_count = Column(Integer, default=0)
    cost_saved = Column(Float, default=0.0)
    last_accessed_at = Column(DateTime, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class VideoAnalytics(Base):
    """Advanced analytics for video quality and performance"""
    __tablename__ = "video_analytics"

    id = Column(String(36), primary_key=True)
    video_id = Column(String(36), ForeignKey("videos.id"), nullable=False, unique=True, index=True)

    # Quality scores
    visual_quality_score = Column(Float)
    audio_quality_score = Column(Float)
    script_coherence_score = Column(Float)
    overall_quality_score = Column(Float, index=True)

    # Cost efficiency
    cost_per_second = Column(Float, index=True)
    cost_vs_average = Column(Float)

    # Provider performance
    image_provider_latency = Column(Float)
    narration_provider_latency = Column(Float)
    image_retry_count = Column(Integer, default=0)
    narration_retry_count = Column(Integer, default=0)

    # User satisfaction
    user_rating = Column(Integer)
    user_feedback = Column(Text)
    regeneration_requested = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class RateLimit(Base):
    """Rate limiting and throttling per user"""
    __tablename__ = "rate_limits"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, unique=True, index=True)
    tier = Column(String(50), default="free")

    # Limits
    videos_per_hour = Column(Integer, default=2)
    videos_per_day = Column(Integer, default=10)
    videos_per_month = Column(Integer, default=50)
    max_concurrent_jobs = Column(Integer, default=1)
    max_video_duration = Column(Integer, default=180)

    # Current usage
    current_hour_count = Column(Integer, default=0)
    current_day_count = Column(Integer, default=0)
    current_month_count = Column(Integer, default=0)
    active_jobs = Column(Integer, default=0)

    # Reset times
    hour_reset_at = Column(DateTime)
    day_reset_at = Column(DateTime)
    month_reset_at = Column(DateTime)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class JobQueue(Base):
    """Priority queue for job management"""
    __tablename__ = "job_queue"

    id = Column(String(36), primary_key=True)
    video_id = Column(String(36), ForeignKey("videos.id"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # Priority and estimation
    priority = Column(Integer, default=5, index=True)
    estimated_cost = Column(Float)
    estimated_duration = Column(Integer)

    # Resource requirements
    requires_gpu = Column(Boolean, default=False)
    requires_premium_provider = Column(Boolean, default=False)

    # Queue management
    status = Column(String(50), default="queued", index=True)
    queued_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    max_wait_time = Column(Integer)
    retry_count = Column(Integer, default=0)

    # Dependencies
    depends_on_job_id = Column(String(36))
