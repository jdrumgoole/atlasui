"""
Organizations API routes.
"""

from fastapi import APIRouter, HTTPException, Query, Body
from typing import Any, Dict
import json
from atlasui.client import AtlasClient

router = APIRouter()


@router.post("/")
async def create_organization(
    name: str = Body(..., embed=True),
    restrictEmployeeAccess: bool = Body(False, embed=True)
) -> Dict[str, Any]:
    """
    Create a new organization.

    Args:
        name: Organization name
        restrictEmployeeAccess: Whether to restrict MongoDB employee access

    Returns:
        Created organization details
    """
    try:
        async with AtlasClient() as client:
            payload = {
                "name": name,
            }
            if restrictEmployeeAccess:
                payload["restrictEmployeeAccess"] = True

            # Try to get more detailed error info
            try:
                return await client.post("/orgs", json=payload)
            except Exception as inner_e:
                # Try to extract and parse the error response
                error_msg = str(inner_e)

                if hasattr(inner_e, 'response') and hasattr(inner_e.response, 'text'):
                    try:
                        # Try to parse JSON error response
                        error_data = json.loads(inner_e.response.text)
                        error_code = error_data.get('errorCode', '')

                        # Provide specific error messages based on error code
                        if error_code == 'API_KEY_MUST_BE_ASSOCIATED_WITH_PAYING_ORG':
                            detail = (
                                "Cannot create organization: Your API key must be associated with a paying organization. "
                                "Free tier organizations cannot create new organizations. "
                                "Please upgrade your organization to a paid tier or use an API key from a paying organization. "
                                "You can create organizations manually in the Atlas console at: "
                                "https://cloud.mongodb.com/v2#/preferences/organizations"
                            )
                        else:
                            # Generic error with all available details
                            detail = error_data.get('detail', error_msg)

                        raise HTTPException(status_code=400, detail=detail)
                    except json.JSONDecodeError:
                        # If JSON parsing fails, use the raw response
                        error_msg = f"{error_msg} - Response: {inner_e.response.text}"

                raise HTTPException(
                    status_code=400,
                    detail=f"Atlas API Error: {error_msg}"
                )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/")
async def list_organizations(
    page_num: int = Query(1, ge=1, description="Page number"),
    items_per_page: int = Query(100, ge=1, le=500, description="Items per page"),
) -> Dict[str, Any]:
    """
    List all organizations.

    Args:
        page_num: Page number (1-indexed)
        items_per_page: Number of items per page

    Returns:
        Organizations list response
    """
    try:
        async with AtlasClient() as client:
            return await client.list_organizations(
                page_num=page_num,
                items_per_page=items_per_page
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{org_id}")
async def get_organization(org_id: str) -> Dict[str, Any]:
    """
    Get a specific organization.

    Args:
        org_id: Organization ID

    Returns:
        Organization details
    """
    try:
        async with AtlasClient() as client:
            return await client.get_organization(org_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{org_id}/projects")
async def list_organization_projects(
    org_id: str,
    page_num: int = Query(1, ge=1, description="Page number"),
    items_per_page: int = Query(100, ge=1, le=500, description="Items per page"),
) -> Dict[str, Any]:
    """
    List all projects in an organization.

    Args:
        org_id: Organization ID
        page_num: Page number (1-indexed)
        items_per_page: Number of items per page

    Returns:
        Projects list response for the organization
    """
    try:
        async with AtlasClient() as client:
            return await client.list_organization_projects(
                org_id=org_id,
                page_num=page_num,
                items_per_page=items_per_page
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
