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
        self.client = httpx.Client(
            auth=auth,
            timeout=self.timeout,
            headers={
                "Accept": "application/vnd.atlas.2023-01-01+json",
                "Content-Type": "application/json",
            },
        )

    def __enter__(self) -> "AtlasClient":
        """Context manager entry."""
        return self

    def __exit__(self, *args: Any) -> None:
        """Context manager exit."""
        self.close()

    def close(self) -> None:
        """Close the HTTP client."""
        self.client.close()

    def _request(
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

        response = self.client.request(
            method=method,
            url=url,
            params=params,
            json=json,
        )

        response.raise_for_status()

        if response.status_code == 204:
            return {}

        return response.json()

    def get(
        self, endpoint: str, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make a GET request."""
        return self._request("GET", endpoint, params=params)

    def post(
        self,
        endpoint: str,
        json: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Make a POST request."""
        return self._request("POST", endpoint, params=params, json=json)

    def put(
        self,
        endpoint: str,
        json: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Make a PUT request."""
        return self._request("PUT", endpoint, params=params, json=json)

    def patch(
        self,
        endpoint: str,
        json: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Make a PATCH request."""
        return self._request("PATCH", endpoint, params=params, json=json)

    def delete(
        self, endpoint: str, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make a DELETE request."""
        return self._request("DELETE", endpoint, params=params)

    # Common Atlas API operations

    def get_root(self) -> Dict[str, Any]:
        """Get API root information."""
        return self.get("/")

    def list_projects(
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
        return self.get(
            "/groups",
            params={"pageNum": page_num, "itemsPerPage": items_per_page}
        )

    def get_project(self, project_id: str) -> Dict[str, Any]:
        """
        Get a specific project.

        Args:
            project_id: Project ID

        Returns:
            Project details
        """
        return self.get(f"/groups/{project_id}")

    def list_clusters(
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
        return self.get(
            f"/groups/{project_id}/clusters",
            params={"pageNum": page_num, "itemsPerPage": items_per_page}
        )

    def get_cluster(self, project_id: str, cluster_name: str) -> Dict[str, Any]:
        """
        Get a specific cluster.

        Args:
            project_id: Project ID
            cluster_name: Cluster name

        Returns:
            Cluster details
        """
        return self.get(f"/groups/{project_id}/clusters/{cluster_name}")

    def create_cluster(
        self, project_id: str, cluster_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create a new cluster.

        Args:
            project_id: Project ID
            cluster_config: Cluster configuration

        Returns:
            Created cluster details
        """
        return self.post(f"/groups/{project_id}/clusters", json=cluster_config)

    def update_cluster(
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
        return self.patch(
            f"/groups/{project_id}/clusters/{cluster_name}", json=cluster_config
        )

    def delete_cluster(self, project_id: str, cluster_name: str) -> Dict[str, Any]:
        """
        Delete a cluster.

        Args:
            project_id: Project ID
            cluster_name: Cluster name

        Returns:
            Deletion response
        """
        return self.delete(f"/groups/{project_id}/clusters/{cluster_name}")

    def list_organizations(
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
        return self.get(
            "/orgs",
            params={"pageNum": page_num, "itemsPerPage": items_per_page}
        )

    def get_organization(self, org_id: str) -> Dict[str, Any]:
        """
        Get a specific organization.

        Args:
            org_id: Organization ID

        Returns:
            Organization details
        """
        return self.get(f"/orgs/{org_id}")

    def list_organization_projects(
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
        return self.get(
            f"/orgs/{org_id}/groups",
            params={"pageNum": page_num, "itemsPerPage": items_per_page}
        )

    def list_databases(
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
        return self.get(
            f"/groups/{project_id}/processes",
            params={"clusterId": cluster_name}
        )

    def get_cluster_databases(
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
            cluster = self.get_cluster(project_id, cluster_name)

            # For now, return empty list as database listing requires
            # additional API calls or direct MongoDB connection
            # This can be enhanced with process/database endpoints
            return []
        except Exception:
            return []
