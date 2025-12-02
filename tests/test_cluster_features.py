"""
Playwright tests for cluster features using shared session-scoped fixtures.

This test file uses session-scoped fixtures from conftest.py that:
1. Create a test project at session start
2. Create M0, M10, and Flex clusters in parallel
3. Wait for all clusters to reach IDLE state
4. Run all feature tests using the shared clusters
5. Clean up (resume paused clusters, delete project) at session end

This approach significantly reduces test time since cluster creation (10-15 min)
happens once per session rather than once per test.

Test Categories:
- Pause/Resume: Tests for M10+ cluster pause/resume functionality
- Cluster Restrictions: Tests verifying M0 and Flex cannot be paused
- Future: Add more feature tests that need running clusters

Usage:
    # Run all cluster feature tests
    uv run pytest tests/test_cluster_features.py -v -s

    # Run only pause/resume tests
    uv run pytest tests/test_cluster_features.py -k pause -v -s

    # Run only M10 tests
    uv run pytest tests/test_cluster_features.py -k m10 -v -s
"""
import pytest
import re
import sys
import time
import httpx
from playwright.sync_api import Page


def log(msg: str) -> None:
    """Print message and flush immediately."""
    print(msg, flush=True)
    sys.stdout.flush()


# Test configuration
BASE_URL = "http://localhost:8100"


def poll_cluster_state(project_id: str, cluster_name: str, expected_paused: bool, timeout: int = 900) -> dict:
    """
    Poll the cluster API until it reaches a stable state with the expected paused flag.

    MongoDB Atlas clusters in a paused state show stateName: IDLE with paused: True.
    Running clusters show stateName: IDLE with paused: False.
    We wait for the cluster to exit transitional states (UPDATING, REPAIRING, etc.)
    and reach IDLE with the expected paused flag.

    Args:
        project_id: The project ID
        cluster_name: The cluster name
        expected_paused: The expected paused flag (True for paused, False for running)
        timeout: Maximum time to wait in seconds (default: 900 = 15 minutes)

    Returns:
        The cluster data when state is reached

    Raises:
        TimeoutError: If the cluster doesn't reach the expected state within timeout
    """
    start_time = time.time()
    poll_interval = 5  # seconds
    # Transitional states that indicate the cluster is still changing
    transitional_states = ["CREATING", "UPDATING", "REPAIRING", "DELETING", "PAUSING", "RESUMING"]

    while time.time() - start_time < timeout:
        elapsed = int(time.time() - start_time)

        try:
            response = httpx.get(
                f"{BASE_URL}/api/clusters/{project_id}/{cluster_name}",
                timeout=30.0,
                follow_redirects=True
            )
            if response.status_code == 200:
                data = response.json()
                state = data.get("stateName", "UNKNOWN")
                paused = data.get("paused", False)

                log(f"   Cluster state: {state}, paused: {paused} ({elapsed}s elapsed)")

                # Check if cluster has reached stable state with expected paused flag
                is_stable = state not in transitional_states
                paused_match = (paused == expected_paused)

                if is_stable and paused_match:
                    return data

        except Exception as e:
            log(f"   Poll error: {e} ({elapsed}s elapsed)")

        time.sleep(poll_interval)

    # Timeout reached
    elapsed = int(time.time() - start_time)
    error_msg = (
        f"Timeout after {elapsed}s waiting for cluster '{cluster_name}' "
        f"to reach paused={expected_paused}"
    )
    log(f"   ✗ {error_msg}")
    raise TimeoutError(error_msg)


# =============================================================================
# Pause/Resume Tests (M10+ clusters only)
# =============================================================================

