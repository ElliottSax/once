"""
Content caching layer for deduplication and cost savings.

This module implements intelligent caching of generated content to avoid
regenerating identical or similar content. Can save 30-50% on generation costs.
"""

import hashlib
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from loguru import logger

from src.database.models import ContentCache


class ContentCacheService:
    """Service for caching and retrieving generated content."""

    def __init__(self, db: Session):
        self.db = db

    def _compute_hash(self, content: str, params: Optional[Dict] = None) -> str:
        """Compute SHA256 hash of content + parameters."""
        hash_input = content
        if params:
            # Sort params for consistent hashing
            hash_input += json.dumps(params, sort_keys=True)

        return hashlib.sha256(hash_input.encode()).hexdigest()

    def _normalize_content(self, content: str) -> str:
        """Normalize content for better cache hits."""
        # Remove extra whitespace
        content = ' '.join(content.split())
        # Lowercase for case-insensitive matching
        content = content.lower()
        # Remove common punctuation variations
        content = content.replace('!', '.').replace('?', '.')
        return content.strip()

    async def check_cache(
        self,
        content_type: str,
        content: str,
        params: Optional[Dict] = None,
        max_age_days: int = 90
    ) -> Optional[Dict[str, Any]]:
        """
        Check if content exists in cache.

        Args:
            content_type: Type of content ('script_segment', 'visual_concept', etc.)
            content: The content to check
            params: Generation parameters
            max_age_days: Maximum age of cached content in days

        Returns:
            Cached data if found, None otherwise
        """
        normalized_content = self._normalize_content(content)
        content_hash = self._compute_hash(normalized_content, params)

        # Query cache
        min_date = datetime.utcnow() - timedelta(days=max_age_days)

        cache_entry = self.db.query(ContentCache).filter(
            and_(
                ContentCache.content_type == content_type,
                ContentCache.content_hash == content_hash,
                ContentCache.created_at >= min_date
            )
        ).first()

        if cache_entry:
            # Update hit count and last accessed
            cache_entry.hit_count += 1
            cache_entry.last_accessed_at = datetime.utcnow()
            self.db.commit()

            logger.info(
                f"Cache HIT for {content_type}: {content_hash[:8]}... "
                f"(hits: {cache_entry.hit_count})"
            )

            return {
                'id': cache_entry.id,
                'content_data': cache_entry.content_data,
                'asset_ids': cache_entry.asset_ids,
                'hit_count': cache_entry.hit_count,
                'cost_saved': cache_entry.cost_saved or 0.0
            }

        logger.debug(f"Cache MISS for {content_type}: {content_hash[:8]}...")
        return None

    async def store_cache(
        self,
        content_type: str,
        content: str,
        content_data: Dict,
        params: Optional[Dict] = None,
        asset_ids: Optional[List[str]] = None,
        generation_cost: float = 0.0
    ) -> str:
        """
        Store content in cache.

        Args:
            content_type: Type of content
            content: The original content
            content_data: Generated data to cache
            params: Generation parameters
            asset_ids: Related asset IDs
            generation_cost: Cost to generate this content

        Returns:
            Cache entry ID
        """
        normalized_content = self._normalize_content(content)
        content_hash = self._compute_hash(normalized_content, params)

        # Check if already exists
        existing = self.db.query(ContentCache).filter(
            and_(
                ContentCache.content_type == content_type,
                ContentCache.content_hash == content_hash
            )
        ).first()

        if existing:
            # Update existing entry
            existing.content_data = content_data
            existing.generation_params = params
            existing.asset_ids = asset_ids
            existing.last_accessed_at = datetime.utcnow()
            self.db.commit()
            logger.info(f"Updated cache entry for {content_type}: {content_hash[:8]}...")
            return existing.id

        # Create new cache entry
        cache_entry = ContentCache(
            content_type=content_type,
            content_hash=content_hash,
            content_data=content_data,
            generation_params=params,
            asset_ids=asset_ids or [],
            hit_count=0,
            cost_saved=generation_cost,  # Will accumulate with each hit
            last_accessed_at=datetime.utcnow(),
            created_at=datetime.utcnow()
        )

        self.db.add(cache_entry)
        self.db.commit()

        logger.info(f"Stored cache entry for {content_type}: {content_hash[:8]}...")
        return cache_entry.id

    async def get_cache_stats(self, days: int = 30) -> Dict[str, Any]:
        """
        Get cache performance statistics.

        Args:
            days: Number of days to analyze

        Returns:
            Cache statistics
        """
        min_date = datetime.utcnow() - timedelta(days=days)

        # Total cache entries
        total_entries = self.db.query(ContentCache).filter(
            ContentCache.created_at >= min_date
        ).count()

        # Total hits
        from sqlalchemy import func
        total_hits = self.db.query(
            func.sum(ContentCache.hit_count)
        ).filter(
            ContentCache.last_accessed_at >= min_date
        ).scalar() or 0

        # Total cost saved
        total_cost_saved = self.db.query(
            func.sum(ContentCache.cost_saved * ContentCache.hit_count)
        ).filter(
            ContentCache.last_accessed_at >= min_date
        ).scalar() or 0.0

        # Most popular entries
        popular_entries = self.db.query(
            ContentCache.content_type,
            func.count(ContentCache.id).label('count'),
            func.sum(ContentCache.hit_count).label('total_hits')
        ).filter(
            ContentCache.created_at >= min_date
        ).group_by(
            ContentCache.content_type
        ).all()

        return {
            'period_days': days,
            'total_entries': total_entries,
            'total_hits': int(total_hits),
            'total_cost_saved': round(total_cost_saved, 2),
            'avg_hits_per_entry': round(total_hits / total_entries, 2) if total_entries > 0 else 0,
            'by_content_type': [
                {
                    'content_type': ct,
                    'entry_count': count,
                    'total_hits': int(hits)
                }
                for ct, count, hits in popular_entries
            ]
        }

    async def cleanup_old_cache(self, days: int = 180) -> int:
        """
        Remove old, unused cache entries.

        Args:
            days: Remove entries older than this many days

        Returns:
            Number of entries removed
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        # Delete entries not accessed recently with low hit count
        deleted = self.db.query(ContentCache).filter(
            or_(
                ContentCache.last_accessed_at < cutoff_date,
                and_(
                    ContentCache.hit_count == 0,
                    ContentCache.created_at < cutoff_date
                )
            )
        ).delete()

        self.db.commit()

        logger.info(f"Cleaned up {deleted} old cache entries")
        return deleted


class ScriptCacheService:
    """Specialized caching for script segments."""

    def __init__(self, cache_service: ContentCacheService):
        self.cache = cache_service

    async def cache_script_segment(
        self,
        prompt: str,
        generated_script: str,
        metadata: Dict
    ) -> str:
        """Cache a generated script segment."""
        return await self.cache.store_cache(
            content_type='script_segment',
            content=prompt,
            content_data={
                'script': generated_script,
                'metadata': metadata
            },
            params={'model': metadata.get('model'), 'temperature': metadata.get('temperature')},
            generation_cost=metadata.get('cost', 0.0)
        )

    async def get_cached_script(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: Optional[float] = None
    ) -> Optional[str]:
        """Retrieve cached script for a prompt."""
        params = {}
        if model:
            params['model'] = model
        if temperature is not None:
            params['temperature'] = temperature

        cached = await self.cache.check_cache(
            content_type='script_segment',
            content=prompt,
            params=params if params else None
        )

        if cached:
            return cached['content_data']['script']
        return None


class ImagePromptCacheService:
    """Specialized caching for image generation prompts."""

    def __init__(self, cache_service: ContentCacheService):
        self.cache = cache_service

    async def cache_image_prompt(
        self,
        prompt: str,
        image_url: str,
        asset_id: str,
        provider: str,
        cost: float
    ) -> str:
        """Cache a generated image prompt."""
        return await self.cache.store_cache(
            content_type='visual_concept',
            content=prompt,
            content_data={
                'image_url': image_url,
                'provider': provider
            },
            params={'provider': provider},
            asset_ids=[asset_id],
            generation_cost=cost
        )

    async def get_cached_image(
        self,
        prompt: str,
        provider: Optional[str] = None
    ) -> Optional[Dict]:
        """Retrieve cached image for a prompt."""
        params = {'provider': provider} if provider else None

        cached = await self.cache.check_cache(
            content_type='visual_concept',
            content=prompt,
            params=params
        )

        if cached:
            return {
                'image_url': cached['content_data']['image_url'],
                'asset_id': cached['asset_ids'][0] if cached['asset_ids'] else None,
                'cache_hit': True,
                'cost_saved': cached.get('cost_saved', 0.0)
            }
        return None


# Example usage in video generation pipeline:
"""
# In video_generator.py

from src.database.caching import ContentCacheService, ImagePromptCacheService

# Initialize
cache_service = ContentCacheService(db_session)
image_cache = ImagePromptCacheService(cache_service)

# Before generating an image
cached_image = await image_cache.get_cached_image(
    prompt="A modern office with people working on computers",
    provider="replicate"
)

if cached_image:
    # Use cached image - saves API call and cost
    logger.info(f"Using cached image, saved ${cached_image['cost_saved']:.2f}")
    return cached_image['image_url']
else:
    # Generate new image
    image_url = await generate_image(prompt)
    await image_cache.cache_image_prompt(
        prompt=prompt,
        image_url=image_url,
        asset_id=asset_id,
        provider="replicate",
        cost=0.50
    )
    return image_url
"""
