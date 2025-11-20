"""
API routes for MongoDB Atlas Clusters.
"""

from fastapi import APIRouter, HTTPException, Query, Body, Response, Request
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from pymongo import MongoClient
from pymongo.errors import OperationFailure, ServerSelectionTimeoutError, ConnectionFailure, ConfigurationError
import urllib.parse

from atlasui.client import AtlasClient
from atlasui.session_manager import get_session_manager

router = APIRouter()


class ClusterLoginRequest(BaseModel):
    """Request model for cluster login."""
    connection_string: str
    username: str
    password: str


@router.post("/login")
async def login_to_cluster(
    request: ClusterLoginRequest,
    response: Response
) -> Dict[str, Any]:
    """
    Login to a cluster with credentials and list databases.

    This creates a persistent session that maintains the MongoDB connection
    for the duration of the user's session (default: 60 minutes).

    This follows MongoDB Atlas best practices:
    - URL-encodes credentials to handle special characters
    - Uses appropriate timeout settings
    - Properly handles TLS/SSL for Atlas connections
    - Maintains persistent connections for session duration

    Args:
        request: Login request containing connection string, username, and password
        response: FastAPI response object for setting cookies

    Returns:
        Session info and list of databases on the cluster
    """
    connection_string = request.connection_string.strip()

    # URL-encode username and password to handle special characters
    # This is the recommended approach per PyMongo documentation
    encoded_username = urllib.parse.quote_plus(request.username)
    encoded_password = urllib.parse.quote_plus(request.password)

    # Parse and build the authenticated connection string
    # Remove any existing credentials from the connection string
    if "mongodb+srv://" in connection_string:
        # Extract everything after mongodb+srv://
        base_url = connection_string.replace("mongodb+srv://", "")
        # Remove existing credentials if present (format: user:pass@host)
        if "@" in base_url:
            base_url = base_url.split("@", 1)[1]
        # Build authenticated URL with encoded credentials
        authenticated_url = f"mongodb+srv://{encoded_username}:{encoded_password}@{base_url}"
        # Store sanitized version without credentials
        sanitized_url = f"mongodb+srv://{base_url}"
    elif "mongodb://" in connection_string:
        # Extract everything after mongodb://
        base_url = connection_string.replace("mongodb://", "")
        # Remove existing credentials if present
        if "@" in base_url:
            base_url = base_url.split("@", 1)[1]
        # Build authenticated URL with encoded credentials
        # For non-SRV connections to Atlas, we need to ensure TLS is enabled
        authenticated_url = f"mongodb://{encoded_username}:{encoded_password}@{base_url}"
        sanitized_url = f"mongodb://{base_url}"
    else:
        raise HTTPException(
            status_code=400,
            detail="Invalid connection string format. Expected mongodb:// or mongodb+srv://"
        )

    # Extract cluster name from connection string (simplified)
    cluster_name = base_url.split('.')[0] if '.' in base_url else 'unknown'

    client = None
    session_manager = get_session_manager()

    try:
        # Connect to the cluster following MongoDB Atlas best practices
        # mongodb+srv:// automatically enables TLS for Atlas
        # Timeouts are set to fail fast for better UX
        client = MongoClient(
            authenticated_url,
            serverSelectionTimeoutMS=10000,  # 10 second timeout for server selection
            connectTimeoutMS=10000,  # 10 second timeout for initial connection
            socketTimeoutMS=10000,  # 10 second timeout for socket operations
        )

        # Force connection and verify authentication
        # The ping command will raise OperationFailure if auth fails
        client.admin.command('ping')

        # List all databases the user has access to
        database_names = client.list_database_names()

        # Get detailed stats for each database
        databases = []
        for db_name in database_names:
            try:
                db = client[db_name]
                stats = db.command("dbStats")
                databases.append({
                    "name": db_name,
                    "sizeOnDisk": stats.get("dataSize", 0),
                    "collections": stats.get("collections", 0),
                    "views": stats.get("views", 0),
                    "indexes": stats.get("indexes", 0)
                })
            except OperationFailure as e:
                # User might not have permissions for this database
                databases.append({
                    "name": db_name,
                    "error": f"Permission denied: {str(e)}"
                })
            except Exception as e:
                # Other errors fetching stats
                databases.append({
                    "name": db_name,
                    "error": str(e)
                })

        # Create a session for this connection
        session_id = session_manager.create_session(
            client=client,
            cluster_name=cluster_name,
            username=request.username,
            connection_string=sanitized_url
        )

        # Set session cookie
        response.set_cookie(
            key="mongodb_session_id",
            value=session_id,
            httponly=True,
            max_age=3600,  # 1 hour
            samesite="lax"
        )

        return {
            "success": True,
            "session_id": session_id,
            "cluster_name": cluster_name,
            "databases": databases,
            "total": len(databases),
            "message": "Session created. Connection will remain active for 60 minutes."
        }

    except OperationFailure as e:
        # Authentication failure or operation not permitted
        # Clean up client on failure
        if client:
            client.close()

        error_msg = str(e)
        if "Authentication failed" in error_msg or "auth failed" in error_msg.lower():
            raise HTTPException(
                status_code=401,
                detail="Authentication failed. Please check your username and password."
            )
        else:
            raise HTTPException(
                status_code=403,
                detail=f"Operation not permitted: {error_msg}"
            )
    except ServerSelectionTimeoutError as e:
        # Could not connect to any servers
        if client:
            client.close()

        raise HTTPException(
            status_code=503,
            detail="Could not connect to cluster. Please verify:\n"
                   "1. Connection string is correct\n"
                   "2. Your IP address is whitelisted in Atlas\n"
                   "3. Cluster is running and accessible"
        )
    except ConnectionFailure as e:
        # Network-level connection failure
        if client:
            client.close()

        raise HTTPException(
            status_code=503,
            detail=f"Connection failed: {str(e)}. Please check network connectivity."
        )
    except ConfigurationError as e:
        # Invalid connection string or configuration
        if client:
            client.close()

        raise HTTPException(
            status_code=400,
            detail=f"Invalid configuration: {str(e)}"
        )
    except Exception as e:
        # Catch-all for unexpected errors
        if client:
            client.close()

        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error: {str(e)}"
        )
    # Note: We do NOT close the client in a finally block anymore
    # The session manager will handle closing it when the session expires


