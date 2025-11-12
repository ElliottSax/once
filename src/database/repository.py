"""
Repository layer for database operations.

Provides clean interface for CRUD operations on database models.
"""

from typing import List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
import uuid

from src.database.models import User, Video, Asset, VideoMetrics, UsageLog, VideoStatusEnum
from src.models.video_request import VideoRequest, VideoResponse


class VideoRepository:
    """Repository for video operations"""

    def __init__(self, session: Session):
        self.session = session

    def create_video(self, user_id: str, request: VideoRequest) -> Video:
        """Create new video job"""
        video = Video(
            id=request.request_id,
            user_id=user_id,
            topic=request.topic,
            script_text=request.raw_script,
            target_duration=request.target_duration,
            quality=request.quality.value,
            image_provider=request.image_provider.value,
            voice_provider=request.voice_provider.value,
            max_cost=request.max_cost,
            status=VideoStatusEnum.PENDING,
            progress=0.0,
            current_step="Initializing",
            created_at=datetime.utcnow()
        )

        self.session.add(video)
        self.session.commit()
        self.session.refresh(video)

        return video

    def get_video(self, video_id: str) -> Optional[Video]:
        """Get video by ID"""
        return self.session.query(Video).filter(Video.id == video_id).first()

    def get_videos_by_user(
        self,
        user_id: str,
        limit: int = 20,
        offset: int = 0,
        status: Optional[VideoStatusEnum] = None
    ) -> List[Video]:
        """Get videos for a user with pagination"""
        query = self.session.query(Video).filter(Video.user_id == user_id)

        if status:
            query = query.filter(Video.status == status)

        return query.order_by(Video.created_at.desc()).offset(offset).limit(limit).all()

    def update_video_status(
        self,
        video_id: str,
        status: VideoStatusEnum,
        progress: float = None,
        current_step: str = None,
        error_message: str = None
    ) -> Optional[Video]:
        """Update video status"""
        video = self.get_video(video_id)
        if not video:
            return None

        video.status = status

        if progress is not None:
            video.progress = progress

        if current_step:
            video.current_step = current_step

        if error_message:
            video.error_message = error_message

        # Set timestamps
        if status == VideoStatusEnum.PROCESSING_SCRIPT and not video.started_at:
            video.started_at = datetime.utcnow()

        if status in [VideoStatusEnum.COMPLETED, VideoStatusEnum.FAILED]:
            video.completed_at = datetime.utcnow()
            if video.started_at:
                video.processing_time_seconds = (
                    video.completed_at - video.started_at
                ).total_seconds()

        self.session.commit()
        self.session.refresh(video)

        return video

    def update_video_result(
        self,
        video_id: str,
        video_path: str,
        duration_seconds: float,
        total_cost: float,
        cost_breakdown: dict = None
    ) -> Optional[Video]:
        """Update video with final results"""
        video = self.get_video(video_id)
        if not video:
            return None

        video.video_path = video_path
        video.duration_seconds = duration_seconds
        video.total_cost = total_cost

        if cost_breakdown:
            video.narration_cost = cost_breakdown.get("narration", 0.0)
            video.image_cost = cost_breakdown.get("images", 0.0)
            video.rendering_cost = cost_breakdown.get("rendering", 0.0)

        self.session.commit()
        self.session.refresh(video)

        return video

    def delete_video(self, video_id: str) -> bool:
        """Delete video and all related data"""
        video = self.get_video(video_id)
        if not video:
            return False

        self.session.delete(video)
        self.session.commit()

        return True

    def get_user_daily_cost(self, user_id: str, date: datetime = None) -> float:
        """Get total cost for user on a specific day"""
        if date is None:
            date = datetime.utcnow()

        start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)

        result = self.session.query(func.sum(Video.total_cost)).filter(
            and_(
                Video.user_id == user_id,
                Video.created_at >= start_of_day,
                Video.created_at < end_of_day,
                Video.status == VideoStatusEnum.COMPLETED
            )
        ).scalar()

        return result or 0.0

    def get_user_monthly_cost(self, user_id: str, year: int = None, month: int = None) -> float:
        """Get total cost for user in a specific month"""
        now = datetime.utcnow()
        if year is None:
            year = now.year
        if month is None:
            month = now.month

        start_of_month = datetime(year, month, 1)
        if month == 12:
            end_of_month = datetime(year + 1, 1, 1)
        else:
            end_of_month = datetime(year, month + 1, 1)

        result = self.session.query(func.sum(Video.total_cost)).filter(
            and_(
                Video.user_id == user_id,
                Video.created_at >= start_of_month,
                Video.created_at < end_of_month,
                Video.status == VideoStatusEnum.COMPLETED
            )
        ).scalar()

        return result or 0.0

    def get_stats(self, user_id: str = None) -> dict:
        """Get generation statistics"""
        query = self.session.query(
            func.count(Video.id).label("total_videos"),
            func.count(Video.id).filter(Video.status == VideoStatusEnum.COMPLETED).label("completed"),
            func.count(Video.id).filter(Video.status == VideoStatusEnum.FAILED).label("failed"),
            func.sum(Video.total_cost).label("total_cost"),
            func.avg(Video.processing_time_seconds).label("avg_time")
        )

        if user_id:
            query = query.filter(Video.user_id == user_id)

        result = query.first()

        return {
            "total_videos": result.total_videos or 0,
            "completed": result.completed or 0,
            "failed": result.failed or 0,
            "total_cost": float(result.total_cost or 0.0),
            "average_processing_time": float(result.avg_time or 0.0)
        }


class UserRepository:
    """Repository for user operations"""

    def __init__(self, session: Session):
        self.session = session

    def create_user(self, email: str, name: str = None) -> User:
        """Create new user"""
        user = User(
            id=str(uuid.uuid4()),
            email=email,
            name=name,
            api_key=self._generate_api_key(),
            created_at=datetime.utcnow()
        )

        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)

        return user

    def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        return self.session.query(User).filter(User.id == user_id).first()

    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        return self.session.query(User).filter(User.email == email).first()

    def get_user_by_api_key(self, api_key: str) -> Optional[User]:
        """Get user by API key"""
        return self.session.query(User).filter(User.api_key == api_key).first()

    def update_user_usage(self, user_id: str, cost: float) -> Optional[User]:
        """Update user usage stats"""
        user = self.get_user(user_id)
        if not user:
            return None

        user.total_videos_generated += 1
        user.total_cost += cost
        user.updated_at = datetime.utcnow()

        self.session.commit()
        self.session.refresh(user)

        return user

    def _generate_api_key(self) -> str:
        """Generate unique API key"""
        import secrets
        return f"vga_{secrets.token_urlsafe(32)}"


class AssetRepository:
    """Repository for asset operations"""

    def __init__(self, session: Session):
        self.session = session

    def create_asset(
        self,
        video_id: str,
        asset_type: str,
        file_path: str,
        **kwargs
    ) -> Asset:
        """Create asset record"""
        asset = Asset(
            id=str(uuid.uuid4()),
            video_id=video_id,
            asset_type=asset_type,
            file_path=file_path,
            **kwargs
        )

        self.session.add(asset)
        self.session.commit()
        self.session.refresh(asset)

        return asset

    def get_assets_by_video(self, video_id: str) -> List[Asset]:
        """Get all assets for a video"""
        return self.session.query(Asset).filter(Asset.video_id == video_id).all()

    def get_asset_by_cache_key(self, cache_key: str) -> Optional[Asset]:
        """Find asset by cache key"""
        return self.session.query(Asset).filter(Asset.cache_key == cache_key).first()
