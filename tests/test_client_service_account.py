"""
Tests for Atlas client with OAuth 2.0 service account authentication.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from atlasui.client import AtlasClient


@patch('atlasui.client.base.httpx.Client')
@patch('atlasui.client.service_account.ServiceAccountAuth')
def test_atlas_client_with_service_account(mock_auth, mock_http_client):
    """Test creating AtlasClient with service account authentication."""
    client = AtlasClient(
        auth_method="service_account",
        service_account_id="test-client-id",
        service_account_secret="test-client-secret"
    )

    assert client.auth_method == "service_account"
    assert mock_auth.called

    # Verify auth was created with correct parameters
    mock_auth.assert_called_once_with(
        client_id="test-client-id",
        client_secret="test-client-secret"
    )


@patch('atlasui.client.base.httpx.Client')
@patch('atlasui.client.service_account.ServiceAccountManager')
def test_atlas_client_with_credentials_file(mock_manager, mock_http_client):
    """Test creating AtlasClient with credentials file."""
    mock_manager_instance = MagicMock()
    mock_auth_instance = MagicMock()
    mock_manager_instance.get_auth.return_value = mock_auth_instance
    mock_manager.return_value = mock_manager_instance

    client = AtlasClient(
        auth_method="service_account",
        service_account_credentials_file="test-credentials.json"
    )

    assert client.auth_method == "service_account"
    assert mock_manager.called
    mock_manager.assert_called_once_with("test-credentials.json")
    mock_manager_instance.get_auth.assert_called_once()


@patch('atlasui.client.base.httpx.Client')
def test_atlas_client_service_account_missing_credentials(mock_http_client):
    """Test AtlasClient raises error when service account credentials are missing."""
    with pytest.raises(ValueError, match="Service account authentication requires"):
        AtlasClient(
            auth_method="service_account"
            # No credentials provided
        )


@patch('atlasui.client.base.httpx.Client')
@patch('atlasui.client.base.DigestAuth')
def test_atlas_client_defaults_to_api_key(mock_digest_auth, mock_http_client):
    """Test AtlasClient defaults to API key authentication."""
    client = AtlasClient(
        public_key="test-public",
        private_key="test-private",
        auth_method="api_key"
    )

    assert client.auth_method == "api_key"
    assert mock_digest_auth.called


@patch('atlasui.client.base.httpx.Client')
def test_atlas_client_api_key_missing_credentials(mock_http_client):
    """Test AtlasClient raises error when API key credentials are missing."""
    with pytest.raises(ValueError, match="API key authentication requires"):
        AtlasClient(
            auth_method="api_key"
            # No credentials provided
        )
