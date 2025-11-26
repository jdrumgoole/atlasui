"""
Base client for MongoDB Atlas API.
"""

import httpx
from typing import Any, Dict, Optional, List, Union
from atlasui.client.auth import DigestAuth
from atlasui.client.service_account import ServiceAccountAuth, ServiceAccountManager
from atlasui.config import settings


class AtlasClient:
    """
    Base client for interacting with MongoDB Atlas Administration API.

    Handles authentication, request/response processing, and error handling.
    """

    def __init__(
        self,
        public_key: Optional[str] = None,
        private_key: Optional[str] = None,
        service_account_id: Optional[str] = None,
        service_account_secret: Optional[str] = None,
        service_account_credentials_file: Optional[str] = None,
        auth_method: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: Optional[int] = None,
    ) -> None:
        """
        Initialize the Atlas API client.

        Args:
            public_key: Atlas public API key (for API key auth)
            private_key: Atlas private API key (for API key auth)
            service_account_id: Service account client ID (for service account auth)
            service_account_secret: Service account private key (for service account auth)
            service_account_credentials_file: Path to service account credentials JSON file
            auth_method: Authentication method ("api_key" or "service_account")
            base_url: Base URL for Atlas API (defaults to settings)
            timeout: Request timeout in seconds (defaults to settings)
        """
        self.base_url = base_url or settings.atlas_api_base_url
        self.timeout = timeout or settings.timeout
        self.auth_method = auth_method or settings.atlas_auth_method

        # Determine authentication method and create appropriate auth handler
        auth: Union[DigestAuth, ServiceAccountAuth]

        if self.auth_method == "service_account":
            # Service Account authentication
            creds_file = service_account_credentials_file or settings.atlas_service_account_credentials_file

            if creds_file:
                # Load from credentials file
                manager = ServiceAccountManager(creds_file)
                auth = manager.get_auth()
            else:
                # Use individual credentials
                client_id = service_account_id or settings.atlas_service_account_id
                private_key_data = service_account_secret or settings.atlas_service_account_secret

                if not client_id or not private_key_data:
                    raise ValueError(
                        "Service account authentication requires either "
                        "service_account_credentials_file or both "
                        "service_account_id and service_account_secret"
                    )

                auth = ServiceAccountAuth(
                    client_id=client_id,
                    client_secret=private_key_data,
                )

        else:
            # API Key authentication (default/legacy)
            self.public_key = public_key or settings.atlas_public_key
            self.private_key = private_key or settings.atlas_private_key

            if not self.public_key or not self.private_key:
                raise ValueError(
                    "API key authentication requires both public_key and private_key"
                )

            auth = DigestAuth(self.public_key, self.private_key)

        # Create HTTP client with the appropriate auth
        # Using 2024-11-13 API version (required for Flex clusters as of Jan 2025)
        self.client = httpx.AsyncClient(
            auth=auth,
            timeout=self.timeout,
            headers={
                "Accept": "application/vnd.atlas.2024-11-13+json",
                "Content-Type": "application/json",
            },
        )

    async def __aenter__(self) -> "AtlasClient":
        """Async context manager entry."""
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Async context manager exit."""
        await self.close()

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Make an HTTP request to the Atlas API.

        Args:
            method: HTTP method (GET, POST, PUT, PATCH, DELETE)
            endpoint: API endpoint path
            params: Query parameters
            json: JSON request body

        Returns:
            Response JSON data

        Raises:
            httpx.HTTPError: If the request fails
        """
        url = f"{self.base_url}{endpoint}"

        response = await self.client.request(
            method=method,
            url=url,
            params=params,
            json=json,
        )

        # Check for errors and include Atlas API error details
        if response.status_code >= 400:
            error_detail = f"Client error '{response.status_code} {response.reason_phrase}' for url '{url}'"
            try:
                error_data = response.json()
                # Atlas API typically returns error details in these fields
                if isinstance(error_data, dict):
                    if 'detail' in error_data:
                        error_detail = f"{error_detail}\nDetail: {error_data['detail']}"
                    elif 'error' in error_data:
                        error_detail = f"{error_detail}\nError: {error_data['error']}"
                    elif 'errorCode' in error_data:
                        error_detail = f"{error_detail}\nError Code: {error_data['errorCode']}"
                        if 'detail' in error_data:
                            error_detail = f"{error_detail}, Detail: {error_data['detail']}"
                        if 'reason' in error_data:
                            error_detail = f"{error_detail}, Reason: {error_data['reason']}"
                    else:
                        # Include the entire error response
                        error_detail = f"{error_detail}\nResponse: {error_data}"
            except Exception:
                # If we can't parse the error response, just use the status
                pass

            # Raise an exception with the detailed error message
            from httpx import HTTPStatusError
            raise HTTPStatusError(error_detail, request=response.request, response=response)

        if response.status_code == 204:
            return {}

        return response.json()

    async def get(
        self, endpoint: str, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make a GET request."""
        return await self._request("GET", endpoint, params=params)

    async def post(
        self,
        endpoint: str,
        json: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Make a POST request."""
        return await self._request("POST", endpoint, params=params, json=json)

    async def put(
        self,
        endpoint: str,
        json: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Make a PUT request."""
        return await self._request("PUT", endpoint, params=params, json=json)

    async def patch(
        self,
        endpoint: str,
        json: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Make a PATCH request."""
        return await self._request("PATCH", endpoint, params=params, json=json)

    async def delete(
        self, endpoint: str, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make a DELETE request."""
        return await self._request("DELETE", endpoint, params=params)

    # Common Atlas API operations

    async def get_root(self) -> Dict[str, Any]:
        """Get API root information."""
        return await self.get("/")

    async def list_projects(
        self, page_num: int = 1, items_per_page: int = 100
    ) -> Dict[str, Any]:
        """
        List all projects/groups.

        Args:
            page_num: Page number (1-indexed)
            items_per_page: Number of items per page

        Returns:
            Projects list response
        """
        return await self.get(
            "/groups",
            params={"pageNum": page_num, "itemsPerPage": items_per_page}
        )

    async def get_project(self, project_id: str) -> Dict[str, Any]:
        """
        Get a specific project.

        Args:
            project_id: Project ID

        Returns:
            Project details
        """
        return await self.get(f"/groups/{project_id}")

    async def create_project(
        self, name: str, org_id: str
    ) -> Dict[str, Any]:
        """
        Create a new project.

        Args:
            name: Project name
            org_id: Organization ID

        Returns:
            Created project details
        """
        payload = {"name": name, "orgId": org_id}
        return await self.post("/groups", json=payload)

    async def delete_project(self, project_id: str) -> Dict[str, Any]:
        """
        Delete a project.

        Args:
            project_id: Project ID

        Returns:
            Deletion response
        """
        return await self.delete(f"/groups/{project_id}")

    async def list_clusters(
        self, project_id: str, page_num: int = 1, items_per_page: int = 100
    ) -> Dict[str, Any]:
        """
        List all clusters in a project.

        Args:
            project_id: Project ID
            page_num: Page number (1-indexed)
            items_per_page: Number of items per page

        Returns:
            Clusters list response
        """
        return await self.get(
            f"/groups/{project_id}/clusters",
            params={"pageNum": page_num, "itemsPerPage": items_per_page}
        )

    async def get_cluster(self, project_id: str, cluster_name: str) -> Dict[str, Any]:
        """
        Get a specific cluster.

        Args:
            project_id: Project ID
            cluster_name: Cluster name

        Returns:
            Cluster details
        """
        return await self.get(f"/groups/{project_id}/clusters/{cluster_name}")

    async def create_cluster(
        self, project_id: str, cluster_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create a new cluster (M0, M10+, etc. - not Flex).

        Args:
            project_id: Project ID
            cluster_config: Cluster configuration

        Returns:
            Created cluster details
        """
        return await self.post(f"/groups/{project_id}/clusters", json=cluster_config)

    async def create_flex_cluster(
        self, project_id: str, cluster_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create a new Flex cluster using the dedicated Flex endpoint.

        As of January 2025, Flex clusters use a separate API endpoint
        from regular clusters (M0, M10+).

        Args:
            project_id: Project ID
            cluster_config: Flex cluster configuration

        Returns:
            Created Flex cluster details
        """
        return await self.post(f"/groups/{project_id}/flexClusters", json=cluster_config)

    async def list_flex_clusters(
        self, project_id: str, page_num: int = 1, items_per_page: int = 100
    ) -> Dict[str, Any]:
        """
        List all Flex clusters in a project.

        As of January 2025, Flex clusters are in a separate endpoint.

        Args:
            project_id: Project ID
            page_num: Page number (1-indexed)
            items_per_page: Number of items per page

        Returns:
            Flex clusters list response
        """
        return await self.get(
            f"/groups/{project_id}/flexClusters",
            params={"pageNum": page_num, "itemsPerPage": items_per_page}
        )

    async def get_flex_cluster(self, project_id: str, cluster_name: str) -> Dict[str, Any]:
        """
        Get a specific Flex cluster.

        Args:
            project_id: Project ID
            cluster_name: Cluster name

        Returns:
            Flex cluster details
        """
        return await self.get(f"/groups/{project_id}/flexClusters/{cluster_name}")

    async def update_cluster(
        self, project_id: str, cluster_name: str, cluster_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update a cluster.

        Args:
            project_id: Project ID
            cluster_name: Cluster name
            cluster_config: Updated cluster configuration

        Returns:
            Updated cluster details
        """
        return await self.patch(
            f"/groups/{project_id}/clusters/{cluster_name}", json=cluster_config
        )

    async def pause_cluster(self, project_id: str, cluster_name: str) -> Dict[str, Any]:
        """
        Pause a cluster.

        Pausing a cluster stops compute but preserves data.
        Only dedicated clusters (M10+) can be paused.
        M0 (Free Tier) and Flex clusters cannot be paused.

        Args:
            project_id: Project ID
            cluster_name: Cluster name

        Returns:
            Updated cluster details with paused=True
        """
        return await self.patch(
            f"/groups/{project_id}/clusters/{cluster_name}",
            json={"paused": True}
        )

    async def resume_cluster(self, project_id: str, cluster_name: str) -> Dict[str, Any]:
        """
        Resume a paused cluster.

        After resuming, you cannot pause the cluster again for 60 minutes.

        Args:
            project_id: Project ID
            cluster_name: Cluster name

        Returns:
            Updated cluster details with paused=False
        """
        return await self.patch(
            f"/groups/{project_id}/clusters/{cluster_name}",
            json={"paused": False}
        )

    async def delete_cluster(self, project_id: str, cluster_name: str) -> Dict[str, Any]:
        """
        Delete a regular cluster (not Flex).

        Args:
            project_id: Project ID
            cluster_name: Cluster name

        Returns:
            Deletion response
        """
        return await self.delete(f"/groups/{project_id}/clusters/{cluster_name}")

    async def delete_flex_cluster(self, project_id: str, cluster_name: str) -> Dict[str, Any]:
        """
        Delete a Flex cluster.

        Args:
            project_id: Project ID
            cluster_name: Cluster name

        Returns:
            Deletion response
        """
        return await self.delete(f"/groups/{project_id}/flexClusters/{cluster_name}")

    async def list_organizations(
        self, page_num: int = 1, items_per_page: int = 100
    ) -> Dict[str, Any]:
        """
        List all organizations.

        Args:
            page_num: Page number (1-indexed)
            items_per_page: Number of items per page

        Returns:
            Organizations list response
        """
        return await self.get(
            "/orgs",
            params={"pageNum": page_num, "itemsPerPage": items_per_page}
        )

    async def get_organization(self, org_id: str) -> Dict[str, Any]:
        """
        Get a specific organization.

        Args:
            org_id: Organization ID

        Returns:
            Organization details
        """
        return await self.get(f"/orgs/{org_id}")

    async def list_organization_projects(
        self, org_id: str, page_num: int = 1, items_per_page: int = 100
    ) -> Dict[str, Any]:
        """
        List all projects in a specific organization.

        Args:
            org_id: Organization ID
            page_num: Page number (1-indexed)
            items_per_page: Number of items per page

        Returns:
            Projects list response for the organization
        """
        return await self.get(
            f"/orgs/{org_id}/groups",
            params={"pageNum": page_num, "itemsPerPage": items_per_page}
        )

    async def list_databases(
        self, project_id: str, cluster_name: str
    ) -> Dict[str, Any]:
        """
        List all databases in a cluster.

        Note: This uses the Data API endpoint to list databases.

        Args:
            project_id: Project ID
            cluster_name: Cluster name

        Returns:
            Databases list response
        """
        # Get cluster connection info to list databases
        # The Atlas Admin API doesn't have a direct endpoint for databases,
        # so we'll use the process databases endpoint which shows database stats
        return await self.get(
            f"/groups/{project_id}/processes",
            params={"clusterId": cluster_name}
        )

    async def get_cluster_databases(
        self, project_id: str, cluster_name: str
    ) -> List[str]:
        """
        Get list of database names in a cluster.

        This is a helper method that extracts database names from cluster metrics.

        Args:
            project_id: Project ID
            cluster_name: Cluster name

        Returns:
            List of database names
        """
        try:
            # Get cluster details which may include database info
            cluster = await self.get_cluster(project_id, cluster_name)

            # For now, return empty list as database listing requires
            # additional API calls or direct MongoDB connection
            # This can be enhanced with process/database endpoints
            return []
        except Exception:
            return []
