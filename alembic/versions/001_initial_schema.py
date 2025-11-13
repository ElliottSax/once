"""Initial schema with User, Video, Asset, VideoMetrics, UsageLog, ApiKey tables

Revision ID: 001
Revises:
Create Date: 2025-11-12

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create users table
    op.create_table('users',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=True),
        sa.Column('api_key', sa.String(length=64), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('daily_budget_limit', sa.Float(), nullable=True),
        sa.Column('monthly_budget_limit', sa.Float(), nullable=True),
        sa.Column('total_videos_generated', sa.Integer(), nullable=True),
        sa.Column('total_cost', sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_api_key'), 'users', ['api_key'], unique=True)
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    # Create videos table with correct enum values
    op.create_table('videos',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('topic', sa.String(length=500), nullable=False),
        sa.Column('script_text', sa.Text(), nullable=True),
        sa.Column('target_duration', sa.Integer(), nullable=True),
        sa.Column('quality', sa.String(length=20), nullable=True),
        sa.Column('image_provider', sa.String(length=50), nullable=True),
        sa.Column('voice_provider', sa.String(length=50), nullable=True),
        sa.Column('max_cost', sa.Float(), nullable=True),
        sa.Column('status', sa.Enum('pending', 'processing_script', 'generating_narration', 'generating_images', 'rendering_video', 'completed', 'failed', name='videostatusenum'), nullable=False),
        sa.Column('progress', sa.Float(), nullable=True),
        sa.Column('current_step', sa.String(length=200), nullable=True),
        sa.Column('video_path', sa.String(length=500), nullable=True),
        sa.Column('thumbnail_path', sa.String(length=500), nullable=True),
        sa.Column('duration_seconds', sa.Float(), nullable=True),
        sa.Column('narration_cost', sa.Float(), nullable=True),
        sa.Column('image_cost', sa.Float(), nullable=True),
        sa.Column('rendering_cost', sa.Float(), nullable=True),
        sa.Column('total_cost', sa.Float(), nullable=True),
        sa.Column('script_data', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('warnings', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('workflow_id', sa.String(length=100), nullable=True),
        sa.Column('workflow_run_id', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('processing_time_seconds', sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_videos_created_at'), 'videos', ['created_at'], unique=False)
    op.create_index(op.f('ix_videos_status'), 'videos', ['status'], unique=False)
    op.create_index(op.f('ix_videos_user_id'), 'videos', ['user_id'], unique=False)
    op.create_index(op.f('ix_videos_workflow_id'), 'videos', ['workflow_id'], unique=False)

    # Create assets table
    op.create_table('assets',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('video_id', sa.String(length=36), nullable=False),
        sa.Column('asset_type', sa.String(length=50), nullable=False),
        sa.Column('file_path', sa.String(length=500), nullable=False),
        sa.Column('file_size_bytes', sa.Integer(), nullable=True),
        sa.Column('mime_type', sa.String(length=100), nullable=True),
        sa.Column('scene_id', sa.String(length=100), nullable=True),
        sa.Column('provider', sa.String(length=50), nullable=True),
        sa.Column('generation_time_seconds', sa.Float(), nullable=True),
        sa.Column('cost', sa.Float(), nullable=True),
        sa.Column('cache_key', sa.String(length=64), nullable=True),
        sa.Column('was_cached', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['video_id'], ['videos.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_assets_cache_key'), 'assets', ['cache_key'], unique=False)
    op.create_index(op.f('ix_assets_video_id'), 'assets', ['video_id'], unique=False)

    # Create video_metrics table
    op.create_table('video_metrics',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('video_id', sa.String(length=36), nullable=False),
        sa.Column('script_processing_time', sa.Float(), nullable=True),
        sa.Column('narration_generation_time', sa.Float(), nullable=True),
        sa.Column('image_generation_time', sa.Float(), nullable=True),
        sa.Column('video_rendering_time', sa.Float(), nullable=True),
        sa.Column('total_time', sa.Float(), nullable=True),
        sa.Column('scenes_generated', sa.Integer(), nullable=True),
        sa.Column('images_generated', sa.Integer(), nullable=True),
        sa.Column('audio_clips_generated', sa.Integer(), nullable=True),
        sa.Column('cache_hits', sa.Integer(), nullable=True),
        sa.Column('cache_misses', sa.Integer(), nullable=True),
        sa.Column('cache_hit_rate', sa.Float(), nullable=True),
        sa.Column('average_image_quality_score', sa.Float(), nullable=True),
        sa.Column('narration_wpm', sa.Float(), nullable=True),
        sa.Column('cost_per_second', sa.Float(), nullable=True),
        sa.Column('cost_per_scene', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['video_id'], ['videos.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_video_metrics_video_id'), 'video_metrics', ['video_id'], unique=True)

    # Create usage_logs table
    op.create_table('usage_logs',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('date', sa.DateTime(), nullable=False),
        sa.Column('videos_generated', sa.Integer(), nullable=True),
        sa.Column('total_cost', sa.Float(), nullable=True),
        sa.Column('total_duration_seconds', sa.Float(), nullable=True),
        sa.Column('narration_cost', sa.Float(), nullable=True),
        sa.Column('image_cost', sa.Float(), nullable=True),
        sa.Column('rendering_cost', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_usage_logs_date'), 'usage_logs', ['date'], unique=False)
    op.create_index(op.f('ix_usage_logs_user_id'), 'usage_logs', ['user_id'], unique=False)

    # Create api_keys table
    op.create_table('api_keys',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('key', sa.String(length=64), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=True),
        sa.Column('scopes', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('rate_limit_per_hour', sa.Integer(), nullable=True),
        sa.Column('rate_limit_per_day', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('last_used_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_api_keys_key'), 'api_keys', ['key'], unique=True)
    op.create_index(op.f('ix_api_keys_user_id'), 'api_keys', ['user_id'], unique=False)


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_index(op.f('ix_api_keys_user_id'), table_name='api_keys')
    op.drop_index(op.f('ix_api_keys_key'), table_name='api_keys')
    op.drop_table('api_keys')

    op.drop_index(op.f('ix_usage_logs_user_id'), table_name='usage_logs')
    op.drop_index(op.f('ix_usage_logs_date'), table_name='usage_logs')
    op.drop_table('usage_logs')

    op.drop_index(op.f('ix_video_metrics_video_id'), table_name='video_metrics')
    op.drop_table('video_metrics')

    op.drop_index(op.f('ix_assets_video_id'), table_name='assets')
    op.drop_index(op.f('ix_assets_cache_key'), table_name='assets')
    op.drop_table('assets')

    op.drop_index(op.f('ix_videos_workflow_id'), table_name='videos')
    op.drop_index(op.f('ix_videos_user_id'), table_name='videos')
    op.drop_index(op.f('ix_videos_status'), table_name='videos')
    op.drop_index(op.f('ix_videos_created_at'), table_name='videos')
    op.drop_table('videos')

    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_index(op.f('ix_users_api_key'), table_name='users')
    op.drop_table('users')

    # Drop enums
    sa.Enum(name='videostatusenum').drop(op.get_bind(), checkfirst=True)
