"""
API routes for setup and configuration wizard.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, Literal
from pydantic import BaseModel
from pathlib import Path

router = APIRouter()


class ConfigCheckResponse(BaseModel):
    """Response for configuration check."""
    configured: bool
    auth_method: str | None = None
    message: str


class APIKeyConfigRequest(BaseModel):
    """Request model for API key configuration."""
    public_key: str
    private_key: str


class ServiceAccountConfigRequest(BaseModel):
    """Request model for service account configuration."""
    client_id: str
    client_secret: str
    project_id: str


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


@router.post("/configure/api-key")
async def configure_api_key(request: APIKeyConfigRequest) -> Dict[str, Any]:
    """
    Configure AtlasUI with API Keys.

    Args:
        request: API key configuration request

    Returns:
        Configuration result
    """
    try:
        # Validate input
        if not request.public_key or len(request.public_key) < 6:
            raise HTTPException(
                status_code=400,
                detail="Invalid public key"
            )

        if not request.private_key or len(request.private_key) < 6:
            raise HTTPException(
                status_code=400,
                detail="Invalid private key"
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
            f"ATLAS_PUBLIC_KEY={request.public_key}\n",
            f"ATLAS_PRIVATE_KEY={request.private_key}\n",
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
async def configure_service_account(
    request: ServiceAccountConfigRequest
) -> Dict[str, Any]:
    """
    Configure AtlasUI with Service Account.

    Args:
        request: Service account configuration request

    Returns:
        Configuration result
    """
    try:
        # Validate input
        if not request.client_id or not request.client_secret:
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
            f"ATLAS_SERVICE_ACCOUNT_CLIENT_ID={request.client_id}\n",
            f"ATLAS_SERVICE_ACCOUNT_CLIENT_SECRET={request.client_secret}\n",
            f"ATLAS_SERVICE_ACCOUNT_PROJECT_ID={request.project_id}\n",
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
        with AtlasClient() as client:
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
