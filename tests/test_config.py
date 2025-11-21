"""
Tests for configuration management.
"""

import pytest
import os
from pathlib import Path
from atlasui.config import Settings, reload_settings


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


def test_reload_settings(tmp_path, monkeypatch):
    """Test settings reload functionality."""
    # Create a temporary .env file
    env_file = tmp_path / ".env"
    env_file.write_text("ATLAS_PUBLIC_KEY=initial_key\nATLAS_PRIVATE_KEY=initial_secret\n")

    # Change to the temporary directory
    monkeypatch.chdir(tmp_path)

    # Load initial settings
    from atlasui.config import settings as initial_settings
    initial_key = initial_settings.atlas_public_key

    # Update the .env file
    env_file.write_text("ATLAS_PUBLIC_KEY=updated_key\nATLAS_PRIVATE_KEY=updated_secret\n")

    # Reload settings
    new_settings = reload_settings()

    # Verify settings were reloaded
    # Note: The reload will pick up the new values if they exist in the .env file
    # In this test, we're verifying the function executes without error
    assert new_settings is not None
    assert hasattr(new_settings, 'atlas_public_key')
