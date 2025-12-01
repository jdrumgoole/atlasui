#!/usr/bin/env python3
"""
Cleanup utility for leftover test resources.

This script finds and deletes test projects that were not cleaned up due to
interrupted test runs (Ctrl+C, crashes, timeouts, etc.).

Test projects follow the naming pattern: test-session-{timestamp}

Usage:
    # List all test projects
    python tests/cleanup_test_resources.py --list

    # Delete all test projects (interactive confirmation)
    python tests/cleanup_test_resources.py --clean

    # Delete specific project by ID
    python tests/cleanup_test_resources.py --project-id PROJECT_ID

    # Force delete without confirmation
    python tests/cleanup_test_resources.py --clean --force
"""

import argparse
import sys
import time
import httpx
from typing import List, Dict, Any, Optional


BASE_URL = "http://localhost:8100"
TEST_PROJECT_PREFIX = "test-session-"
DELETION_TIMEOUT = 600  # 10 minutes


def _log(msg: str) -> None:
    """Print message with flush."""
    print(msg, flush=True)


def get_all_projects() -> List[Dict[str, Any]]:
    """Get all projects from Atlas."""
    try:
        response = httpx.get(
            f"{BASE_URL}/api/projects/",
            timeout=30.0,
            follow_redirects=True
        )
        response.raise_for_status()
        return response.json().get("results", [])
    except Exception as e:
        _log(f"Error fetching projects: {e}")
        return []


def get_test_projects() -> List[Dict[str, Any]]:
    """Get all test projects (matching test-session-* pattern)."""
    all_projects = get_all_projects()
    return [
        proj for proj in all_projects
        if proj.get("name", "").startswith(TEST_PROJECT_PREFIX)
    ]


def get_clusters_in_project(project_id: str) -> List[Dict[str, Any]]:
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
                    "state": cluster.get("stateName", "IDLE"),
                    "type": "flex"
                })
    except Exception as e:
        _log(f"   Warning getting flex clusters: {e}")

    return clusters


def delete_project(project_id: str) -> bool:
    """Delete a project (cascade deletes all clusters)."""
    try:
        response = httpx.delete(
            f"{BASE_URL}/api/projects/{project_id}?confirmed=true",
            timeout=120.0,
            follow_redirects=True
        )
        return response.status_code in [200, 202, 204]
    except Exception as e:
        _log(f"   Error deleting project: {e}")
        return False


def wait_for_project_deleted(project_id: str, timeout: int = DELETION_TIMEOUT) -> bool:
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


def list_test_projects() -> None:
    """List all test projects and their clusters."""
    test_projects = get_test_projects()

    if not test_projects:
        _log("No test projects found.")
        return

    _log(f"Found {len(test_projects)} test project(s):\n")

    for proj in test_projects:
        proj_id = proj.get("id")
        proj_name = proj.get("name")
        _log(f"Project: {proj_name}")
        _log(f"  ID: {proj_id}")

        clusters = get_clusters_in_project(proj_id)
        if clusters:
            _log(f"  Clusters ({len(clusters)}):")
            for cluster in clusters:
                _log(f"    - {cluster['name']} ({cluster['type']}, {cluster['state']})")
        else:
            _log("  Clusters: None")
        _log("")


def clean_test_projects(force: bool = False) -> None:
    """Delete all test projects with optional confirmation."""
    test_projects = get_test_projects()

    if not test_projects:
        _log("No test projects found to clean up.")
        return

    # Show what will be deleted
    _log(f"Found {len(test_projects)} test project(s) to delete:\n")
    for proj in test_projects:
        proj_name = proj.get("name")
        proj_id = proj.get("id")
        clusters = get_clusters_in_project(proj_id)
        _log(f"  - {proj_name} (ID: {proj_id})")
        if clusters:
            _log(f"    Clusters: {', '.join(c['name'] for c in clusters)}")

    # Confirm deletion
    if not force:
        _log("\nThis will DELETE all test projects and their clusters.")
        response = input("Continue? [y/N]: ").strip().lower()
        if response not in ["y", "yes"]:
            _log("Cancelled.")
            return

    # Delete projects
    _log("\nDeleting test projects...")
    for proj in test_projects:
        proj_name = proj.get("name")
        proj_id = proj.get("id")
        _log(f"\n  Deleting {proj_name}...")

        if delete_project(proj_id):
            _log("    Deletion initiated, waiting for completion...")
            if wait_for_project_deleted(proj_id):
                _log("    ✓ Deleted successfully")
            else:
                _log("    ⚠ Deletion timed out (may still be deleting)")
        else:
            _log("    ✗ Failed to delete")

    _log("\n✓ Cleanup complete")


def clean_project_by_id(project_id: str, force: bool = False) -> None:
    """Delete a specific project by ID."""
    # Verify project exists
    try:
        response = httpx.get(
            f"{BASE_URL}/api/projects/{project_id}",
            timeout=30.0,
            follow_redirects=True
        )
        if response.status_code == 404:
            _log(f"Project {project_id} not found.")
            return
        project = response.json()
        proj_name = project.get("name", "Unknown")
    except Exception as e:
        _log(f"Error fetching project: {e}")
        return

    # Show what will be deleted
    _log(f"Project: {proj_name} (ID: {project_id})")
    clusters = get_clusters_in_project(project_id)
    if clusters:
        _log(f"Clusters ({len(clusters)}):")
        for cluster in clusters:
            _log(f"  - {cluster['name']} ({cluster['type']}, {cluster['state']})")

    # Confirm deletion
    if not force:
        _log("\nThis will DELETE the project and all its clusters.")
        response = input("Continue? [y/N]: ").strip().lower()
        if response not in ["y", "yes"]:
            _log("Cancelled.")
            return

    # Delete project
    _log(f"\nDeleting project {proj_name}...")
    if delete_project(project_id):
        _log("  Deletion initiated, waiting for completion...")
        if wait_for_project_deleted(project_id):
            _log("  ✓ Deleted successfully")
        else:
            _log("  ⚠ Deletion timed out (may still be deleting)")
    else:
        _log("  ✗ Failed to delete")


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Cleanup utility for leftover test resources",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        "--list",
        action="store_true",
        help="List all test projects and their clusters"
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Delete all test projects (with confirmation)"
    )
    parser.add_argument(
        "--project-id",
        help="Delete a specific project by ID"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Skip confirmation prompts"
    )

    args = parser.parse_args()

    # Check that server is running
    try:
        response = httpx.get(f"{BASE_URL}/health", timeout=2.0)
        if response.status_code != 200:
            _log(f"Error: AtlasUI server not responding at {BASE_URL}")
            _log("Start the server with: atlasui start --port 8100")
            sys.exit(1)
    except Exception:
        _log(f"Error: Cannot connect to AtlasUI server at {BASE_URL}")
        _log("Start the server with: atlasui start --port 8100")
        sys.exit(1)

    # Execute command
    if args.list:
        list_test_projects()
    elif args.clean:
        clean_test_projects(force=args.force)
    elif args.project_id:
        clean_project_by_id(args.project_id, force=args.force)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
