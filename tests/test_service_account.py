"""
Tests for service account OAuth 2.0 authentication.
"""

import pytest
from unittest.mock import Mock, patch, mock_open
import json
from pathlib import Path

from atlasui.client.service_account import (
    ServiceAccountAuth,
    ServiceAccountManager
)


def test_service_account_auth_initialization():
    """Test ServiceAccountAuth can be initialized."""
    auth = ServiceAccountAuth(
        client_id="test-client-id",
        client_secret="test-client-secret"
    )
    assert auth.client_id == "test-client-id"
    assert auth.client_secret == "test-client-secret"
    assert auth.token_url == "https://cloud.mongodb.com/api/oauth/token"
    assert auth.token_expiry_buffer == 300


def test_service_account_auth_with_custom_token_url():
    """Test ServiceAccountAuth with custom token URL."""
    auth = ServiceAccountAuth(
        client_id="test-client-id",
        client_secret="test-client-secret",
        token_url="https://custom.example.com/oauth/token"
    )
    assert auth.token_url == "https://custom.example.com/oauth/token"


@patch('atlasui.client.service_account.httpx.Client')
def test_request_token_success(mock_client_class):
    """Test successful OAuth token request."""
    # Mock successful token response
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "access_token": "test-access-token",
        "token_type": "Bearer",
        "expires_in": 3600
    }

    mock_client_instance = Mock()
    mock_client_instance.post.return_value = mock_response
    mock_client_instance.__enter__ = Mock(return_value=mock_client_instance)
    mock_client_instance.__exit__ = Mock(return_value=False)
    mock_client_class.return_value = mock_client_instance

    auth = ServiceAccountAuth(
        client_id="test-client-id",
        client_secret="test-client-secret"
    )

    token_response = auth._request_token()

    assert token_response["access_token"] == "test-access-token"
    assert token_response["token_type"] == "Bearer"
    assert token_response["expires_in"] == 3600

    # Verify the request was made correctly
    mock_client_instance.post.assert_called_once()
    call_args = mock_client_instance.post.call_args
    assert "grant_type" in call_args.kwargs["data"]
    assert call_args.kwargs["data"]["grant_type"] == "client_credentials"


@patch('atlasui.client.service_account.httpx.Client')
def test_request_token_failure(mock_client_class):
    """Test failed OAuth token request."""
    # Mock failed token response
    mock_response = Mock()
    mock_response.status_code = 401
    mock_response.text = "Unauthorized"
    mock_response.json.return_value = {"error": "invalid_client"}

    mock_client_instance = Mock()
    mock_client_instance.post.return_value = mock_response
    mock_client_instance.__enter__ = Mock(return_value=mock_client_instance)
    mock_client_instance.__exit__ = Mock(return_value=False)
    mock_client_class.return_value = mock_client_instance

    auth = ServiceAccountAuth(
        client_id="test-client-id",
        client_secret="wrong-secret"
    )

    with pytest.raises(Exception, match="OAuth token request failed"):
        auth._request_token()


def test_service_account_manager_initialization():
    """Test ServiceAccountManager initialization."""
    manager = ServiceAccountManager()
    assert manager.credentials is None
    assert manager.credentials_file is None


def test_service_account_manager_with_file():
    """Test ServiceAccountManager with credentials file."""
    credentials = {
        "client_id": "test-client-id",
        "client_secret": "test-client-secret",
        "token_url": "https://cloud.mongodb.com/api/oauth/token"
    }

    mock_file_content = json.dumps(credentials)

    with patch("pathlib.Path.exists", return_value=True):
        with patch("pathlib.Path.open", mock_open(read_data=mock_file_content)):
            manager = ServiceAccountManager()
            manager.load_credentials("test-credentials.json")

    assert manager.credentials is not None
    assert manager.credentials["client_id"] == "test-client-id"
    assert manager.credentials["client_secret"] == "test-client-secret"


def test_service_account_manager_missing_file():
    """Test ServiceAccountManager with missing credentials file."""
    with patch("pathlib.Path.exists", return_value=False):
        manager = ServiceAccountManager()
        with pytest.raises(FileNotFoundError):
            manager.load_credentials("missing-file.json")


def test_service_account_manager_invalid_credentials():
    """Test ServiceAccountManager with invalid credentials."""
    invalid_credentials = {
        "client_id": "test-client-id"
        # Missing client_secret
    }

    mock_file_content = json.dumps(invalid_credentials)

    with patch("pathlib.Path.exists", return_value=True):
        with patch("pathlib.Path.open", mock_open(read_data=mock_file_content)):
            manager = ServiceAccountManager()
            with pytest.raises(ValueError, match="Missing required fields"):
                manager.load_credentials("invalid-credentials.json")


