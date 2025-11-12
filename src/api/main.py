"""
FastAPI application for video generation API.

Endpoints:
- POST /api/videos/generate - Start video generation
- GET /api/videos/{video_id} - Get video status
- GET /api/videos/{video_id}/download - Download video
- POST /api/videos/estimate - Estimate cost
- GET /api/health - Health check
- WS /api/videos/{video_id}/progress - Progress updates via WebSocket
"""

from fastapi import FastAPI, BackgroundTasks, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from typing import Dict, Optional, List
from datetime import datetime
import uuid
import asyncio
from loguru import logger

from src.api.models import (
    GenerateVideoRequest,
    VideoStatusResponse,
    CostEstimateRequest,
    CostEstimateResponse,
    ErrorResponse
)
from src.models.video_request import VideoRequest, VideoQuality, ImageProvider, VoiceProvider
from src.services.video_generator import VideoGenerator

# Initialize FastAPI app
app = FastAPI(
    title="Video Generation API",
    description="Automated YouTube explainer video generation",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for video jobs (use Redis/DB in production)
video_jobs: Dict[str, dict] = {}

# WebSocket connections for progress updates
websocket_connections: Dict[str, List[WebSocket]] = {}


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }


@app.post("/api/videos/generate", response_model=VideoStatusResponse)
async def generate_video(
    request: GenerateVideoRequest,
    background_tasks: BackgroundTasks
):
    """
    Start video generation job.

    Creates a new video generation request and processes it in the background.
    Returns immediately with a job ID for tracking progress.
    """
    # Create unique video ID
    video_id = f"video_{uuid.uuid4().hex[:12]}"

    # Create video request
    video_request = VideoRequest(
        request_id=video_id,
        topic=request.topic,
        raw_script=request.script,
        target_duration=request.duration,
        quality=VideoQuality(request.quality),
        image_provider=ImageProvider(request.image_provider),
        voice_provider=VoiceProvider(request.voice_provider),
        max_cost=request.max_cost
    )

    # Initialize job status
    video_jobs[video_id] = {
        "id": video_id,
        "status": "pending",
        "created_at": datetime.utcnow(),
        "progress": 0,
        "current_step": "Initializing",
        "request": video_request,
        "response": None,
        "error": None
    }

    # Start generation in background
    background_tasks.add_task(process_video_generation, video_id, video_request)

    logger.info(f"Video generation started: {video_id}")

    return VideoStatusResponse(
        video_id=video_id,
        status="pending",
        progress=0,
        current_step="Initializing",
        created_at=video_jobs[video_id]["created_at"]
    )


async def process_video_generation(video_id: str, request: VideoRequest):
    """Background task to process video generation"""
    try:
        generator = VideoGenerator()

        # Progress callback to update job status
        async def progress_callback(progress: float, message: str):
            if video_id in video_jobs:
                video_jobs[video_id]["progress"] = progress
                video_jobs[video_id]["current_step"] = message

                # Notify WebSocket clients
                await broadcast_progress(video_id, progress, message)

        # Generate video
        response = await generator.generate_video(request, progress_callback)

        # Update job status
        video_jobs[video_id]["response"] = response
        video_jobs[video_id]["status"] = response.status.value
        video_jobs[video_id]["progress"] = 100.0

        if response.status.value == "completed":
            logger.info(f"Video generation completed: {video_id}")
        else:
            logger.error(f"Video generation failed: {video_id} - {response.error_message}")
            video_jobs[video_id]["error"] = response.error_message

    except Exception as e:
        logger.error(f"Video generation error: {video_id} - {e}", exc_info=True)
        video_jobs[video_id]["status"] = "failed"
        video_jobs[video_id]["error"] = str(e)


