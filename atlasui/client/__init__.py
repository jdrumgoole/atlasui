"""
MongoDB Atlas API Client.

This module provides a Python client for interacting with the MongoDB Atlas Administration API.
Supports both API key authentication (legacy) and service account authentication (recommended).
"""

from atlasui.client.base import AtlasClient
from atlasui.client.auth import DigestAuth
from atlasui.client.service_account import ServiceAccountAuth, ServiceAccountManager

__all__ = ["AtlasClient", "DigestAuth", "ServiceAccountAuth", "ServiceAccountManager"]
