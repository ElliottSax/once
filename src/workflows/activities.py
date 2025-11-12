"""
Temporal activities for video generation workflow.

Each activity is a discrete unit of work that can be retried independently.
"""

import asyncio
from pathlib import Path
from temporalio import activity
from loguru import logger

from src.services.script_processor import ScriptProcessor
from src.services.narration_service import NarrationService
from src.services.image_service import ImageService
from src.services.remotion_service import RemotionService
from src.models.video_request import VideoScript, CostBreakdown, ImageProvider, VoiceProvider
from config.settings import get_settings


@activity.defn(name="process_script")
async def process_script_activity(
    topic: str,
    raw_script: str,
    target_duration: int
) -> VideoScript:
    """
    Activity: Process raw script into structured scenes.

    Args:
        topic: Video topic
        raw_script: Raw script text
        target_duration: Target duration in seconds

    Returns:
        Processed VideoScript
    """
    activity.logger.info(f"Processing script for: {topic}")

    processor = ScriptProcessor()
    script = processor.process_script(
        text=raw_script,
        title=topic,
        target_duration=target_duration
    )

    activity.logger.info(f"Script processed: {len(script.scenes)} scenes")
    return script


@activity.defn(name="generate_narration")
async def generate_narration_activity(
    script: VideoScript,
    request_id: str,
    voice_provider: str
) -> list[Path]:
    """
    Activity: Generate narration audio for all scenes.

    Args:
        script: Video script with scenes
        request_id: Request ID for workspace
        voice_provider: Voice provider to use

    Returns:
        List of paths to generated audio files
    """
    activity.logger.info(f"Generating narration: {len(script.scenes)} scenes")

    settings = get_settings()
    workspace = Path(settings.checkpoint_dir) / request_id / "narration"
    workspace.mkdir(parents=True, exist_ok=True)

    async with NarrationService() as service:
        texts = [scene.narration_text for scene in script.scenes]
        results = await service.generate_batch(texts, workspace)

    audio_paths = [result[0] for result in results]
    activity.logger.info(f"Narration generated: {len(audio_paths)} files")

    return audio_paths


@activity.defn(name="generate_images")
async def generate_images_activity(
    script: VideoScript,
    request_id: str,
    image_provider: str
) -> list[Path]:
    """
    Activity: Generate images for all scenes.

    Args:
        script: Video script with scenes
        request_id: Request ID for workspace
        image_provider: Image provider to use

    Returns:
        List of paths to generated images
    """
    activity.logger.info(f"Generating images: {len(script.scenes)} scenes")

    settings = get_settings()
    workspace = Path(settings.checkpoint_dir) / request_id / "images"
    workspace.mkdir(parents=True, exist_ok=True)

    service = ImageService()

    # Extract prompts (skip title/conclusion)
    prompts = []
    scene_indices = []

    for i, scene in enumerate(script.scenes):
        if scene.scene_type.value not in ['title', 'conclusion']:
            prompts.append(scene.visual_description)
            scene_indices.append(i)

    # Generate images
    results = await service.generate_batch(
        prompts,
        workspace,
        ImageProvider(image_provider)
    )

    # Fill in with None for skipped scenes
    full_results = [None] * len(script.scenes)
    for idx, result in zip(scene_indices, results):
        full_results[idx] = result

    activity.logger.info(f"Images generated: {len(results)} files")
    return full_results


@activity.defn(name="render_video")
async def render_video_activity(
    script: VideoScript,
    narration_paths: list[Path],
    image_paths: list[Path],
    request_id: str,
    quality: str
) -> Path:
    """
    Activity: Render final video with Remotion.

    Args:
        script: Video script
        narration_paths: Paths to narration audio files
        image_paths: Paths to generated images
        request_id: Request ID
        quality: Video quality

    Returns:
        Path to rendered video
    """
    activity.logger.info("Rendering video with Remotion")

    settings = get_settings()
    workspace = Path(settings.checkpoint_dir) / request_id

    # Update scene paths
    for i, scene in enumerate(script.scenes):
        if i < len(narration_paths):
            scene.narration_audio_path = narration_paths[i]
        if i < len(image_paths):
            scene.image_path = image_paths[i]

    # Prepare Remotion data
    import json
    remotion_data = {
        "title": script.title,
        "description": script.description,
        "scenes": [
            {
                "id": scene.scene_id,
                "type": scene.scene_type.value,
                "narrationText": scene.narration_text,
                "visualDescription": scene.visual_description,
                "startTime": scene.start_time,
                "duration": scene.duration,
                "audioPath": str(scene.narration_audio_path) if scene.narration_audio_path else None,
                "imagePath": str(scene.image_path) if scene.image_path else None,
                "animationStyle": scene.animation_style,
                "keywords": scene.keywords
            }
            for scene in script.scenes
        ],
        "totalDuration": script.total_duration,
        "quality": quality,
        "metadata": {
            "requestId": request_id,
            "targetAudience": script.target_audience,
            "tone": script.tone
        }
    }

    # Save data file
    data_path = workspace / "remotion_data.json"
    data_path.write_text(json.dumps(remotion_data, indent=2, default=str))

    # Render video
    output_path = workspace / "output" / f"{request_id}.mp4"
    service = RemotionService()

    video_path = await service.render_video(
        video_data_path=data_path,
        output_path=output_path,
        quality=quality
    )

    activity.logger.info(f"Video rendered: {video_path}")
    return video_path


@activity.defn(name="calculate_costs")
async def calculate_costs_activity(
    script: VideoScript,
    request: dict,  # VideoRequest as dict
    narration_paths: list[Path],
    image_paths: list[Path]
) -> CostBreakdown:
    """
    Activity: Calculate detailed cost breakdown.

    Args:
        script: Video script
        request: Original request (as dict)
        narration_paths: Generated audio files
        image_paths: Generated images

    Returns:
        Cost breakdown
    """
    activity.logger.info("Calculating costs")

    breakdown = CostBreakdown()

    # Narration costs
    total_chars = sum(len(scene.narration_text) for scene in script.scenes)
    breakdown.narration_cost = total_chars * 0.00015

    # Image costs
    provider_costs = {
        'dalle3_standard': 0.040,
        'dalle3_hd': 0.080,
        'sdxl_fast': 0.002,
        'sdxl_quality': 0.004
    }

    image_count = len([p for p in image_paths if p is not None])
    image_provider = request.get('image_provider', 'dalle3_standard')
    breakdown.image_generation_cost = image_count * provider_costs.get(image_provider, 0.040)

    # Rendering costs
    duration_minutes = script.total_duration / 60
    breakdown.rendering_cost = duration_minutes * 0.05

    # Total
    breakdown.total_cost = (
        breakdown.narration_cost +
        breakdown.image_generation_cost +
        breakdown.rendering_cost
    )

    activity.logger.info(f"Total cost: ${breakdown.total_cost:.2f}")
    return breakdown
