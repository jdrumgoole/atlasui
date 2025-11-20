"""
Pytest configuration and fixtures.
"""

import pytest
from unittest.mock import Mock, patch
from atlasui.client import AtlasClient


@pytest.fixture
def mock_atlas_client():
    """Create a mock Atlas client for testing."""
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
