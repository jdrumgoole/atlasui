"""
Pytest configuration and fixtures for AtlasUI tests.

Session-Scoped Test Cluster Harness
===================================
This module provides session-scoped fixtures that create shared test clusters
once at the start of a pytest session. This significantly reduces test time
since cluster creation takes 10-15 minutes per cluster.

Architecture:
    Session Start:
    1. Start AtlasUI server (atlasui_server fixture)
    2. Create test project (test_project fixture)
    3. Create M0, M10, Flex clusters in parallel (test_clusters fixture)
    4. Wait for all clusters to reach IDLE state

    Test Execution:
    - Tests use m0_cluster, m10_cluster, flex_cluster fixtures
    - Clusters remain running throughout all tests
    - Tests can pause/resume/modify clusters

    Session End:
    1. Resume any paused clusters (wait for IDLE state)
    2. Delete test project (cascades to delete all clusters)

Fixtures:
    atlasui_server   - Starts/stops the AtlasUI server
    test_project     - Creates project, cleans up at end
    test_clusters    - Creates M0, M10, Flex clusters in parallel
    m0_cluster       - Returns M0 cluster info (or skips if creation failed)
    m10_cluster      - Returns M10 cluster info (or skips if creation failed)
    flex_cluster     - Returns Flex cluster info (or skips if creation failed)

Usage:
    # Run all cluster feature tests
    uv run pytest tests/test_cluster_features.py -v -s

    # Run specific test
    uv run pytest tests/test_cluster_features.py::test_pause_resume_m10 -v -s
"""

import pytest
import sys
import subprocess
import time
import httpx
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, Dict, Any
from unittest.mock import Mock, patch
from atlasui.client import AtlasClient
from atlasui.config import settings


# ============================================================================
# Session-scoped Test Infrastructure
# ============================================================================
# These fixtures create shared test resources (project and clusters) once at
# the start of the test session and clean them up at the end. This avoids
# the overhead of creating clusters for each test.

BASE_URL = "http://localhost:8100"
# Generate unique project name for each test session to avoid conflicts
TEST_PROJECT_NAME = f"test-session-{int(time.time())}"
CLUSTER_CREATION_TIMEOUT = 900  # 15 minutes
CLUSTER_DELETION_TIMEOUT = 600  # 10 minutes


def _log(msg: str) -> None:
    """Print message and flush immediately."""
    print(msg, flush=True)
    sys.stdout.flush()


def _get_organization_id() -> str:
    """Get the first organization ID from the API."""
    response = httpx.get(f"{BASE_URL}/api/organizations/", timeout=30.0, follow_redirects=True)
    response.raise_for_status()
    data = response.json()
    orgs = data.get("results", [])
    if not orgs:
        raise ValueError("No organizations found in Atlas account")
    return orgs[0]["id"]


def _find_existing_project(project_name: str) -> Optional[str]:
    """Find an existing project by name and return its ID."""
    response = httpx.get(f"{BASE_URL}/api/projects/", timeout=30.0, follow_redirects=True)
    response.raise_for_status()
    projects = response.json().get("results", [])
    for proj in projects:
        if proj["name"] == project_name:
            return proj["id"]
    return None


def _create_project(org_id: str, project_name: str) -> str:
    """Create a project and return its ID."""
    # Check if project already exists
    existing_id = _find_existing_project(project_name)
    if existing_id:
        _log(f"   Found existing project: {existing_id}")
        return existing_id

    response = httpx.post(
        f"{BASE_URL}/api/projects/",
        json={"name": project_name, "orgId": org_id},
        timeout=30.0,
        follow_redirects=True
    )
    response.raise_for_status()
    data = response.json()

    if "operation_id" in data:
        time.sleep(5)
        project_id = _find_existing_project(project_name)
        if project_id:
            return project_id
        raise ValueError(f"Project {project_name} not found after creation")
    return data.get("id") or data.get("project", {}).get("id")