@app.get("/api/videos/{video_id}", response_model=VideoStatusResponse)
async def get_video_status(video_id: str):
    """Get status of a video generation job"""
    if video_id not in video_jobs:
        raise HTTPException(status_code=404, detail="Video not found")

    job = video_jobs[video_id]
    response = job.get("response")

    return VideoStatusResponse(
        video_id=video_id,
        status=job["status"],
        progress=job.get("progress", 0),
        current_step=job.get("current_step", ""),
        created_at=job["created_at"],
        completed_at=response.completed_at if response else None,
        video_url=f"/api/videos/{video_id}/download" if job["status"] == "completed" else None,
        error_message=job.get("error"),
        cost=response.cost_breakdown.total_cost if response and response.cost_breakdown else None
    )


@app.get("/api/videos/{video_id}/download")
async def download_video(video_id: str):
    """Download completed video"""
    if video_id not in video_jobs:
        raise HTTPException(status_code=404, detail="Video not found")

    job = video_jobs[video_id]

    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail="Video not ready")

    response = job.get("response")
    if not response or not response.video_path:
        raise HTTPException(status_code=500, detail="Video file not found")

    video_path = Path(response.video_path)
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
    # Create temporary request for estimation
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
    """
    WebSocket endpoint for real-time progress updates.

    Clients connect to receive live updates about video generation progress.
    """
    await websocket.accept()

    # Add connection to tracking
    if video_id not in websocket_connections:
        websocket_connections[video_id] = []
    websocket_connections[video_id].append(websocket)

    try:
        # Send current status immediately
        if video_id in video_jobs:
            job = video_jobs[video_id]
            await websocket.send_json({
                "type": "status",
                "progress": job.get("progress", 0),
                "message": job.get("current_step", ""),
                "status": job.get("status", "unknown")
            })

        # Keep connection open and listen for messages
        while True:
            # Wait for messages from client (e.g., ping/pong)
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                # Echo back (keep-alive)
                await websocket.send_json({"type": "pong"})
            except asyncio.TimeoutError:
                # Send periodic heartbeat
                await websocket.send_json({"type": "heartbeat"})

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {video_id}")
    finally:
        # Remove connection
        if video_id in websocket_connections:
            websocket_connections[video_id].remove(websocket)


async def broadcast_progress(video_id: str, progress: float, message: str):
    """Broadcast progress update to all connected WebSocket clients"""
    if video_id not in websocket_connections:
        return

    message_data = {
        "type": "progress",
        "progress": progress,
        "message": message
    }

    # Send to all connected clients
    disconnected = []
    for ws in websocket_connections[video_id]:
        try:
            await ws.send_json(message_data)
        except Exception as e:
            logger.warning(f"Failed to send to WebSocket: {e}")
            disconnected.append(ws)

    # Clean up disconnected clients
    for ws in disconnected:
        websocket_connections[video_id].remove(ws)


@app.get("/api/videos", response_model=List[VideoStatusResponse])
async def list_videos(limit: int = 20, offset: int = 0):
    """List all video generation jobs"""
    jobs = list(video_jobs.values())
    jobs.sort(key=lambda x: x["created_at"], reverse=True)

    paginated = jobs[offset:offset + limit]

    return [
        VideoStatusResponse(
            video_id=job["id"],
            status=job["status"],
            progress=job.get("progress", 0),
            current_step=job.get("current_step", ""),
            created_at=job["created_at"],
            video_url=f"/api/videos/{job['id']}/download" if job["status"] == "completed" else None
        )
        for job in paginated
    ]


@app.delete("/api/videos/{video_id}")
async def delete_video(video_id: str):
    """Delete a video and cleanup resources"""
    if video_id not in video_jobs:
        raise HTTPException(status_code=404, detail="Video not found")

    job = video_jobs[video_id]

    # Cleanup workspace
    generator = VideoGenerator()
    generator.cleanup_workspace(video_id, keep_final_video=False)

    # Remove from tracking
    del video_jobs[video_id]

    logger.info(f"Video deleted: {video_id}")

    return {"status": "deleted", "video_id": video_id}


# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=exc.detail,
            status_code=exc.status_code
        ).dict()
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Internal server error",
            status_code=500
        ).dict()
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