def test_service_account_manager_get_auth():
    """Test ServiceAccountManager get_auth method."""
    credentials = {
        "client_id": "test-client-id",
        "client_secret": "test-client-secret",
        "token_url": "https://cloud.mongodb.com/api/oauth/token"
    }

    manager = ServiceAccountManager()
    manager.credentials = credentials

    auth = manager.get_auth()
    assert isinstance(auth, ServiceAccountAuth)
    assert auth.client_id == "test-client-id"
    assert auth.client_secret == "test-client-secret"


def test_service_account_manager_get_auth_no_credentials():
    """Test ServiceAccountManager get_auth without loaded credentials."""
    manager = ServiceAccountManager()

    with pytest.raises(ValueError, match="Credentials not loaded"):
        manager.get_auth()


def test_service_account_manager_create_credentials_file(tmp_path):
    """Test creating a credentials file."""
    output_file = tmp_path / "service-account.json"

    ServiceAccountManager.create_credentials_file(
        client_id="test-client-id",
        client_secret="test-client-secret",
        output_file=str(output_file)
    )

    assert output_file.exists()

    # Verify contents
    with output_file.open() as f:
        credentials = json.load(f)

    assert credentials["client_id"] == "test-client-id"
    assert credentials["client_secret"] == "test-client-secret"
    assert credentials["token_url"] == "https://cloud.mongodb.com/api/oauth/token"

    # Verify permissions (on Unix systems)
    import sys
    if sys.platform != "win32":
        import stat
        mode = output_file.stat().st_mode
        # Should be read/write for owner only (0o600)
        assert stat.S_IMODE(mode) == 0o600


def test_service_account_manager_create_with_custom_token_url(tmp_path):
    """Test creating credentials file with custom token URL."""
    output_file = tmp_path / "service-account-custom.json"

    ServiceAccountManager.create_credentials_file(
        client_id="test-client-id",
        client_secret="test-client-secret",
        output_file=str(output_file),
        token_url="https://custom.example.com/oauth/token"
    )

    with output_file.open() as f:
        credentials = json.load(f)

    assert credentials["token_url"] == "https://custom.example.com/oauth/token"


@patch('atlasui.client.service_account.httpx.Client')
@patch('atlasui.client.service_account.time.time')
def test_get_access_token_caching(mock_time, mock_client_class):
    """Test that access tokens are cached and reused."""
    # Mock time
    mock_time.return_value = 1000.0

    # Mock successful token response
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "access_token": "test-token",
        "token_type": "Bearer",
        "expires_in": 3600
    }

    mock_client_instance = Mock()
    mock_client_instance.post.return_value = mock_response
    mock_client_instance.__enter__ = Mock(return_value=mock_client_instance)
    mock_client_instance.__exit__ = Mock(return_value=False)
    mock_client_class.return_value = mock_client_instance

    auth = ServiceAccountAuth(
        client_id="test-client-id",
        client_secret="test-client-secret"
    )

    # First call - should request token
    token1 = auth._get_access_token()
    assert token1 == "test-token"
    assert mock_client_instance.post.call_count == 1

    # Second call - should use cached token
    token2 = auth._get_access_token()
    assert token2 == "test-token"
    assert mock_client_instance.post.call_count == 1  # Still 1, not 2


@patch('atlasui.client.service_account.httpx.Client')
@patch('atlasui.client.service_account.time.time')
def test_get_access_token_refresh(mock_time, mock_client_class):
    """Test that access tokens are refreshed when expired."""
    # Mock time - start at 1000, then move to 4500 (past expiry buffer)
    mock_time.side_effect = [1000.0, 4500.0]

    # Mock successful token responses
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.side_effect = [
        {
            "access_token": "first-token",
            "token_type": "Bearer",
            "expires_in": 3600
        },
        {
            "access_token": "second-token",
            "token_type": "Bearer",
            "expires_in": 3600
        }
    ]

    mock_client_instance = Mock()
    mock_client_instance.post.return_value = mock_response
    mock_client_instance.__enter__ = Mock(return_value=mock_client_instance)
    mock_client_instance.__exit__ = Mock(return_value=False)
    mock_client_class.return_value = mock_client_instance

    auth = ServiceAccountAuth(
        client_id="test-client-id",
        client_secret="test-client-secret"
    )

    # First call - should request token
    token1 = auth._get_access_token()
    assert token1 == "first-token"

    # Second call (after time has passed) - should refresh token
    token2 = auth._get_access_token()
    assert token2 == "second-token"
    assert mock_client_instance.post.call_count == 2