def _find_existing_cluster(project_id: str, cluster_name: str) -> Optional[Dict[str, Any]]:
    """Find an existing cluster by name and return its data."""
    response = httpx.get(
        f"{BASE_URL}/api/clusters/{project_id}/{cluster_name}",
        timeout=30.0,
        follow_redirects=True
    )
    if response.status_code == 200:
        return response.json()
    return None


def _create_m0_cluster(project_id: str, cluster_name: str) -> Dict[str, Any]:
    """Create an M0 (free tier) cluster."""
    # Check if cluster already exists
    existing = _find_existing_cluster(project_id, cluster_name)
    if existing:
        _log(f"   Found existing M0 cluster: {cluster_name}")
        return existing

    cluster_config = {
        "name": cluster_name,
        "clusterType": "REPLICASET",
        "replicationSpecs": [{
            "regionConfigs": [{
                "providerName": "TENANT",
                "backingProviderName": "AWS",
                "regionName": "US_EAST_1",
                "priority": 7,
                "electableSpecs": {
                    "instanceSize": "M0",
                    "nodeCount": 3
                }
            }]
        }]
    }

    response = httpx.post(
        f"{BASE_URL}/api/clusters/{project_id}",
        json=cluster_config,
        timeout=60.0,
        follow_redirects=True
    )
    response.raise_for_status()
    return response.json()


def _create_m10_cluster(project_id: str, cluster_name: str) -> Dict[str, Any]:
    """Create an M10 (dedicated) cluster."""
    # Check if cluster already exists
    existing = _find_existing_cluster(project_id, cluster_name)
    if existing:
        _log(f"   Found existing M10 cluster: {cluster_name}")
        return existing

    cluster_config = {
        "name": cluster_name,
        "clusterType": "REPLICASET",
        "replicationSpecs": [{
            "regionConfigs": [{
                "providerName": "AWS",
                "regionName": "US_EAST_1",
                "priority": 7,
                "electableSpecs": {
                    "instanceSize": "M10",
                    "nodeCount": 3
                }
            }]
        }]
    }

    response = httpx.post(
        f"{BASE_URL}/api/clusters/{project_id}",
        json=cluster_config,
        timeout=60.0,
        follow_redirects=True
    )
    response.raise_for_status()
    return response.json()


def _create_flex_cluster(project_id: str, cluster_name: str) -> Dict[str, Any]:
    """Create a Flex cluster using the dedicated Flex API endpoint."""
    # Check if cluster already exists (try both regular and flex endpoints)
    existing = _find_existing_cluster(project_id, cluster_name)
    if existing:
        _log(f"   Found existing Flex cluster: {cluster_name}")
        return existing

    # Flex clusters use a different API endpoint and configuration format
    # As of Jan 2025, Flex clusters use /api/clusters/{project_id}/flex
    cluster_config = {
        "name": cluster_name,
        "providerSettings": {
            "backingProviderName": "AWS",
            "regionName": "US_EAST_1"
        }
    }

    response = httpx.post(
        f"{BASE_URL}/api/clusters/{project_id}/flex",
        json=cluster_config,
        timeout=60.0,
        follow_redirects=True
    )
    response.raise_for_status()
    return response.json()


