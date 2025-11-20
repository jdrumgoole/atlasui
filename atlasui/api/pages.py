"""
Web page routes for AtlasUI.
"""

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from atlasui.client import AtlasClient

router = APIRouter()

# Setup templates
TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Redirect home to organizations page."""
    return RedirectResponse(url="/organizations", status_code=302)


@router.get("/organizations", response_class=HTMLResponse)
async def organizations(request: Request):
    """Render the organizations list page."""
    return templates.TemplateResponse("organizations.html", {"request": request})


@router.get("/organizations/{org_id_or_name}/projects", response_class=HTMLResponse)
async def organization_projects(request: Request, org_id_or_name: str):
    """Render the projects page for a specific organization."""
    return templates.TemplateResponse("projects.html", {
        "request": request,
        "org_id_or_name": org_id_or_name
    })


@router.get("/projects/{project_id_or_name}", response_class=HTMLResponse)
async def project_clusters(request: Request, project_id_or_name: str):
    """Render the clusters page for a specific project."""
    return templates.TemplateResponse("clusters.html", {
        "request": request,
        "project_id_or_name": project_id_or_name
    })


@router.get("/projects")
async def projects_redirect(request: Request):
    """Redirect to the first organization's projects page."""
    try:
        with AtlasClient() as client:
            orgs_data = client.list_organizations(page_num=1, items_per_page=1)
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
    return templates.TemplateResponse("all_clusters.html", {"request": request})


@router.get("/clusters/{cluster_name}/databases", response_class=HTMLResponse)
async def cluster_databases(request: Request, cluster_name: str):
    """Render the databases page for a specific cluster."""
    return templates.TemplateResponse("databases.html", {
        "request": request,
        "cluster_name": cluster_name
    })
