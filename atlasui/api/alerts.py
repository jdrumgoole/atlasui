"""
API routes for MongoDB Atlas Alerts.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any

from atlasui.client import AtlasClient

router = APIRouter()


@router.get("/{project_id}")
async def list_alerts(project_id: str) -> Dict[str, Any]:
    """
    List all alerts for a project.

    Args:
        project_id: MongoDB Atlas project ID

    Returns:
        Alerts list
    """
    try:
        async with AtlasClient() as client:
            return await client.get(f"/groups/{project_id}/alerts")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}/{alert_id}")
async def get_alert(project_id: str, alert_id: str) -> Dict[str, Any]:
    """
    Get details of a specific alert.

    Args:
        project_id: MongoDB Atlas project ID
        alert_id: Alert ID

    Returns:
        Alert details
    """
    try:
        async with AtlasClient() as client:
            return await client.get(f"/groups/{project_id}/alerts/{alert_id}")
    except Exception as e:
        if "404" in str(e):
            raise HTTPException(
                status_code=404,
                detail=f"Alert {alert_id} not found in project {project_id}"
            )
        raise HTTPException(status_code=500, detail=str(e))