@router.get("/{project_id}")
async def list_clusters(
    project_id: str,
    page_num: int = Query(1, ge=1, description="Page number"),
    items_per_page: int = Query(100, ge=1, le=500, description="Items per page"),
) -> Dict[str, Any]:
    """
    List all clusters in a project.

    Args:
        project_id: MongoDB Atlas project ID
        page_num: Page number (1-indexed)
        items_per_page: Number of items per page (max 500)

    Returns:
        Clusters list with pagination info
    """
    try:
        with AtlasClient() as client:
            return client.list_clusters(
                project_id=project_id,
                page_num=page_num,
                items_per_page=items_per_page
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}/{cluster_name}")
async def get_cluster(project_id: str, cluster_name: str) -> Dict[str, Any]:
    """
    Get details of a specific cluster.

    Args:
        project_id: MongoDB Atlas project ID
        cluster_name: Cluster name

    Returns:
        Cluster details
    """
    try:
        with AtlasClient() as client:
            return client.get_cluster(project_id, cluster_name)
    except Exception as e:
        if "404" in str(e):
            raise HTTPException(
                status_code=404,
                detail=f"Cluster {cluster_name} not found in project {project_id}"
            )
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{project_id}")
async def create_cluster(
    project_id: str,
    cluster_config: Dict[str, Any] = Body(..., description="Cluster configuration")
) -> Dict[str, Any]:
    """
    Create a new cluster in a project.

    Args:
        project_id: MongoDB Atlas project ID
        cluster_config: Cluster configuration

    Returns:
        Created cluster details
    """
    try:
        with AtlasClient() as client:
            return client.create_cluster(project_id, cluster_config)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{project_id}/{cluster_name}")