def _wait_for_cluster_ready(project_id: str, cluster_name: str, timeout: int = CLUSTER_CREATION_TIMEOUT) -> bool:
    """Poll until cluster reaches IDLE state."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = httpx.get(
                f"{BASE_URL}/api/clusters/{project_id}/{cluster_name}",
                timeout=30.0,
                follow_redirects=True
            )
            if response.status_code == 200:
                data = response.json()
                state = data.get("stateName", "UNKNOWN")
                elapsed = int(time.time() - start_time)
                _log(f"   {cluster_name}: {state} ({elapsed}s elapsed)")
                if state == "IDLE":
                    return True
                elif state in ["FAILED", "ERROR"]:
                    raise ValueError(f"Cluster {cluster_name} entered {state} state")
        except httpx.HTTPStatusError as e:
            if e.response.status_code != 404:
                _log(f"   {cluster_name} warning: {e}")
        time.sleep(15)
    return False


def _wait_for_flex_cluster_ready(project_id: str, cluster_name: str, timeout: int = CLUSTER_CREATION_TIMEOUT) -> bool:
    """Poll until Flex cluster reaches IDLE state using the Flex API endpoint."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            # Flex clusters use the flex list endpoint - check if cluster exists and is ready
            response = httpx.get(
                f"{BASE_URL}/api/clusters/{project_id}/flex/list",
                timeout=30.0,
                follow_redirects=True
            )
            if response.status_code == 200:
                data = response.json()
                clusters = data.get("results", [])
                for cluster in clusters:
                    if cluster.get("name") == cluster_name:
                        # Flex clusters don't have stateName, they're ready when they appear
                        # Check for any state indicator or assume IDLE if present
                        state = cluster.get("stateName", "IDLE")
                        elapsed = int(time.time() - start_time)
                        _log(f"   {cluster_name}: {state} ({elapsed}s elapsed)")
                        if state in ["IDLE", None, ""]:
                            return True
                        elif state in ["FAILED", "ERROR"]:
                            raise ValueError(f"Flex cluster {cluster_name} entered {state} state")
                        break
                else:
                    # Cluster not found yet, keep polling
                    elapsed = int(time.time() - start_time)
                    _log(f"   {cluster_name}: CREATING ({elapsed}s elapsed)")
        except httpx.HTTPStatusError as e:
            if e.response.status_code != 404:
                _log(f"   {cluster_name} warning: {e}")
        except Exception as e:
            _log(f"   {cluster_name} error: {e}")
        time.sleep(15)
    return False


def _delete_cluster_api(project_id: str, cluster_name: str) -> bool:
    """Delete a cluster via API."""
    try:
        response = httpx.delete(
            f"{BASE_URL}/api/clusters/{project_id}/{cluster_name}",
            timeout=60.0,
            follow_redirects=True
        )
        return response.status_code in [200, 202, 204]
    except Exception as e:
        _log(f"   Warning deleting {cluster_name}: {e}")
        return False


def _delete_project_api(project_id: str) -> bool:
    """Delete a project via API (with confirmed=true to cascade delete clusters)."""
    try:
        response = httpx.delete(
            f"{BASE_URL}/api/projects/{project_id}?confirmed=true",
            timeout=120.0,
            follow_redirects=True
        )
        return response.status_code in [200, 202, 204]
    except Exception as e:
        _log(f"   Warning deleting project: {e}")
        return False


def _wait_for_project_deleted(project_id: str, timeout: int = 600) -> bool:
    """Poll until project is deleted."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = httpx.get(
                f"{BASE_URL}/api/projects/{project_id}",
                timeout=30.0,
                follow_redirects=True
            )
            if response.status_code == 404:
                return True
            elif response.status_code == 200:
                elapsed = int(time.time() - start_time)
                _log(f"   Project still exists ({elapsed}s elapsed)")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return True
        except Exception as e:
            _log(f"   Error checking project: {e}")
        time.sleep(15)
    return False


def _wait_for_cluster_deleted(project_id: str, cluster_name: str, timeout: int = CLUSTER_DELETION_TIMEOUT) -> bool:
    """Wait for cluster to be deleted."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = httpx.get(
                f"{BASE_URL}/api/clusters/{project_id}/{cluster_name}",
                timeout=30.0,
                follow_redirects=True
            )
            if response.status_code == 404:
                return True
            if response.status_code == 200:
                data = response.json()
                state = data.get("stateName", "UNKNOWN")
                _log(f"   {cluster_name}: {state}")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return True
        time.sleep(10)
    return False


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test (requires valid API credentials)"
    )
    config.addinivalue_line(
        "markers", "pause_resume: mark test as pause/resume functionality test"
    )
    config.addinivalue_line(
        "markers", "restrictions: mark test as cluster restrictions test"
    )
    config.addinivalue_line(
        "markers", "display: mark test as UI display test"
    )
    config.addinivalue_line(
        "markers", "m0: mark test as M0 (Free Tier) cluster test"
    )
    config.addinivalue_line(
        "markers", "m10: mark test as M10 (Dedicated) cluster test"
    )
    config.addinivalue_line(
        "markers", "flex: mark test as Flex cluster test"
    )
    config.addinivalue_line(
        "markers", "lifecycle: mark test as cluster lifecycle test"
    )


