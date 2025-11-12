"""
Data models for video generation requests and responses.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from pathlib import Path


class VideoQuality(str, Enum):
    """Video quality presets"""
    DRAFT = "draft"  # 720p, faster rendering
    STANDARD = "standard"  # 1080p, standard quality
    PREMIUM = "premium"  # 1080p, high quality, slower rendering


class ImageProvider(str, Enum):
    """Image generation providers"""
    DALLE3_STANDARD = "dalle3_standard"  # DALL-E 3 standard quality
    DALLE3_HD = "dalle3_hd"  # DALL-E 3 HD quality
    SDXL_FAST = "sdxl_fast"  # SDXL fast generation
    SDXL_QUALITY = "sdxl_quality"  # SDXL high quality


class VoiceProvider(str, Enum):
    """Voice synthesis providers"""
    ELEVENLABS_TURBO = "elevenlabs_turbo"  # Fast, cost-effective
    ELEVENLABS_STANDARD = "elevenlabs_standard"  # Standard quality
    ELEVENLABS_PREMIUM = "elevenlabs_premium"  # Premium voices


class VideoStatus(str, Enum):
    """Video generation status"""
    PENDING = "pending"
    PROCESSING_SCRIPT = "processing_script"
    GENERATING_NARRATION = "generating_narration"
    GENERATING_IMAGES = "generating_images"
    RENDERING_VIDEO = "rendering_video"
    COMPLETED = "completed"
    FAILED = "failed"


class SceneType(str, Enum):
    """Types of scenes in a video"""
    TITLE = "title"  # Title card
    CONCEPT = "concept"  # Explaining a concept
    COMPARISON = "comparison"  # Comparing two things
    PROCESS = "process"  # Step-by-step process
    DATA = "data"  # Data visualization
    QUOTE = "quote"  # Quote display
    CONCLUSION = "conclusion"  # Summary/conclusion


class Scene(BaseModel):
    """Individual scene in a video"""
    scene_id: str = Field(..., description="Unique scene identifier")
    scene_type: SceneType = Field(..., description="Type of scene")

    # Content
    narration_text: str = Field(..., description="Narration script for this scene")
    visual_description: str = Field(..., description="Description of visual content")

    # Timing (in seconds)
    start_time: float = Field(..., description="Scene start time in seconds")
    duration: float = Field(..., description="Scene duration in seconds")

    # Generated assets (populated during generation)
    narration_audio_path: Optional[Path] = Field(default=None, description="Path to narration audio")
    image_path: Optional[Path] = Field(default=None, description="Path to generated image")

    # Metadata
    keywords: List[str] = Field(default_factory=list, description="Key concepts in scene")
    animation_style: str = Field(default="fade", description="Animation transition style")


class VideoScript(BaseModel):
    """Complete video script with scenes"""
    title: str = Field(..., description="Video title")
    description: str = Field(..., description="Video description")

    # Scenes
    scenes: List[Scene] = Field(..., description="List of scenes in order")

    # Metadata
    total_duration: float = Field(..., description="Total video duration in seconds")
    target_audience: str = Field(default="general", description="Target audience level")
    tone: str = Field(default="educational", description="Tone of narration")

    # Content analysis
    key_topics: List[str] = Field(default_factory=list, description="Main topics covered")
    complexity_score: float = Field(default=0.5, description="Content complexity (0-1)")


class VideoRequest(BaseModel):
    """Request to generate a video"""
    request_id: str = Field(..., description="Unique request identifier")

    # Input
    topic: str = Field(..., description="Topic or title of video")
    raw_script: Optional[str] = Field(default=None, description="User-provided script (optional)")
    research_urls: List[str] = Field(default_factory=list, description="URLs for research")

    # Quality settings
    quality: VideoQuality = Field(default=VideoQuality.STANDARD)
    image_provider: ImageProvider = Field(default=ImageProvider.DALLE3_STANDARD)
    voice_provider: VoiceProvider = Field(default=VoiceProvider.ELEVENLABS_TURBO)

    # Constraints
    target_duration: int = Field(default=300, description="Target duration in seconds")
    max_cost: float = Field(default=12.0, description="Maximum cost in USD")

    # Processing
    skip_research: bool = Field(default=False, description="Skip automated research phase")
    use_cache: bool = Field(default=True, description="Use cached assets if available")

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    user_id: Optional[str] = Field(default=None)


class AssetCost(BaseModel):
    """Cost breakdown for a single asset"""
    asset_type: str  # "narration", "image", "video_render"
    provider: str
    quantity: int
    unit_cost: float
    total_cost: float


class CostBreakdown(BaseModel):
    """Detailed cost breakdown for video generation"""
    narration_cost: float = Field(default=0.0)
    image_generation_cost: float = Field(default=0.0)
    rendering_cost: float = Field(default=0.0)
    other_costs: float = Field(default=0.0)

    total_cost: float = Field(default=0.0)

    # Detailed breakdown
    assets: List[AssetCost] = Field(default_factory=list)


class VideoResponse(BaseModel):
    """Response from video generation"""
    request_id: str
    status: VideoStatus

    # Progress
    progress_percentage: float = Field(default=0.0, ge=0.0, le=100.0)
    current_step: str = Field(default="Initializing")

    # Generated content
    script: Optional[VideoScript] = None
    video_path: Optional[Path] = None
    thumbnail_path: Optional[Path] = None

    # Metadata
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    processing_time_seconds: Optional[float] = None

    # Costs
    cost_breakdown: Optional[CostBreakdown] = None

    # Error handling
    error_message: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)


class GenerationMetrics(BaseModel):
    """Performance metrics for video generation"""
    request_id: str

    # Timing breakdown (seconds)
    script_processing_time: float = 0.0
    narration_generation_time: float = 0.0
    image_generation_time: float = 0.0
    video_rendering_time: float = 0.0
    total_time: float = 0.0

    # Asset counts
    scenes_generated: int = 0
    images_generated: int = 0
    audio_clips_generated: int = 0

    # Cache efficiency
    cache_hits: int = 0
    cache_misses: int = 0
    cache_hit_rate: float = 0.0

    # Quality metrics
    average_image_quality_score: Optional[float] = None
    narration_wpm: Optional[float] = None  # Words per minute

    # Cost efficiency
    cost_per_second: float = 0.0
    cost_per_scene: float = 0.0
