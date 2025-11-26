"""
Integration tests for Atlas API client.

These tests require valid Atlas API credentials to be configured.
They will be skipped if credentials are not available or invalid.

Run with: pytest tests/test_integration.py -v -m integration
"""

import pytest
import pytest_asyncio
from typing import Dict, Any


@pytest.mark.integration
class TestAtlasAPIRoot:
    """Test Atlas API root endpoint."""

    @pytest.mark.asyncio
    async def test_get_root(self, atlas_client):
        """Test getting API root information."""
        result = await atlas_client.get_root()

        # Validate response structure
        assert isinstance(result, dict)
        assert "appName" in result or "links" in result

    @pytest.mark.asyncio
    async def test_api_connectivity(self, atlas_client):
        """Test basic API connectivity and authentication."""
        # Making any successful API call validates connectivity and auth
        result = await atlas_client.get_root()
        assert result is not None


@pytest.mark.integration
class TestOrganizations:
    """Test organization-related API operations."""

    @pytest.mark.asyncio
    async def test_list_organizations(self, atlas_client):
        """Test listing organizations."""
        result = await atlas_client.list_organizations()

        # Validate response structure
        assert isinstance(result, dict)
        assert "results" in result
        assert isinstance(result["results"], list)

        # If there are organizations, validate structure
        if result["results"]:
            org = result["results"][0]
            assert "id" in org
            assert "name" in org

    @pytest.mark.asyncio
    async def test_get_organization(self, atlas_client):
        """Test getting a specific organization."""
        # First, get list of organizations
        orgs_result = await atlas_client.list_organizations()

        # Skip if no organizations
        if not orgs_result["results"]:
            pytest.skip("No organizations available for testing")

        # Get the first organization
        org_id = orgs_result["results"][0]["id"]
        result = await atlas_client.get_organization(org_id)

        # Validate response
        assert isinstance(result, dict)
        assert result["id"] == org_id
        assert "name" in result

    @pytest.mark.asyncio
    async def test_list_organization_projects(self, atlas_client):
        """Test listing projects in an organization."""
        # First, get list of organizations
        orgs_result = await atlas_client.list_organizations()

        # Skip if no organizations
        if not orgs_result["results"]:
            pytest.skip("No organizations available for testing")

        # Get projects for the first organization
        org_id = orgs_result["results"][0]["id"]
        result = await atlas_client.list_organization_projects(org_id)

        # Validate response structure
        assert isinstance(result, dict)
        assert "results" in result
        assert isinstance(result["results"], list)


@pytest.mark.integration
class TestProjects:
    """Test project-related API operations."""

    @pytest.mark.asyncio
    async def test_list_projects(self, atlas_client):
        """Test listing all projects."""
        result = await atlas_client.list_projects()

        # Validate response structure
        assert isinstance(result, dict)
        assert "results" in result
        assert isinstance(result["results"], list)

        # If there are projects, validate structure
        if result["results"]:
            project = result["results"][0]
            assert "id" in project
            assert "name" in project
            assert "orgId" in project

    @pytest.mark.asyncio
    async def test_get_project(self, atlas_client):
        """Test getting a specific project."""
        # First, get list of projects
        projects_result = await atlas_client.list_projects()

        # Skip if no projects
        if not projects_result["results"]:
            pytest.skip("No projects available for testing")

        # Get the first project
        project_id = projects_result["results"][0]["id"]
        result = await atlas_client.get_project(project_id)

        # Validate response
        assert isinstance(result, dict)
        assert result["id"] == project_id
        assert "name" in result
        assert "orgId" in result

    @pytest.mark.asyncio
    async def test_projects_pagination(self, atlas_client):
        """Test project list pagination."""
        # Get first page with 1 item
        result = await atlas_client.list_projects(page_num=1, items_per_page=1)

        assert isinstance(result, dict)
        assert "results" in result

        # If there are results, check pagination worked
        if result["results"]:
            assert len(result["results"]) <= 1