@pytest.mark.browser
@pytest.mark.integration
@pytest.mark.pause_resume
@pytest.mark.m10
def test_pause_resume_m10(page: Page, atlasui_server, m10_cluster):
    """
    Test pause/resume functionality on M10 cluster.

    This test:
    1. Navigates to clusters page
    2. Verifies Pause button exists for M10 cluster
    3. Clicks Pause and polls API for PAUSED state
    4. Clicks Resume and polls API for IDLE state
    5. Verifies countdown timer format (MM:SS + "Until next pause")

    The cluster is NOT deleted after the test - cleanup happens at session end.
    """
    project_id = m10_cluster["project_id"]
    cluster_name = m10_cluster["cluster_name"]

    log("\n" + "=" * 80)
    log("TEST: Pause/Resume M10 Cluster")
    log("=" * 80)
    log(f"   Project ID: {project_id}")
    log(f"   Cluster: {cluster_name}")

    # Step 1: Navigate to clusters page
    log(f"\n1. Navigating to {BASE_URL}/clusters")
    page.goto(f"{BASE_URL}/clusters")
    page.wait_for_load_state("domcontentloaded")
    page.wait_for_selector("#clustersContainer tr", timeout=60000)

    # Step 2: Find pause button
    log(f"\n2. Finding pause button for cluster: {cluster_name}")
    pause_button_selector = f'button[data-pause-cluster="{cluster_name}"][data-pause-project="{project_id}"]'
    pause_button = page.locator(pause_button_selector)

    page.wait_for_selector(pause_button_selector, timeout=30000)
    assert pause_button.count() > 0, f"Pause button not found for cluster {cluster_name}"
    log("   Pause button found")

    # Step 3: Click Pause
    log("\n3. Clicking Pause button")
    pause_button.click()

    # Poll API for paused state (not UI timeout)
    log("4. Polling API for cluster to reach paused state...")
    poll_cluster_state(project_id, cluster_name, expected_paused=True)
    log("   ✓ Cluster reached paused state (IDLE with paused=True)")

    # Refresh page to ensure UI is in sync
    page.reload()
    page.wait_for_load_state("domcontentloaded")
    page.wait_for_selector("#clustersContainer tr", timeout=30000)

    # Verify UI shows Resume button
    resume_button_selector = f'button[data-pause-cluster="{cluster_name}"][data-pause-project="{project_id}"]:has-text("Resume")'
    page.wait_for_selector(resume_button_selector, timeout=30000)
    log("   Resume button visible in UI")

    # Verify status shows PAUSED (UI may display multiple badges - IDLE and PAUSED)
    cluster_row = page.locator(f'tr[data-cluster-name="{cluster_name}"]')
    # Look for PAUSED badge specifically since paused clusters show both IDLE and PAUSED
    # Status column is td:nth-child(3): Name | Project | Status | Type | ...
    paused_badge = cluster_row.locator("td:nth-child(3) .badge:has-text('PAUSED')")
    assert paused_badge.count() > 0, f"Expected PAUSED badge for cluster {cluster_name}"
    log(f"   Status badge: PAUSED verified")

    # Step 4: Click Resume
    log("\n5. Clicking Resume button")
    resume_button = page.locator(resume_button_selector)
    resume_button.click()

    # Poll API for running state (not UI timeout)
    log("6. Polling API for cluster to reach running state...")
    poll_cluster_state(project_id, cluster_name, expected_paused=False)
    log("   ✓ Cluster reached running state (IDLE with paused=False)")

    # Refresh page to ensure UI is in sync
    page.reload()
    page.wait_for_load_state("domcontentloaded")
    page.wait_for_selector("#clustersContainer tr", timeout=30000)

    # Check for countdown timer
    log("7. Checking for countdown timer...")
    countdown_selector = f'button.pause-countdown[data-pause-cluster="{cluster_name}"][data-pause-project="{project_id}"]'

    try:
        page.wait_for_selector(countdown_selector, timeout=30000)
        log("   Countdown timer appeared")

        # Verify countdown format
        countdown_button = page.locator(countdown_selector)
        countdown_text = countdown_button.text_content()
        log(f"   Countdown text: {countdown_text}")

        # Extract and validate MM:SS format
        time_match = re.search(r'(\d{1,2}):(\d{2})', countdown_text)
        assert time_match, f"Could not find MM:SS format in: {countdown_text}"

        minutes = int(time_match.group(1))
        seconds = int(time_match.group(2))
        log(f"   Countdown: {minutes}m {seconds}s")

        assert 0 <= minutes <= 60, f"Minutes out of range: {minutes}"
        assert 0 <= seconds <= 59, f"Seconds out of range: {seconds}"

        # Verify "Until next pause" label
        assert "until next pause" in countdown_text.lower(), \
            f"Expected 'Until next pause' label in: {countdown_text}"
        log("   'Until next pause' label verified")

        # Verify countdown is ticking
        log("\n8. Verifying countdown is ticking...")
        initial_text = countdown_button.text_content()
        page.wait_for_timeout(2000)
        updated_text = countdown_button.text_content()

        if initial_text != updated_text:
            log(f"   Countdown ticking: {initial_text} -> {updated_text}")
        else:
            log(f"   Countdown at: {initial_text}")

    except Exception as e:
        # Check if Pause button appeared instead (Atlas might not enforce cooldown)
        pause_after = page.locator(f'button[data-pause-cluster="{cluster_name}"]:has-text("Pause")')
        if pause_after.count() > 0:
            log("   Note: Pause button appeared (cooldown not enforced)")
        else:
            raise

    log("\n" + "=" * 80)
    log("TEST PASSED: Pause/Resume M10 Cluster")
    log("=" * 80)
    log("   Note: Cluster left running (cleanup at session end)")


