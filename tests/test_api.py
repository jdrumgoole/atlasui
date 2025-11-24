"""
Tests for FastAPI routes.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock, AsyncMock

from atlasui.server import app

client = TestClient(app)


def test_health_check():
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data


def test_root_redirect():
    """Test root endpoint redirects."""
    response = client.get("/", follow_redirects=False)
    # Accept either 302 (Found) or 307 (Temporary Redirect)
    assert response.status_code in [302, 307]
    # Should redirect to organizations or dashboard or root
    assert response.headers["location"] in ["/", "/dashboard", "/organizations"]


@patch('atlasui.api.projects.AtlasClient')
def test_list_projects_api(mock_client_class, sample_projects_response):
    """Test list projects API endpoint."""
    mock_client = AsyncMock()
    mock_client.list_projects.return_value = sample_projects_response
    mock_client_class.return_value.__aenter__.return_value = mock_client

    response = client.get("/api/projects/")
    assert response.status_code == 200
    data = response.json()
    assert data["totalCount"] == 1
    assert len(data["results"]) == 1


@patch('atlasui.api.projects.AtlasClient')
def test_get_project_api(mock_client_class, sample_project):
    """Test get project API endpoint."""
    mock_client = AsyncMock()
    mock_client.get_project.return_value = sample_project
    mock_client_class.return_value.__aenter__.return_value = mock_client

    project_id = "5a0a1e7e0f2912c554080adc"
    response = client.get(f"/api/projects/{project_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Project"


@patch('atlasui.api.clusters.AtlasClient')
def test_list_clusters_api(mock_client_class, sample_clusters_response):
    """Test list clusters API endpoint."""
    mock_client = AsyncMock()
    mock_client.list_clusters.return_value = sample_clusters_response
    mock_client_class.return_value.__aenter__.return_value = mock_client

    project_id = "5a0a1e7e0f2912c554080adc"
    response = client.get(f"/api/clusters/{project_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["totalCount"] == 1
    assert len(data["results"]) == 1


@patch('atlasui.api.clusters.AtlasClient')
def test_get_cluster_api(mock_client_class, sample_cluster):
    """Test get cluster API endpoint."""
    mock_client = AsyncMock()
    mock_client.get_cluster.return_value = sample_cluster
    mock_client_class.return_value.__aenter__.return_value = mock_client

    project_id = "5a0a1e7e0f2912c554080adc"
    cluster_name = "test-cluster"
    response = client.get(f"/api/clusters/{project_id}/{cluster_name}")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "test-cluster"
    assert data["stateName"] == "IDLE"
