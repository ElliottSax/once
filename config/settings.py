"""
Configuration management for the video automation system.
"""

import os
from typing import Optional
from pathlib import Path
from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # ========================================================================
    # AI Generation APIs
    # ========================================================================

    openai_api_key: str = Field(..., env="OPENAI_API_KEY")
    replicate_api_token: str = Field(..., env="REPLICATE_API_TOKEN")
    elevenlabs_api_key: str = Field(..., env="ELEVENLABS_API_KEY")

    # ========================================================================
    # Cloud Infrastructure
    # ========================================================================

    aws_access_key_id: str = Field(..., env="AWS_ACCESS_KEY_ID")
    aws_secret_access_key: str = Field(..., env="AWS_SECRET_ACCESS_KEY")
    aws_region: str = Field(default="us-east-1", env="AWS_REGION")

    s3_bucket_assets: str = Field(..., env="AWS_S3_BUCKET_ASSETS")
    s3_bucket_videos: str = Field(..., env="AWS_S3_BUCKET_VIDEOS")
    s3_bucket_cache: str = Field(..., env="AWS_S3_BUCKET_CACHE")

    # Remotion Lambda (optional)
    remotion_lambda_function_name: Optional[str] = Field(
        default=None, env="REMOTION_LAMBDA_FUNCTION_NAME"
    )
    remotion_bundle_url: Optional[str] = Field(
        default=None, env="REMOTION_BUNDLE_URL"
    )

    # ========================================================================
    # YouTube API
    # ========================================================================

    youtube_api_key: Optional[str] = Field(default=None, env="YOUTUBE_API_KEY")
    youtube_client_id: Optional[str] = Field(default=None, env="YOUTUBE_CLIENT_ID")
    youtube_client_secret: Optional[str] = Field(
        default=None, env="YOUTUBE_CLIENT_SECRET"
    )

    # ========================================================================
    # Database
    # ========================================================================

    database_url: str = Field(..., env="DATABASE_URL")
    redis_url: str = Field(default="redis://localhost:6379", env="REDIS_URL")

    # ========================================================================
    # Application Settings
    # ========================================================================

    environment: str = Field(default="development", env="ENVIRONMENT")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")

    # Cost limits
    max_cost_per_video: float = Field(default=20.0, env="MAX_COST_PER_VIDEO")
    daily_budget_limit: float = Field(default=200.0, env="DAILY_BUDGET_LIMIT")

    # Quality settings
    default_render_quality: str = Field(
        default="standard", env="DEFAULT_RENDER_QUALITY"
    )
    default_image_provider: str = Field(
        default="dalle3_standard", env="DEFAULT_IMAGE_PROVIDER"
    )
    default_voice_provider: str = Field(
        default="elevenlabs_turbo", env="DEFAULT_VOICE_PROVIDER"
    )

    # Performance
    max_concurrent_generations: int = Field(
        default=5, env="MAX_CONCURRENT_GENERATIONS"
    )
    cache_enabled: bool = Field(default=True, env="CACHE_ENABLED")
    cache_ttl_days: int = Field(default=30, env="CACHE_TTL_DAYS")

    # ========================================================================
    # Development Settings
    # ========================================================================

    use_local_gpu: bool = Field(default=True, env="USE_LOCAL_GPU")
    ffmpeg_path: str = Field(default="/usr/bin/ffmpeg", env="FFMPEG_PATH")

    debug_mode: bool = Field(default=False, env="DEBUG_MODE")
    save_intermediate_outputs: bool = Field(
        default=True, env="SAVE_INTERMEDIATE_OUTPUTS"
    )
    checkpoint_dir: Path = Field(
        default=Path("/tmp/video_automation_checkpoints"),
        env="CHECKPOINT_DIR"
    )

    # ========================================================================
    # Computed Properties
    # ========================================================================

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment == "development"

    @property
    def use_lambda_rendering(self) -> bool:
        """Check if Lambda rendering is configured and should be used."""
        return (
            self.remotion_lambda_function_name is not None
            and self.remotion_bundle_url is not None
        )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()
