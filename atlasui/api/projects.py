"""
API routes for MongoDB Atlas Projects (Groups).
"""

from fastapi import APIRouter, HTTPException, Query, Body
from typing import Dict, Any, List

from atlasui.client import AtlasClient

router = APIRouter()


@router.get("/")
async def list_projects(
    page_num: int = Query(1, ge=1, description="Page number"),
    items_per_page: int = Query(100, ge=1, le=500, description="Items per page"),
) -> Dict[str, Any]:
    """
    List all MongoDB Atlas projects.

    Args:
        page_num: Page number (1-indexed)
        items_per_page: Number of items per page (max 500)

    Returns:
        Projects list with pagination info
    """
    try:
        async with AtlasClient() as client:
            return await client.list_projects(page_num=page_num, items_per_page=items_per_page)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/")
async def create_project(
    name: str = Body(..., embed=True),
    orgId: str = Body(..., embed=True)
) -> Dict[str, Any]:
    """
    Create a new project.

    Args:
        name: Project name
        orgId: Organization ID

    Returns:
        Operation queued confirmation
    """
    try:
        # Queue the creation operation
        from atlasui.operations_manager import get_operation_manager, OperationType
        manager = get_operation_manager()
        operation_id = manager.queue_operation(
            type=OperationType.CREATE_PROJECT,
            name=f"Creating project: {name}",
            metadata={"name": name, "org_id": orgId}
        )

        return {
            "success": True,
            "message": f"Project creation queued",
            "operation_id": operation_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}")
async def get_project(project_id: str) -> Dict[str, Any]:
    """
    Get details of a specific project.

    Args:
        project_id: MongoDB Atlas project ID

    Returns:
        Project details
    """
    try:
        async with AtlasClient() as client:
            return await client.get_project(project_id)
    except Exception as e:
        if "404" in str(e):
            raise HTTPException(status_code=404, detail=f"Project {project_id} not found")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{project_id}")