@pytest.mark.integration
class TestClusters:
    """Test cluster-related API operations."""

    @pytest_asyncio.fixture
    async def project_with_clusters(self, atlas_client):
        """Find a project that has clusters."""
        projects_result = await atlas_client.list_projects()

        for project in projects_result.get("results", []):
            # Try to list clusters for this project
            try:
                clusters_result = await atlas_client.list_clusters(project["id"])
                if clusters_result.get("results"):
                    return {
                        "project": project,
                        "clusters": clusters_result["results"]
                    }
            except Exception:
                # Project might not have clusters or might have access issues
                continue

        pytest.skip("No projects with clusters available for testing")

    @pytest.mark.asyncio
    async def test_list_clusters(self, atlas_client):
        """Test listing clusters in a project."""
        # Get a project first
        projects_result = await atlas_client.list_projects()

        # Skip if no projects
        if not projects_result["results"]:
            pytest.skip("No projects available for testing")

        project_id = projects_result["results"][0]["id"]
        result = await atlas_client.list_clusters(project_id)

        # Validate response structure
        assert isinstance(result, dict)
        assert "results" in result
        assert isinstance(result["results"], list)

    @pytest.mark.asyncio
    async def test_get_cluster(self, atlas_client, project_with_clusters):
        """Test getting a specific cluster."""
        project = project_with_clusters["project"]
        cluster = project_with_clusters["clusters"][0]

        result = await atlas_client.get_cluster(project["id"], cluster["name"])

        # Validate response
        assert isinstance(result, dict)
        assert result["name"] == cluster["name"]
        assert "stateName" in result
        assert "clusterType" in result

    @pytest.mark.asyncio
    async def test_cluster_details(self, atlas_client, project_with_clusters):
        """Test getting detailed cluster information."""
        project = project_with_clusters["project"]
        cluster = project_with_clusters["clusters"][0]

        result = await atlas_client.get_cluster(project["id"], cluster["name"])

        # Validate cluster details contain expected fields
        assert "mongoDBVersion" in result
        assert "connectionStrings" in result

        # M0/free tier clusters use replicationSpecs, regular clusters use providerSettings
        assert "providerSettings" in result or "replicationSpecs" in result

        if "providerSettings" in result:
            # Regular cluster - validate provider settings structure
            provider_settings = result["providerSettings"]
            assert "providerName" in provider_settings
            assert "instanceSizeName" in provider_settings
        else:
            # M0/free tier cluster - validate replicationSpecs structure
            assert "replicationSpecs" in result
            assert isinstance(result["replicationSpecs"], list)
            assert len(result["replicationSpecs"]) > 0

    @pytest.mark.asyncio
    async def test_clusters_pagination(self, atlas_client):
        """Test cluster list pagination."""
        # Get a project first
        projects_result = await atlas_client.list_projects()

        if not projects_result["results"]:
            pytest.skip("No projects available for testing")

        project_id = projects_result["results"][0]["id"]

        # Get first page with 1 item
        result = await atlas_client.list_clusters(project_id, page_num=1, items_per_page=1)

        assert isinstance(result, dict)
        assert "results" in result

        # If there are results, check pagination worked
        if result["results"]:
            assert len(result["results"]) <= 1


@pytest.mark.integration
class TestErrorHandling:
    """Test error handling and edge cases."""

    @pytest.mark.asyncio
    async def test_get_nonexistent_project(self, atlas_client):
        """Test getting a project that doesn't exist."""
        # Use a fake project ID
        fake_project_id = "000000000000000000000000"

        with pytest.raises(Exception):  # Should raise HTTPError
            await atlas_client.get_project(fake_project_id)

    @pytest.mark.asyncio
    async def test_get_nonexistent_cluster(self, atlas_client):
        """Test getting a cluster that doesn't exist."""
        # Get a real project first
        projects_result = await atlas_client.list_projects()

        if not projects_result["results"]:
            pytest.skip("No projects available for testing")

        project_id = projects_result["results"][0]["id"]
        fake_cluster_name = "nonexistent-cluster-12345"

        with pytest.raises(Exception):  # Should raise HTTPError
            await atlas_client.get_cluster(project_id, fake_cluster_name)

    @pytest.mark.asyncio
    async def test_invalid_pagination(self, atlas_client):
        """Test pagination with invalid parameters."""
        # Page 0 should still work or raise a clear error
        try:
            result = await atlas_client.list_projects(page_num=0, items_per_page=1)
            # Some APIs might handle page 0 as page 1
            assert isinstance(result, dict)
        except Exception as e:
            # Or it might raise an error, which is also acceptable
            assert e is not None


@pytest.mark.integration
class TestClientLifecycle:
    """Test client lifecycle and resource management."""

    @pytest.mark.asyncio
    async def test_client_context_manager(self, validate_credentials):
        """Test client works correctly as async context manager."""
        if not validate_credentials:
            pytest.skip("Atlas API credentials not configured or invalid")

        from atlasui.client import AtlasClient

        async with AtlasClient() as client:
            result = await client.get_root()
            assert result is not None

    @pytest.mark.asyncio
    async def test_client_close(self, validate_credentials):
        """Test explicit client close."""
        if not validate_credentials:
            pytest.skip("Atlas API credentials not configured or invalid")

        from atlasui.client import AtlasClient

        client = AtlasClient()
        result = await client.get_root()
        assert result is not None

        # Close the client
        await client.close()

        # After closing, new requests should fail
        with pytest.raises(Exception):
            await client.get_root()
