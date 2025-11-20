"""
Tests for configuration management.
"""

import pytest
from atlasui.config import Settings


def test_settings_defaults():
    """Test default settings."""
    settings = Settings(
        atlas_public_key="test_public",
        atlas_private_key="test_private"
    )
    assert settings.atlas_base_url == "https://cloud.mongodb.com"
    assert settings.atlas_api_version == "v2"
    assert settings.app_name == "AtlasUI"
    assert settings.port == 8000


def test_atlas_api_base_url():
    """Test Atlas API base URL property."""
    settings = Settings(
        atlas_public_key="test_public",
        atlas_private_key="test_private",
        atlas_base_url="https://custom.mongodb.com",
        atlas_api_version="v3"
    )
    assert settings.atlas_api_base_url == "https://custom.mongodb.com/api/atlas/v3"