async def delete_project(
    project_id: str,
    confirmed: bool = Query(False, description="Confirm deletion of clusters")
) -> Dict[str, Any]:
    """
    Delete a project.

    Args:
        project_id: MongoDB Atlas project ID
        confirmed: Whether user has confirmed deletion of clusters

    Returns:
        Operation queued confirmation or confirmation request
    """
    try:
        # Get project name for the operation display
        project_name = project_id  # Default to ID
        async with AtlasClient() as client:
            try:
                project_data = await client.get_project(project_id)
                project_name = project_data.get("name", project_id)
            except Exception:
                pass  # If we can't get the name, use the ID

            # Check for clusters in the project (both regular and Flex)
            clusters = []
            flex_clusters = []
            try:
                clusters_data = await client.list_clusters(project_id)
                clusters = clusters_data.get("results", [])
            except Exception:
                pass  # If we can't list clusters, proceed anyway

            # Also check for Flex clusters (they use a separate API endpoint)
            try:
                flex_clusters_data = await client.list_flex_clusters(project_id)
                flex_clusters = flex_clusters_data.get("results", [])
            except Exception:
                pass  # If we can't list Flex clusters, proceed anyway

            # Combine both types
            all_clusters = clusters + flex_clusters

            # If not confirmed, require confirmation (always, regardless of clusters)
            if not confirmed:
                cluster_info = []
                for cluster in all_clusters:
                    cluster_info.append({
                        "name": cluster.get("name"),
                        "type": cluster.get("clusterType", "REPLICASET"),
                        "state": cluster.get("stateName", "UNKNOWN")
                    })

                message = f"This project contains {len(all_clusters)} cluster(s). All clusters will be deleted." if all_clusters else "This project will be permanently deleted."

                return {
                    "confirmation_required": True,
                    "project_name": project_name,
                    "clusters": cluster_info,
                    "message": message
                }

        # Queue the deletion operation (with cluster info if any)
        from atlasui.operations_manager import get_operation_manager, OperationType
        manager = get_operation_manager()

        cluster_names = [c.get("name") for c in all_clusters] if all_clusters else []

        operation_id = manager.queue_operation(
            type=OperationType.DELETE_PROJECT,
            name=f"Deleting project: {project_name}",
            metadata={
                "project_id": project_id,
                "project_name": project_name,
                "clusters": cluster_names
            }
        )

        return {
            "success": True,
            "message": f"Project deletion queued",
            "operation_id": operation_id
        }
    except Exception as e:
        error_str = str(e)

        # Handle 404 - Project not found
        if "404" in error_str:
            raise HTTPException(status_code=404, detail=f"Project {project_id} not found")

        # Handle 409 - Conflict (project has active resources)
        if "409" in error_str or "Conflict" in error_str:
            # Try to get detailed information about what's blocking deletion
            blocking_resources = []

            try:
                async with AtlasClient() as client:
                    # Check for clusters
                    try:
                        clusters_data = client.list_clusters(project_id)
                        clusters = clusters_data.get("results", [])
                        if clusters:
                            cluster_names = [c.get("name") for c in clusters]
                            blocking_resources.append(f"{len(clusters)} cluster(s): {', '.join(cluster_names)}")
                    except Exception:
                        pass

                    # Check for database users
                    try:
                        users_response = client.get(f"/groups/{project_id}/databaseUsers")
                        users = users_response.get("results", [])
                        if users:
                            user_names = [u.get("username") for u in users[:5]]  # Show first 5
                            user_count = len(users)
                            if user_count > 5:
                                blocking_resources.append(f"{user_count} database user(s): {', '.join(user_names)}, and {user_count - 5} more")
                            else:
                                blocking_resources.append(f"{user_count} database user(s): {', '.join(user_names)}")
                    except Exception:
                        pass

            except Exception:
                pass

            if blocking_resources:
                detail = f"Cannot delete project. It contains:\n• " + "\n• ".join(blocking_resources) + "\n\nPlease remove all resources before deleting the project."
            else:
                detail = "Cannot delete project. It contains active resources (possibly IP access lists, alert configurations, custom roles, or other settings). Please check the Atlas console and remove all resources before deleting the project."

            raise HTTPException(status_code=409, detail=detail)

        # Handle other "cannot delete" errors
        if "CANNOT_DELETE" in error_str or "CANNOT_CLOSE_GROUP_ACTIVE" in error_str:
            raise HTTPException(
                status_code=400,
                detail="Cannot delete project. Please ensure all clusters and resources are deleted first."
            )

        # Generic error
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}/access-list")
async def get_project_access_list(project_id: str) -> Dict[str, Any]:
    """
    Get IP access list (whitelist) for a specific project.

    Args:
        project_id: MongoDB Atlas project ID

    Returns:
        IP access list entries
    """
    try:
        async with AtlasClient() as client:
            return await client.get(f"/groups/{project_id}/accessList")
    except Exception as e:
        if "404" in str(e):
            # No access list entries or project not found - return empty results
            return {"results": [], "totalCount": 0}
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{project_id}/access-list")
async def add_ip_to_access_list(
    project_id: str,
    ip_address: str = Body(None, embed=True),
    cidr_block: str = Body(None, embed=True),
    comment: str = Body(None, embed=True)
) -> Dict[str, Any]:
    """
    Add an IP address or CIDR block to the project's access list.

    Args:
        project_id: MongoDB Atlas project ID
        ip_address: Single IP address (e.g., "192.168.1.1")
        cidr_block: CIDR block (e.g., "192.168.1.0/24")
        comment: Optional comment for the entry

    Returns:
        Created access list entry
    """
    if not ip_address and not cidr_block:
        raise HTTPException(
            status_code=400,
            detail="Either ip_address or cidr_block must be provided"
        )

    try:
        async with AtlasClient() as client:
            # Build the entry - Atlas API accepts an array of entries
            entry: Dict[str, Any] = {}
            if ip_address:
                entry["ipAddress"] = ip_address
            elif cidr_block:
                entry["cidrBlock"] = cidr_block

            if comment:
                entry["comment"] = comment

            # Atlas API expects an array of entries
            result = await client.post(
                f"/groups/{project_id}/accessList",
                json=[entry]
            )
            return {
                "success": True,
                "message": "IP address added to access list",
                "results": result.get("results", [result])
            }
    except Exception as e:
        error_str = str(e)
        if "DUPLICATE" in error_str or "already exists" in error_str.lower():
            raise HTTPException(
                status_code=409,
                detail="This IP address or CIDR block already exists in the access list"
            )
        if "INVALID" in error_str:
            raise HTTPException(
                status_code=400,
                detail="Invalid IP address or CIDR block format"
            )
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{project_id}/access-list/{entry_value}")
async def delete_ip_from_access_list(
    project_id: str,
    entry_value: str
) -> Dict[str, Any]:
    """
    Remove an IP address or CIDR block from the project's access list.

    Args:
        project_id: MongoDB Atlas project ID
        entry_value: IP address or CIDR block to remove (URL-encoded if contains /)

    Returns:
        Deletion confirmation
    """
    try:
        async with AtlasClient() as client:
            # The entry_value should be URL-encoded for CIDR blocks
            # FastAPI handles URL decoding automatically
            await client.delete(f"/groups/{project_id}/accessList/{entry_value}")
            return {
                "success": True,
                "message": f"IP address {entry_value} removed from access list"
            }
    except Exception as e:
        error_str = str(e)
        if "404" in error_str:
            raise HTTPException(
                status_code=404,
                detail=f"IP address {entry_value} not found in access list"
            )
        raise HTTPException(status_code=500, detail=str(e))
