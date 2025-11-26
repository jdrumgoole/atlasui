"""
API routes for setup and configuration wizard.
"""

import re
from fastapi import APIRouter, HTTPException, Request
from typing import Dict, Any, Literal
from pydantic import BaseModel, field_validator
from pathlib import Path
from slowapi import Limiter
from slowapi.util import get_remote_address

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


def validate_atlas_public_key(key: str) -> bool:
    """
    Validate Atlas API public key format.
    Atlas public keys are 8 alphanumeric characters.
    """
    if not key:
        return False
    # Public keys are 8 alphanumeric characters
    return bool(re.match(r'^[a-z0-9]{8}$', key, re.IGNORECASE))


def validate_atlas_private_key(key: str) -> bool:
    """
    Validate Atlas API private key format.
    Atlas private keys are UUID-like strings (36 chars with hyphens).
    """
    if not key:
        return False
    # Private keys are typically UUID format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
    return bool(re.match(r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$', key, re.IGNORECASE))


class ConfigCheckResponse(BaseModel):
    """Response for configuration check."""
    configured: bool
    auth_method: str | None = None
    message: str


class ConfigInfoResponse(BaseModel):
    """Response for configuration info."""
    configured: bool
    auth_method: str | None = None
    config_file_path: str | None = None
    public_key_preview: str | None = None
    client_id_preview: str | None = None
    base_url: str
    api_version: str
    message: str
    preferred_cloud_provider: str | None = None
    preferred_region: str | None = None


class APIKeyConfigRequest(BaseModel):
    """Request model for API key configuration."""
    public_key: str
    private_key: str


class ServiceAccountConfigRequest(BaseModel):
    """Request model for service account configuration."""
    client_id: str
    client_secret: str
    project_id: str


class PreferencesRequest(BaseModel):
    """Request model for user preferences."""
    preferred_cloud_provider: str | None = None
    preferred_region: str | None = None


@router.get("/check")
async def check_configuration() -> ConfigCheckResponse:
    """
    Check if AtlasUI is configured.

    Returns:
        Configuration status
    """
    env_path = Path(".env")

    if not env_path.exists():
        return ConfigCheckResponse(
            configured=False,
            auth_method=None,
            message="Configuration file not found. Please complete setup."
        )

    # Read .env and check for Atlas credentials
    try:
        with env_path.open('r') as f:
            content = f.read()

        has_public_key = "ATLAS_PUBLIC_KEY" in content
        has_private_key = "ATLAS_PRIVATE_KEY" in content
        has_service_account = "ATLAS_SERVICE_ACCOUNT" in content

        if has_public_key and has_private_key:
            return ConfigCheckResponse(
                configured=True,
                auth_method="api_key",
                message="Configured with API Keys"
            )
        elif has_service_account:
            return ConfigCheckResponse(
                configured=True,
                auth_method="service_account",
                message="Configured with Service Account"
            )
        else:
            return ConfigCheckResponse(
                configured=False,
                auth_method=None,
                message="Atlas credentials not found. Please complete setup."
            )

    except Exception as e:
        return ConfigCheckResponse(
            configured=False,
            auth_method=None,
            message=f"Error reading configuration: {str(e)}"
        )


@router.get("/info")
async def get_configuration_info() -> ConfigInfoResponse:
    """
    Get detailed configuration information for display.

    Returns:
        Configuration details including auth method, file path, and masked credentials
    """
    from atlasui.config import settings

    env_path = Path(".env")
    config_file_path = str(env_path.absolute()) if env_path.exists() else None

    # Determine auth method and get masked credentials
    auth_method = None
    public_key_preview = None
    client_id_preview = None
    configured = False
    message = "Not configured"

    if settings.atlas_auth_method == "api_key":
        if settings.atlas_public_key and settings.atlas_private_key:
            auth_method = "API Key"
            # Show first 8 chars of public key
            public_key_preview = settings.atlas_public_key[:8] + "..." if len(settings.atlas_public_key) > 8 else settings.atlas_public_key
            configured = True
            message = "Configured with API Keys"
    elif settings.atlas_auth_method == "service_account":
        if settings.atlas_service_account_id and settings.atlas_service_account_secret:
            auth_method = "Service Account"
            # Show first 8 chars of client ID
            client_id_preview = settings.atlas_service_account_id[:8] + "..." if len(settings.atlas_service_account_id) > 8 else settings.atlas_service_account_id
            configured = True
            message = "Configured with Service Account"
        elif settings.atlas_service_account_credentials_file:
            auth_method = "Service Account (Credentials File)"
            client_id_preview = settings.atlas_service_account_credentials_file
            configured = True
            message = "Configured with Service Account credentials file"

    return ConfigInfoResponse(
        configured=configured,
        auth_method=auth_method,
        config_file_path=config_file_path,
        public_key_preview=public_key_preview,
        client_id_preview=client_id_preview,
        base_url=settings.atlas_base_url,
        api_version=settings.atlas_api_version,
        message=message,
        preferred_cloud_provider=settings.preferred_cloud_provider,
        preferred_region=settings.preferred_region
    )


@router.post("/preferences")
async def save_preferences(request: PreferencesRequest) -> Dict[str, Any]:
    """
    Save user preferences for cloud provider and region.

    Args:
        request: Preferences to save

    Returns:
        Result of the operation
    """
    try:
        env_path = Path(".env")

        # Read existing .env if it exists
        existing_lines = []
        if env_path.exists():
            with env_path.open('r') as f:
                existing_lines = f.readlines()

        # Remove old preference settings
        new_lines = []
        for line in existing_lines:
            if not line.startswith('PREFERRED_CLOUD_PROVIDER=') and not line.startswith('PREFERRED_REGION='):
                new_lines.append(line)

        # Add new preference settings
        if request.preferred_cloud_provider:
            new_lines.append(f"PREFERRED_CLOUD_PROVIDER={request.preferred_cloud_provider}\n")
        if request.preferred_region:
            new_lines.append(f"PREFERRED_REGION={request.preferred_region}\n")

        # Write updated .env
        with env_path.open('w') as f:
            f.writelines(new_lines)

        # Reload settings to pick up the new preferences
        from atlasui.config import reload_settings
        reload_settings()

        return {
            "success": True,
            "message": "Preferences saved successfully",
            "preferred_cloud_provider": request.preferred_cloud_provider,
            "preferred_region": request.preferred_region
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save preferences: {str(e)}"
        )


@router.post("/configure/api-key")
@limiter.limit("5/minute")
async def configure_api_key(request: Request, config: APIKeyConfigRequest) -> Dict[str, Any]:
    """
    Configure AtlasUI with API Keys.

    Rate limited to 5 requests per minute to prevent brute force attacks.

    Args:
        request: API key configuration request

    Returns:
        Configuration result
    """
    try:
        # Validate input format
        if not validate_atlas_public_key(config.public_key):
            raise HTTPException(
                status_code=400,
                detail="Invalid public key format. Expected 8 alphanumeric characters."
            )

        if not validate_atlas_private_key(config.private_key):
            raise HTTPException(
                status_code=400,
                detail="Invalid private key format. Expected UUID format (xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx)."
            )

        env_path = Path(".env")

        # Read existing .env if it exists
        existing_lines = []
        if env_path.exists():
            with env_path.open('r') as f:
                existing_lines = f.readlines()

        # Remove old Atlas authentication settings
        new_lines = []
        for line in existing_lines:
            if any(key in line for key in [
                'ATLAS_AUTH_METHOD',
                'ATLAS_PUBLIC_KEY',
                'ATLAS_PRIVATE_KEY',
                'ATLAS_SERVICE_ACCOUNT',
            ]):
                continue
            new_lines.append(line)

        # Add new API key configuration
        config_lines = [
            "\n# MongoDB Atlas API Key Configuration\n",
            "ATLAS_AUTH_METHOD=api_key\n",
            f"ATLAS_PUBLIC_KEY={config.public_key}\n",
            f"ATLAS_PRIVATE_KEY={config.private_key}\n",
            "ATLAS_BASE_URL=https://cloud.mongodb.com\n",
            "ATLAS_API_VERSION=v2\n",
        ]

        # Write updated .env
        with env_path.open('w') as f:
            f.writelines(new_lines)
            f.writelines(config_lines)

        # Set secure permissions
        try:
            env_path.chmod(0o600)
        except Exception:
            pass  # Permissions may not be settable on all systems

        # Reload settings to pick up the new credentials
        from atlasui.config import reload_settings
        reload_settings()

        return {
            "success": True,
            "auth_method": "api_key",
            "message": "API Keys configured successfully",
            "file_path": str(env_path.absolute())
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Configuration failed: {str(e)}"
        )


@router.post("/configure/service-account")
@limiter.limit("5/minute")
async def configure_service_account(
    request: Request,
    config: ServiceAccountConfigRequest
) -> Dict[str, Any]:
    """
    Configure AtlasUI with Service Account.

    Rate limited to 5 requests per minute to prevent brute force attacks.

    Args:
        config: Service account configuration request

    Returns:
        Configuration result
    """
    try:
        # Validate input
        if not config.client_id or not config.client_secret:
            raise HTTPException(
                status_code=400,
                detail="Invalid service account credentials"
            )

        env_path = Path(".env")

        # Read existing .env if it exists
        existing_lines = []
        if env_path.exists():
            with env_path.open('r') as f:
                existing_lines = f.readlines()

        # Remove old Atlas authentication settings
        new_lines = []
        for line in existing_lines:
            if any(key in line for key in [
                'ATLAS_AUTH_METHOD',
                'ATLAS_PUBLIC_KEY',
                'ATLAS_PRIVATE_KEY',
                'ATLAS_SERVICE_ACCOUNT',
            ]):
                continue
            new_lines.append(line)

        # Add new service account configuration
        config_lines = [
            "\n# MongoDB Atlas Service Account Configuration\n",
            "ATLAS_AUTH_METHOD=service_account\n",
            f"ATLAS_SERVICE_ACCOUNT_CLIENT_ID={config.client_id}\n",
            f"ATLAS_SERVICE_ACCOUNT_CLIENT_SECRET={config.client_secret}\n",
            f"ATLAS_SERVICE_ACCOUNT_PROJECT_ID={config.project_id}\n",
            "ATLAS_BASE_URL=https://cloud.mongodb.com\n",
            "ATLAS_API_VERSION=v2\n",
        ]

        # Write updated .env
        with env_path.open('w') as f:
            f.writelines(new_lines)
            f.writelines(config_lines)

        # Set secure permissions
        try:
            env_path.chmod(0o600)
        except Exception:
            pass

        # Reload settings to pick up the new credentials
        from atlasui.config import reload_settings
        reload_settings()

        return {
            "success": True,
            "auth_method": "service_account",
            "message": "Service Account configured successfully",
            "file_path": str(env_path.absolute()),
            "warning": "Service accounts are project-scoped and have limited functionality"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Configuration failed: {str(e)}"
        )


@router.post("/test-connection")
async def test_connection(auth_method: str) -> Dict[str, Any]:
    """
    Test Atlas API connection with current configuration.

    Args:
        auth_method: Authentication method to test (api_key or service_account)

    Returns:
        Connection test result
    """
    try:
        from atlasui.client import AtlasClient

        # Load configuration from environment
        async with AtlasClient() as client:
            # Test basic connectivity
            result = client.get_root()

            # Try to list organizations
            try:
                orgs = client.list_organizations(items_per_page=5)
                org_count = orgs.get('totalCount', 0)
                org_list = [
                    {
                        "name": org.get('name', 'N/A'),
                        "id": org.get('id', 'N/A')
                    }
                    for org in orgs.get('results', [])[:5]
                ]

                return {
                    "success": True,
                    "message": "Successfully connected to Atlas API",
                    "organizations_count": org_count,
                    "organizations": org_list
                }
            except Exception as org_error:
                # Connection works but can't list organizations
                return {
                    "success": True,
                    "message": "Connected to Atlas but limited access",
                    "warning": str(org_error),
                    "organizations_count": 0,
                    "organizations": []
                }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Connection test failed: {str(e)}"
        )


class CredentialsFileRequest(BaseModel):
    """Request model for loading credentials from a file."""
    file_path: str


class CredentialsFileResponse(BaseModel):
    """Response for credentials file loading."""
    success: bool
    auth_method: str | None = None
    message: str
    credentials_found: dict | None = None


def validate_credentials_file_path(file_path: str) -> Path:
    """
    Validate and sanitize file path to prevent path traversal attacks.

    Only allows files in:
    - User's home directory and subdirectories
    - Current working directory and subdirectories

    Blocks access to sensitive system files.
    """
    import os

    # Blocked paths that should never be accessed
    BLOCKED_PATTERNS = [
        '/etc/', '/var/', '/usr/', '/bin/', '/sbin/',
        '/proc/', '/sys/', '/dev/', '/root/',
        '.ssh/', '.gnupg/', '.aws/', '.azure/', '.gcp/',
        'shadow', 'passwd', 'sudoers',
    ]

    try:
        # Expand user home directory and resolve to absolute path
        expanded_path = os.path.expanduser(file_path)
        resolved_path = Path(expanded_path).resolve()

        # Check against blocked patterns
        path_str = str(resolved_path).lower()
        for pattern in BLOCKED_PATTERNS:
            if pattern in path_str:
                raise ValueError(f"Access denied: Cannot read from protected path")

        # Must be within home directory or current working directory
        home_dir = Path.home().resolve()
        cwd = Path.cwd().resolve()

        is_in_home = str(resolved_path).startswith(str(home_dir))
        is_in_cwd = str(resolved_path).startswith(str(cwd))

        if not (is_in_home or is_in_cwd):
            raise ValueError("Access denied: File must be in home directory or current working directory")

        # Must be a regular file (not directory, symlink to outside, etc.)
        if not resolved_path.is_file():
            raise ValueError("Path is not a regular file")

        # Check file size to prevent reading huge files
        if resolved_path.stat().st_size > 1024 * 1024:  # 1MB limit
            raise ValueError("File too large (max 1MB)")

        return resolved_path

    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"Invalid file path: {str(e)}")


