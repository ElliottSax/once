"""
Command-line interface for video generation.

Usage:
    python -m src.cli generate --topic "Introduction to Python" --script script.txt
    python -m src.cli estimate --topic "Machine Learning Basics" --script script.txt
"""

import asyncio
import click
from pathlib import Path
from loguru import logger
import sys
import uuid
from datetime import datetime

from config.settings import get_settings
from src.models.video_request import VideoRequest, VideoQuality, ImageProvider, VoiceProvider
from src.services.video_generator import VideoGenerator


# Configure logger
logger.remove()
logger.add(
    sys.stderr,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
    level="INFO"
)


@click.group()
def cli():
    """Video generation CLI"""
    pass


@cli.command()
@click.option('--topic', required=True, help='Video topic/title')
@click.option('--script', type=click.Path(exists=True), help='Path to script file')
@click.option('--duration', default=300, help='Target duration in seconds (default: 300)')
@click.option('--quality', type=click.Choice(['draft', 'standard', 'premium']), default='standard')
@click.option('--image-provider', type=click.Choice(['dalle3_standard', 'dalle3_hd', 'sdxl_fast', 'sdxl_quality']), default='dalle3_standard')
@click.option('--voice-provider', type=click.Choice(['elevenlabs_turbo', 'elevenlabs_standard', 'elevenlabs_premium']), default='elevenlabs_turbo')
@click.option('--max-cost', default=12.0, help='Maximum cost in USD (default: 12.0)')
@click.option('--output', type=click.Path(), help='Output directory')
def generate(topic, script, duration, quality, image_provider, voice_provider, max_cost, output):
    """Generate a video from a script"""
    click.echo(f"🎬 Generating video: {topic}")
    click.echo(f"Duration target: {duration}s")
    click.echo(f"Quality: {quality}")
    click.echo(f"Max cost: ${max_cost:.2f}")
    click.echo()

    # Load script
    raw_script = None
    if script:
        script_path = Path(script)
        raw_script = script_path.read_text()
        click.echo(f"📄 Script loaded: {len(raw_script)} characters")
    else:
        click.echo("⚠️  No script provided - automated research not yet implemented")
        return

    # Create request
    request = VideoRequest(
        request_id=f"video_{uuid.uuid4().hex[:8]}",
        topic=topic,
        raw_script=raw_script,
        target_duration=duration,
        quality=VideoQuality(quality),
        image_provider=ImageProvider(image_provider),
        voice_provider=VoiceProvider(voice_provider),
        max_cost=max_cost
    )

    # Progress callback
    def progress_callback(percent, message):
        click.echo(f"[{percent:3.0f}%] {message}")

    # Run generation
    async def run():
        generator = VideoGenerator()

        # Estimate cost first
        click.echo("💰 Estimating cost...")
        estimated_cost = await generator.estimate_cost(request)
        click.echo(f"Estimated cost: ${estimated_cost:.2f}")

        if estimated_cost > max_cost:
            click.echo(f"❌ Estimated cost (${estimated_cost:.2f}) exceeds max (${max_cost:.2f})")
            if not click.confirm("Continue anyway?"):
                return

        click.echo()
        click.echo("🚀 Starting generation...")
        click.echo()

        response = await generator.generate_video(
            request,
            progress_callback=lambda p, m: progress_callback(p, m)
        )

        click.echo()
        if response.status.value == 'completed':
            click.echo("✅ Video generation completed!")
            click.echo(f"Video: {response.video_path}")
            if response.cost_breakdown:
                click.echo(f"Total cost: ${response.cost_breakdown.total_cost:.2f}")
            if response.processing_time_seconds:
                click.echo(f"Processing time: {response.processing_time_seconds:.1f}s")
        else:
            click.echo(f"❌ Generation failed: {response.error_message}")

    asyncio.run(run())


