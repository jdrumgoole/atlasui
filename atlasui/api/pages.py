"""
Web page routes for AtlasUI.
"""

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from atlasui.client import AtlasClient
from atlasui.config import settings

router = APIRouter()

# Setup templates
TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Add global variables to templates
templates.env.globals["app_version"] = settings.app_version
templates.env.globals["app_author"] = "joe@joedrumgoole.com"


def is_configured() -> bool:
    """Check if AtlasUI is configured with credentials."""
    env_path = Path(".env")

    if not env_path.exists():
        return False

    try:
        with env_path.open('r') as f:
            content = f.read()

        # Check for API Key configuration
        has_api_key = "ATLAS_PUBLIC_KEY" in content and "ATLAS_PRIVATE_KEY" in content

        # Check for Service Account configuration
        has_service_account = "ATLAS_SERVICE_ACCOUNT_CLIENT_ID" in content

        return has_api_key or has_service_account
    except Exception:
        return False


@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Redirect home to setup or organizations based on configuration status."""
    if not is_configured():
        return RedirectResponse(url="/setup", status_code=302)
    return RedirectResponse(url="/organizations", status_code=302)


@router.get("/setup", response_class=HTMLResponse)
async def setup_wizard(request: Request, register: bool = False):
    """Render the setup wizard page."""
    # If already configured and not explicitly registering a new org, redirect to organizations
    if is_configured() and not register:
        return RedirectResponse(url="/organizations", status_code=302)

    return templates.TemplateResponse(request, "setup.html")


@router.get("/organizations", response_class=HTMLResponse)
async def organizations(request: Request):
    """Render the organizations list page."""
    return templates.TemplateResponse(request, "organizations.html")


@router.get("/organizations/{org_id_or_name}/projects", response_class=HTMLResponse)
async def organization_projects(request: Request, org_id_or_name: str):
    """Render the projects page for a specific organization."""
    return templates.TemplateResponse(
        request,
        "projects.html",
        {"org_id_or_name": org_id_or_name}
    )


@router.get("/projects")
async def projects_redirect(request: Request):
    """Redirect to the first organization's projects page."""
    try:
        async with AtlasClient() as client:
            orgs_data = await client.list_organizations(page_num=1, items_per_page=1)
            orgs = orgs_data.get("results", [])
            if orgs:
                first_org = orgs[0]
                org_name = first_org.get("name", first_org.get("id"))
                return RedirectResponse(url=f"/organizations/{org_name}/projects", status_code=302)
            else:
                raise HTTPException(status_code=404, detail="No organizations found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch organizations: {str(e)}")


@router.get("/clusters", response_class=HTMLResponse)
async def all_clusters(request: Request):
    """Render the all clusters page showing clusters from all projects."""
    return templates.TemplateResponse(request, "all_clusters.html")


@router.get("/clusters/{cluster_name}/databases", response_class=HTMLResponse)
async def cluster_databases(request: Request, cluster_name: str):
    """Render the databases page for a specific cluster."""
    return templates.TemplateResponse(
        request,
        "databases.html",
        {"cluster_name": cluster_name}
    )
