"""
API routes for MongoDB Atlas Users and Access Management.
"""

from fastapi import APIRouter, HTTPException, Body
from typing import Dict, Any, List
from pydantic import BaseModel

from atlasui.client import AtlasClient

router = APIRouter()


class DatabaseUserRole(BaseModel):
    """Database user role."""
    roleName: str
    databaseName: str


class CreateDatabaseUserRequest(BaseModel):
    """Request model for creating a database user."""
    username: str
    password: str
    databaseName: str = "admin"
    roles: List[DatabaseUserRole]


@router.get("/{project_id}")
async def list_users(project_id: str) -> Dict[str, Any]:
    """
    List all database users in a project (shorthand route).

    Args:
        project_id: MongoDB Atlas project ID

    Returns:
        Database users list
    """
    try:
        async with AtlasClient() as client:
            return await client.get(f"/groups/{project_id}/databaseUsers")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}/database-users")
async def list_database_users(project_id: str) -> Dict[str, Any]:
    """
    List all database users in a project.

    Args:
        project_id: MongoDB Atlas project ID

    Returns:
        Database users list
    """
    try:
        async with AtlasClient() as client:
            return await client.get(f"/groups/{project_id}/databaseUsers")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}/api-keys")
async def list_api_keys(project_id: str) -> Dict[str, Any]:
    """
    List all API keys for a project.

    Args:
        project_id: MongoDB Atlas project ID

    Returns:
        API keys list
    """
    try:
        async with AtlasClient() as client:
            return await client.get(f"/groups/{project_id}/apiKeys")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{project_id}/database-users")
async def create_database_user(
    project_id: str,
    request: CreateDatabaseUserRequest
) -> Dict[str, Any]:
    """
    Create a new database user in a project.

    Args:
        project_id: MongoDB Atlas project ID
        request: Database user creation request

    Returns:
        Created database user details
    """
    try:
        # Build the request payload for Atlas API
        payload = {
            "username": request.username,
            "password": request.password,
            "databaseName": request.databaseName,
            "roles": [
                {
                    "roleName": role.roleName,
                    "databaseName": role.databaseName
                }
                for role in request.roles
            ]
        }

        async with AtlasClient() as client:
            return await client.post(f"/groups/{project_id}/databaseUsers", json=payload)
    except Exception as e:
        error_msg = str(e)
        if "409" in error_msg or "DUPLICATE" in error_msg.upper():
            raise HTTPException(
                status_code=409,
                detail=f"User '{request.username}' already exists in this project"
            )
        elif "400" in error_msg:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid request: {error_msg}"
            )
        else:
            raise HTTPException(status_code=500, detail=error_msg)