@cli.command()
@click.option('--topic', required=True, help='Video topic/title')
@click.option('--script', type=click.Path(exists=True), help='Path to script file')
@click.option('--duration', default=300, help='Target duration in seconds')
@click.option('--image-provider', type=click.Choice(['dalle3_standard', 'dalle3_hd', 'sdxl_fast', 'sdxl_quality']), default='dalle3_standard')
@click.option('--voice-provider', type=click.Choice(['elevenlabs_turbo', 'elevenlabs_standard', 'elevenlabs_premium']), default='elevenlabs_turbo')
def estimate(topic, script, duration, image_provider, voice_provider):
    """Estimate cost for video generation"""
    click.echo(f"💰 Estimating cost for: {topic}")

    # Load script
    raw_script = None
    if script:
        script_path = Path(script)
        raw_script = script_path.read_text()

    # Create request
    request = VideoRequest(
        request_id="estimate",
        topic=topic,
        raw_script=raw_script,
        target_duration=duration,
        image_provider=ImageProvider(image_provider),
        voice_provider=VoiceProvider(voice_provider)
    )

    async def run():
        generator = VideoGenerator()
        cost = await generator.estimate_cost(request)

        click.echo()
        click.echo(f"Estimated total cost: ${cost:.2f}")
        click.echo()
        click.echo("Breakdown (approximate):")

        if raw_script:
            from src.services.script_processor import ScriptProcessor
            processor = ScriptProcessor()
            script_obj = processor.process_script(raw_script, topic, duration)

            narration_chars = sum(len(s.narration_text) for s in script_obj.scenes)
            narration_cost = narration_chars * 0.00015

            image_count = len([s for s in script_obj.scenes if s.scene_type.value not in ['title', 'conclusion']])
            image_costs = {
                'dalle3_standard': 0.040,
                'dalle3_hd': 0.080,
                'sdxl_fast': 0.002,
                'sdxl_quality': 0.004
            }
            image_cost = image_count * image_costs[image_provider]

            rendering_cost = (duration / 60) * 0.05

            click.echo(f"  Narration: ${narration_cost:.2f} ({narration_chars} chars)")
            click.echo(f"  Images: ${image_cost:.2f} ({image_count} images @ ${image_costs[image_provider]} each)")
            click.echo(f"  Rendering: ${rendering_cost:.2f} ({duration/60:.1f} minutes)")

    asyncio.run(run())


@cli.command()
def test():
    """Run a test generation with sample script"""
    click.echo("🧪 Running test generation...")

    sample_script = """
    Python is one of the most popular programming languages in the world.
    It's known for its simple, readable syntax that makes it perfect for beginners.

    Python is versatile and can be used for web development, data science, automation, and more.
    Companies like Google, Netflix, and NASA use Python for critical systems.

    One of Python's greatest strengths is its extensive library ecosystem.
    Libraries like NumPy, Pandas, and TensorFlow make complex tasks simple.

    Getting started with Python is easy. You can download it for free and start coding in minutes.
    The Python community is welcoming and always ready to help newcomers.
    """

    # Create temporary script file
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write(sample_script)
        script_path = f.name

    # Run generation with test settings
    from click.testing import CliRunner
    runner = CliRunner()

    result = runner.invoke(
        generate,
        [
            '--topic', 'Introduction to Python Programming',
            '--script', script_path,
            '--duration', '60',
            '--quality', 'draft',
            '--image-provider', 'sdxl_fast',
            '--max-cost', '5.0'
        ]
    )

    click.echo(result.output)

    # Cleanup
    Path(script_path).unlink()


@cli.command()
def info():
    """Show system information and configuration"""
    click.echo("System Information")
    click.echo("=" * 50)

    settings = get_settings()

    click.echo(f"Environment: {settings.environment}")
    click.echo(f"Log level: {settings.log_level}")
    click.echo()
    click.echo("Configuration:")
    click.echo(f"  Max cost per video: ${settings.max_cost_per_video:.2f}")
    click.echo(f"  Daily budget limit: ${settings.daily_budget_limit:.2f}")
    click.echo(f"  Default quality: {settings.default_render_quality}")
    click.echo(f"  Default image provider: {settings.default_image_provider}")
    click.echo(f"  Default voice provider: {settings.default_voice_provider}")
    click.echo(f"  Max concurrent generations: {settings.max_concurrent_generations}")
    click.echo(f"  Cache enabled: {settings.cache_enabled}")
    click.echo()
    click.echo("Workspace:")
    click.echo(f"  Checkpoint dir: {settings.checkpoint_dir}")
    click.echo()


if __name__ == '__main__':
    cli()
