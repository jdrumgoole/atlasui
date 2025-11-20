"""
Service Account authentication for MongoDB Atlas API using OAuth 2.0.

MongoDB Atlas service accounts use the OAuth 2.0 Client Credentials flow
to obtain access tokens for API authentication.
"""

import httpx
import json
import base64
from typing import Optional, Dict, Any
from pathlib import Path
from datetime import datetime, timedelta
import time


class ServiceAccountAuth(httpx.Auth):
    """
    OAuth 2.0 authentication using MongoDB Atlas Service Accounts.

    Service accounts use the Client Credentials flow to exchange
    client ID and client secret for access tokens.

    Reference: https://www.mongodb.com/docs/atlas/api/service-accounts-overview/
    """

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        token_url: str = "https://cloud.mongodb.com/api/oauth/token",
        token_expiry_buffer: int = 300,  # 5 minutes before expiry
    ) -> None:
        """
        Initialize Service Account OAuth 2.0 authentication.

        Args:
            client_id: Service account client ID from Atlas
            client_secret: Service account client secret from Atlas
            token_url: OAuth token endpoint URL
            token_expiry_buffer: Seconds before expiry to refresh token (default: 300)
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.token_url = token_url
        self.token_expiry_buffer = token_expiry_buffer

        self._access_token: Optional[str] = None
        self._token_type: str = "Bearer"
        self._expires_at: Optional[float] = None

    def _request_token(self) -> Dict[str, Any]:
        """
        Request an access token using OAuth 2.0 Client Credentials flow.

        MongoDB Atlas requires HTTP Basic Authentication with the client credentials.
        The client_id and client_secret are sent as Basic Auth in the Authorization header.

        Returns:
            Token response containing access_token, token_type, and expires_in

        Raises:
            httpx.HTTPError: If token request fails
        """
        # Encode credentials for HTTP Basic Auth
        credentials = f"{self.client_id}:{self.client_secret}"
        b64_credentials = base64.b64encode(credentials.encode()).decode()

        # Prepare token request according to OAuth 2.0 spec
        data = {
            "grant_type": "client_credentials",
        }

        # Make token request with Basic Auth
        with httpx.Client() as client:
            response = client.post(
                self.token_url,
                data=data,
                headers={
                    "Authorization": f"Basic {b64_credentials}",
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Accept": "application/json",
                },
                timeout=30.0,
            )

            # Check for errors
            if response.status_code != 200:
                error_detail = response.text
                try:
                    error_json = response.json()
                    error_detail = error_json.get("error_description", error_json.get("error", error_detail))
                except Exception:
                    pass

                raise httpx.HTTPError(
                    f"OAuth token request failed ({response.status_code}): {error_detail}"
                )

            return response.json()

    def _get_access_token(self) -> str:
        """
        Get a valid access token, requesting a new one if necessary.

        Returns:
            Valid access token string

        Raises:
            httpx.HTTPError: If token request fails
        """
        current_time = time.time()

        # Check if we need a new token
        if (
            self._access_token is None
            or self._expires_at is None
            or current_time >= (self._expires_at - self.token_expiry_buffer)
        ):
            # Request new token
            token_response = self._request_token()

            # Extract token information
            self._access_token = token_response["access_token"]
            self._token_type = token_response.get("token_type", "Bearer")

            # Calculate expiration time
            expires_in = token_response.get("expires_in", 3600)  # Default 1 hour
            self._expires_at = current_time + expires_in

        return self._access_token

    def auth_flow(self, request: httpx.Request):
        """
        Add OAuth 2.0 Bearer token authentication to the request.

        Args:
            request: The outgoing HTTP request

        Yields:
            Authenticated request
        """
        # Get access token
        token = self._get_access_token()

        # Add Authorization header with Bearer token
        request.headers["Authorization"] = f"{self._token_type} {token}"

        # Yield the authenticated request
        yield request


class ServiceAccountManager:
    """
    Manager for service account credentials and operations.
    """

    def __init__(self, credentials_file: Optional[str] = None) -> None:
        """
        Initialize service account manager.

        Args:
            credentials_file: Path to service account credentials JSON file
        """
        self.credentials_file = credentials_file
        self.credentials: Optional[Dict[str, Any]] = None

        if credentials_file:
            self.load_credentials(credentials_file)

    def load_credentials(self, credentials_file: str) -> None:
        """
        Load service account credentials from JSON file.

        The JSON file should have the following structure:
        {
            "client_id": "your-client-id",
            "client_secret": "your-client-secret",
            "token_url": "https://cloud.mongodb.com/api/oauth/token"  # optional
        }

        Args:
            credentials_file: Path to credentials JSON file

        Raises:
            FileNotFoundError: If credentials file doesn't exist
            ValueError: If required fields are missing
        """
        path = Path(credentials_file)
        if not path.exists():
            raise FileNotFoundError(f"Credentials file not found: {credentials_file}")

        with path.open() as f:
            self.credentials = json.load(f)

        # Validate required fields
        required_fields = ["client_id", "client_secret"]
        missing_fields = [f for f in required_fields if f not in self.credentials]
        if missing_fields:
            raise ValueError(
                f"Missing required fields in credentials: {', '.join(missing_fields)}"
            )

    def get_auth(self) -> ServiceAccountAuth:
        """
        Get ServiceAccountAuth instance from loaded credentials.

        Returns:
            ServiceAccountAuth instance

        Raises:
            ValueError: If credentials are not loaded
        """
        if not self.credentials:
            raise ValueError("Credentials not loaded. Call load_credentials() first.")

        return ServiceAccountAuth(
            client_id=self.credentials["client_id"],
            client_secret=self.credentials["client_secret"],
            token_url=self.credentials.get(
                "token_url",
                "https://cloud.mongodb.com/api/oauth/token"
            ),
        )

    @staticmethod
    def create_credentials_file(
        client_id: str,
        client_secret: str,
        output_file: str,
        token_url: str = "https://cloud.mongodb.com/api/oauth/token",
    ) -> None:
        """
        Create a service account credentials file.

        Args:
            client_id: Service account client ID
            client_secret: Service account client secret
            output_file: Path to output credentials file
            token_url: OAuth token endpoint URL
        """
        credentials = {
            "client_id": client_id,
            "client_secret": client_secret,
            "token_url": token_url,
        }

        path = Path(output_file)
        path.parent.mkdir(parents=True, exist_ok=True)

        with path.open("w") as f:
            json.dump(credentials, f, indent=2)

        # Set restrictive permissions (owner read/write only)
        try:
            path.chmod(0o600)
        except Exception:
            # Windows doesn't support chmod the same way
            pass

        print(f"Service account credentials saved to: {output_file}")
        print("⚠ Keep this file secure and never commit it to version control!")
