"""
Remotion video rendering service.

Handles interaction with Remotion for video rendering:
- Calls Remotion CLI for rendering
- Manages render jobs
- Handles Lambda rendering (when configured)
"""

import asyncio
import json
import subprocess
from pathlib import Path
from typing import Optional, Dict
from loguru import logger

from config.settings import get_settings


class RemotionService:
    """Service for rendering videos with Remotion"""

    def __init__(self):
        """Initialize Remotion service"""
        self.settings = get_settings()
        self.remotion_dir = Path(__file__).parent.parent.parent / "remotion"

    async def render_video(
        self,
        video_data_path: Path,
        output_path: Path,
        composition_id: str = "FullVideo",
        quality: str = "standard"
    ) -> Path:
        """
        Render video using Remotion.

        Args:
            video_data_path: Path to JSON file with video data
            output_path: Where to save the rendered video
            composition_id: Remotion composition ID
            quality: Rendering quality (draft/standard/premium)

        Returns:
            Path to rendered video file
        """
        logger.info(f"Starting Remotion render: {composition_id}")
        logger.info(f"Data: {video_data_path}")
        logger.info(f"Output: {output_path}")

        # Load video data to get duration
        with open(video_data_path, 'r') as f:
            video_data = json.load(f)

        total_duration = video_data.get('totalDuration', 300)
        fps = 30
        duration_frames = int(total_duration * fps)

        # Prepare Remotion props (pass video data as JSON string)
        props_json = json.dumps({"videoData": video_data})

        # Determine rendering method
        if self.settings.use_lambda_rendering:
            return await self._render_with_lambda(
                composition_id,
                props_json,
                output_path,
                duration_frames,
                quality
            )
        else:
            return await self._render_locally(
                composition_id,
                props_json,
                output_path,
                duration_frames,
                quality
            )

    async def _render_locally(
        self,
        composition_id: str,
        props_json: str,
        output_path: Path,
        duration_frames: int,
        quality: str
    ) -> Path:
        """Render video locally using Remotion CLI"""
        logger.info("Rendering locally with Remotion CLI")

        # Create output directory
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Quality settings
        quality_settings = self._get_quality_settings(quality)

        # Build Remotion command
        cmd = [
            "npx",
            "remotion",
            "render",
            "src/index.tsx",
            composition_id,
            str(output_path),
            "--props", props_json,
            "--overwrite",
        ]

        # Add quality settings
        if quality_settings.get('codec'):
            cmd.extend(["--codec", quality_settings['codec']])
        if quality_settings.get('crf'):
            cmd.extend(["--crf", str(quality_settings['crf'])])
        if quality_settings.get('pixel_format'):
            cmd.extend(["--pixel-format", quality_settings['pixel_format']])

        logger.debug(f"Remotion command: {' '.join(cmd)}")

        try:
            # Run Remotion render
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(self.remotion_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            # Stream output
            async def stream_output(stream, prefix):
                while True:
                    line = await stream.readline()
                    if not line:
                        break
                    logger.info(f"{prefix}: {line.decode().strip()}")

            # Monitor both stdout and stderr
            await asyncio.gather(
                stream_output(process.stdout, "Remotion"),
                stream_output(process.stderr, "Remotion-Error")
            )

            # Wait for completion
            returncode = await process.wait()

            if returncode != 0:
                raise Exception(f"Remotion render failed with code {returncode}")

            logger.info(f"Remotion render completed: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Remotion render error: {e}")
            raise

    async def _render_with_lambda(
        self,
        composition_id: str,
        props_json: str,
        output_path: Path,
        duration_frames: int,
        quality: str
    ) -> Path:
        """Render video using Remotion Lambda"""
        logger.info("Rendering with Remotion Lambda")

        # TODO: Implement Lambda rendering
        # This requires:
        # 1. Upload bundle to S3
        # 2. Invoke Lambda function
        # 3. Poll for completion
        # 4. Download result from S3

        logger.warning("Lambda rendering not yet implemented, falling back to local")
        return await self._render_locally(
            composition_id,
            props_json,
            output_path,
            duration_frames,
            quality
        )

    def _get_quality_settings(self, quality: str) -> Dict:
        """Get encoding settings for quality preset"""
        settings = {
            'draft': {
                'codec': 'h264',
                'crf': 28,  # Lower quality, faster
                'pixel_format': 'yuv420p',
            },
            'standard': {
                'codec': 'h264',
                'crf': 18,  # Good quality
                'pixel_format': 'yuv420p',
            },
            'premium': {
                'codec': 'h264',
                'crf': 15,  # High quality
                'pixel_format': 'yuv420p',
            }
        }

        return settings.get(quality, settings['standard'])

    async def check_remotion_available(self) -> bool:
        """Check if Remotion is installed and available"""
        try:
            process = await asyncio.create_subprocess_exec(
                "npx", "remotion", "--version",
                cwd=str(self.remotion_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                version = stdout.decode().strip()
                logger.info(f"Remotion available: {version}")
                return True
            else:
                logger.warning("Remotion not available")
                return False

        except Exception as e:
            logger.warning(f"Error checking Remotion: {e}")
            return False

    def estimate_render_time(self, duration_seconds: float, quality: str) -> float:
        """
        Estimate render time in seconds.

        Args:
            duration_seconds: Video duration
            quality: Quality preset

        Returns:
            Estimated render time in seconds
        """
        # Rough estimates based on quality
        # These are multipliers of video duration
        multipliers = {
            'draft': 0.5,  # Renders faster than real-time
            'standard': 1.5,  # Renders at 1.5x video duration
            'premium': 3.0,  # Renders at 3x video duration
        }

        multiplier = multipliers.get(quality, 1.5)
        estimated_time = duration_seconds * multiplier

        logger.debug(
            f"Render time estimate: {estimated_time:.1f}s "
            f"for {duration_seconds:.1f}s video at {quality} quality"
        )

        return estimated_time