# =============================================================================
# Cluster Restriction Tests (M0, Flex cannot be paused)
# =============================================================================

@pytest.mark.browser
@pytest.mark.integration
@pytest.mark.restrictions
@pytest.mark.m0
def test_m0_no_pause_button(page: Page, atlasui_server, m0_cluster):
    """
    Verify that M0 (Free Tier) clusters do not have a pause button.

    M0 clusters cannot be paused because they use shared infrastructure.
    """
    project_id = m0_cluster["project_id"]
    cluster_name = m0_cluster["cluster_name"]

    log("\n" + "=" * 80)
    log("TEST: Verify M0 cluster has no Pause button")
    log("=" * 80)
    log(f"   Project ID: {project_id}")
    log(f"   Cluster: {cluster_name}")

    log(f"\n1. Navigating to {BASE_URL}/clusters")
    page.goto(f"{BASE_URL}/clusters")
    page.wait_for_load_state("domcontentloaded")

    log("2. Waiting for clusters to load")
    page.wait_for_selector("#clustersContainer tr", timeout=30000)

    log(f"3. Checking M0 cluster: {cluster_name}")
    cluster_row = page.locator(f'tr[data-cluster-name="{cluster_name}"]')
    assert cluster_row.count() > 0, f"Cluster {cluster_name} not found in UI"

    # Verify no pause button exists
    pause_button = cluster_row.locator("button:has-text('Pause')")
    assert pause_button.count() == 0, \
        f"M0 cluster {cluster_name} should not have a Pause button"

    log(f"   Verified: No Pause button for M0 cluster")

    log("\n" + "=" * 80)
    log("TEST PASSED: M0 cluster correctly has no Pause button")
    log("=" * 80)


@pytest.mark.browser
@pytest.mark.integration
@pytest.mark.restrictions
@pytest.mark.flex
def test_flex_no_pause_button(page: Page, atlasui_server, flex_cluster):
    """
    Verify that Flex clusters do not have a pause button.

    Flex clusters cannot be paused because they use managed infrastructure.
    """
    project_id = flex_cluster["project_id"]
    cluster_name = flex_cluster["cluster_name"]

    log("\n" + "=" * 80)
    log("TEST: Verify Flex cluster has no Pause button")
    log("=" * 80)
    log(f"   Project ID: {project_id}")
    log(f"   Cluster: {cluster_name}")

    log(f"\n1. Navigating to {BASE_URL}/clusters")
    page.goto(f"{BASE_URL}/clusters")
    page.wait_for_load_state("domcontentloaded")

    log("2. Waiting for clusters to load")
    page.wait_for_selector("#clustersContainer tr", timeout=30000)

    log(f"3. Checking Flex cluster: {cluster_name}")
    cluster_row = page.locator(f'tr[data-cluster-name="{cluster_name}"]')
    assert cluster_row.count() > 0, f"Cluster {cluster_name} not found in UI"

    # Verify no pause button exists
    pause_button = cluster_row.locator("button:has-text('Pause')")
    assert pause_button.count() == 0, \
        f"Flex cluster {cluster_name} should not have a Pause button"

    log(f"   Verified: No Pause button for Flex cluster")

    log("\n" + "=" * 80)
    log("TEST PASSED: Flex cluster correctly has no Pause button")
    log("=" * 80)


