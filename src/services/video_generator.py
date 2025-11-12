"""
Main video generation orchestrator.

Coordinates the entire video generation pipeline:
1. Script processing and scene generation
2. Narration generation
3. Image generation
4. Video rendering with Remotion
5. Asset management and cleanup
"""

import asyncio
from pathlib import Path
from typing import Optional, Dict, List
from datetime import datetime
from loguru import logger
import json

from config.settings import get_settings
from src.models.video_request import (
    VideoRequest,
    VideoResponse,
    VideoStatus,
    CostBreakdown,
    AssetCost,
    GenerationMetrics,
    ImageProvider
)
from src.services.script_processor import ScriptProcessor
from src.services.narration_service import NarrationService
from src.services.image_service import ImageService


class VideoGenerator:
    """
    Main orchestrator for video generation pipeline.

    Handles the complete workflow from script to final video.
    """

    def __init__(self):
        """Initialize video generator"""
        self.settings = get_settings()
        self.script_processor = ScriptProcessor()

        # Workspace setup
        self.workspace = Path(self.settings.checkpoint_dir)
        self.workspace.mkdir(parents=True, exist_ok=True)

    async def generate_video(
        self,
        request: VideoRequest,
        progress_callback: Optional[callable] = None
    ) -> VideoResponse:
        """
        Generate a complete video from request.

        Args:
            request: Video generation request
            progress_callback: Optional callback(progress, message) for updates

        Returns:
            VideoResponse with results and metadata
        """
        logger.info(f"Starting video generation: {request.request_id}")
        logger.info(f"Topic: {request.topic}")

        start_time = datetime.utcnow()
        metrics = GenerationMetrics(request_id=request.request_id)

        # Initialize response
        response = VideoResponse(
            request_id=request.request_id,
            status=VideoStatus.PENDING,
            started_at=start_time
        )

        try:
            # Step 1: Process script
            response.status = VideoStatus.PROCESSING_SCRIPT
            response.current_step = "Processing script and generating scenes"
            if progress_callback:
                await progress_callback(10, response.current_step)

            script_start = datetime.utcnow()

            if request.raw_script:
                script = self.script_processor.process_script(
                    request.raw_script,
                    request.topic,
                    request.target_duration
                )
            else:
                # TODO: Implement automated research and script generation
                raise NotImplementedError("Automated script generation not yet implemented")

            metrics.script_processing_time = (datetime.utcnow() - script_start).total_seconds()
            metrics.scenes_generated = len(script.scenes)
            response.script = script

            logger.info(f"Script processed: {len(script.scenes)} scenes, {script.total_duration:.1f}s")

            # Step 2: Generate narration
            response.status = VideoStatus.GENERATING_NARRATION
            response.current_step = "Generating narration audio"
            if progress_callback:
                await progress_callback(30, response.current_step)

            narration_start = datetime.utcnow()
            narration_dir = self.workspace / request.request_id / "narration"
            narration_dir.mkdir(parents=True, exist_ok=True)

            narration_results = await self._generate_narrations(
                script.scenes,
                narration_dir,
                request.voice_provider
            )

            metrics.narration_generation_time = (datetime.utcnow() - narration_start).total_seconds()
            metrics.audio_clips_generated = len(narration_results)

            # Update scene audio paths
            for scene, (audio_path, duration) in zip(script.scenes, narration_results):
                scene.narration_audio_path = audio_path
                # Update duration based on actual narration
                if duration > 0:
                    scene.duration = duration + 1.0  # Add 1s buffer for visuals

            logger.info(f"Narration generated: {len(narration_results)} audio files")

            # Step 3: Generate images
            response.status = VideoStatus.GENERATING_IMAGES
            response.current_step = "Generating visual assets"
            if progress_callback:
                await progress_callback(60, response.current_step)

            image_start = datetime.utcnow()
            image_dir = self.workspace / request.request_id / "images"
            image_dir.mkdir(parents=True, exist_ok=True)

            image_results = await self._generate_images(
                script.scenes,
                image_dir,
                request.image_provider
            )

            metrics.image_generation_time = (datetime.utcnow() - image_start).total_seconds()
            metrics.images_generated = len(image_results)

            # Update scene image paths
            for scene, image_path in zip(script.scenes, image_results):
                scene.image_path = image_path

            logger.info(f"Images generated: {len(image_results)} images")

            # Step 4: Prepare Remotion data
            response.current_step = "Preparing video composition"
            if progress_callback:
                await progress_callback(80, response.current_step)

            remotion_data = self._prepare_remotion_data(script, request)
            remotion_data_path = self.workspace / request.request_id / "remotion_data.json"
            remotion_data_path.write_text(json.dumps(remotion_data, indent=2, default=str))

            logger.info(f"Remotion data prepared: {remotion_data_path}")

            # Step 5: Render video with Remotion
            response.status = VideoStatus.RENDERING_VIDEO
            response.current_step = "Rendering final video"
            if progress_callback:
                await progress_callback(90, response.current_step)

            render_start = datetime.utcnow()
            video_path = await self._render_video(
                remotion_data_path,
                request.request_id,
                request.quality
            )

            metrics.video_rendering_time = (datetime.utcnow() - render_start).total_seconds()
            response.video_path = video_path

            logger.info(f"Video rendered: {video_path}")

            # Step 6: Calculate costs
            cost_breakdown = self._calculate_costs(
                script,
                request,
                metrics
            )
            response.cost_breakdown = cost_breakdown

            # Finalize
            response.status = VideoStatus.COMPLETED
            response.current_step = "Completed"
            response.completed_at = datetime.utcnow()
            response.progress_percentage = 100.0

            metrics.total_time = (response.completed_at - start_time).total_seconds()

            logger.info(
                f"Video generation completed: {metrics.total_time:.1f}s, "
                f"${cost_breakdown.total_cost:.2f}"
            )

            if progress_callback:
                await progress_callback(100, "Completed")

        except Exception as e:
            logger.error(f"Video generation failed: {e}", exc_info=True)
            response.status = VideoStatus.FAILED
            response.error_message = str(e)
            response.completed_at = datetime.utcnow()

        response.processing_time_seconds = (
            response.completed_at - start_time
        ).total_seconds() if response.completed_at else None

        return response

    async def _generate_narrations(
        self,
        scenes: List,
        output_dir: Path,
        voice_provider: str
    ) -> List[tuple]:
        """Generate narration audio for all scenes"""
        async with NarrationService() as narration_service:
            texts = [scene.narration_text for scene in scenes]
            results = await narration_service.generate_batch(texts, output_dir)
            return results

    async def _generate_images(
        self,
        scenes: List,
        output_dir: Path,
        image_provider: ImageProvider
    ) -> List[Path]:
        """Generate images for all scenes"""
        image_service = ImageService()

        # Skip title and conclusion scenes (use generated graphics instead)
        prompts = []
        scene_indices = []

        for i, scene in enumerate(scenes):
            if scene.scene_type.value not in ['title', 'conclusion']:
                prompts.append(scene.visual_description)
                scene_indices.append(i)

        # Generate images
        results = await image_service.generate_batch(
            prompts,
            output_dir,
            image_provider
        )

        # Fill in with None for skipped scenes
        full_results = [None] * len(scenes)
        for idx, result in zip(scene_indices, results):
            full_results[idx] = result

        return full_results

    def _prepare_remotion_data(self, script, request: VideoRequest) -> Dict:
        """Prepare data structure for Remotion rendering"""
        scenes_data = []

        for scene in script.scenes:
            scene_data = {
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
            scenes_data.append(scene_data)

        return {
            "title": script.title,
            "description": script.description,
            "scenes": scenes_data,
            "totalDuration": script.total_duration,
            "quality": request.quality.value,
            "metadata": {
                "requestId": request.request_id,
                "createdAt": datetime.utcnow().isoformat(),
                "targetAudience": script.target_audience,
                "tone": script.tone
            }
        }

    async def _render_video(
        self,
        remotion_data_path: Path,
        request_id: str,
        quality: str
    ) -> Path:
        """Render video using Remotion"""
        from src.services.remotion_service import RemotionService

        output_dir = self.workspace / request_id / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        video_path = output_dir / f"{request_id}.mp4"

        # Check if Remotion is available
        remotion_service = RemotionService()
        is_available = await remotion_service.check_remotion_available()

        if not is_available:
            logger.warning(
                "Remotion not available. "
                "Install with: cd remotion && npm install"
            )
            # Create placeholder for testing
            video_path.write_text("Placeholder - Remotion not installed")
            return video_path

        # Render with Remotion
        try:
            video_path = await remotion_service.render_video(
                video_data_path=remotion_data_path,
                output_path=video_path,
                composition_id="FullVideo",
                quality=quality
            )

            logger.info(f"Video rendered successfully: {video_path}")
            return video_path

        except Exception as e:
            logger.error(f"Remotion rendering failed: {e}")
            # Create error placeholder
            video_path.write_text(f"Rendering failed: {e}")
            raise

    def _calculate_costs(
        self,
        script,
        request: VideoRequest,
        metrics: GenerationMetrics
    ) -> CostBreakdown:
        """Calculate detailed cost breakdown"""
        breakdown = CostBreakdown()

        # Narration costs
        total_chars = sum(len(scene.narration_text) for scene in script.scenes)
        narration_unit_cost = 0.00015  # ElevenLabs turbo
        breakdown.narration_cost = total_chars * narration_unit_cost

        breakdown.assets.append(AssetCost(
            asset_type="narration",
            provider=request.voice_provider.value,
            quantity=metrics.audio_clips_generated,
            unit_cost=narration_unit_cost,
            total_cost=breakdown.narration_cost
        ))

        # Image generation costs
        provider_costs = {
            ImageProvider.DALLE3_STANDARD: 0.040,
            ImageProvider.DALLE3_HD: 0.080,
            ImageProvider.SDXL_FAST: 0.002,
            ImageProvider.SDXL_QUALITY: 0.004
        }

        image_unit_cost = provider_costs.get(request.image_provider, 0.040)
        breakdown.image_generation_cost = metrics.images_generated * image_unit_cost

        breakdown.assets.append(AssetCost(
            asset_type="image",
            provider=request.image_provider.value,
            quantity=metrics.images_generated,
            unit_cost=image_unit_cost,
            total_cost=breakdown.image_generation_cost
        ))

        # Rendering costs
        duration_minutes = script.total_duration / 60
        rendering_unit_cost = 0.05  # Per minute
        breakdown.rendering_cost = duration_minutes * rendering_unit_cost

        breakdown.assets.append(AssetCost(
            asset_type="rendering",
            provider="remotion_lambda",
            quantity=1,
            unit_cost=breakdown.rendering_cost,
            total_cost=breakdown.rendering_cost
        ))

        # Total
        breakdown.total_cost = (
            breakdown.narration_cost +
            breakdown.image_generation_cost +
            breakdown.rendering_cost +
            breakdown.other_costs
        )

        return breakdown

    async def estimate_cost(self, request: VideoRequest) -> float:
        """
        Estimate total cost before generation.

        Args:
            request: Video request

        Returns:
            Estimated cost in USD
        """
        # Process script to get scene count
        if request.raw_script:
            script = self.script_processor.process_script(
                request.raw_script,
                request.topic,
                request.target_duration
            )
        else:
            # Rough estimate without script
            estimated_scenes = request.target_duration // 20  # ~20s per scene
            estimated_chars = request.target_duration * 3  # ~3 chars per second
            narration_cost = estimated_chars * 0.00015
            image_cost = estimated_scenes * 0.04
            rendering_cost = (request.target_duration / 60) * 0.05
            return narration_cost + image_cost + rendering_cost

        settings = {
            'image_provider': request.image_provider.value,
            'voice_provider': request.voice_provider.value
        }

        return self.script_processor.estimate_total_cost(script, settings)

    def cleanup_workspace(self, request_id: str, keep_final_video: bool = True):
        """
        Clean up temporary files for a request.

        Args:
            request_id: Request ID to clean up
            keep_final_video: Whether to keep the final video file
        """
        workspace_dir = self.workspace / request_id

        if not workspace_dir.exists():
            return

        if keep_final_video:
            # Move video to permanent storage
            output_dir = workspace_dir / "output"
            if output_dir.exists():
                # Keep output, remove intermediate files
                for subdir in ['narration', 'images']:
                    subdir_path = workspace_dir / subdir
                    if subdir_path.exists():
                        import shutil
                        shutil.rmtree(subdir_path)
                logger.info(f"Cleaned intermediate files for {request_id}")
        else:
            # Remove everything
            import shutil
            shutil.rmtree(workspace_dir)
            logger.info(f"Removed all files for {request_id}")
