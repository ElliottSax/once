"""
Temporal worker for video generation workflows.

Runs workflows and activities for durable video generation.
"""

import asyncio
from temporalio.client import Client
from temporalio.worker import Worker
from loguru import logger

from config.settings import get_settings
from src.workflows.video_workflow import VideoGenerationWorkflow, BatchVideoGenerationWorkflow
from src.workflows import activities


async def run_worker():
    """
    Start Temporal worker.

    Connects to Temporal server and starts processing workflows and activities.
    """
    settings = get_settings()

    # Connect to Temporal server
    # In production, configure with actual Temporal Cloud credentials
    client = await Client.connect("localhost:7233")

    logger.info("Connected to Temporal server")

    # Create worker
    worker = Worker(
        client,
        task_queue="video-generation",
        workflows=[
            VideoGenerationWorkflow,
            BatchVideoGenerationWorkflow
        ],
        activities=[
            activities.process_script_activity,
            activities.generate_narration_activity,
            activities.generate_images_activity,
            activities.render_video_activity,
            activities.calculate_costs_activity,
        ],
        max_concurrent_activities=settings.max_concurrent_generations,
        max_concurrent_workflow_tasks=10,
    )

    logger.info("Starting Temporal worker...")
    logger.info("Task queue: video-generation")
    logger.info(f"Max concurrent activities: {settings.max_concurrent_generations}")

    # Run worker
    await worker.run()


def main():
    """Main entry point for worker"""
    logger.info("🚀 Starting Video Generation Worker")

    try:
        asyncio.run(run_worker())
    except KeyboardInterrupt:
        logger.info("Worker stopped by user")
    except Exception as e:
        logger.error(f"Worker error: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
