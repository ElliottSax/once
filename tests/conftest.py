"""
Pytest configuration and fixtures
"""

import pytest
import os
from typing import Dict


@pytest.fixture(autouse=True)
def clear_settings_cache():
    """Clear settings cache before each test"""
    from config import settings
    settings._settings_instance = None
    yield
    settings._settings_instance = None


@pytest.fixture
def minimal_env_vars(monkeypatch) -> Dict[str, str]:
    """Set minimal required environment variables for testing"""
    env_vars = {
        "OPENAI_API_KEY": "sk-test-key",
        "REPLICATE_API_TOKEN": "r8-test-token",
        "ELEVENLABS_API_KEY": "test-key",
        "AWS_ACCESS_KEY_ID": "test-access-key",
        "AWS_SECRET_ACCESS_KEY": "test-secret-key",
        "AWS_S3_BUCKET_ASSETS": "test-assets",
        "AWS_S3_BUCKET_VIDEOS": "test-videos",
        "AWS_S3_BUCKET_CACHE": "test-cache",
        "DATABASE_URL": "postgresql://test:test@localhost:5432/test",
    }

    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)

    return env_vars
