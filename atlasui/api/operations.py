"""
API routes for Operation Management.
"""

from fastapi import APIRouter, Response
from fastapi.responses import StreamingResponse
from typing import Dict, Any, List
import asyncio
import json
import logging

from atlasui.operations_manager import get_operation_manager

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/stream")
async def stream_operations():
    """
    Server-Sent Events endpoint for real-time operation updates.

    Clients connect to this endpoint to receive live updates about
    operation status changes.
    """
    async def event_generator():
        """Generate SSE events"""
        manager = get_operation_manager()

        # Queue to receive events
        event_queue = asyncio.Queue()

        # Listener callback
        async def listener(event: str, operation: Dict[str, Any]):
            await event_queue.put((event, operation))

        # Register listener
        manager.add_listener(listener)

        try:
            # Send initial state - all existing operations
            for operation in manager.get_all_operations():
                yield f"event: init\ndata: {json.dumps(operation)}\n\n"

            # Stream updates
            while True:
                try:
                    # Wait for next event with timeout
                    event, operation = await asyncio.wait_for(
                        event_queue.get(),
                        timeout=30.0  # Send keepalive every 30 seconds
                    )

                    # Send event to client
                    yield f"event: {event}\ndata: {json.dumps(operation)}\n\n"

                except asyncio.TimeoutError:
                    # Send keepalive comment
                    yield ": keepalive\n\n"

        except asyncio.CancelledError:
            logger.info("SSE client disconnected")
        finally:
            # Cleanup
            manager.remove_listener(listener)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )


@router.get("/")
async def list_operations() -> List[Dict[str, Any]]:
    """
    Get all operations.

    Returns:
        List of all operations with their current status
    """
    manager = get_operation_manager()
    return manager.get_all_operations()


@router.delete("/{operation_id}")
async def clear_operation(operation_id: int) -> Dict[str, Any]:
    """
    Clear a completed or failed operation.

    Args:
        operation_id: Operation ID to clear

    Returns:
        Success status
    """
    manager = get_operation_manager()
    success = manager.clear_operation(operation_id)

    if success:
        return {"success": True, "message": f"Operation {operation_id} cleared"}
    else:
        return {
            "success": False,
            "message": f"Operation {operation_id} not found or not in terminal state"
        }
