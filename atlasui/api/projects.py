"""
API routes for MongoDB Atlas Projects (Groups).
"""

from fastapi import APIRouter, HTTPException, Query
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
        with AtlasClient() as client:
            return client.list_projects(page_num=page_num, items_per_page=items_per_page)
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
        with AtlasClient() as client:
            return client.get_project(project_id)
    except Exception as e:
        if "404" in str(e):
            raise HTTPException(status_code=404, detail=f"Project {project_id} not found")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{project_id}")
async def delete_project(project_id: str) -> Dict[str, Any]:
    """
    Delete a project.

    Args:
        project_id: MongoDB Atlas project ID

    Returns:
        Deletion confirmation
    """
    try:
        with AtlasClient() as client:
            result = client.delete_project(project_id)
            return {"success": True, "message": f"Project {project_id} deleted successfully", "result": result}
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
                with AtlasClient() as client:
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