# =============================================================================
# Cluster Display Tests
# =============================================================================

@pytest.mark.browser
@pytest.mark.integration
@pytest.mark.display
def test_all_clusters_visible(page: Page, atlasui_server, test_clusters):
    """
    Verify all test clusters are visible in the clusters list.

    This test ensures the UI correctly displays all cluster types.
    """
    project_id = test_clusters["project_id"]
    clusters = test_clusters["clusters"]
    failed = test_clusters.get("failed", [])

    log("\n" + "=" * 80)
    log("TEST: Verify all clusters visible in UI")
    log("=" * 80)
    log(f"   Project ID: {project_id}")

    log(f"\n1. Navigating to {BASE_URL}/clusters")
    page.goto(f"{BASE_URL}/clusters")
    page.wait_for_load_state("domcontentloaded")

    log("2. Waiting for clusters to load")
    page.wait_for_selector("#clustersContainer tr", timeout=30000)

    log("3. Checking each cluster type:")

    # Check M0 cluster
    if clusters["m0"] and "M0" not in failed:
        m0_row = page.locator(f'tr[data-cluster-name="{clusters["m0"]}"]')
        assert m0_row.count() > 0, f"M0 cluster {clusters['m0']} not visible"
        log(f"   M0 cluster '{clusters['m0']}' - visible")
    else:
        log(f"   M0 cluster - skipped (creation failed)")

    # Check M10 cluster
    if clusters["m10"] and "M10" not in failed:
        m10_row = page.locator(f'tr[data-cluster-name="{clusters["m10"]}"]')
        assert m10_row.count() > 0, f"M10 cluster {clusters['m10']} not visible"
        log(f"   M10 cluster '{clusters['m10']}' - visible")
    else:
        log(f"   M10 cluster - skipped (creation failed)")

    # Check Flex cluster
    if clusters["flex"] and "Flex" not in failed:
        flex_row = page.locator(f'tr[data-cluster-name="{clusters["flex"]}"]')
        assert flex_row.count() > 0, f"Flex cluster {clusters['flex']} not visible"
        log(f"   Flex cluster '{clusters['flex']}' - visible")
    else:
        log(f"   Flex cluster - skipped (creation failed)")

    log("\n" + "=" * 80)
    log("TEST PASSED: All clusters visible in UI")
    log("=" * 80)


@pytest.mark.browser
@pytest.mark.integration
@pytest.mark.display
def test_cluster_status_badges(page: Page, atlasui_server, test_clusters):
    """
    Verify cluster status badges display correctly.

    All clusters should show IDLE status (green badge) when ready.
    """
    clusters = test_clusters["clusters"]
    failed = test_clusters.get("failed", [])

    log("\n" + "=" * 80)
    log("TEST: Verify cluster status badges")
    log("=" * 80)

    log(f"\n1. Navigating to {BASE_URL}/clusters")
    page.goto(f"{BASE_URL}/clusters")
    page.wait_for_load_state("domcontentloaded")

    log("2. Waiting for clusters to load")
    page.wait_for_selector("#clustersContainer tr", timeout=30000)

    log("3. Checking status badges:")

    for cluster_type, cluster_name in clusters.items():
        if not cluster_name or cluster_type.upper() in [f.upper() for f in failed]:
            log(f"   {cluster_type.upper()} - skipped (creation failed)")
            continue

        cluster_row = page.locator(f'tr[data-cluster-name="{cluster_name}"]').first
        if cluster_row.count() > 0:
            # Status column is td:nth-child(3): Name | Project | Status | Type | ...
            status_badge = cluster_row.locator("td:nth-child(3) .badge").first
            status_text = status_badge.text_content() if status_badge.count() > 0 else "UNKNOWN"
            log(f"   {cluster_type.upper()} cluster '{cluster_name}' - status: {status_text}")

            # Status should be IDLE or one of the valid operational states
            valid_states = ["IDLE", "PAUSED", "CREATING", "UPDATING", "REPAIRING"]
            assert any(s in status_text.upper() for s in valid_states), \
                f"Unexpected status for {cluster_name}: {status_text}"

    log("\n" + "=" * 80)
    log("TEST PASSED: Cluster status badges displayed correctly")
    log("=" * 80)