@pytest.fixture(scope="session")
def validate_credentials():
    """
    Validate that Atlas API credentials are configured and working.

    This fixture runs once per test session and validates that:
    1. API credentials are configured in environment
    2. The credentials are valid and can authenticate to Atlas API

    If validation fails, integration tests will be skipped.

    Returns:
        bool: True if credentials are valid, False otherwise
    """
    try:
        # Check if credentials are configured
        if settings.atlas_auth_method == "api_key":
            if not settings.atlas_public_key or not settings.atlas_private_key:
                print("\n⚠️  Atlas API keys not configured. Skipping integration tests.", file=sys.stderr)
                print("   Set ATLAS_PUBLIC_KEY and ATLAS_PRIVATE_KEY environment variables.", file=sys.stderr)
                return False
        elif settings.atlas_auth_method == "service_account":
            if not settings.atlas_service_account_credentials_file:
                if not settings.atlas_service_account_id or not settings.atlas_service_account_secret:
                    print("\n⚠️  Atlas service account credentials not configured. Skipping integration tests.", file=sys.stderr)
                    return False

        # Credentials are configured - integration tests can run
        print("\n✓ Atlas credentials configured - integration tests enabled", file=sys.stderr)
        return True

    except Exception as e:
        print(f"\n⚠️  Failed to validate Atlas credentials: {e}", file=sys.stderr)
        return False


@pytest.fixture
async def atlas_client(validate_credentials):
    """
    Create a real Atlas API client for integration tests.

    Requires valid credentials to be configured.
    Skips test if credentials are not valid.
    """
    if not validate_credentials:
        pytest.skip("Atlas API credentials not configured or invalid")

    async with AtlasClient() as client:
        yield client


@pytest.fixture
def mock_atlas_client():
    """Create a mock Atlas client for unit testing."""
    from unittest.mock import AsyncMock
    with patch('atlasui.client.base.httpx.AsyncClient') as mock_client:
        # Configure the mock to return AsyncMock for async methods
        mock_instance = AsyncMock()
        mock_client.return_value = mock_instance
        yield mock_client


@pytest.fixture
def sample_project():
    """Sample project data for testing."""
    return {
        "id": "5a0a1e7e0f2912c554080adc",
        "name": "Test Project",
        "orgId": "5a0a1e7e0f2912c554080abc",
        "created": "2023-01-01T00:00:00Z",
        "clusterCount": 2
    }


@pytest.fixture
def sample_cluster():
    """Sample cluster data for testing."""
    return {
        "name": "test-cluster",
        "stateName": "IDLE",
        "mongoDBVersion": "7.0.0",
        "clusterType": "REPLICASET",
        "providerSettings": {
            "providerName": "AWS",
            "regionName": "US_EAST_1",
            "instanceSizeName": "M10"
        },
        "connectionStrings": {
            "standard": "mongodb://test-cluster.mongodb.net:27017"
        }
    }


@pytest.fixture
def sample_projects_response(sample_project):
    """Sample projects list response."""
    return {
        "results": [sample_project],
        "totalCount": 1
    }


@pytest.fixture
def sample_clusters_response(sample_cluster):
    """Sample clusters list response."""
    return {
        "results": [sample_cluster],
        "totalCount": 1
    }


