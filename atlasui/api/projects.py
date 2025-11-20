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
