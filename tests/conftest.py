"""
Pytest configuration and fixtures.
"""

import pytest
import sys
from unittest.mock import Mock, patch
from atlasui.client import AtlasClient
from atlasui.config import settings


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test (requires valid API credentials)"
    )


@pytest.fixture(scope="session")
def validate_credentials():
    """
    Validate that Atlas API credentials are configured and working.

    This fixture runs once per test session and validates that:
    1. API credentials are configured in environment
    2. The credentials are valid and can authenticate to Atlas API

    If validation fails, integration tests will be skipped.

    Returns:
        bool: True if credentials are valid, False otherwise
    """
    try:
        # Check if credentials are configured
        if settings.atlas_auth_method == "api_key":
            if not settings.atlas_public_key or not settings.atlas_private_key:
                print("\n⚠️  Atlas API keys not configured. Skipping integration tests.", file=sys.stderr)
                print("   Set ATLAS_PUBLIC_KEY and ATLAS_PRIVATE_KEY environment variables.", file=sys.stderr)
                return False
        elif settings.atlas_auth_method == "service_account":
            if not settings.atlas_service_account_credentials_file:
                if not settings.atlas_service_account_id or not settings.atlas_service_account_secret:
                    print("\n⚠️  Atlas service account credentials not configured. Skipping integration tests.", file=sys.stderr)
                    return False

        # Validate credentials work by making a test API call
        with AtlasClient() as client:
            try:
                # Try to get API root - this validates authentication
                client.get_root()
                print("\n✓ Atlas API credentials validated successfully", file=sys.stderr)
                return True
            except Exception as e:
                print(f"\n⚠️  Atlas API credentials validation failed: {e}", file=sys.stderr)
                print("   Please check your API keys or service account credentials.", file=sys.stderr)
                return False

    except Exception as e:
        print(f"\n⚠️  Failed to validate Atlas credentials: {e}", file=sys.stderr)
        return False


@pytest.fixture
def atlas_client(validate_credentials):
    """
    Create a real Atlas API client for integration tests.

    Requires valid credentials to be configured.
    Skips test if credentials are not valid.
    """
    if not validate_credentials:
        pytest.skip("Atlas API credentials not configured or invalid")

    with AtlasClient() as client:
        yield client


@pytest.fixture
def mock_atlas_client():
    """Create a mock Atlas client for unit testing."""
    with patch('atlasui.client.base.httpx.Client') as mock_client:
        yield mock_client


@pytest.fixture
def sample_project():
    """Sample project data for testing."""
    return {
        "id": "5a0a1e7e0f2912c554080adc",
        "name": "Test Project",
        "orgId": "5a0a1e7e0f2912c554080abc",
        "created": "2023-01-01T00:00:00Z",
        "clusterCount": 2
    }


@pytest.fixture
def sample_cluster():
    """Sample cluster data for testing."""
    return {
        "name": "test-cluster",
        "stateName": "IDLE",
        "mongoDBVersion": "7.0.0",
        "clusterType": "REPLICASET",
        "providerSettings": {
            "providerName": "AWS",
            "regionName": "US_EAST_1",
            "instanceSizeName": "M10"
        },
        "connectionStrings": {
            "standard": "mongodb://test-cluster.mongodb.net:27017"
        }
    }


@pytest.fixture
def sample_projects_response(sample_project):
    """Sample projects list response."""
    return {
        "results": [sample_project],
        "totalCount": 1
    }


@pytest.fixture
def sample_clusters_response(sample_cluster):
    """Sample clusters list response."""
    return {
        "results": [sample_cluster],
        "totalCount": 1
    }
