"""
Databases API routes.
"""

from fastapi import APIRouter, HTTPException
from typing import Any, Dict, List
from atlasui.client import AtlasClient

router = APIRouter()


@router.get("/{project_id}/{cluster_name}")
async def list_databases(
    project_id: str,
    cluster_name: str
) -> Dict[str, Any]:
    """
    List all databases in a cluster.

    Note: The Atlas Admin API doesn't provide a direct database listing endpoint.
    This endpoint returns process information which may include database statistics.

    Args:
        project_id: Project ID
        cluster_name: Cluster name

    Returns:
        Database information response
    """
    try:
        async with AtlasClient() as client:
            # Get database names (currently returns empty list)
            # This is a placeholder for future enhancement
            database_names = client.get_cluster_databases(project_id, cluster_name)

            return {
                "results": [{"name": db} for db in database_names],
                "totalCount": len(database_names)
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}/{cluster_name}/processes")
async def list_cluster_processes(
    project_id: str,
    cluster_name: str
) -> Dict[str, Any]:
    """
    List cluster processes (which may include database stats).

    Args:
        project_id: Project ID
        cluster_name: Cluster name

    Returns:
        Cluster processes response
    """
    try:
        async with AtlasClient() as client:
            return await client.list_databases(project_id, cluster_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
