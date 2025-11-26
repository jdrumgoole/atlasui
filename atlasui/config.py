"""
Configuration management for AtlasUI using Pydantic Settings.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
from pathlib import Path

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:
    import tomli as tomllib  # Python 3.10


def _get_version() -> str:
    """Read version from pyproject.toml."""
    try:
        pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
        with open(pyproject_path, "rb") as f:
            pyproject = tomllib.load(f)
            return pyproject.get("project", {}).get("version", "0.0.0")
    except Exception:
        # Fallback version if reading fails
        return "0.0.0"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # MongoDB Atlas API Configuration - API Keys (Legacy)
    atlas_public_key: Optional[str] = None
    atlas_private_key: Optional[str] = None

    # MongoDB Atlas API Configuration - Service Account (Recommended)
    atlas_service_account_id: Optional[str] = None
    atlas_service_account_secret: Optional[str] = None
    atlas_service_account_credentials_file: Optional[str] = None

    # Common Atlas Configuration
    atlas_base_url: str = "https://cloud.mongodb.com"
    atlas_api_version: str = "v2"
    atlas_auth_method: str = "api_key"  # "api_key" or "service_account"

    # Application Configuration
    app_name: str = "AtlasUI"
    app_version: str = _get_version()
    debug: bool = False

    # Web Server Configuration
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = False

    # API Client Configuration
    timeout: int = 30
    max_retries: int = 3

    # User Preferences
    preferred_cloud_provider: Optional[str] = None  # AWS, GCP, AZURE
    preferred_region: Optional[str] = None  # e.g., US_EAST_1, EU_WEST_1

    @property
    def atlas_api_base_url(self) -> str:
        """Get the full Atlas API base URL."""
        return f"{self.atlas_base_url}/api/atlas/{self.atlas_api_version}"

    def validate_credentials(self) -> None:
        """
        Validate that appropriate credentials are configured.

        Raises:
            ValueError: If credentials are not properly configured
        """
        if self.atlas_auth_method == "api_key":
            if not self.atlas_public_key or not self.atlas_private_key:
                raise ValueError(
                    "API key authentication requires both "
                    "ATLAS_PUBLIC_KEY and ATLAS_PRIVATE_KEY to be set"
                )
        elif self.atlas_auth_method == "service_account":
            # Check for credentials file first
            if self.atlas_service_account_credentials_file:
                return
            # Otherwise check for individual credentials
            if not self.atlas_service_account_id or not self.atlas_service_account_secret:
                raise ValueError(
                    "Service account authentication requires either "
                    "ATLAS_SERVICE_ACCOUNT_CREDENTIALS_FILE or both "
                    "ATLAS_SERVICE_ACCOUNT_ID and ATLAS_SERVICE_ACCOUNT_SECRET"
                )
        else:
            raise ValueError(
                f"Invalid auth method: {self.atlas_auth_method}. "
                "Must be 'api_key' or 'service_account'"
            )


# Global settings instance
settings = Settings()


def reload_settings() -> Settings:
    """
    Reload settings from environment and .env file.

    This is useful when the .env file is updated at runtime (e.g., via web configuration).

    Returns:
        New Settings instance with reloaded values
    """
    global settings
    # Force Pydantic to reload by creating a new instance
    # This will re-read the .env file
    settings = Settings()
    return settings
