"""
Integration tests for AtlasUI web API endpoints.

These tests require valid Atlas API credentials to be configured.
They will be skipped if credentials are not available or invalid.

Run with: pytest tests/test_api_integration.py -v -m integration
"""

import pytest
from fastapi.testclient import TestClient
from atlasui.server import app


@pytest.fixture
def client(validate_credentials):
    """Create a test client for the FastAPI application."""
    if not validate_credentials:
        pytest.skip("Atlas API credentials not configured or invalid")

    return TestClient(app)


@pytest.mark.integration
class TestHealthEndpoint:
    """Test health check endpoint."""

    def test_health_check(self, client):
        """Test the health check endpoint."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data


@pytest.mark.integration
class TestProjectsAPI:
    """Test projects API endpoints."""

    def test_list_projects(self, client):
        """Test listing projects via API."""
        response = client.get("/api/projects/")

        assert response.status_code == 200
        data = response.json()

        # Validate response structure
        assert "results" in data
        assert isinstance(data["results"], list)

        # If there are projects, validate structure
        if data["results"]:
            project = data["results"][0]
            assert "id" in project
            assert "name" in project

    def test_get_project(self, client):
        """Test getting a specific project via API."""
        # First, get list of projects
        list_response = client.get("/api/projects/")
        projects = list_response.json()["results"]

        # Skip if no projects
        if not projects:
            pytest.skip("No projects available for testing")

        # Get the first project
        project_id = projects[0]["id"]
        response = client.get(f"/api/projects/{project_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == project_id


@pytest.mark.integration
class TestClustersAPI:
    """Test clusters API endpoints."""

    def test_list_clusters_for_project(self, client):
        """Test listing clusters for a project via API."""
        # First, get a project
        projects_response = client.get("/api/projects/")
        projects = projects_response.json()["results"]

        # Skip if no projects
        if not projects:
            pytest.skip("No projects available for testing")

        project_id = projects[0]["id"]
        response = client.get(f"/api/clusters/{project_id}")

        assert response.status_code == 200
        data = response.json()

        # Validate response structure
        assert "results" in data
        assert isinstance(data["results"], list)

    def test_get_cluster_details(self, client):
        """Test getting cluster details via API."""
        # First, get a project
        projects_response = client.get("/api/projects/")
        projects = projects_response.json()["results"]

        if not projects:
            pytest.skip("No projects available for testing")

        # Get clusters for the project
        project_id = projects[0]["id"]
        clusters_response = client.get(f"/api/clusters/{project_id}")
        clusters = clusters_response.json()["results"]

        if not clusters:
            pytest.skip("No clusters available for testing")

        # Get details for the first cluster
        cluster_name = clusters[0]["name"]
        response = client.get(f"/api/clusters/{project_id}/{cluster_name}")

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == cluster_name


@pytest.mark.integration
class TestResourcesEndpoints:
    """Test endpoints that return resources."""

    def test_get_organizations(self, client):
        """Test getting organizations via API."""
        response = client.get("/api/organizations/")

        assert response.status_code == 200
        data = response.json()

        # Response should have results array
        assert "results" in data
        assert isinstance(data["results"], list)

        # If there are organizations, validate structure
        if data["results"]:
            org = data["results"][0]
            assert "id" in org
            assert "name" in org

    def test_get_organization_details(self, client):
        """Test getting a specific organization."""
        # First get list of organizations
        list_response = client.get("/api/organizations/")
        orgs = list_response.json()["results"]

        if not orgs:
            pytest.skip("No organizations available for testing")

        org_id = orgs[0]["id"]
        response = client.get(f"/api/organizations/{org_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == org_id

    def test_get_organization_projects(self, client):
        """Test getting projects for a specific organization."""
        # First get list of organizations
        list_response = client.get("/api/organizations/")
        orgs = list_response.json()["results"]

        if not orgs:
            pytest.skip("No organizations available for testing")

        org_id = orgs[0]["id"]
        response = client.get(f"/api/organizations/{org_id}/projects")

        assert response.status_code == 200
        data = response.json()
        assert "results" in data


@pytest.mark.integration
class TestPagesEndpoints:
    """Test HTML page rendering endpoints."""

    def test_index_page(self, client):
        """Test the index/home page."""
        response = client.get("/")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_organizations_page(self, client):
        """Test the organizations page."""
        response = client.get("/organizations")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_projects_page(self, client):
        """Test the all projects page."""
        response = client.get("/projects")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_clusters_page(self, client):
        """Test the all clusters page."""
        response = client.get("/clusters")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    # Note: test_project_specific_page removed - per-project clusters page was consolidated
    # into the global /clusters page


@pytest.mark.integration
class TestErrorHandling:
    """Test API error handling."""

    def test_nonexistent_project(self, client):
        """Test getting a project that doesn't exist."""
        fake_project_id = "000000000000000000000000"
        response = client.get(f"/api/projects/{fake_project_id}")

        # Should return an error status code
        assert response.status_code >= 400

    def test_nonexistent_cluster(self, client):
        """Test getting a cluster that doesn't exist."""
        # Get a real project first
        projects_response = client.get("/api/projects/")
        projects = projects_response.json()["results"]

        if not projects:
            pytest.skip("No projects available for testing")

        project_id = projects[0]["id"]
        fake_cluster_name = "nonexistent-cluster-12345"

        response = client.get(f"/api/clusters/{project_id}/{fake_cluster_name}")

        # Should return an error status code
        assert response.status_code >= 400
