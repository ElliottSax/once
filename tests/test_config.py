"""
Tests for configuration management
"""

import pytest
import os
from unittest.mock import patch
from config.settings import Settings, get_settings


class TestSettings:
    """Test configuration loading and validation"""

    def test_settings_with_mock_env(self, monkeypatch):
        """Test that settings can be created with mocked environment"""
        # Set required environment variables
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
        monkeypatch.setenv("REPLICATE_API_TOKEN", "r8-test-token")
        monkeypatch.setenv("ELEVENLABS_API_KEY", "test-key")
        monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test-access-key")
        monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test-secret-key")
        monkeypatch.setenv("AWS_S3_BUCKET_ASSETS", "test-assets")
        monkeypatch.setenv("AWS_S3_BUCKET_VIDEOS", "test-videos")
        monkeypatch.setenv("AWS_S3_BUCKET_CACHE", "test-cache")
        monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

        # Create settings instance
        settings = Settings()

        assert settings.openai_api_key == "sk-test-key"
        assert settings.environment == "development"  # default
        assert settings.aws_region == "us-east-1"  # default

    def test_environment_detection(self, monkeypatch):
        """Test environment detection methods"""
        # Set up minimal required env vars
        self._set_minimal_env(monkeypatch)

        # Test development environment
        monkeypatch.setenv("ENVIRONMENT", "development")
        settings = Settings()
        assert settings.is_development is True
        assert settings.is_production is False

    def test_production_environment(self, monkeypatch):
        """Test production environment detection"""
        self._set_minimal_env(monkeypatch)
        monkeypatch.setenv("ENVIRONMENT", "production")

        settings = Settings()
        assert settings.is_production is True
        assert settings.is_development is False

    def test_cost_limits_are_positive(self, monkeypatch):
        """Test that cost limits are positive values"""
        self._set_minimal_env(monkeypatch)

        settings = Settings()
        assert settings.max_cost_per_video > 0
        assert settings.daily_budget_limit > 0

    def test_lambda_rendering_detection(self, monkeypatch):
        """Test Lambda rendering configuration detection"""
        self._set_minimal_env(monkeypatch)

        # Without Lambda config
        settings = Settings()
        assert settings.use_lambda_rendering is False

        # With Lambda config
        monkeypatch.setenv("REMOTION_LAMBDA_FUNCTION_NAME", "test-function")
        monkeypatch.setenv("REMOTION_BUNDLE_URL", "https://test.com/bundle")
        settings = Settings()
        assert settings.use_lambda_rendering is True

    def _set_minimal_env(self, monkeypatch):
        """Helper to set minimal required environment variables"""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        monkeypatch.setenv("REPLICATE_API_TOKEN", "r8-test")
        monkeypatch.setenv("ELEVENLABS_API_KEY", "test")
        monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
        monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test")
        monkeypatch.setenv("AWS_S3_BUCKET_ASSETS", "test")
        monkeypatch.setenv("AWS_S3_BUCKET_VIDEOS", "test")
        monkeypatch.setenv("AWS_S3_BUCKET_CACHE", "test")
        monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/test")


class TestAPIConfiguration:
    """Test API configuration validation"""

    def test_optional_youtube_credentials(self, monkeypatch):
        """Test that YouTube credentials are optional"""
        self._set_minimal_env(monkeypatch)

        settings = Settings()
        assert settings.youtube_api_key is None
        assert settings.youtube_client_id is None

    def test_default_values(self, monkeypatch):
        """Test default configuration values"""
        self._set_minimal_env(monkeypatch)

        settings = Settings()
        assert settings.aws_region == "us-east-1"
        assert settings.redis_url == "redis://localhost:6379"
        assert settings.log_level == "INFO"
        assert settings.max_concurrent_generations == 5
        assert settings.cache_enabled is True

    def _set_minimal_env(self, monkeypatch):
        """Helper to set minimal required environment variables"""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        monkeypatch.setenv("REPLICATE_API_TOKEN", "r8-test")
        monkeypatch.setenv("ELEVENLABS_API_KEY", "test")
        monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
        monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test")
        monkeypatch.setenv("AWS_S3_BUCKET_ASSETS", "test")
        monkeypatch.setenv("AWS_S3_BUCKET_VIDEOS", "test")
        monkeypatch.setenv("AWS_S3_BUCKET_CACHE", "test")
        monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/test")


class TestGetSettingsFunction:
    """Test the get_settings lazy loading function"""

    def test_get_settings_lazy_load(self, monkeypatch):
        """Test that get_settings returns a settings instance"""
        self._set_minimal_env(monkeypatch)

        settings = get_settings()
        assert isinstance(settings, Settings)

        # Should return same instance on subsequent calls
        settings2 = get_settings()
        assert settings is settings2

    def _set_minimal_env(self, monkeypatch):
        """Helper to set minimal required environment variables"""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        monkeypatch.setenv("REPLICATE_API_TOKEN", "r8-test")
        monkeypatch.setenv("ELEVENLABS_API_KEY", "test")
        monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
        monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test")
        monkeypatch.setenv("AWS_S3_BUCKET_ASSETS", "test")
        monkeypatch.setenv("AWS_S3_BUCKET_VIDEOS", "test")
        monkeypatch.setenv("AWS_S3_BUCKET_CACHE", "test")
        monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/test")


# Sample pytest fixture for future tests
@pytest.fixture
def mock_settings():
    """Provide mock settings for testing"""
    return {
        'openai_api_key': 'sk-test-key',
        'environment': 'test',
        'max_cost_per_video': 20.0,
    }