async def update_cluster(
    project_id: str,
    cluster_name: str,
    cluster_config: Dict[str, Any] = Body(..., description="Updated cluster configuration")
) -> Dict[str, Any]:
    """
    Update an existing cluster.

    Args:
        project_id: MongoDB Atlas project ID
        cluster_name: Cluster name
        cluster_config: Updated cluster configuration

    Returns:
        Updated cluster details
    """
    try:
        with AtlasClient() as client:
            return client.update_cluster(project_id, cluster_name, cluster_config)
    except Exception as e:
        if "404" in str(e):
            raise HTTPException(
                status_code=404,
                detail=f"Cluster {cluster_name} not found in project {project_id}"
            )
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{project_id}/{cluster_name}")
async def delete_cluster(project_id: str, cluster_name: str) -> Dict[str, Any]:
    """
    Delete a cluster.

    Args:
        project_id: MongoDB Atlas project ID
        cluster_name: Cluster name

    Returns:
        Deletion confirmation
    """
    try:
        with AtlasClient() as client:
            return client.delete_cluster(project_id, cluster_name)
    except Exception as e:
        if "404" in str(e):
            raise HTTPException(
                status_code=404,
                detail=f"Cluster {cluster_name} not found in project {project_id}"
            )
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/session/status")
async def get_session_status(request: Request) -> Dict[str, Any]:
    """
    Check the status of the current MongoDB session.

    Returns:
        Session information if active, or error if no session exists
    """
    session_id = request.cookies.get("mongodb_session_id")

    if not session_id:
        return {
            "active": False,
            "message": "No active session"
        }

    session_manager = get_session_manager()
    session_info = session_manager.get_session_info(session_id)

    if session_info is None:
        return {
            "active": False,
            "message": "Session expired or not found"
        }

    return {
        "active": True,
        **session_info
    }


@router.post("/session/logout")
async def logout_session(request: Request, response: Response) -> Dict[str, Any]:
    """
    Logout and terminate the current MongoDB session.

    Returns:
        Logout confirmation
    """
    session_id = request.cookies.get("mongodb_session_id")

    if not session_id:
        raise HTTPException(
            status_code=400,
            detail="No active session to logout"
        )

    session_manager = get_session_manager()
    removed = session_manager.remove_session(session_id)

    # Clear the session cookie
    response.delete_cookie(key="mongodb_session_id")

    if removed:
        return {
            "success": True,
            "message": "Session terminated successfully"
        }
    else:
        return {
            "success": True,
            "message": "Session was already expired or not found"
        }


@router.get("/session/list")
async def list_active_sessions() -> Dict[str, Any]:
    """
    List all active MongoDB sessions (admin endpoint).

    Returns:
        List of active sessions
    """
    session_manager = get_session_manager()
    sessions = session_manager.list_sessions()

    return {
        "total": len(sessions),
        "sessions": sessions
    }


@router.get("/session/databases")
async def get_databases_from_session(request: Request) -> Dict[str, Any]:
    """
    Get databases using the active session.

    This allows reloading database information without re-authenticating.

    Returns:
        List of databases from the active session
    """
    session_id = request.cookies.get("mongodb_session_id")

    if not session_id:
        raise HTTPException(
            status_code=401,
            detail="No active session. Please login first."
        )

    session_manager = get_session_manager()
    session = session_manager.get_session(session_id)

    if session is None:
        raise HTTPException(
            status_code=401,
            detail="Session expired or not found. Please login again."
        )

    try:
        # Use the existing MongoDB client from the session
        client = session.client

        # Verify connection is still alive
        client.admin.command('ping')

        # List all databases
        database_names = client.list_database_names()

        # Get detailed stats for each database
        databases = []
        for db_name in database_names:
            try:
                db = client[db_name]
                stats = db.command("dbStats")
                databases.append({
                    "name": db_name,
                    "sizeOnDisk": stats.get("dataSize", 0),
                    "collections": stats.get("collections", 0),
                    "views": stats.get("views", 0),
                    "indexes": stats.get("indexes", 0)
                })
            except OperationFailure as e:
                databases.append({
                    "name": db_name,
                    "error": f"Permission denied: {str(e)}"
                })
            except Exception as e:
                databases.append({
                    "name": db_name,
                    "error": str(e)
                })

        return {
            "success": True,
            "session_id": session_id,
            "cluster_name": session.cluster_name,
            "username": session.username,
            "databases": databases,
            "total": len(databases)
        }

    except OperationFailure as e:
        # Session connection is broken, remove it
        session_manager.remove_session(session_id)
        raise HTTPException(
            status_code=401,
            detail="Session connection lost. Please login again."
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching databases: {str(e)}"
        )
