"""
Temporal workflow for video generation.

Provides durable, fault-tolerant video generation with automatic retries
and state persistence.
"""

from datetime import timedelta
from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from src.models.video_request import VideoRequest, VideoResponse


@workflow.defn(name="VideoGenerationWorkflow")
class VideoGenerationWorkflow:
    """
    Main workflow for video generation.

    Orchestrates the complete video generation pipeline with durability
    and fault tolerance. Each step is an activity that can be retried
    independently.
    """

    @workflow.run
    async def run(self, request: VideoRequest) -> VideoResponse:
        """
        Execute video generation workflow.

        Args:
            request: Video generation request

        Returns:
            VideoResponse with final results
        """
        workflow.logger.info(f"Starting video workflow: {request.request_id}")

        # Default retry policy for all activities
        retry_policy = RetryPolicy(
            initial_interval=timedelta(seconds=1),
            maximum_interval=timedelta(seconds=60),
            maximum_attempts=3,
            backoff_coefficient=2.0,
        )

        try:
            # Step 1: Process script and generate scenes
            workflow.logger.info("Step 1: Processing script")
            script = await workflow.execute_activity(
                "process_script",
                args=[request.topic, request.raw_script, request.target_duration],
                start_to_close_timeout=timedelta(minutes=2),
                retry_policy=retry_policy,
            )

            # Step 2: Generate narration audio
            workflow.logger.info("Step 2: Generating narration")
            narration_paths = await workflow.execute_activity(
                "generate_narration",
                args=[script, request.request_id, request.voice_provider],
                start_to_close_timeout=timedelta(minutes=10),
                retry_policy=retry_policy,
            )

            # Step 3: Generate images
            workflow.logger.info("Step 3: Generating images")
            image_paths = await workflow.execute_activity(
                "generate_images",
                args=[script, request.request_id, request.image_provider],
                start_to_close_timeout=timedelta(minutes=15),
                retry_policy=retry_policy,
            )

            # Step 4: Render video with Remotion
            workflow.logger.info("Step 4: Rendering video")
            video_path = await workflow.execute_activity(
                "render_video",
                args=[
                    script,
                    narration_paths,
                    image_paths,
                    request.request_id,
                    request.quality
                ],
                start_to_close_timeout=timedelta(minutes=30),
                retry_policy=retry_policy,
            )

            # Step 5: Calculate costs
            workflow.logger.info("Step 5: Calculating costs")
            cost_breakdown = await workflow.execute_activity(
                "calculate_costs",
                args=[script, request, narration_paths, image_paths],
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=retry_policy,
            )

            # Create success response
            response = VideoResponse(
                request_id=request.request_id,
                status="completed",
                progress_percentage=100.0,
                current_step="Completed",
                script=script,
                video_path=video_path,
                cost_breakdown=cost_breakdown,
            )

            workflow.logger.info(f"Video workflow completed: {request.request_id}")
            return response

        except Exception as e:
            workflow.logger.error(f"Video workflow failed: {e}")

            # Create failure response
            response = VideoResponse(
                request_id=request.request_id,
                status="failed",
                error_message=str(e),
            )

            return response


@workflow.defn(name="BatchVideoGenerationWorkflow")
class BatchVideoGenerationWorkflow:
    """
    Workflow for generating multiple videos in parallel.

    Useful for batch processing or campaign generation.
    """

    @workflow.run
    async def run(self, requests: list[VideoRequest]) -> list[VideoResponse]:
        """
        Execute batch video generation.

        Args:
            requests: List of video generation requests

        Returns:
            List of VideoResponses
        """
        workflow.logger.info(f"Starting batch workflow: {len(requests)} videos")

        # Start child workflows for each video
        child_workflows = []
        for request in requests:
            child = workflow.execute_child_workflow(
                VideoGenerationWorkflow.run,
                args=[request],
                id=f"video-{request.request_id}",
                task_queue="video-generation",
            )
            child_workflows.append(child)

        # Wait for all to complete
        results = await workflow.wait_for_all(*child_workflows)

        workflow.logger.info(f"Batch workflow completed: {len(results)} videos")
        return results
