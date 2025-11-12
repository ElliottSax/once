"""
FastAPI application with PostgreSQL database integration.

This version uses persistent database storage instead of in-memory dictionaries.
"""

from fastapi import FastAPI, BackgroundTasks, HTTPException, WebSocket, WebSocketDisconnect, Depends
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pathlib import Path
from typing import Dict, List
from datetime import datetime
import asyncio
from loguru import logger

from src.api.models import (
    GenerateVideoRequest,
    VideoStatusResponse,
    CostEstimateRequest,
    CostEstimateResponse
)
from src.models.video_request import VideoRequest, VideoQuality, ImageProvider, VoiceProvider
from src.services.video_generator import VideoGenerator
from src.database import (
    init_db,
    get_db,
    VideoRepository,
    UserRepository,
    VideoStatusEnum
)

# Initialize FastAPI app
app = FastAPI(
    title="Video Generation API",
    description="Automated YouTube explainer video generation with PostgreSQL",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket connections
websocket_connections: Dict[str, List[WebSocket]] = {}


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    logger.info("Initializing database...")
    init_db()
    logger.info("Database initialized")


@app.get("/api/health")
async def health_check(db: Session = Depends(get_db)):
    """Health check with database connectivity"""
    try:
        # Test database connection
        db.execute("SELECT 1")
        db_status = "connected"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_status = "disconnected"

    return {
        "status": "healthy" if db_status == "connected" else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "2.0.0",
        "database": db_status
    }


@app.post("/api/videos/generate", response_model=VideoStatusResponse)
async def generate_video(
    request: GenerateVideoRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Start video generation job with database persistence.
    """
    # TODO: Get user from auth header
    # For now, use default user or create one
    user_repo = UserRepository(db)
    user = user_repo.get_user_by_email("default@example.com")
    if not user:
        user = user_repo.create_user("default@example.com", "Default User")

    # Check user budget limits
    video_repo = VideoRepository(db)
    daily_cost = video_repo.get_user_daily_cost(user.id)
    if daily_cost + request.max_cost > user.daily_budget_limit:
        raise HTTPException(
            status_code=429,
            detail=f"Daily budget limit exceeded. Current: ${daily_cost:.2f}, Limit: ${user.daily_budget_limit:.2f}"
        )

    # Create video request
    video_request = VideoRequest(
        request_id=f"video_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
        topic=request.topic,
        raw_script=request.script,
        target_duration=request.duration,
        quality=VideoQuality(request.quality),
        image_provider=ImageProvider(request.image_provider),
        voice_provider=VoiceProvider(request.voice_provider),
        max_cost=request.max_cost
    )

    # Create database record
    video = video_repo.create_video(user.id, video_request)

    # Start generation in background
    background_tasks.add_task(process_video_generation_db, video.id, video_request)

    logger.info(f"Video generation started: {video.id}")

    return VideoStatusResponse(
        video_id=video.id,
        status=video.status.value,
        progress=video.progress,
        current_step=video.current_step,
        created_at=video.created_at
    )


async def process_video_generation_db(video_id: str, request: VideoRequest):
    """Background task with database persistence"""
    from src.database import get_db_session

    try:
        generator = VideoGenerator()

        # Progress callback
        async def progress_callback(progress: float, message: str):
            with get_db_session() as session:
                repo = VideoRepository(session)

                # Map message to status
                status = VideoStatusEnum.PROCESSING_SCRIPT
                if "narration" in message.lower():
                    status = VideoStatusEnum.GENERATING_NARRATION
                elif "image" in message.lower():
                    status = VideoStatusEnum.GENERATING_IMAGES
                elif "render" in message.lower():
                    status = VideoStatusEnum.RENDERING_VIDEO

                repo.update_video_status(
                    video_id,
                    status=status,
                    progress=progress,
                    current_step=message
                )

                # Notify WebSocket clients
                await broadcast_progress(video_id, progress, message)

        # Generate video
        response = await generator.generate_video(request, progress_callback)

        # Update database with results
        with get_db_session() as session:
            repo = VideoRepository(session)
            user_repo = UserRepository(session)

            if response.status.value == "completed":
                repo.update_video_result(
                    video_id,
                    video_path=str(response.video_path),
                    duration_seconds=response.script.total_duration if response.script else 0,
                    total_cost=response.cost_breakdown.total_cost if response.cost_breakdown else 0,
                    cost_breakdown={
                        "narration": response.cost_breakdown.narration_cost if response.cost_breakdown else 0,
                        "images": response.cost_breakdown.image_generation_cost if response.cost_breakdown else 0,
                        "rendering": response.cost_breakdown.rendering_cost if response.cost_breakdown else 0
                    }
                )

                repo.update_video_status(
                    video_id,
                    status=VideoStatusEnum.COMPLETED,
                    progress=100.0,
                    current_step="Completed"
                )

                # Update user usage
                video = repo.get_video(video_id)
                if video:
                    user_repo.update_user_usage(video.user_id, video.total_cost)

                logger.info(f"Video generation completed: {video_id}")
            else:
                repo.update_video_status(
                    video_id,
                    status=VideoStatusEnum.FAILED,
                    error_message=response.error_message
                )
                logger.error(f"Video generation failed: {video_id}")

    except Exception as e:
        logger.error(f"Video generation error: {video_id} - {e}", exc_info=True)

        with get_db_session() as session:
            repo = VideoRepository(session)
            repo.update_video_status(
                video_id,
                status=VideoStatusEnum.FAILED,
                error_message=str(e)
            )


@app.get("/api/videos/{video_id}", response_model=VideoStatusResponse)
async def get_video_status(video_id: str, db: Session = Depends(get_db)):
    """Get video status from database"""
    repo = VideoRepository(db)
    video = repo.get_video(video_id)

    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    return VideoStatusResponse(
        video_id=video.id,
        status=video.status.value,
        progress=video.progress,
        current_step=video.current_step or "",
        created_at=video.created_at,
        completed_at=video.completed_at,
        video_url=f"/api/videos/{video.id}/download" if video.status == VideoStatusEnum.COMPLETED else None,
        error_message=video.error_message,
        cost=video.total_cost
    )


@app.get("/api/videos/{video_id}/download")
async def download_video(video_id: str, db: Session = Depends(get_db)):
    """Download completed video"""
    repo = VideoRepository(db)
    video = repo.get_video(video_id)

    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    if video.status != VideoStatusEnum.COMPLETED:
        raise HTTPException(status_code=400, detail="Video not ready")

    if not video.video_path:
        raise HTTPException(status_code=500, detail="Video file not found")

    video_path = Path(video.video_path)
    if not video_path.exists():
        raise HTTPException(status_code=500, detail="Video file missing")

    return FileResponse(
        path=str(video_path),
        media_type="video/mp4",
        filename=f"{video_id}.mp4"
    )


@app.post("/api/videos/estimate", response_model=CostEstimateResponse)
async def estimate_cost(request: CostEstimateRequest):
    """Estimate cost for video generation"""
    video_request = VideoRequest(
        request_id="estimate",
        topic=request.topic,
        raw_script=request.script,
        target_duration=request.duration,
        image_provider=ImageProvider(request.image_provider),
        voice_provider=VoiceProvider(request.voice_provider)
    )

    generator = VideoGenerator()
    estimated_cost = await generator.estimate_cost(video_request)

    return CostEstimateResponse(
        estimated_cost=estimated_cost,
        duration=request.duration,
        breakdown={
            "narration": estimated_cost * 0.4,
            "images": estimated_cost * 0.4,
            "rendering": estimated_cost * 0.2
        }
    )


@app.websocket("/api/videos/{video_id}/progress")
async def websocket_progress(websocket: WebSocket, video_id: str):
    """WebSocket for real-time progress updates"""
    await websocket.accept()

    if video_id not in websocket_connections:
        websocket_connections[video_id] = []
    websocket_connections[video_id].append(websocket)

    try:
        # Send current status
        from src.database import get_db_session
        with get_db_session() as session:
            repo = VideoRepository(session)
            video = repo.get_video(video_id)

            if video:
                await websocket.send_json({
                    "type": "status",
                    "progress": video.progress,
                    "message": video.current_step or "",
                    "status": video.status.value
                })

        # Keep connection open
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                await websocket.send_json({"type": "pong"})
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "heartbeat"})

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {video_id}")
    finally:
        if video_id in websocket_connections:
            websocket_connections[video_id].remove(websocket)


async def broadcast_progress(video_id: str, progress: float, message: str):
    """Broadcast progress to WebSocket clients"""
    if video_id not in websocket_connections:
        return

    message_data = {
        "type": "progress",
        "progress": progress,
        "message": message
    }

    disconnected = []
    for ws in websocket_connections[video_id]:
        try:
            await ws.send_json(message_data)
        except Exception as e:
            logger.warning(f"Failed to send to WebSocket: {e}")
            disconnected.append(ws)

    for ws in disconnected:
        websocket_connections[video_id].remove(ws)


@app.get("/api/videos", response_model=List[VideoStatusResponse])
async def list_videos(
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """List videos with pagination"""
    # TODO: Filter by authenticated user
    repo = VideoRepository(db)

    # Get default user for now
    user_repo = UserRepository(db)
    user = user_repo.get_user_by_email("default@example.com")

    if not user:
        return []

    videos = repo.get_videos_by_user(user.id, limit=limit, offset=offset)

    return [
        VideoStatusResponse(
            video_id=video.id,
            status=video.status.value,
            progress=video.progress,
            current_step=video.current_step or "",
            created_at=video.created_at,
            completed_at=video.completed_at,
            video_url=f"/api/videos/{video.id}/download" if video.status == VideoStatusEnum.COMPLETED else None,
            cost=video.total_cost
        )
        for video in videos
    ]


@app.delete("/api/videos/{video_id}")
async def delete_video(video_id: str, db: Session = Depends(get_db)):
    """Delete video and cleanup resources"""
    repo = VideoRepository(db)
    video = repo.get_video(video_id)

    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    # Cleanup workspace
    generator = VideoGenerator()
    generator.cleanup_workspace(video_id, keep_final_video=False)

    # Delete from database
    repo.delete_video(video_id)

    logger.info(f"Video deleted: {video_id}")

    return {"status": "deleted", "video_id": video_id}


@app.get("/api/stats")
async def get_stats(db: Session = Depends(get_db)):
    """Get generation statistics"""
    repo = VideoRepository(db)

    # TODO: Filter by authenticated user
    user_repo = UserRepository(db)
    user = user_repo.get_user_by_email("default@example.com")

    if not user:
        return {"error": "No user found"}

    stats = repo.get_stats(user.id)

    return {
        **stats,
        "user": {
            "total_videos": user.total_videos_generated,
            "total_cost": user.total_cost,
            "daily_limit": user.daily_budget_limit,
            "monthly_limit": user.monthly_budget_limit
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
