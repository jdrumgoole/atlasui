"""
FastAPI server for AtlasUI web interface.
"""

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path

from atlasui.config import settings
from atlasui.api import projects, clusters, alerts, backups, users, pages, organizations, databases

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="MongoDB Atlas Administration UI",
)

# Get paths
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"

# Ensure directories exist
STATIC_DIR.mkdir(exist_ok=True)
TEMPLATES_DIR.mkdir(exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Setup templates
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Include API routers
app.include_router(organizations.router, prefix="/api/organizations", tags=["Organizations"])
app.include_router(projects.router, prefix="/api/projects", tags=["Projects"])
app.include_router(clusters.router, prefix="/api/clusters", tags=["Clusters"])
app.include_router(alerts.router, prefix="/api/alerts", tags=["Alerts"])
app.include_router(backups.router, prefix="/api/backups", tags=["Backups"])
app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(databases.router, prefix="/api/databases", tags=["Databases"])

# Include page routers
app.include_router(pages.router, tags=["Pages"])


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": settings.app_version}


def main() -> None:
    """Run the FastAPI server."""
    uvicorn.run(
        "atlasui.server:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
    )


if __name__ == "__main__":
    main()
