"""
Image generation service using DALL-E 3 and SDXL.

Handles:
- AI image generation with multiple providers
- Prompt engineering and optimization
- Image quality validation
- Caching and cost optimization
"""

import asyncio
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from loguru import logger
import aiohttp
import hashlib
import replicate
from openai import AsyncOpenAI

from config.settings import get_settings
from src.models.video_request import ImageProvider


class ImageService:
    """Generate images using AI models"""

    def __init__(self):
        """Initialize image service"""
        self.settings = get_settings()
        self.openai_client = AsyncOpenAI(api_key=self.settings.openai_api_key)
        self.replicate_client = replicate.Client(api_token=self.settings.replicate_api_token)

        # Image generation settings
        self.default_size = "1792x1024"  # 16:9 aspect ratio
        self.default_quality = "standard"

    async def generate_image(
        self,
        prompt: str,
        output_path: Path,
        provider: ImageProvider = ImageProvider.DALLE3_STANDARD,
        style: str = "digital_art",
        use_cache: bool = True
    ) -> Path:
        """
        Generate an image from a text prompt.

        Args:
            prompt: Text description of desired image
            output_path: Where to save the generated image
            provider: Image generation provider to use
            style: Visual style (digital_art, photorealistic, illustration, etc.)
            use_cache: Whether to use cached images

        Returns:
            Path to generated image
        """
        logger.info(f"Generating image with {provider.value}: {prompt[:100]}...")

        # Check cache first
        if use_cache and self.settings.cache_enabled:
            cached_path = await self._check_cache(prompt, provider)
            if cached_path:
                logger.info(f"Using cached image: {cached_path}")
                return cached_path

        # Optimize prompt for the provider
        optimized_prompt = self._optimize_prompt(prompt, provider, style)

        # Generate based on provider
        if provider in [ImageProvider.DALLE3_STANDARD, ImageProvider.DALLE3_HD]:
            image_path = await self._generate_dalle3(
                optimized_prompt,
                output_path,
                provider == ImageProvider.DALLE3_HD
            )
        elif provider in [ImageProvider.SDXL_FAST, ImageProvider.SDXL_QUALITY]:
            image_path = await self._generate_sdxl(
                optimized_prompt,
                output_path,
                provider == ImageProvider.SDXL_QUALITY
            )
        else:
            raise ValueError(f"Unsupported provider: {provider}")

        # Cache the result
        if use_cache and self.settings.cache_enabled:
            await self._cache_image(prompt, provider, image_path)

        logger.info(f"Image generated and saved to {image_path}")
        return image_path

    async def generate_batch(
        self,
        prompts: List[str],
        output_dir: Path,
        provider: ImageProvider = ImageProvider.DALLE3_STANDARD,
        style: str = "digital_art"
    ) -> List[Path]:
        """
        Generate multiple images concurrently.

        Args:
            prompts: List of image prompts
            output_dir: Directory to save images
            provider: Image generation provider
            style: Visual style

        Returns:
            List of paths to generated images
        """
        output_dir.mkdir(parents=True, exist_ok=True)

        tasks = []
        for i, prompt in enumerate(prompts):
            output_path = output_dir / f"image_{i:03d}.png"
            task = self.generate_image(prompt, output_path, provider, style)
            tasks.append(task)

        # Limit concurrent requests to avoid rate limits
        max_concurrent = min(self.settings.max_concurrent_generations, 3)
        results = []

        for i in range(0, len(tasks), max_concurrent):
            batch = tasks[i:i + max_concurrent]
            batch_results = await asyncio.gather(*batch, return_exceptions=True)

            for result in batch_results:
                if isinstance(result, Exception):
                    logger.error(f"Image generation failed: {result}")
                    results.append(None)
                else:
                    results.append(result)

            # Rate limiting delay between batches
            if i + max_concurrent < len(tasks):
                await asyncio.sleep(2)

        return [r for r in results if r is not None]

    async def _generate_dalle3(
        self,
        prompt: str,
        output_path: Path,
        hd_quality: bool = False
    ) -> Path:
        """Generate image using DALL-E 3"""
        try:
            response = await self.openai_client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size="1792x1024",
                quality="hd" if hd_quality else "standard",
                n=1,
            )

            # Download image
            image_url = response.data[0].url
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as resp:
                    if resp.status == 200:
                        output_path.parent.mkdir(parents=True, exist_ok=True)
                        image_data = await resp.read()
                        output_path.write_bytes(image_data)
                    else:
                        raise Exception(f"Failed to download image: {resp.status}")

            logger.debug(f"DALL-E 3 image generated: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"DALL-E 3 generation failed: {e}")
            raise

    async def _generate_sdxl(
        self,
        prompt: str,
        output_path: Path,
        high_quality: bool = False
    ) -> Path:
        """Generate image using Stable Diffusion XL"""
        try:
            # Use Replicate API for SDXL
            model_version = "stability-ai/sdxl:39ed52f2a78e934b3ba6e2a89f5b1c712de7dfea535525255b1aa35c5565e08b"

            parameters = {
                "prompt": prompt,
                "width": 1792 if high_quality else 1024,
                "height": 1024,
                "num_inference_steps": 50 if high_quality else 25,
                "guidance_scale": 7.5,
                "scheduler": "DPMSolverMultistep",
                "negative_prompt": "ugly, blurry, low quality, distorted, deformed, bad anatomy"
            }

            # Run generation (async)
            output = await asyncio.to_thread(
                self.replicate_client.run,
                model_version,
                input=parameters
            )

            # Download result
            if output and len(output) > 0:
                image_url = output[0]
                async with aiohttp.ClientSession() as session:
                    async with session.get(image_url) as resp:
                        if resp.status == 200:
                            output_path.parent.mkdir(parents=True, exist_ok=True)
                            image_data = await resp.read()
                            output_path.write_bytes(image_data)
                        else:
                            raise Exception(f"Failed to download SDXL image: {resp.status}")
            else:
                raise Exception("No output from SDXL model")

            logger.debug(f"SDXL image generated: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"SDXL generation failed: {e}")
            raise

    def _optimize_prompt(
        self,
        prompt: str,
        provider: ImageProvider,
        style: str
    ) -> str:
        """
        Optimize prompt for specific provider and style.

        Args:
            prompt: Original prompt
            provider: Target provider
            style: Desired style

        Returns:
            Optimized prompt
        """
        # Style descriptors
        style_modifiers = {
            "digital_art": "digital art, clean lines, vibrant colors, modern aesthetic",
            "photorealistic": "photorealistic, highly detailed, professional photography, 8k",
            "illustration": "illustration, hand-drawn style, artistic, creative",
            "minimalist": "minimalist design, simple shapes, clean composition",
            "isometric": "isometric view, 3D rendered, game art style",
            "infographic": "infographic style, data visualization, clear and informative"
        }

        style_desc = style_modifiers.get(style, "professional, high quality")

        # Provider-specific optimizations
        if provider in [ImageProvider.DALLE3_STANDARD, ImageProvider.DALLE3_HD]:
            # DALL-E 3 works well with natural language
            optimized = f"{prompt}, {style_desc}, professional quality"

        elif provider in [ImageProvider.SDXL_FAST, ImageProvider.SDXL_QUALITY]:
            # SDXL benefits from more specific artistic direction
            optimized = f"{prompt}, {style_desc}, trending on artstation, highly detailed, sharp focus"

        else:
            optimized = f"{prompt}, {style_desc}"

        # Ensure safe content
        optimized = self._ensure_safe_prompt(optimized)

        return optimized

    def _ensure_safe_prompt(self, prompt: str) -> str:
        """Ensure prompt complies with content policies"""
        # Remove potentially problematic terms
        unsafe_terms = ["nsfw", "explicit", "violent", "gore", "sexual"]

        prompt_lower = prompt.lower()
        for term in unsafe_terms:
            if term in prompt_lower:
                logger.warning(f"Removing unsafe term from prompt: {term}")
                prompt = prompt.replace(term, "")

        return prompt.strip()

    async def _check_cache(
        self,
        prompt: str,
        provider: ImageProvider
    ) -> Optional[Path]:
        """Check if image exists in cache"""
        # Create cache key from prompt and provider
        cache_key = hashlib.md5(f"{prompt}_{provider.value}".encode()).hexdigest()
        cache_dir = Path(self.settings.checkpoint_dir) / "image_cache"
        cache_path = cache_dir / f"{cache_key}.png"

        if cache_path.exists():
            return cache_path

        return None

    async def _cache_image(
        self,
        prompt: str,
        provider: ImageProvider,
        image_path: Path
    ):
        """Cache generated image"""
        try:
            cache_key = hashlib.md5(f"{prompt}_{provider.value}".encode()).hexdigest()
            cache_dir = Path(self.settings.checkpoint_dir) / "image_cache"
            cache_dir.mkdir(parents=True, exist_ok=True)

            cache_path = cache_dir / f"{cache_key}.png"

            # Copy image to cache
            import shutil
            shutil.copy2(image_path, cache_path)

            logger.debug(f"Image cached: {cache_path}")

        except Exception as e:
            logger.warning(f"Failed to cache image: {e}")

    def estimate_cost(
        self,
        num_images: int,
        provider: ImageProvider
    ) -> float:
        """
        Estimate cost for image generation.

        Args:
            num_images: Number of images to generate
            provider: Image provider

        Returns:
            Estimated cost in USD
        """
        # Pricing (approximate as of 2024)
        prices = {
            ImageProvider.DALLE3_STANDARD: 0.040,
            ImageProvider.DALLE3_HD: 0.080,
            ImageProvider.SDXL_FAST: 0.002,
            ImageProvider.SDXL_QUALITY: 0.004
        }

        price_per_image = prices.get(provider, 0.04)
        return num_images * price_per_image

    def validate_image(self, image_path: Path) -> Tuple[bool, Optional[str]]:
        """
        Validate generated image quality.

        Args:
            image_path: Path to image

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            from PIL import Image

            img = Image.open(image_path)

            # Check dimensions
            if img.size[0] < 512 or img.size[1] < 512:
                return False, "Image resolution too low"

            # Check file size (should be reasonable)
            file_size_mb = image_path.stat().st_size / (1024 * 1024)
            if file_size_mb > 50:
                return False, "Image file size too large"

            if file_size_mb < 0.01:
                return False, "Image file size suspiciously small"

            # Basic quality check - ensure not a blank image
            img_array = np.array(img)
            if np.std(img_array) < 10:  # Very low variance = likely blank
                return False, "Image appears to be blank or corrupted"

            return True, None

        except Exception as e:
            return False, f"Image validation error: {e}"


# Convenience function for synchronous usage
def generate_image_sync(
    prompt: str,
    output_path: Path,
    provider: ImageProvider = ImageProvider.DALLE3_STANDARD
) -> Path:
    """Synchronous wrapper for image generation"""
    async def _generate():
        service = ImageService()
        return await service.generate_image(prompt, output_path, provider)

    return asyncio.run(_generate())
