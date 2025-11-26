"""
API routes for MongoDB Atlas Clusters.
"""

from fastapi import APIRouter, HTTPException, Query, Body, Response, Request
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from pymongo import MongoClient
from pymongo.errors import OperationFailure, ServerSelectionTimeoutError, ConnectionFailure, ConfigurationError
import urllib.parse
import time
from slowapi import Limiter
from slowapi.util import get_remote_address

from atlasui.client import AtlasClient
from atlasui.session_manager import get_session_manager
from atlasui.operations_manager import get_operation_manager, OperationType

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

# Simple cache for cluster listings (TTL: 30 seconds)
_cluster_cache = {}
_cache_ttl = 30  # seconds


class ClusterLoginRequest(BaseModel):
    """Request model for cluster login."""
    connection_string: str
    username: str
    password: str


@router.post("/login")
@limiter.limit("10/minute")
async def login_to_cluster(
    request: Request,
    login_request: ClusterLoginRequest,
    response: Response
) -> Dict[str, Any]:
    """
    Login to a cluster with credentials and list databases.

    Rate limited to 10 requests per minute to prevent brute force attacks.

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
    connection_string = login_request.connection_string.strip()

    # URL-encode username and password to handle special characters
    # This is the recommended approach per PyMongo documentation
    encoded_username = urllib.parse.quote_plus(login_request.username)
    encoded_password = urllib.parse.quote_plus(login_request.password)

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
            username=login_request.username,
            connection_string=sanitized_url
        )

        # Set session cookie with security flags
        # Note: secure=True requires HTTPS in production (localhost exempt for development)
        response.set_cookie(
            key="mongodb_session_id",
            value=session_id,
            httponly=True,  # Prevents JavaScript access
            secure=True,    # Only send over HTTPS (browsers allow localhost exception)
            samesite="strict",  # Strict CSRF protection
            max_age=3600,  # 1 hour
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
    List all clusters in a project (regular clusters only, not Flex).

    Args:
        project_id: MongoDB Atlas project ID
        page_num: Page number (1-indexed)
        items_per_page: Number of items per page (max 500)

    Returns:
        Clusters list with pagination info
    """
    # Check cache
    cache_key = f"clusters_{project_id}_{page_num}_{items_per_page}"
    now = time.time()

    if cache_key in _cluster_cache:
        cached_data, cached_time = _cluster_cache[cache_key]
        if now - cached_time < _cache_ttl:
            return cached_data

    # Fetch from Atlas API
    try:
        async with AtlasClient() as client:
            result = await client.list_clusters(
                project_id=project_id,
                page_num=page_num,
                items_per_page=items_per_page
            )

        # Cache the result
        _cluster_cache[cache_key] = (result, now)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}/flex/list")
