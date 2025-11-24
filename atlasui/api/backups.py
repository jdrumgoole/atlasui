"""
API routes for MongoDB Atlas Backups.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any

from atlasui.client import AtlasClient

router = APIRouter()


@router.get("/{project_id}/{cluster_name}/snapshots")
async def list_snapshots(project_id: str, cluster_name: str) -> Dict[str, Any]:
    """
    List all backup snapshots for a cluster.

    Args:
        project_id: MongoDB Atlas project ID
        cluster_name: Cluster name

    Returns:
        Snapshots list
    """
    try:
        async with AtlasClient() as client:
            return await client.get(
                f"/groups/{project_id}/clusters/{cluster_name}/backup/snapshots"
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}/{cluster_name}/schedule")
async def get_backup_schedule(project_id: str, cluster_name: str) -> Dict[str, Any]:
    """
    Get backup schedule for a cluster.

    Args:
        project_id: MongoDB Atlas project ID
        cluster_name: Cluster name

    Returns:
        Backup schedule configuration
    """
    try:
        async with AtlasClient() as client:
            return await client.get(
                f"/groups/{project_id}/clusters/{cluster_name}/backup/schedule"
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
