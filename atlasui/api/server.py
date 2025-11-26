"""
API routes for server management operations.
"""

import os
import signal
from fastapi import APIRouter
from typing import Dict, Any

from atlasui.session_manager import get_session_manager

router = APIRouter()


@router.post("/shutdown")
async def shutdown_server() -> Dict[str, Any]:
    """
    Gracefully shut down the server.

    This endpoint closes all active MongoDB sessions and then
    sends a SIGTERM signal to shut down the FastAPI server.

    Returns:
        Shutdown confirmation message
    """
    # Close all active MongoDB sessions
    session_manager = get_session_manager()
    session_count = len(session_manager)
    session_manager.close_all_sessions()

    print(f"\nShutdown requested via API")
    print(f"Closed {session_count} MongoDB session(s)")
    print("Shutting down server...")

    # Schedule the shutdown after sending the response
    # This allows the response to be sent before the server shuts down
    import asyncio
    asyncio.create_task(shutdown_after_delay())

    return {
        "success": True,
        "message": "Server shutdown initiated",
        "sessions_closed": session_count
    }


async def shutdown_after_delay():
    """Wait a moment then shutdown the server."""
    import asyncio
    from pathlib import Path

    await asyncio.sleep(0.5)  # Give time for response to be sent

    # Read the PID from the PID file if it exists
    pid_file = Path("atlasui.pid")
    if pid_file.exists():
        try:
            # Get the main server process PID from the PID file
            main_pid = int(pid_file.read_text().strip())
            print(f"Killing main server process (PID: {main_pid})")
            os.kill(main_pid, signal.SIGTERM)
        except (ValueError, OSError, ProcessLookupError) as e:
            print(f"Failed to kill main process from PID file: {e}")
            # Fallback to killing current process
            os.kill(os.getpid(), signal.SIGTERM)
    else:
        # No PID file, just kill the current process
        print(f"No PID file found, killing current process (PID: {os.getpid()})")
        os.kill(os.getpid(), signal.SIGTERM)
