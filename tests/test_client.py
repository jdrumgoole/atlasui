"""
Tests for Atlas API client.
"""

import pytest
from unittest.mock import Mock, patch
from atlasui.client import AtlasClient


def test_atlas_client_initialization():
    """Test Atlas client can be initialized."""
    with patch('atlasui.client.base.httpx.Client'):
        client = AtlasClient(
            public_key="test_public",
            private_key="test_private",
            base_url="https://test.mongodb.com/api/atlas/v2"
        )
        assert client.public_key == "test_public"
        assert client.private_key == "test_private"
        assert client.base_url == "https://test.mongodb.com/api/atlas/v2"


def test_atlas_client_context_manager():
    """Test Atlas client works as context manager."""
    with patch('atlasui.client.base.httpx.Client'):
        with AtlasClient(public_key="test", private_key="test") as client:
            assert client is not None


def test_get_root(mock_atlas_client):
    """Test getting API root."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"appName": "MongoDB Atlas"}
    mock_response.raise_for_status = Mock()

    mock_atlas_client.return_value.request.return_value = mock_response

    with AtlasClient(public_key="test", private_key="test") as client:
        result = client.get_root()
        assert result["appName"] == "MongoDB Atlas"


def test_list_projects(mock_atlas_client, sample_projects_response):
    """Test listing projects."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = sample_projects_response
    mock_response.raise_for_status = Mock()

    mock_atlas_client.return_value.request.return_value = mock_response

    with AtlasClient(public_key="test", private_key="test") as client:
        result = client.list_projects()
        assert result["totalCount"] == 1
        assert len(result["results"]) == 1
        assert result["results"][0]["name"] == "Test Project"


def test_get_project(mock_atlas_client, sample_project):
    """Test getting a specific project."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = sample_project
    mock_response.raise_for_status = Mock()

    mock_atlas_client.return_value.request.return_value = mock_response

    with AtlasClient(public_key="test", private_key="test") as client:
        result = client.get_project("5a0a1e7e0f2912c554080adc")
        assert result["name"] == "Test Project"
        assert result["id"] == "5a0a1e7e0f2912c554080adc"


def test_list_clusters(mock_atlas_client, sample_clusters_response):
    """Test listing clusters."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = sample_clusters_response
    mock_response.raise_for_status = Mock()

    mock_atlas_client.return_value.request.return_value = mock_response

    with AtlasClient(public_key="test", private_key="test") as client:
        result = client.list_clusters("5a0a1e7e0f2912c554080adc")
        assert result["totalCount"] == 1
        assert len(result["results"]) == 1
        assert result["results"][0]["name"] == "test-cluster"


def test_get_cluster(mock_atlas_client, sample_cluster):
    """Test getting a specific cluster."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = sample_cluster
    mock_response.raise_for_status = Mock()

    mock_atlas_client.return_value.request.return_value = mock_response

    with AtlasClient(public_key="test", private_key="test") as client:
        result = client.get_cluster("5a0a1e7e0f2912c554080adc", "test-cluster")
        assert result["name"] == "test-cluster"
        assert result["stateName"] == "IDLE"
        assert result["mongoDBVersion"] == "7.0.0"
