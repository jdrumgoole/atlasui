"""
Backend Operation Queue Manager

Manages long-running Atlas operations (cluster creation, deletion, etc.)
and provides real-time status updates via Server-Sent Events.
"""

import asyncio
import time
from datetime import datetime
from typing import Dict, Any, Optional, Callable, List
from enum import Enum
import logging

from atlasui.client import AtlasClient

logger = logging.getLogger(__name__)


class OperationStatus(str, Enum):
    """Operation status enum"""
    QUEUED = "queued"
    IN_PROGRESS = "in-progress"
    COMPLETED = "completed"
    FAILED = "failed"


class OperationType(str, Enum):
    """Operation type enum"""
    CREATE_CLUSTER = "create_cluster"
    DELETE_CLUSTER = "delete_cluster"
    CREATE_FLEX_CLUSTER = "create_flex_cluster"
    DELETE_FLEX_CLUSTER = "delete_flex_cluster"
    CREATE_PROJECT = "create_project"
    DELETE_PROJECT = "delete_project"


class Operation:
    """Represents a single operation"""

    def __init__(
        self,
        id: int,
        type: OperationType,
        name: str,
        metadata: Dict[str, Any]
    ):
        self.id = id
        self.type = type
        self.name = name
        self.metadata = metadata
        self.status = OperationStatus.QUEUED
        self.progress: Optional[str] = None
        self.result: Optional[Dict[str, Any]] = None
        self.error: Optional[str] = None
        self.queued_at = datetime.utcnow()
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        # Track complete history of status changes with timestamps
        self.status_history: List[Dict[str, Any]] = []
        self._add_history_entry("queued", "Operation queued")

    def _add_history_entry(self, status: str, message: str):
        """Add an entry to the status history"""
        self.status_history.append({
            "timestamp": datetime.utcnow().isoformat(),
            "status": status,
            "message": message
        })

    def update_status(self, status: OperationStatus, message: Optional[str] = None):
        """Update status and add to history"""
        self.status = status
        if message:
            self._add_history_entry(status.value, message)

    def update_progress(self, message: str):
        """Update progress and add to history"""
        self.progress = message
        self._add_history_entry(self.status.value, message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert operation to dictionary for JSON serialization"""
        return {
            "id": self.id,
            "type": self.type.value,
            "name": self.name,
            "metadata": self.metadata,
            "status": self.status.value,
            "progress": self.progress,
            "result": self.result,
            "error": self.error,
            "queuedAt": self.queued_at.isoformat() if self.queued_at else None,
            "startedAt": self.started_at.isoformat() if self.started_at else None,
            "completedAt": self.completed_at.isoformat() if self.completed_at else None,
            "statusHistory": self.status_history,
        }


class OperationManager:
    """
    Manages operation queue and background workers.

    Singleton instance that handles:
    - Queueing operations
    - Running background workers to execute operations
    - Polling Atlas API for operation status
    - Emitting events for status updates
    """

    _instance: Optional['OperationManager'] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True
        self.operations: Dict[int, Operation] = {}
        self.operation_id_counter = 0
        self.listeners: List[Callable] = []
        self.worker_task: Optional[asyncio.Task] = None
        self.is_running = False
        self.running_tasks: set = set()  # Track running operation tasks
        self.max_concurrent_operations = 5  # Maximum concurrent operations

    async def start(self):
        """Start the operation manager and background worker"""
        if not self.is_running:
            self.is_running = True
            self.worker_task = asyncio.create_task(self._worker_loop())
            logger.info("OperationManager started")

    async def stop(self):
        """Stop the operation manager"""
        self.is_running = False
        if self.worker_task:
            self.worker_task.cancel()
            try:
                await self.worker_task
            except asyncio.CancelledError:
                pass
        logger.info("OperationManager stopped")

    def add_listener(self, callback: Callable):
        """Add a listener for operation events"""
        self.listeners.append(callback)

    def remove_listener(self, callback: Callable):
        """Remove a listener"""
        if callback in self.listeners:
            self.listeners.remove(callback)

    async def _notify_listeners(self, event: str, operation: Operation):
        """Notify all listeners of an event"""
        for listener in self.listeners:
            try:
                if asyncio.iscoroutinefunction(listener):
                    await listener(event, operation.to_dict())
                else:
                    listener(event, operation.to_dict())
            except Exception as e:
                logger.error(f"Error in listener: {e}")

    def queue_operation(
        self,
        type: OperationType,
        name: str,
        metadata: Dict[str, Any]
    ) -> int:
        """
        Queue a new operation.

        Args:
            type: Type of operation
            name: Display name
            metadata: Operation-specific data (project_id, cluster_name, etc.)

        Returns:
            Operation ID
        """
        self.operation_id_counter += 1
        operation = Operation(
            id=self.operation_id_counter,
            type=type,
            name=name,
            metadata=metadata
        )

        self.operations[operation.id] = operation

        # Log operation queuing with details
        logger.info(f"Operation {operation.id} queued: {type.value}")
        logger.info(f"  Name: {name}")
        logger.info(f"  Metadata: {metadata}")

        # Notify listeners asynchronously
        asyncio.create_task(self._notify_listeners("queued", operation))

        return operation.id

    def get_operation(self, operation_id: int) -> Optional[Operation]:
        """Get an operation by ID"""
        return self.operations.get(operation_id)

    def get_all_operations(self) -> List[Dict[str, Any]]:
        """Get all operations as dictionaries"""
        return [op.to_dict() for op in self.operations.values()]

    def clear_operation(self, operation_id: int) -> bool:
        """Clear a completed or failed operation"""
        operation = self.operations.get(operation_id)
        if operation and operation.status in [OperationStatus.COMPLETED, OperationStatus.FAILED]:
            del self.operations[operation_id]
            return True
        return False

    async def _worker_loop(self):
        """Background worker that processes operations"""
        logger.info("Operation worker started")

        while self.is_running:
            try:
                # Clean up completed tasks
                self.running_tasks = {task for task in self.running_tasks if not task.done()}

                # Find queued operations
                queued_ops = [
                    op for op in self.operations.values()
                    if op.status == OperationStatus.QUEUED
                ]

                # Start new operations if we have capacity
                if queued_ops and len(self.running_tasks) < self.max_concurrent_operations:
                    # Start as many operations as we have capacity for
                    available_slots = self.max_concurrent_operations - len(self.running_tasks)
                    operations_to_start = sorted(queued_ops, key=lambda op: op.queued_at)[:available_slots]

                    for operation in operations_to_start:
                        task = asyncio.create_task(self._process_operation(operation))
                        self.running_tasks.add(task)
                        logger.info(f"Started operation {operation.id} ({len(self.running_tasks)}/{self.max_concurrent_operations} running)")

                # Sleep briefly before checking again
                await asyncio.sleep(0.5)

            except asyncio.CancelledError:
                # Cancel all running tasks
                for task in self.running_tasks:
                    task.cancel()
                break
            except Exception as e:
                logger.error(f"Error in worker loop: {e}")
                await asyncio.sleep(1)

        logger.info("Operation worker stopped")

    async def _process_operation(self, operation: Operation):
        """Process a single operation"""
        try:
            operation.update_status(OperationStatus.IN_PROGRESS, "Operation started")
            operation.started_at = datetime.utcnow()

            # Log operation start with details
            logger.info(f"Operation {operation.id} started: {operation.type.value}")
            logger.info(f"  Name: {operation.name}")
            logger.info(f"  Metadata: {operation.metadata}")

            await self._notify_listeners("started", operation)

            # Execute operation based on type
            if operation.type == OperationType.CREATE_CLUSTER:
                await self._process_create_cluster(operation)
            elif operation.type == OperationType.CREATE_FLEX_CLUSTER:
                await self._process_create_flex_cluster(operation)
            elif operation.type == OperationType.DELETE_CLUSTER:
                await self._process_delete_cluster(operation)
            elif operation.type == OperationType.DELETE_FLEX_CLUSTER:
                await self._process_delete_flex_cluster(operation)
            elif operation.type == OperationType.CREATE_PROJECT:
                await self._process_create_project(operation)
            elif operation.type == OperationType.DELETE_PROJECT:
                await self._process_delete_project(operation)
            else:
                raise ValueError(f"Unknown operation type: {operation.type}")

            operation.update_status(OperationStatus.COMPLETED, "Operation completed successfully")
            operation.completed_at = datetime.utcnow()

            # Calculate duration
            duration = (operation.completed_at - operation.started_at).total_seconds()

            # Log operation completion with details
            logger.info(f"Operation {operation.id} completed successfully")
            logger.info(f"  Type: {operation.type.value}")
            logger.info(f"  Name: {operation.name}")
            logger.info(f"  Duration: {duration:.1f}s")
            if operation.result:
                logger.info(f"  Result: {operation.result}")

            await self._notify_listeners("completed", operation)

        except Exception as e:
            operation.update_status(OperationStatus.FAILED, f"Operation failed: {str(e)}")
            operation.error = str(e)
            operation.completed_at = datetime.utcnow()

            # Calculate duration even for failed operations
            duration = (operation.completed_at - operation.started_at).total_seconds() if operation.started_at else 0

            # Log operation failure with comprehensive details
            logger.error(f"Operation {operation.id} failed")
            logger.error(f"  Type: {operation.type.value}")
            logger.error(f"  Name: {operation.name}")
            logger.error(f"  Duration: {duration:.1f}s")
            logger.error(f"  Metadata: {operation.metadata}")
            logger.error(f"  Error: {e}")

            await self._notify_listeners("failed", operation)

    async def _process_create_cluster(self, operation: Operation):
        """Process cluster creation"""
        project_id = operation.metadata["project_id"]
        cluster_config = operation.metadata["cluster_config"]

        # Create cluster
        async with AtlasClient() as client:
            result = await client.create_cluster(project_id, cluster_config)
            operation.result = result
            cluster_name = result.get("name")

        # Poll for completion
        operation.update_progress("Waiting for cluster to become available...")
        await self._notify_listeners("progress", operation)

        await self._poll_cluster_status(
            project_id,
            cluster_name,
            target_state="IDLE",
            operation=operation
        )

    async def _process_create_flex_cluster(self, operation: Operation):
        """Process Flex cluster creation"""
        project_id = operation.metadata["project_id"]
        cluster_config = operation.metadata["cluster_config"]

        # Create Flex cluster
        async with AtlasClient() as client:
            result = await client.create_flex_cluster(project_id, cluster_config)
            operation.result = result
            cluster_name = result.get("name")

        # Poll for completion
        operation.update_progress("Waiting for Flex cluster to become available...")
        await self._notify_listeners("progress", operation)

        # Flex clusters might have different states, but usually go to IDLE
        await self._poll_flex_cluster_status(
            project_id,
            cluster_name,
            target_state="IDLE",
            operation=operation
        )

    async def _process_delete_cluster(self, operation: Operation):
        """Process cluster deletion"""
        project_id = operation.metadata["project_id"]
        cluster_name = operation.metadata["cluster_name"]

        # Delete cluster
        async with AtlasClient() as client:
            try:
                result = await client.delete_cluster(project_id, cluster_name)
                operation.result = result
            except Exception as e:
                error_msg = str(e)
                # If it's a Flex cluster, try the Flex endpoint
                if "Flex cluster" in error_msg and "cannot be used in the Cluster API" in error_msg:
                    result = await client.delete_flex_cluster(project_id, cluster_name)
                    operation.result = result
                else:
                    raise

        # Poll until cluster is gone
        operation.update_progress("Waiting for cluster to be deleted...")
        await self._notify_listeners("progress", operation)

        await self._poll_cluster_deletion(project_id, cluster_name, operation)

    async def _process_delete_flex_cluster(self, operation: Operation):
        """Process Flex cluster deletion"""
        project_id = operation.metadata["project_id"]
        cluster_name = operation.metadata["cluster_name"]

        # Delete Flex cluster
        async with AtlasClient() as client:
            result = await client.delete_flex_cluster(project_id, cluster_name)
            operation.result = result

        # Poll until cluster is gone
        operation.update_progress("Waiting for Flex cluster to be deleted...")
        await self._notify_listeners("progress", operation)

        await self._poll_flex_cluster_deletion(project_id, cluster_name, operation)

    async def _poll_cluster_status(
        self,
        project_id: str,
        cluster_name: str,
        target_state: str,
        operation: Operation,
        max_attempts: int = 180,  # 15 minutes with 5-second intervals
        poll_interval: int = 5
    ):
        """Poll cluster status until it reaches target state"""
        for attempt in range(max_attempts):
            try:
                async with AtlasClient() as client:
                    cluster = await client.get_cluster(project_id, cluster_name)

                state = cluster.get("stateName", "UNKNOWN")
                operation.update_progress(f"Cluster state: {state}")
                await self._notify_listeners("progress", operation)

                if state == target_state:
                    return
                elif state in ["FAILED", "ERROR"]:
                    raise Exception(f"Cluster entered {state} state")

                await asyncio.sleep(poll_interval)

            except Exception as e:
                if "404" in str(e):
                    # Cluster not found yet (might be still creating)
                    await asyncio.sleep(poll_interval)
                else:
                    raise

        raise Exception(f"Timeout waiting for cluster to reach {target_state} state")

    async def _poll_flex_cluster_status(
        self,
        project_id: str,
        cluster_name: str,
        target_state: str,
        operation: Operation,
        max_attempts: int = 180,
        poll_interval: int = 5
    ):
        """Poll Flex cluster status until it reaches target state"""
        for attempt in range(max_attempts):
            try:
                async with AtlasClient() as client:
                    cluster = await client.get_flex_cluster(project_id, cluster_name)

                state = cluster.get("stateName", "UNKNOWN")
                operation.update_progress(f"Flex cluster state: {state}")
                await self._notify_listeners("progress", operation)

                if state == target_state:
                    return
                elif state in ["FAILED", "ERROR"]:
                    raise Exception(f"Flex cluster entered {state} state")

                await asyncio.sleep(poll_interval)

            except Exception as e:
                if "404" in str(e):
                    await asyncio.sleep(poll_interval)
                else:
                    raise

        raise Exception(f"Timeout waiting for Flex cluster to reach {target_state} state")

    async def _poll_cluster_deletion(
        self,
        project_id: str,
        cluster_name: str,
        operation: Operation,
        max_attempts: int = 180,
        poll_interval: int = 5
    ):
        """Poll until cluster is deleted (404)"""
        for attempt in range(max_attempts):
            try:
                async with AtlasClient() as client:
                    cluster = await client.get_cluster(project_id, cluster_name)

                state = cluster.get("stateName", "UNKNOWN")
                operation.update_progress(f"Deleting cluster... (state: {state})")
                await self._notify_listeners("progress", operation)

                await asyncio.sleep(poll_interval)

            except Exception as e:
                if "404" in str(e):
                    # Cluster deleted successfully
                    return
                # For other errors, continue polling
                await asyncio.sleep(poll_interval)

        raise Exception("Timeout waiting for cluster deletion")

    async def _poll_flex_cluster_deletion(
        self,
        project_id: str,
        cluster_name: str,
        operation: Operation,
        max_attempts: int = 180,
        poll_interval: int = 5
    ):
        """Poll until Flex cluster is deleted (404)"""
        for attempt in range(max_attempts):
            try:
                async with AtlasClient() as client:
                    cluster = await client.get_flex_cluster(project_id, cluster_name)

                state = cluster.get("stateName", "UNKNOWN")
                operation.update_progress(f"Deleting Flex cluster... (state: {state})")
                await self._notify_listeners("progress", operation)

                await asyncio.sleep(poll_interval)

            except Exception as e:
                if "404" in str(e):
                    # Flex cluster deleted successfully
                    return
                await asyncio.sleep(poll_interval)

        raise Exception("Timeout waiting for Flex cluster deletion")

    async def _process_create_project(self, operation: Operation):
        """Process project creation"""
        name = operation.metadata["name"]
        org_id = operation.metadata["org_id"]

        # Create project
        async with AtlasClient() as client:
            result = await client.create_project(name=name, org_id=org_id)
            operation.result = result

        operation.update_progress("Project created successfully")
        await self._notify_listeners("progress", operation)

    async def _process_delete_project(self, operation: Operation):
        """Process project deletion with cascading cluster deletion (in parallel)"""
        project_id = operation.metadata["project_id"]
        project_name = operation.metadata.get("project_name", project_id)
        cluster_names = operation.metadata.get("clusters", [])

        async with AtlasClient() as client:
            # Step 1: Delete all clusters if any exist (in parallel)
            if cluster_names:
                operation.update_progress(f"Deleting {len(cluster_names)} cluster(s) in parallel...")
                await self._notify_listeners("progress", operation)

                # Create deletion tasks for all clusters concurrently
                deletion_tasks = []
                for cluster_name in cluster_names:
                    task = asyncio.create_task(
                        self._delete_single_cluster(client, project_id, cluster_name, operation)
                    )
                    deletion_tasks.append(task)

                # Wait for all cluster deletions to complete
                try:
                    results = await asyncio.gather(*deletion_tasks, return_exceptions=True)

                    # Check if any deletions failed
                    failed_clusters = []
                    for i, result in enumerate(results):
                        if isinstance(result, Exception):
                            failed_clusters.append(f"{cluster_names[i]}: {result}")

                    if failed_clusters:
                        raise Exception(f"Failed to delete clusters: {'; '.join(failed_clusters)}")

                except Exception as e:
                    logger.error(f"Error during parallel cluster deletion: {e}")
                    raise

                # Step 1.5: Poll project to verify all clusters are actually gone
                operation.update_progress("Verifying all clusters are deleted...")
                await self._notify_listeners("progress", operation)

                await self._poll_project_clusters_gone(client, project_id, operation)

                operation.update_progress("All clusters deleted")
                await self._notify_listeners("progress", operation)

            # Step 2: Delete the project
            operation.update_progress("Deleting project...")
            await self._notify_listeners("progress", operation)

            result = await client.delete_project(project_id)
            operation.result = result

        operation.update_progress("Project deleted successfully")
        await self._notify_listeners("progress", operation)

    async def _delete_single_cluster(
        self,
        client: AtlasClient,
        project_id: str,
        cluster_name: str,
        parent_operation: Operation
    ):
        """Delete a single cluster (helper for parallel deletion).

        Creates a separate Operation for each cluster deletion so it appears
        in the operations log and triggers UI updates on the all clusters page.
        """
        # Create a separate Operation for this cluster deletion
        self.operation_id_counter += 1
        cluster_operation = Operation(
            id=self.operation_id_counter,
            type=OperationType.DELETE_CLUSTER,
            name=f"Deleting cluster: {cluster_name}",
            metadata={
                "project_id": project_id,
                "cluster_name": cluster_name,
                "parent_operation_id": parent_operation.id
            }
        )
        self.operations[cluster_operation.id] = cluster_operation

        # Emit queued event
        await self._notify_listeners("queued", cluster_operation)

        try:
            logger.info(f"Initiating deletion of cluster: {cluster_name}")

            # Mark as in-progress
            cluster_operation.started_at = datetime.utcnow()
            cluster_operation.update_status(OperationStatus.IN_PROGRESS, "Starting cluster deletion")
            await self._notify_listeners("started", cluster_operation)

            # Try regular cluster deletion first
            is_flex = False
            try:
                await client.delete_cluster(project_id, cluster_name)
                cluster_operation.update_progress("Deletion initiated, waiting for completion...")
                await self._notify_listeners("progress", cluster_operation)
            except Exception as e:
                error_msg = str(e)
                # If cluster is already being deleted, that's fine - continue
                if "already been requested for deletion" in error_msg:
                    logger.info(f"Cluster {cluster_name} is already being deleted, skipping...")
                    cluster_operation.update_progress("Cluster already being deleted, monitoring...")
                    await self._notify_listeners("progress", cluster_operation)
                # If it fails with Flex cluster error, try Flex deletion
                elif "Flex cluster" in error_msg and "cannot be used in the Cluster API" in error_msg:
                    is_flex = True
                    try:
                        await client.delete_flex_cluster(project_id, cluster_name)
                        cluster_operation.update_progress("Flex cluster deletion initiated...")
                        await self._notify_listeners("progress", cluster_operation)
                    except Exception as flex_e:
                        # If Flex deletion also fails with "already requested", that's also fine
                        if "already been requested for deletion" in str(flex_e):
                            logger.info(f"Flex cluster {cluster_name} is already being deleted, skipping...")
                            cluster_operation.update_progress("Flex cluster already being deleted, monitoring...")
                            await self._notify_listeners("progress", cluster_operation)
                        else:
                            raise
                else:
                    raise

            # Poll until cluster is deleted
            await self._poll_cluster_deletion_simple(client, project_id, cluster_name)

            logger.info(f"Cluster {cluster_name} deleted successfully")

            # Mark as completed
            cluster_operation.update_status(OperationStatus.COMPLETED, "Cluster deleted successfully")
            cluster_operation.completed_at = datetime.utcnow()
            await self._notify_listeners("completed", cluster_operation)

        except Exception as e:
            logger.error(f"Failed to delete cluster {cluster_name}: {e}")
            # Mark as failed
            cluster_operation.update_status(OperationStatus.FAILED, str(e))
            cluster_operation.error = str(e)
            cluster_operation.completed_at = datetime.utcnow()
            await self._notify_listeners("failed", cluster_operation)
            raise Exception(f"Failed to delete cluster {cluster_name}: {e}")

    async def _poll_project_clusters_gone(
        self,
        client: AtlasClient,
        project_id: str,
        operation: Operation,
        max_attempts: int = 180,
        poll_interval: int = 5
    ):
        """Poll project until all clusters are gone (empty list)"""
        logger.info(f"Polling project {project_id} to verify all clusters are deleted")

        for attempt in range(max_attempts):
            try:
                # List all clusters in the project
                clusters_data = await client.list_clusters(project_id)
                clusters = clusters_data.get("results", [])

                # Also check Flex clusters
                try:
                    flex_clusters_data = await client.list_flex_clusters(project_id)
                    flex_clusters = flex_clusters_data.get("results", [])
                except Exception:
                    flex_clusters = []

                total_clusters = len(clusters) + len(flex_clusters)

                if total_clusters == 0:
                    logger.info(f"All clusters removed from project {project_id}")
                    return

                # Update progress with cluster count
                cluster_names = [c.get("name", "unknown") for c in clusters]
                flex_cluster_names = [c.get("name", "unknown") for c in flex_clusters]
                all_names = cluster_names + flex_cluster_names

                logger.info(f"Project {project_id} still has {total_clusters} cluster(s): {', '.join(all_names)}")
                operation.update_progress(f"Waiting for {total_clusters} cluster(s) to be fully deleted: {', '.join(all_names[:3])}{'...' if len(all_names) > 3 else ''}")
                await self._notify_listeners("progress", operation)

                await asyncio.sleep(poll_interval)

            except Exception as e:
                error_msg = str(e)
                # If we get a 404 on the project itself, that's unexpected but might mean it was deleted
                if "404" in error_msg:
                    logger.warning(f"Project {project_id} returned 404 during cluster verification")
                    return
                logger.warning(f"Error checking clusters for project {project_id}: {e}")
                await asyncio.sleep(poll_interval)

        raise Exception(f"Timeout waiting for all clusters to be removed from project {project_id}")

    async def _poll_cluster_deletion_simple(
        self,
        client: AtlasClient,
        project_id: str,
        cluster_name: str,
        max_attempts: int = 180,
        poll_interval: int = 5
    ):
        """Poll until cluster is deleted (404) - simplified version for use within async context"""
        for attempt in range(max_attempts):
            try:
                # Try regular cluster first
                try:
                    await client.get_cluster(project_id, cluster_name)
                except Exception as e:
                    if "404" in str(e):
                        return  # Cluster deleted successfully
                    # Try Flex cluster
                    try:
                        await client.get_flex_cluster(project_id, cluster_name)
                    except Exception as flex_e:
                        if "404" in str(flex_e):
                            return  # Flex cluster deleted successfully
                        # Neither worked, continue polling
                await asyncio.sleep(poll_interval)
            except Exception as e:
                if "404" in str(e):
                    return  # Cluster deleted
                await asyncio.sleep(poll_interval)

        raise Exception(f"Timeout waiting for cluster {cluster_name} deletion")


# Global singleton instance
_manager: Optional[OperationManager] = None


def get_operation_manager() -> OperationManager:
    """Get the global OperationManager instance"""
    global _manager
    if _manager is None:
        _manager = OperationManager()
    return _manager