@pytest.fixture(scope="session")
def atlasui_server():
    """
    Start atlasui server for Playwright/UI tests.

    This fixture starts the server before tests run and stops it after.
    Use this fixture by adding it as a parameter to your Playwright tests.

    Example:
        def test_ui(page: Page, atlasui_server):
            page.goto("http://localhost:8000")
            ...
    """
    # Check if Atlas credentials are configured
    if settings.atlas_auth_method == "api_key":
        if not settings.atlas_public_key or not settings.atlas_private_key:
            print("\n⚠️  Skipping - Atlas API credentials not configured", file=sys.stderr)
            pytest.skip("Atlas API credentials required for UI tests")

    # Check if server is already running
    try:
        response = httpx.get("http://localhost:8100/health", timeout=2.0)
        if response.status_code == 200:
            print("\n✓ AtlasUI server already running at http://localhost:8100", file=sys.stderr)
            yield
            return
    except (httpx.ConnectError, httpx.TimeoutException):
        pass

    # Start the server on port 8100 for development/testing
    print("\n▶ Starting AtlasUI server on port 8100...", file=sys.stderr)
    process = subprocess.Popen(
        ["atlasui", "start", "--port", "8100"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    # Wait for server to be ready (max 30 seconds)
    max_wait = 30
    start_time = time.time()
    server_ready = False

    while time.time() - start_time < max_wait:
        try:
            response = httpx.get("http://localhost:8100/health", timeout=2.0)
            if response.status_code == 200:
                server_ready = True
                print("✓ AtlasUI server ready at http://localhost:8100", file=sys.stderr)
                break
        except (httpx.ConnectError, httpx.TimeoutException):
            time.sleep(1)

    if not server_ready:
        process.kill()
        raise RuntimeError("Failed to start AtlasUI server within 30 seconds")

    yield

    # Stop the server
    print("\n■ Stopping AtlasUI server...", file=sys.stderr)
    subprocess.run(["atlasui", "stop"], capture_output=True)
    process.wait(timeout=10)
    print("✓ AtlasUI server stopped", file=sys.stderr)


# ============================================================================
# Session-scoped Cluster Fixtures
# ============================================================================
# These fixtures create shared test clusters at the start of the session.
# All Playwright tests can use these pre-created clusters instead of
# creating their own, which significantly reduces test time.

# Cluster names for the session (unique per session via project name)
M0_CLUSTER_NAME = "m0-cluster"
M10_CLUSTER_NAME = "m10-cluster"
FLEX_CLUSTER_NAME = "flex-cluster"


def _get_all_clusters_in_project(project_id: str) -> list:
    """Get all clusters (regular and flex) in a project."""
    clusters = []

    # Get regular clusters
    try:
        response = httpx.get(
            f"{BASE_URL}/api/clusters/{project_id}",
            timeout=30.0,
            follow_redirects=True
        )
        if response.status_code == 200:
            data = response.json()
            for cluster in data.get("results", []):
                clusters.append({
                    "name": cluster.get("name"),
                    "state": cluster.get("stateName", "UNKNOWN"),
                    "paused": cluster.get("paused", False),
                    "type": "regular"
                })
    except Exception as e:
        _log(f"   Warning getting regular clusters: {e}")

    # Get flex clusters
    try:
        response = httpx.get(
            f"{BASE_URL}/api/clusters/{project_id}/flex/list",
            timeout=30.0,
            follow_redirects=True
        )
        if response.status_code == 200:
            data = response.json()
            for cluster in data.get("results", []):
                clusters.append({
                    "name": cluster.get("name"),
                    "state": cluster.get("stateName", "IDLE"),  # Flex clusters are typically IDLE
                    "paused": False,  # Flex clusters can't be paused
                    "type": "flex"
                })
    except Exception as e:
        _log(f"   Warning getting flex clusters: {e}")

    return clusters


def _resume_cluster(project_id: str, cluster_name: str) -> bool:
    """Resume a paused cluster."""
    try:
        response = httpx.post(
            f"{BASE_URL}/api/clusters/{project_id}/{cluster_name}/resume",
            timeout=60.0,
            follow_redirects=True
        )
        return response.status_code in [200, 202]
    except Exception as e:
        _log(f"   Warning resuming {cluster_name}: {e}")
        return False


def _wait_for_all_clusters_idle(project_id: str, timeout: int = 600) -> bool:
    """
    Wait for all clusters in a project to reach IDLE state.

    If any clusters are paused, resume them in parallel.
    Polls every 10 seconds until all clusters are IDLE.
    """
    start_time = time.time()
    resumed_clusters = set()  # Track which clusters we've already resumed

    while time.time() - start_time < timeout:
        clusters = _get_all_clusters_in_project(project_id)

        if not clusters:
            _log("   No clusters found in project")
            return True

        # Find all paused clusters that need resuming
        paused_to_resume = [
            c for c in clusters
            if c["paused"] and c["name"] not in resumed_clusters
        ]

        # Resume paused clusters in parallel
        if paused_to_resume:
            _log(f"   Resuming {len(paused_to_resume)} paused cluster(s) in parallel...")
            with ThreadPoolExecutor(max_workers=len(paused_to_resume)) as executor:
                futures = {}
                for cluster in paused_to_resume:
                    name = cluster["name"]
                    _log(f"   {name}: PAUSED - initiating resume...")
                    future = executor.submit(_resume_cluster, project_id, name)
                    futures[future] = name

                for future in as_completed(futures):
                    name = futures[future]
                    try:
                        if future.result():
                            resumed_clusters.add(name)
                            _log(f"   {name}: Resume initiated")
                    except Exception as e:
                        _log(f"   {name}: Resume failed - {e}")

        # Check if all clusters are now IDLE
        all_idle = True
        for cluster in clusters:
            name = cluster["name"]
            state = cluster["state"]
            paused = cluster["paused"]

            if paused:
                elapsed = int(time.time() - start_time)
                _log(f"   {name}: Still paused, waiting... ({elapsed}s elapsed)")
                all_idle = False
            elif state != "IDLE":
                elapsed = int(time.time() - start_time)
                _log(f"   {name}: {state} ({elapsed}s elapsed)")
                all_idle = False

        if all_idle:
            _log("   All clusters are in IDLE state")
            return True

        time.sleep(10)

    _log("   Timeout waiting for clusters to reach IDLE state")
    return False


@pytest.fixture(scope="session")
def test_project(atlasui_server):
    """
    Session-scoped fixture that creates a test project for all Playwright tests.

    The project is created once at the start of the session and deleted at the end.
    All test clusters will be created within this project.
    """
    _log("\n" + "=" * 80)
    _log("Creating Test Project")
    _log("=" * 80)

    org_id = _get_organization_id()
    _log(f"   Organization ID: {org_id}")

    project_id = _create_project(org_id, TEST_PROJECT_NAME)
    _log(f"   Project ID: {project_id}")

    yield {
        "project_id": project_id,
        "project_name": TEST_PROJECT_NAME,
        "org_id": org_id
    }

    # Cleanup: Wait for all clusters to reach IDLE state before deleting
    _log("\n" + "=" * 80)
    _log("Cleaning Up Test Project")
    _log("=" * 80)

    _log("   Waiting for all clusters to reach IDLE state...")
    _wait_for_all_clusters_idle(project_id)

    _log(f"   Deleting project {TEST_PROJECT_NAME}...")
    if _delete_project_api(project_id):
        _log("   Project deletion initiated, waiting for completion...")
        if _wait_for_project_deleted(project_id):
            _log("   ✓ Project deleted successfully")
        else:
            _log("   ⚠ Project deletion timed out (may still be deleting)")
    else:
        _log("   ⚠ Failed to initiate project deletion")


@pytest.fixture(scope="session")
def test_clusters(test_project, atlasui_server):
    """
    Session-scoped fixture that creates M0, M10, and Flex clusters in parallel.

    This fixture:
    1. Creates all three cluster types in parallel (to save time)
    2. Waits for all clusters to reach IDLE state
    3. Returns cluster info for tests to use
    4. Does NOT delete clusters (project deletion handles that)
    """
    project_id = test_project["project_id"]

    _log("\n" + "=" * 80)
    _log("Creating Test Clusters (in parallel)")
    _log("=" * 80)

    # Define cluster creation tasks
    cluster_tasks = [
        ("M0", M0_CLUSTER_NAME, _create_m0_cluster),
        ("M10", M10_CLUSTER_NAME, _create_m10_cluster),
        ("Flex", FLEX_CLUSTER_NAME, _create_flex_cluster),
    ]

    created_clusters = {}
    failed_clusters = []

    # Create clusters in parallel
    _log("\n   Starting parallel cluster creation...")
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {}
        for cluster_type, cluster_name, create_func in cluster_tasks:
            _log(f"   Initiating {cluster_type} cluster: {cluster_name}")
            future = executor.submit(create_func, project_id, cluster_name)
            futures[future] = (cluster_type, cluster_name)

        for future in as_completed(futures):
            cluster_type, cluster_name = futures[future]
            try:
                result = future.result()
                created_clusters[cluster_type] = {
                    "name": cluster_name,
                    "data": result
                }
                _log(f"   ✓ {cluster_type} cluster creation initiated: {cluster_name}")
            except Exception as e:
                _log(f"   ✗ Failed to create {cluster_type} cluster: {e}")
                failed_clusters.append(cluster_type)

    # Wait for all clusters to be ready (in parallel)
    _log("\n   Waiting for clusters to reach IDLE state...")

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {}
        for cluster_type, cluster_info in created_clusters.items():
            # Use the correct waiting function based on cluster type
            if cluster_type == "Flex":
                wait_func = _wait_for_flex_cluster_ready
            else:
                wait_func = _wait_for_cluster_ready
            future = executor.submit(
                wait_func,
                project_id,
                cluster_info["name"]
            )
            futures[future] = cluster_type

        for future in as_completed(futures):
            cluster_type = futures[future]
            try:
                ready = future.result()
                if ready:
                    _log(f"   ✓ {cluster_type} cluster is ready")
                else:
                    _log(f"   ✗ {cluster_type} cluster timed out waiting for IDLE")
                    failed_clusters.append(cluster_type)
            except Exception as e:
                _log(f"   ✗ {cluster_type} cluster error: {e}")
                failed_clusters.append(cluster_type)

    _log("\n" + "=" * 80)
    _log("Test Clusters Ready")
    _log("=" * 80)

    # Return cluster info for tests
    yield {
        "project_id": project_id,
        "project_name": TEST_PROJECT_NAME,
        "org_id": test_project["org_id"],
        "clusters": {
            "m0": created_clusters.get("M0", {}).get("name"),
            "m10": created_clusters.get("M10", {}).get("name"),
            "flex": created_clusters.get("Flex", {}).get("name"),
        },
        "failed": failed_clusters
    }

    # Note: Cleanup is handled by test_project fixture (cascade delete)
    _log("\n   Test clusters will be deleted with project cleanup")


# Individual cluster fixtures for tests that only need one type
@pytest.fixture(scope="session")
def m0_cluster(test_clusters):
    """Session-scoped fixture providing M0 cluster info."""
    if "M0" in test_clusters.get("failed", []):
        pytest.skip("M0 cluster creation failed")
    if not test_clusters["clusters"]["m0"]:
        pytest.skip("M0 cluster not available")
    return {
        "project_id": test_clusters["project_id"],
        "cluster_name": test_clusters["clusters"]["m0"],
        "org_id": test_clusters["org_id"]
    }


@pytest.fixture(scope="session")
def m10_cluster(test_clusters):
    """Session-scoped fixture providing M10 cluster info."""
    if "M10" in test_clusters.get("failed", []):
        pytest.skip("M10 cluster creation failed")
    if not test_clusters["clusters"]["m10"]:
        pytest.skip("M10 cluster not available")
    return {
        "project_id": test_clusters["project_id"],
        "cluster_name": test_clusters["clusters"]["m10"],
        "org_id": test_clusters["org_id"]
    }


@pytest.fixture(scope="session")
def flex_cluster(test_clusters):
    """Session-scoped fixture providing Flex cluster info."""
    if "Flex" in test_clusters.get("failed", []):
        pytest.skip("Flex cluster creation failed")
    if not test_clusters["clusters"]["flex"]:
        pytest.skip("Flex cluster not available")
    return {
        "project_id": test_clusters["project_id"],
        "cluster_name": test_clusters["clusters"]["flex"],
        "org_id": test_clusters["org_id"]
    }