@router.post("/load-credentials-file")
async def load_credentials_file(request: CredentialsFileRequest) -> CredentialsFileResponse:
    """
    Load credentials from a file path.

    Supports:
    - JSON files with service account credentials (client_id, client_secret)
    - JSON files with API keys (public_key/publicKey, private_key/privateKey)
    - .env files with ATLAS_PUBLIC_KEY/ATLAS_PRIVATE_KEY or service account vars

    Args:
        request: File path to load credentials from

    Returns:
        Detected credentials and auth method

    Security:
        - Only allows files in user's home directory or current working directory
        - Blocks access to sensitive system paths (/etc, .ssh, etc.)
        - File size limited to 1MB
    """
    import json

    # Validate path to prevent traversal attacks
    try:
        validated_path = validate_credentials_file_path(request.file_path)
    except ValueError as e:
        return CredentialsFileResponse(
            success=False,
            message=str(e)
        )

    if not validated_path.exists():
        return CredentialsFileResponse(
            success=False,
            message="File not found"
        )

    try:
        with open(validated_path, 'r') as f:
            content = f.read()

        # Try to parse as JSON first
        try:
            data = json.loads(content)

            # Check for service account credentials (MongoDB Atlas format)
            if 'client_id' in data and 'client_secret' in data:
                return CredentialsFileResponse(
                    success=True,
                    auth_method="service_account",
                    message="Found service account credentials",
                    credentials_found={
                        "client_id": data['client_id'],
                        "client_secret": data['client_secret'],
                        "project_id": data.get('project_id', '')
                    }
                )

            # Check for API keys (various formats)
            public_key = data.get('public_key') or data.get('publicKey') or data.get('ATLAS_PUBLIC_KEY')
            private_key = data.get('private_key') or data.get('privateKey') or data.get('ATLAS_PRIVATE_KEY')

            if public_key and private_key:
                return CredentialsFileResponse(
                    success=True,
                    auth_method="api_key",
                    message="Found API key credentials",
                    credentials_found={
                        "public_key": public_key,
                        "private_key": private_key
                    }
                )

            return CredentialsFileResponse(
                success=False,
                message="JSON file does not contain recognized credentials. Expected: client_id/client_secret or public_key/private_key"
            )

        except json.JSONDecodeError:
            # Not JSON, try parsing as .env format
            credentials = {}
            for line in content.split('\n'):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' in line:
                    key, _, value = line.partition('=')
                    key = key.strip()
                    value = value.strip().strip('"\'')
                    credentials[key] = value

            # Check for API keys
            public_key = credentials.get('ATLAS_PUBLIC_KEY')
            private_key = credentials.get('ATLAS_PRIVATE_KEY')

            if public_key and private_key:
                return CredentialsFileResponse(
                    success=True,
                    auth_method="api_key",
                    message="Found API key credentials in .env format",
                    credentials_found={
                        "public_key": public_key,
                        "private_key": private_key
                    }
                )

            # Check for service account
            client_id = credentials.get('ATLAS_SERVICE_ACCOUNT_CLIENT_ID') or credentials.get('ATLAS_SERVICE_ACCOUNT_ID')
            client_secret = credentials.get('ATLAS_SERVICE_ACCOUNT_CLIENT_SECRET') or credentials.get('ATLAS_SERVICE_ACCOUNT_SECRET')

            if client_id and client_secret:
                return CredentialsFileResponse(
                    success=True,
                    auth_method="service_account",
                    message="Found service account credentials in .env format",
                    credentials_found={
                        "client_id": client_id,
                        "client_secret": client_secret,
                        "project_id": credentials.get('ATLAS_SERVICE_ACCOUNT_PROJECT_ID', '')
                    }
                )

            return CredentialsFileResponse(
                success=False,
                message="File does not contain recognized Atlas credentials"
            )

    except Exception as e:
        return CredentialsFileResponse(
            success=False,
            message=f"Error reading file: {str(e)}"
        )