async def list_flex_clusters(
    project_id: str,
    page_num: int = Query(1, ge=1, description="Page number"),
    items_per_page: int = Query(100, ge=1, le=500, description="Items per page"),
) -> Dict[str, Any]:
    """
    List all Flex clusters in a project.

    As of January 2025, Flex clusters are in a separate API endpoint.

    Args:
        project_id: MongoDB Atlas project ID
        page_num: Page number (1-indexed)
        items_per_page: Number of items per page (max 500)

    Returns:
        Flex clusters list with pagination info
    """
    # Check cache
    cache_key = f"flex_{project_id}_{page_num}_{items_per_page}"
    now = time.time()

    if cache_key in _cluster_cache:
        cached_data, cached_time = _cluster_cache[cache_key]
        if now - cached_time < _cache_ttl:
            return cached_data

    # Fetch from Atlas API
    try:
        async with AtlasClient() as client:
            result = await client.list_flex_clusters(
                project_id=project_id,
                page_num=page_num,
                items_per_page=items_per_page
            )

        # Cache the result
        _cluster_cache[cache_key] = (result, now)
        return result
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
        async with AtlasClient() as client:
            return await client.get_cluster(project_id, cluster_name)
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

    This endpoint handles M0, M10+, and other regular clusters.
    For Flex clusters, use the dedicated /flex endpoint.

    This endpoint queues the operation and returns immediately.
    Use the /api/operations/stream endpoint to monitor progress.

    Args:
        project_id: MongoDB Atlas project ID
        cluster_config: Cluster configuration

    Returns:
        Operation ID and initial status
    """
    cluster_name = cluster_config.get("name", "Unknown")

    # Queue the operation
    manager = get_operation_manager()
    operation_id = manager.queue_operation(
        type=OperationType.CREATE_CLUSTER,
        name=f"Creating cluster: {cluster_name}",
        metadata={
            "project_id": project_id,
            "cluster_config": cluster_config
        }
    )

    return {
        "operation_id": operation_id,
        "message": f"Cluster creation queued for {cluster_name}",
        "cluster_name": cluster_name
    }


@router.post("/{project_id}/flex")
async def create_flex_cluster(
    project_id: str,
    cluster_config: Dict[str, Any] = Body(..., description="Flex cluster configuration")
) -> Dict[str, Any]:
    """
    Create a new Flex cluster in a project.

    As of January 2025, Flex clusters use a dedicated API endpoint
    (/api/atlas/v2/groups/{groupId}/flexClusters).

    This endpoint queues the operation and returns immediately.
    Use the /api/operations/stream endpoint to monitor progress.

    Args:
        project_id: MongoDB Atlas project ID
        cluster_config: Flex cluster configuration

    Returns:
        Operation ID and initial status
    """
    cluster_name = cluster_config.get("name", "Unknown")

    # Queue the operation
    manager = get_operation_manager()
    operation_id = manager.queue_operation(
        type=OperationType.CREATE_FLEX_CLUSTER,
        name=f"Creating Flex cluster: {cluster_name}",
        metadata={
            "project_id": project_id,
            "cluster_config": cluster_config
        }
    )

    return {
        "operation_id": operation_id,
        "message": f"Flex cluster creation queued for {cluster_name}",
        "cluster_name": cluster_name
    }


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
        async with AtlasClient() as client:
            return await client.update_cluster(project_id, cluster_name, cluster_config)
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
    Delete a cluster (automatically detects if it's a Flex cluster).

    This endpoint queues the operation and returns immediately.
    The operation manager will automatically detect whether this is a
    regular cluster or Flex cluster and use the appropriate API endpoint.
    Use the /api/operations/stream endpoint to monitor progress.

    Args:
        project_id: MongoDB Atlas project ID
        cluster_name: Cluster name

    Returns:
        Operation ID and initial status
    """
    # Queue the operation - the operation manager will handle detection
    manager = get_operation_manager()
    operation_id = manager.queue_operation(
        type=OperationType.DELETE_CLUSTER,
        name=f"Deleting cluster: {cluster_name}",
        metadata={
            "project_id": project_id,
            "cluster_name": cluster_name
        }
    )

    return {
        "operation_id": operation_id,
        "message": f"Cluster deletion queued for {cluster_name}",
        "cluster_name": cluster_name
    }


@router.post("/{project_id}/{cluster_name}/pause")
async def pause_cluster(project_id: str, cluster_name: str) -> Dict[str, Any]:
    """
    Pause a cluster.

    Pausing a cluster stops compute but preserves data. This reduces costs
    while maintaining your data and cluster configuration.

    Only dedicated clusters (M10+) can be paused.
    M0 (Free Tier) and Flex clusters cannot be paused.

    Args:
        project_id: MongoDB Atlas project ID
        cluster_name: Cluster name

    Returns:
        Updated cluster details
    """
    try:
        async with AtlasClient() as client:
            result = await client.pause_cluster(project_id, cluster_name)
            return {
                "success": True,
                "message": f"Cluster {cluster_name} is being paused",
                "cluster": result
            }
    except Exception as e:
        error_msg = str(e)
        if "M0" in error_msg or "free tier" in error_msg.lower():
            raise HTTPException(
                status_code=400,
                detail="M0 (Free Tier) clusters cannot be paused"
            )
        elif "Flex" in error_msg:
            raise HTTPException(
                status_code=400,
                detail="Flex clusters cannot be paused"
            )
        elif "404" in error_msg:
            raise HTTPException(
                status_code=404,
                detail=f"Cluster {cluster_name} not found in project {project_id}"
            )
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{project_id}/{cluster_name}/resume")
async def resume_cluster(project_id: str, cluster_name: str) -> Dict[str, Any]:
    """
    Resume a paused cluster.

    After resuming a cluster, you cannot pause it again for 60 minutes.
    The client should track this cooldown period.

    Args:
        project_id: MongoDB Atlas project ID
        cluster_name: Cluster name

    Returns:
        Updated cluster details with resume timestamp for cooldown tracking
    """
    try:
        async with AtlasClient() as client:
            result = await client.resume_cluster(project_id, cluster_name)
            return {
                "success": True,
                "message": f"Cluster {cluster_name} is being resumed",
                "cluster": result,
                "resumed_at": time.time(),  # Unix timestamp for 60-min cooldown tracking
                "cooldown_ends_at": time.time() + 3600  # 60 minutes from now
            }
    except Exception as e:
        error_msg = str(e)
        if "404" in error_msg:
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
