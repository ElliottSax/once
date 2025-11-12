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
        sa.Column('api_key', sa.String(length=64), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('daily_budget_limit', sa.Float(), nullable=True),
        sa.Column('monthly_budget_limit', sa.Float(), nullable=True),
        sa.Column('total_videos_generated', sa.Integer(), nullable=True),
        sa.Column('total_cost', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_api_key'), 'users', ['api_key'], unique=True)
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)

    # Create videos table
    op.create_table('videos',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=True),
        sa.Column('topic', sa.String(length=500), nullable=True),
        sa.Column('raw_script', sa.Text(), nullable=True),
        sa.Column('status', sa.Enum('queued', 'processing', 'completed', 'failed', name='videostatusenum'), nullable=True),
        sa.Column('progress', sa.Float(), nullable=True),
        sa.Column('current_step', sa.String(length=200), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('video_path', sa.String(length=500), nullable=True),
        sa.Column('target_duration', sa.Integer(), nullable=True),
        sa.Column('actual_duration', sa.Float(), nullable=True),
        sa.Column('quality', sa.String(length=50), nullable=True),
        sa.Column('image_provider', sa.String(length=50), nullable=True),
        sa.Column('voice_provider', sa.String(length=50), nullable=True),
        sa.Column('narration_cost', sa.Float(), nullable=True),
        sa.Column('image_generation_cost', sa.Float(), nullable=True),
        sa.Column('rendering_cost', sa.Float(), nullable=True),
        sa.Column('total_cost', sa.Float(), nullable=True),
        sa.Column('script_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_videos_id'), 'videos', ['id'], unique=False)
    op.create_index(op.f('ix_videos_status'), 'videos', ['status'], unique=False)
    op.create_index(op.f('ix_videos_user_id'), 'videos', ['user_id'], unique=False)

    # Create assets table
    op.create_table('assets',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('video_id', sa.String(length=36), nullable=True),
        sa.Column('asset_type', sa.Enum('image', 'audio', 'video', 'data', name='assettypeenum'), nullable=True),
        sa.Column('file_path', sa.String(length=500), nullable=True),
        sa.Column('s3_url', sa.String(length=500), nullable=True),
        sa.Column('file_size_bytes', sa.Integer(), nullable=True),
        sa.Column('duration_seconds', sa.Float(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('cache_key', sa.String(length=128), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['video_id'], ['videos.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_assets_cache_key'), 'assets', ['cache_key'], unique=False)
    op.create_index(op.f('ix_assets_id'), 'assets', ['id'], unique=False)
    op.create_index(op.f('ix_assets_video_id'), 'assets', ['video_id'], unique=False)

    # Create video_metrics table
    op.create_table('video_metrics',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('video_id', sa.String(length=36), nullable=True),
        sa.Column('script_processing_time', sa.Float(), nullable=True),
        sa.Column('narration_generation_time', sa.Float(), nullable=True),
        sa.Column('image_generation_time', sa.Float(), nullable=True),
        sa.Column('video_rendering_time', sa.Float(), nullable=True),
        sa.Column('total_processing_time', sa.Float(), nullable=True),
        sa.Column('num_scenes', sa.Integer(), nullable=True),
        sa.Column('num_images_generated', sa.Integer(), nullable=True),
        sa.Column('num_retries', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['video_id'], ['videos.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_video_metrics_id'), 'video_metrics', ['id'], unique=False)
    op.create_index(op.f('ix_video_metrics_video_id'), 'video_metrics', ['video_id'], unique=True)

    # Create usage_logs table
    op.create_table('usage_logs',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=True),
        sa.Column('date', sa.Date(), nullable=True),
        sa.Column('videos_generated', sa.Integer(), nullable=True),
        sa.Column('total_cost', sa.Float(), nullable=True),
        sa.Column('total_duration', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_usage_logs_date'), 'usage_logs', ['date'], unique=False)
    op.create_index(op.f('ix_usage_logs_id'), 'usage_logs', ['id'], unique=False)
    op.create_index('ix_user_date', 'usage_logs', ['user_id', 'date'], unique=True)

    # Create api_keys table
    op.create_table('api_keys',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=True),
        sa.Column('key_hash', sa.String(length=128), nullable=False),
        sa.Column('key_prefix', sa.String(length=16), nullable=True),
        sa.Column('name', sa.String(length=100), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('last_used_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_api_keys_id'), 'api_keys', ['id'], unique=False)
    op.create_index(op.f('ix_api_keys_key_hash'), 'api_keys', ['key_hash'], unique=True)


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_index(op.f('ix_api_keys_key_hash'), table_name='api_keys')
    op.drop_index(op.f('ix_api_keys_id'), table_name='api_keys')
    op.drop_table('api_keys')

    op.drop_index('ix_user_date', table_name='usage_logs')
    op.drop_index(op.f('ix_usage_logs_id'), table_name='usage_logs')
    op.drop_index(op.f('ix_usage_logs_date'), table_name='usage_logs')
    op.drop_table('usage_logs')

    op.drop_index(op.f('ix_video_metrics_video_id'), table_name='video_metrics')
    op.drop_index(op.f('ix_video_metrics_id'), table_name='video_metrics')
    op.drop_table('video_metrics')

    op.drop_index(op.f('ix_assets_video_id'), table_name='assets')
    op.drop_index(op.f('ix_assets_id'), table_name='assets')
    op.drop_index(op.f('ix_assets_cache_key'), table_name='assets')
    op.drop_table('assets')

    op.drop_index(op.f('ix_videos_user_id'), table_name='videos')
    op.drop_index(op.f('ix_videos_status'), table_name='videos')
    op.drop_index(op.f('ix_videos_id'), table_name='videos')
    op.drop_table('videos')

    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_index(op.f('ix_users_api_key'), table_name='users')
    op.drop_table('users')

    # Drop enums
    sa.Enum(name='videostatusenum').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='assettypeenum').drop(op.get_bind(), checkfirst=True)
