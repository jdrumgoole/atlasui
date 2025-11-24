"""
FastAPI server for AtlasUI web interface.
"""

import asyncio
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path

from atlasui.config import settings
from atlasui.api import projects, clusters, alerts, backups, users, pages, organizations, databases, server, setup, operations
from atlasui.session_manager import get_session_manager
from atlasui.operations_manager import get_operation_manager


# Background task for cleaning up expired sessions
async def cleanup_sessions_task():
    """Background task that periodically cleans up expired MongoDB sessions."""
    session_manager = get_session_manager()
    while True:
        try:
            await asyncio.sleep(300)  # Run every 5 minutes
            expired_count = session_manager.cleanup_expired_sessions()
            if expired_count > 0:
                print(f"Cleaned up {expired_count} expired MongoDB session(s)")
        except Exception as e:
            print(f"Error in session cleanup task: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI app.
    Handles startup and shutdown events.
    """
    # Startup
    print("Starting AtlasUI server...")
    print("Initializing MongoDB session manager...")
    print("Starting operation manager...")

    # Start operation manager
    operation_manager = get_operation_manager()
    await operation_manager.start()

    # Start background cleanup task
    cleanup_task = asyncio.create_task(cleanup_sessions_task())

    yield

    # Shutdown
    print("Shutting down AtlasUI server...")

    # Stop operation manager
    print("Stopping operation manager...")
    await operation_manager.stop()

    # Cancel cleanup task
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass

    # Close all MongoDB sessions
    session_manager = get_session_manager()
    session_count = len(session_manager)
    session_manager.close_all_sessions()
    print(f"Closed {session_count} MongoDB session(s)")


# Create FastAPI app with lifespan
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="MongoDB Atlas Administration UI",
    lifespan=lifespan,
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

# Add global variables to templates
templates.env.globals["app_version"] = settings.app_version
templates.env.globals["app_author"] = "joe@joedrumgoole.com"

# Include API routers
app.include_router(setup.router, prefix="/api/setup", tags=["Setup"])
app.include_router(organizations.router, prefix="/api/organizations", tags=["Organizations"])
app.include_router(projects.router, prefix="/api/projects", tags=["Projects"])
app.include_router(clusters.router, prefix="/api/clusters", tags=["Clusters"])
app.include_router(alerts.router, prefix="/api/alerts", tags=["Alerts"])
app.include_router(backups.router, prefix="/api/backups", tags=["Backups"])
app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(databases.router, prefix="/api/databases", tags=["Databases"])
app.include_router(operations.router, prefix="/api/operations", tags=["Operations"])
app.include_router(server.router, prefix="/api/server", tags=["Server"])

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
