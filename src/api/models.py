"""
Pydantic models for API requests and responses.
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict
from datetime import datetime


class GenerateVideoRequest(BaseModel):
    """Request to generate a video"""
    topic: str = Field(..., description="Video topic/title", min_length=3, max_length=200)
    script: str = Field(..., description="Video script content", min_length=50)
    duration: int = Field(default=300, description="Target duration in seconds", ge=30, le=1800)
    quality: str = Field(default="standard", description="Video quality", pattern="^(draft|standard|premium)$")
    image_provider: str = Field(
        default="dalle3_standard",
        description="Image generation provider",
        pattern="^(dalle3_standard|dalle3_hd|sdxl_fast|sdxl_quality)$"
    )
    voice_provider: str = Field(
        default="elevenlabs_turbo",
        description="Voice synthesis provider",
        pattern="^(elevenlabs_turbo|elevenlabs_standard|elevenlabs_premium)$"
    )
    max_cost: float = Field(default=12.0, description="Maximum cost in USD", ge=1.0, le=100.0)

    class Config:
        schema_extra = {
            "example": {
                "topic": "Introduction to Python Programming",
                "script": "Python is one of the most popular programming languages...",
                "duration": 300,
                "quality": "standard",
                "image_provider": "dalle3_standard",
                "voice_provider": "elevenlabs_turbo",
                "max_cost": 12.0
            }
        }


class VideoStatusResponse(BaseModel):
    """Response with video generation status"""
    video_id: str
    status: str  # pending, processing_script, generating_narration, etc.
    progress: float = Field(..., ge=0.0, le=100.0, description="Progress percentage")
    current_step: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    video_url: Optional[str] = None
    error_message: Optional[str] = None
    cost: Optional[float] = None

    class Config:
        schema_extra = {
            "example": {
                "video_id": "video_abc123def456",
                "status": "generating_narration",
                "progress": 45.0,
                "current_step": "Generating narration audio",
                "created_at": "2024-01-15T10:30:00Z",
                "completed_at": None,
                "video_url": None,
                "error_message": None,
                "cost": None
            }
        }


class CostEstimateRequest(BaseModel):
    """Request to estimate video generation cost"""
    topic: str = Field(..., description="Video topic", min_length=3)
    script: Optional[str] = Field(None, description="Video script (optional)")
    duration: int = Field(default=300, description="Target duration in seconds", ge=30, le=1800)
    image_provider: str = Field(default="dalle3_standard")
    voice_provider: str = Field(default="elevenlabs_turbo")


class CostEstimateResponse(BaseModel):
    """Response with cost estimate"""
    estimated_cost: float = Field(..., description="Total estimated cost in USD")
    duration: int = Field(..., description="Video duration in seconds")
    breakdown: Dict[str, float] = Field(..., description="Cost breakdown by component")

    class Config:
        schema_extra = {
            "example": {
                "estimated_cost": 2.50,
                "duration": 300,
                "breakdown": {
                    "narration": 1.00,
                    "images": 1.00,
                    "rendering": 0.50
                }
            }
        }


class ErrorResponse(BaseModel):
    """Error response"""
    error: str
    status_code: int
    details: Optional[Dict] = None
