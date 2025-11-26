"""
Tests for Atlas API client.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from atlasui.client import AtlasClient


def test_atlas_client_initialization():
    """Test Atlas client can be initialized."""
    with patch('atlasui.client.base.httpx.AsyncClient'):
        client = AtlasClient(
            public_key="test_public",
            private_key="test_private",
            base_url="https://test.mongodb.com/api/atlas/v2"
        )
        assert client.public_key == "test_public"
        assert client.private_key == "test_private"
        assert client.base_url == "https://test.mongodb.com/api/atlas/v2"


@pytest.mark.asyncio
async def test_atlas_client_context_manager():
    """Test Atlas client works as async context manager."""
    with patch('atlasui.client.base.httpx.AsyncClient') as mock_client:
        # Configure the mock instance to have async methods
        mock_instance = AsyncMock()
        mock_client.return_value = mock_instance

        async with AtlasClient(public_key="test", private_key="test") as client:
            assert client is not None


@pytest.mark.asyncio
async def test_get_root(mock_atlas_client):
    """Test getting API root."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"appName": "MongoDB Atlas"}

    # Configure the async request method
    mock_atlas_client.return_value.request = AsyncMock(return_value=mock_response)

    async with AtlasClient(public_key="test", private_key="test") as client:
        result = await client.get_root()
        assert result["appName"] == "MongoDB Atlas"


@pytest.mark.asyncio
async def test_list_projects(mock_atlas_client, sample_projects_response):
    """Test listing projects."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = sample_projects_response

    # Configure the async request method
    mock_atlas_client.return_value.request = AsyncMock(return_value=mock_response)

    async with AtlasClient(public_key="test", private_key="test") as client:
        result = await client.list_projects()
        assert result["totalCount"] == 1
        assert len(result["results"]) == 1
        assert result["results"][0]["name"] == "Test Project"


@pytest.mark.asyncio
async def test_get_project(mock_atlas_client, sample_project):
    """Test getting a specific project."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = sample_project

    # Configure the async request method
    mock_atlas_client.return_value.request = AsyncMock(return_value=mock_response)

    async with AtlasClient(public_key="test", private_key="test") as client:
        result = await client.get_project("5a0a1e7e0f2912c554080adc")
        assert result["name"] == "Test Project"
        assert result["id"] == "5a0a1e7e0f2912c554080adc"


@pytest.mark.asyncio
async def test_list_clusters(mock_atlas_client, sample_clusters_response):
    """Test listing clusters."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = sample_clusters_response

    # Configure the async request method
    mock_atlas_client.return_value.request = AsyncMock(return_value=mock_response)

    async with AtlasClient(public_key="test", private_key="test") as client:
        result = await client.list_clusters("5a0a1e7e0f2912c554080adc")
        assert result["totalCount"] == 1
        assert len(result["results"]) == 1
        assert result["results"][0]["name"] == "test-cluster"


@pytest.mark.asyncio
async def test_get_cluster(mock_atlas_client, sample_cluster):
    """Test getting a specific cluster."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = sample_cluster

    # Configure the async request method
    mock_atlas_client.return_value.request = AsyncMock(return_value=mock_response)

    async with AtlasClient(public_key="test", private_key="test") as client:
        result = await client.get_cluster("5a0a1e7e0f2912c554080adc", "test-cluster")
        assert result["name"] == "test-cluster"
        assert result["stateName"] == "IDLE"
        assert result["mongoDBVersion"] == "7.0.0"