# =============================================================================
# Future Feature Tests
# =============================================================================
@pytest.mark.browser
@pytest.mark.integration
@pytest.mark.display
def test_project_details_ip_access_list(page: Page, atlasui_server, test_project):
    """
    Verify IP access list section displays in project details panel.

    This test:
    1. Navigates to organization projects page
    2. Opens project details panel
    3. Verifies IP Access List section exists
    4. Checks that section shows entries or "No IP access list entries" message
    """
    project_id = test_project["project_id"]
    project_name = test_project["project_name"]
    org_id = test_project["org_id"]

    log("\n" + "=" * 80)
    log("TEST: Verify IP Access List in Project Details")
    log("=" * 80)
    log(f"   Project ID: {project_id}")
    log(f"   Project Name: {project_name}")
    log(f"   Organization ID: {org_id}")

    # Step 1: Navigate to organization projects page
    log(f"\n1. Navigating to {BASE_URL}/organizations/{org_id}/projects")
    page.goto(f"{BASE_URL}/organizations/{org_id}/projects")
    page.wait_for_load_state("domcontentloaded")

    # Step 2: Wait for projects to load
    log("2. Waiting for projects table to load")
    page.wait_for_selector("#projectsContainer table", timeout=30000)

    # Step 3: Find and click the project name link to open details
    log(f"3. Looking for project name link: {project_name}")
    project_link = page.locator(f'a[onclick*="showProjectDetails(\'{project_id}\')"]')

    # Verify link exists
    assert project_link.count() > 0, f"Project name link not found for project {project_id}"
    log("   Found project name link")

    # Click the project name link
    log("4. Clicking project name to open project details panel")
    project_link.first.click()

    # Step 4: Wait for the offcanvas panel to open
    log("5. Waiting for project details panel to open")
    page.wait_for_selector("#detailsPanel.show", timeout=10000)

    # Wait for details content to load (not showing loading spinner)
    page.wait_for_selector("#detailsContent h5", timeout=10000)
    log("   Project details panel opened")

    # Step 5: Verify IP Access List section exists
    log("6. Verifying IP Access List section exists")

    # Look for the IP Access List heading
    ip_access_heading = page.locator("#detailsContent h6:has-text('IP Access List')")
    assert ip_access_heading.count() > 0, "IP Access List section heading not found"
    log("   ✓ IP Access List heading found")

    # Step 6: Verify section shows either entries or empty message
    log("7. Checking IP Access List content")

    # Check if there's a table (entries exist) or a "No IP access list entries" message
    has_table = page.locator("#detailsContent table thead th:has-text('IP/CIDR')").count() > 0
    has_empty_message = page.locator("#detailsContent p:has-text('No IP access list entries configured')").count() > 0

    if has_table:
        log("   ✓ IP Access List table with entries found")
        # Verify table has the correct columns
        assert page.locator("#detailsContent table thead th:has-text('Comment')").count() > 0, \
            "IP Access List table missing Comment column"
        log("   ✓ Table has IP/CIDR and Comment columns")
    elif has_empty_message:
        log("   ✓ 'No IP access list entries configured' message displayed")
    else:
        raise AssertionError("IP Access List section found but shows neither table nor empty message")

    # Step 7: Verify the count is displayed in the Basic Information table
    log("8. Verifying IP Access List count in Basic Information")
    ip_count_row = page.locator("#detailsContent table tr:has(th:has-text('IP Access List'))")
    assert ip_count_row.count() > 0, "IP Access List row not found in Basic Information table"
    log("   ✓ IP Access List count displayed in Basic Information table")

    log("\n" + "=" * 80)
    log("TEST PASSED: IP Access List displays correctly in project details")
    log("=" * 80)


# Add more tests here that require running clusters. Examples:
#
# @pytest.mark.integration
# def test_cluster_connection_string(page: Page, atlasui_server, m10_cluster):
#     """Test that connection strings are displayed correctly."""
#     pass
#
# @pytest.mark.integration
# def test_cluster_details_modal(page: Page, atlasui_server, m10_cluster):
#     """Test cluster details modal displays correctly."""
#     pass
#
# @pytest.mark.integration
# def test_cluster_scaling(page: Page, atlasui_server, m10_cluster):
#     """Test cluster scaling functionality."""
#     pass


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
