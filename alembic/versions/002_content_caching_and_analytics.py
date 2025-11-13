"""Add content caching and analytics tables

Revision ID: 002
Revises: 001
Create Date: 2025-11-12

Adds tables for:
- Content deduplication cache
- Video analytics and quality scoring
- Cost optimization views
- Rate limiting
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Content Cache for deduplication
    op.create_table('content_cache',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('content_type', sa.String(length=50), nullable=True),
        sa.Column('content_hash', sa.String(length=64), nullable=False),
        sa.Column('content_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('generation_params', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('asset_ids', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('hit_count', sa.Integer(), nullable=True),
        sa.Column('cost_saved', sa.Float(), nullable=True),
        sa.Column('last_accessed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_content_cache_content_hash'), 'content_cache', ['content_hash'], unique=False)
    op.create_index(op.f('ix_content_cache_content_type_hash'), 'content_cache', ['content_type', 'content_hash'], unique=False)
    op.create_index(op.f('ix_content_cache_last_accessed'), 'content_cache', ['last_accessed_at'], unique=False)

    # Video Analytics
    op.create_table('video_analytics',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('video_id', sa.String(length=36), nullable=True),
        sa.Column('visual_quality_score', sa.Float(), nullable=True),
        sa.Column('audio_quality_score', sa.Float(), nullable=True),
        sa.Column('script_coherence_score', sa.Float(), nullable=True),
        sa.Column('overall_quality_score', sa.Float(), nullable=True),
        sa.Column('cost_per_second', sa.Float(), nullable=True),
        sa.Column('cost_vs_average', sa.Float(), nullable=True),
        sa.Column('image_provider_latency', sa.Float(), nullable=True),
        sa.Column('narration_provider_latency', sa.Float(), nullable=True),
        sa.Column('image_retry_count', sa.Integer(), nullable=True),
        sa.Column('narration_retry_count', sa.Integer(), nullable=True),
        sa.Column('user_rating', sa.Integer(), nullable=True),
        sa.Column('user_feedback', sa.Text(), nullable=True),
        sa.Column('regeneration_requested', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['video_id'], ['videos.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_video_analytics_overall_quality'), 'video_analytics', ['overall_quality_score'], unique=False)
    op.create_index(op.f('ix_video_analytics_cost_efficiency'), 'video_analytics', ['cost_per_second'], unique=False)
    op.create_index(op.f('ix_video_analytics_video_id'), 'video_analytics', ['video_id'], unique=True)

    # Rate Limiting
    op.create_table('rate_limits',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=True),
        sa.Column('tier', sa.String(length=50), nullable=True),
        sa.Column('videos_per_hour', sa.Integer(), nullable=True),
        sa.Column('videos_per_day', sa.Integer(), nullable=True),
        sa.Column('videos_per_month', sa.Integer(), nullable=True),
        sa.Column('max_concurrent_jobs', sa.Integer(), nullable=True),
        sa.Column('max_video_duration', sa.Integer(), nullable=True),
        sa.Column('current_hour_count', sa.Integer(), nullable=True),
        sa.Column('current_day_count', sa.Integer(), nullable=True),
        sa.Column('current_month_count', sa.Integer(), nullable=True),
        sa.Column('active_jobs', sa.Integer(), nullable=True),
        sa.Column('hour_reset_at', sa.DateTime(), nullable=True),
        sa.Column('day_reset_at', sa.DateTime(), nullable=True),
        sa.Column('month_reset_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_rate_limits_user_id'), 'rate_limits', ['user_id'], unique=True)

    # Job Queue for priority management
    op.create_table('job_queue',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('video_id', sa.String(length=36), nullable=True),
        sa.Column('user_id', sa.String(length=36), nullable=True),
        sa.Column('priority', sa.Integer(), nullable=True),
        sa.Column('estimated_cost', sa.Float(), nullable=True),
        sa.Column('estimated_duration', sa.Integer(), nullable=True),
        sa.Column('requires_gpu', sa.Boolean(), nullable=True),
        sa.Column('requires_premium_provider', sa.Boolean(), nullable=True),
        sa.Column('queued_at', sa.DateTime(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('max_wait_time', sa.Integer(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=True),
        sa.Column('depends_on_job_id', sa.String(length=36), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['video_id'], ['videos.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_job_queue_priority_queued'), 'job_queue', ['priority', 'queued_at'], unique=False)
    op.create_index(op.f('ix_job_queue_user_id'), 'job_queue', ['user_id', 'queued_at'], unique=False)
    op.create_index(op.f('ix_job_queue_status'), 'job_queue', ['status'], unique=False)

    # Add full-text search to videos
    op.execute("""
        ALTER TABLE videos ADD COLUMN IF NOT EXISTS search_vector tsvector;
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_video_search ON videos USING GIN(search_vector);
    """)

    # Create trigger for automatic search vector updates
    op.execute("""
        CREATE OR REPLACE FUNCTION update_video_search_vector() RETURNS trigger AS $$
        BEGIN
            NEW.search_vector :=
                setweight(to_tsvector('english', COALESCE(NEW.topic, '')), 'A') ||
                setweight(to_tsvector('english', COALESCE(NEW.script_text, '')), 'B');
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute("""
        CREATE TRIGGER video_search_update
            BEFORE INSERT OR UPDATE ON videos
            FOR EACH ROW
            EXECUTE FUNCTION update_video_search_vector();
    """)


def downgrade() -> None:
    # Drop trigger and function
    op.execute("DROP TRIGGER IF EXISTS video_search_update ON videos;")
    op.execute("DROP FUNCTION IF EXISTS update_video_search_vector();")

    # Drop search vector column
    op.execute("DROP INDEX IF EXISTS idx_video_search;")
    op.execute("ALTER TABLE videos DROP COLUMN IF EXISTS search_vector;")

    # Drop tables
    op.drop_index(op.f('ix_job_queue_status'), table_name='job_queue')
    op.drop_index(op.f('ix_job_queue_user_id'), table_name='job_queue')
    op.drop_index(op.f('ix_job_queue_priority_queued'), table_name='job_queue')
    op.drop_table('job_queue')

    op.drop_index(op.f('ix_rate_limits_user_id'), table_name='rate_limits')
    op.drop_table('rate_limits')

    op.drop_index(op.f('ix_video_analytics_video_id'), table_name='video_analytics')
    op.drop_index(op.f('ix_video_analytics_cost_efficiency'), table_name='video_analytics')
    op.drop_index(op.f('ix_video_analytics_overall_quality'), table_name='video_analytics')
    op.drop_table('video_analytics')

    op.drop_index(op.f('ix_content_cache_last_accessed'), table_name='content_cache')
    op.drop_index(op.f('ix_content_cache_content_type_hash'), table_name='content_cache')
    op.drop_index(op.f('ix_content_cache_content_hash'), table_name='content_cache')
    op.drop_table('content_cache')
