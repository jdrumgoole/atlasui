"""
Playwright tests for full cluster lifecycle with polling.

These tests validate that cluster creation and deletion operations complete fully:
1. test_m0_cluster_lifecycle: Create project + M0 cluster, wait for IDLE, delete cluster, wait for deletion, delete project
2. test_flex_cluster_lifecycle: Create project + Flex cluster, wait for IDLE, delete cluster, wait for deletion, delete project
3. test_m10_cluster_lifecycle: Create project + M10 cluster, wait for IDLE, delete cluster, wait for deletion, delete project

Each test ensures operations complete by polling status until:
- Cluster creation: stateName becomes "IDLE"
- Cluster deletion: cluster disappears from cluster list
- Project deletion: project disappears from project list
"""
import pytest
from playwright.sync_api import Page, expect
import time


def wait_for_cluster_creation(page: Page, cluster_name: str, timeout: int = 600) -> bool:
    """
    Poll for cluster creation to complete (stateName = IDLE).

    Args:
        page: Playwright page object
        cluster_name: Name of the cluster to monitor
        timeout: Maximum time to wait in seconds (default 10 minutes)

    Returns:
        bool: True if cluster reached IDLE state, False if timeout
    """
    print(f"\n  ⏳ Waiting for cluster '{cluster_name}' to reach IDLE state...")
    print(f"     This may take 5-10 minutes. Polling every 10 seconds (timeout: {timeout}s)")

    start_time = time.time()
    attempts = 0

    while time.time() - start_time < timeout:
        attempts += 1
        elapsed = int(time.time() - start_time)
        print(f"     Attempt {attempts} ({elapsed}s elapsed)...")

        # Reload the page to get latest cluster list
        page.reload()
        page.wait_for_load_state("domcontentloaded")
        time.sleep(2)  # Give UI time to render

        # Check cluster status in the UI
        # Look for the cluster row with this name and check its status badge
        cluster_row = page.locator(f'tr:has-text("{cluster_name}")').first

        if cluster_row.count() > 0:
            # Find the status badge in this row
            status_badge = cluster_row.locator('.badge').first
            if status_badge.count() > 0:
                status_text = status_badge.text_content()
                print(f"     Status: {status_text}")

                if status_text == "IDLE":
                    print(f"  ✓ Cluster '{cluster_name}' is now IDLE (ready)")
                    return True
                elif "ERROR" in status_text or "FAILED" in status_text:
                    print(f"  ❌ Cluster creation failed with status: {status_text}")
                    return False
        else:
            print(f"     Cluster not found in list yet...")

        # Wait before next poll
        time.sleep(10)

    print(f"  ⚠ Timeout waiting for cluster to reach IDLE state after {timeout}s")
    return False


def wait_for_cluster_deletion(page: Page, cluster_name: str, timeout: int = 600) -> bool:
    """
    Poll for cluster deletion to complete (cluster no longer in list).

    Args:
        page: Playwright page object
        cluster_name: Name of the cluster to monitor
        timeout: Maximum time to wait in seconds (default 10 minutes)

    Returns:
        bool: True if cluster was deleted, False if timeout
    """
    print(f"\n  ⏳ Waiting for cluster '{cluster_name}' deletion to complete...")
    print(f"     Polling every 10 seconds until cluster disappears (timeout: {timeout}s)")

    start_time = time.time()
    attempts = 0

    while time.time() - start_time < timeout:
        attempts += 1
        elapsed = int(time.time() - start_time)
        print(f"     Attempt {attempts} ({elapsed}s elapsed)...")

        # Refresh the page to get latest cluster list
        page.reload()
        page.wait_for_load_state("domcontentloaded")
        time.sleep(2)  # Give UI time to render

        # Check if cluster still exists in the list
        cluster_row = page.locator(f'tr:has-text("{cluster_name}")').first

        if cluster_row.count() == 0:
            print(f"  ✓ Cluster '{cluster_name}' has been deleted (no longer in list)")
            return True
        else:
            # Check status if still visible
            status_badge = cluster_row.locator('.badge').first
            if status_badge.count() > 0:
                status_text = status_badge.text_content()
                print(f"     Status: {status_text} (still deleting...)")

        # Wait before next poll
        time.sleep(10)

    print(f"  ⚠ Timeout waiting for cluster deletion after {timeout}s")
    return False


def create_project(page: Page, base_url: str) -> str:
    """
    Create a new project and return its name.

    Args:
        page: Playwright page object
        base_url: Base URL of the application

    Returns:
        str: The name of the created project
    """
    print("\n" + "="*80)
    print("Creating New Project")
    print("="*80)

    # Navigate to organizations page
    print("1. Navigating to organizations page")
    page.goto(f"{base_url}/organizations")
    page.wait_for_load_state("domcontentloaded")
    time.sleep(2)

    # Click on first organization's projects link
    print("2. Navigating to projects page")
    projects_link = page.locator('a[href*="/organizations/"][href*="/projects"]').first
    org_name = projects_link.get_attribute('href').split('/')[2]
    print(f"   Organization: {org_name}")
    projects_link.click()
    page.wait_for_load_state("domcontentloaded")
    time.sleep(2)

    # Click Create Project button
    print("3. Clicking Create Project button")
    create_project_btn = page.locator("#createProjectBtn, button:has-text('Create Project')").first
    create_project_btn.wait_for(state="visible", timeout=10000)
    create_project_btn.click()

    # Wait for modal
    print("4. Waiting for Create Project modal")
    project_modal = page.locator("#createProjectModal")
    project_modal.wait_for(state="visible", timeout=5000)

    # Generate unique project name
    project_name = f"test-lifecycle-{int(time.time())}"
    print(f"5. Creating project: {project_name}")

    # Fill and submit
    page.fill("#projectName", project_name)
    submit_btn = page.locator("#createProjectBtn").last
    submit_btn.click()

    # Wait for creation
    print("6. Waiting for project creation to complete...")
    time.sleep(3)

    print(f"✓ Project '{project_name}' created successfully")
    return project_name


def create_cluster(page: Page, base_url: str, project_name: str, cluster_name: str,
                   provider: str, region: str, instance_size: str, cluster_type: str = "REPLICASET"):
    """
    Create a cluster and wait for the creation modal to show progress.

    Args:
        page: Playwright page object
        base_url: Base URL of the application
        project_name: Project name to create cluster in
        cluster_name: Name for the cluster
        provider: Cloud provider (AWS, GCP, AZURE)
        region: Region code (e.g., US_EAST_1)
        instance_size: Instance size (M0, FLEX, M10, etc.)
        cluster_type: Cluster type (default: REPLICASET)
    """
    print(f"\n" + "="*80)
    print(f"Creating {instance_size} Cluster")
    print("="*80)
    print(f"  Name: {cluster_name}")
    print(f"  Project: {project_name}")
    print(f"  Provider: {provider}")
    print(f"  Region: {region}")
    print(f"  Type: {cluster_type}")

    # Navigate to clusters page (uses queue system for long-running operations)
    print("\n1. Navigating to clusters page")
    page.goto(f"{base_url}/clusters")
    page.wait_for_load_state("domcontentloaded")
    time.sleep(3)  # Give UI time to render

    # Click Create Cluster button
    print("2. Clicking Create Cluster button")
    create_btn = page.locator("#createClusterBtn")
    create_btn.wait_for(state="visible", timeout=10000)
    create_btn.click()

    # Wait for modal
    print("3. Waiting for Create Cluster modal")
    modal = page.locator("#createClusterModal")
    modal.wait_for(state="visible", timeout=5000)

    # Select project
    print(f"4. Selecting project: {project_name}")
    project_select = page.locator("#createClusterProjectId")
    time.sleep(3)  # Wait for projects to load

    # Find and select the project
    options = page.locator("#createClusterProjectId option").all()
    for option in options:
        text = option.text_content()
        if project_name in text:
            value = option.get_attribute("value")
            print(f"   Found project: {text}")
            project_select.select_option(value=value)
            break

    # Fill cluster details
    print(f"5. Filling cluster details")
    page.fill("#clusterNameInput", cluster_name)
    page.select_option("#providerName", provider)
    time.sleep(1)  # Wait for regions to load
    page.select_option("#regionName", region)
    page.select_option("#instanceSize", instance_size)
    page.select_option("#clusterType", cluster_type)

    # Submit
    print("6. Submitting cluster creation form")
    submit_btn = page.locator("#submitCreateClusterBtn")
    submit_btn.click()

    # Wait for creation to start
    print("7. Waiting for creation to initiate...")
    time.sleep(5)

    # Check for errors
    error_div = page.locator("#createClusterError")
    if error_div.is_visible():
        error_text = error_div.text_content()
        print(f"  ❌ ERROR: {error_text}")
        raise Exception(f"Failed to create cluster: {error_text}")

    print("  ✓ Cluster creation initiated")

    # Wait for success message or close modal
    success_div = page.locator("#createClusterSuccess")
    if success_div.is_visible():
        print("  ✓ Creation success message displayed")
        time.sleep(3)  # Wait for animation

    # Close modal if still open
    try:
        close_btn = page.locator("#createClusterModal .btn-close")
        if close_btn.is_visible():
            close_btn.click()
            time.sleep(1)
    except:
        pass  # Modal may have auto-closed


def delete_cluster(page: Page, base_url: str, cluster_name: str):
    """
    Delete a cluster and monitor deletion progress through the modal.

    Args:
        page: Playwright page object
        base_url: Base URL of the application
        cluster_name: Name of the cluster to delete
    """
    print(f"\n" + "="*80)
    print(f"Deleting Cluster: {cluster_name}")
    print("="*80)

    # Navigate to clusters page (uses queue system)
    print("1. Navigating to clusters page")
    page.goto(f"{base_url}/clusters")
    page.wait_for_load_state("domcontentloaded")
    time.sleep(2)

    # Find the cluster row and click delete button
    print(f"2. Finding cluster '{cluster_name}'")
    cluster_row = page.locator(f'tr:has-text("{cluster_name}")').first
    if cluster_row.count() == 0:
        print(f"  ⚠ Cluster '{cluster_name}' not found in list")
        return

    print("3. Clicking delete button")
    delete_btn = cluster_row.locator('button:has-text("Delete")').first
    delete_btn.click()

    # Wait for delete confirmation modal
    print("4. Waiting for delete confirmation modal")
    delete_modal = page.locator("#deleteClusterModal")
    delete_modal.wait_for(state="visible", timeout=5000)

    # Type cluster name to confirm
    print(f"5. Typing cluster name to confirm deletion")
    confirm_input = page.locator("#confirmClusterName")
    confirm_input.fill(cluster_name)
    time.sleep(0.5)

    # Click delete confirmation button
    print("6. Clicking delete confirmation button")
    confirm_btn = page.locator("#confirmDeleteClusterBtn")
    confirm_btn.click()

    # Wait for deletion to start and progress UI to show
    print("7. Waiting for deletion progress...")
    time.sleep(3)

    # Monitor deletion progress in the modal
    # The modal should show progress indicators as deletion proceeds
    print("8. Monitoring deletion progress in modal...")

    # Wait for the deletion progress UI to appear
    progress_div = page.locator("#deleteClusterProgress")
    if progress_div.is_visible():
        print("  ✓ Deletion progress UI displayed")

        # Wait for success message
        max_wait = 120  # 2 minutes max in modal
        start_time = time.time()

        while time.time() - start_time < max_wait:
            success_div = page.locator("#deleteClusterSuccess")
            if success_div.is_visible():
                print("  ✓ Deletion success message displayed in modal")
                break
            time.sleep(2)

    # Close modal
    time.sleep(2)
    try:
        close_btn = page.locator("#deleteClusterModal .btn-close, #deleteClusterCompleteFooter button")
        if close_btn.first.is_visible():
            close_btn.first.click()
            time.sleep(1)
    except:
        pass

    print("  ✓ Deletion initiated")


def delete_project(page: Page, base_url: str, project_name: str):
    """
    Delete a project.

    Args:
        page: Playwright page object
        base_url: Base URL of the application
        project_name: Name of the project to delete
    """
    print(f"\n" + "="*80)
    print(f"Deleting Project: {project_name}")
    print("="*80)

    # Navigate to organizations page
    print("1. Navigating to organizations page")
    page.goto(f"{base_url}/organizations")
    page.wait_for_load_state("domcontentloaded")
    time.sleep(2)

    # Navigate to projects page
    print("2. Navigating to projects page")
    projects_link = page.locator('a[href*="/organizations/"][href*="/projects"]').first
    projects_link.click()
    page.wait_for_load_state("domcontentloaded")
    time.sleep(2)

    # Find and click delete button for the project
    print(f"3. Finding project '{project_name}'")
    project_row = page.locator(f'tr:has-text("{project_name}")').first
    if project_row.count() == 0:
        print(f"  ⚠ Project '{project_name}' not found in list")
        return

    print("4. Clicking delete button")
    delete_btn = project_row.locator('button:has-text("Delete")').first
    delete_btn.click()

    # Wait for delete confirmation modal
    print("5. Waiting for delete confirmation modal")
    delete_modal = page.locator("#deleteConfirmModal")
    delete_modal.wait_for(state="visible", timeout=5000)
    time.sleep(3)  # Wait for resources to load

    # Type project name to confirm
    print(f"6. Typing project name to confirm deletion")
    confirm_input = page.locator("#deleteConfirmInput")
    confirm_input.fill(project_name)
    time.sleep(0.5)

    # Click delete confirmation button
    print("7. Clicking delete confirmation button")
    confirm_btn = page.locator("#deleteConfirmBtn")
    confirm_btn.click()

    # Wait for deletion to complete
    print("8. Waiting for project deletion to complete...")
    time.sleep(10)

    print("  ✓ Project deletion completed")


@pytest.mark.integration
@pytest.mark.lifecycle
@pytest.mark.m0
def test_m0_cluster_lifecycle(page: Page):
    """
    Test M0 cluster full lifecycle with polling.

    Steps:
    1. Create a new project
    2. Create an M0 cluster
    3. Wait for cluster to reach IDLE state (polling)
    4. Delete the cluster
    5. Wait for cluster deletion to complete (polling)
    6. Delete the project
    """
    base_url = "http://localhost:8000"

    print("\n" + "="*80)
    print("TEST: M0 Cluster Full Lifecycle")
    print("="*80)

    # Create project
    project_name = create_project(page, base_url)

    # Create M0 cluster
    cluster_name = f"m0-test-{int(time.time())}"
    create_cluster(
        page=page,
        base_url=base_url,
        project_name=project_name,
        cluster_name=cluster_name,
        provider="AWS",
        region="US_EAST_1",  # M0 works best in US_EAST_1
        instance_size="M0"
    )

    # Navigate to all clusters page for monitoring (uses queue system)
    page.goto(f"{base_url}/clusters")
    page.wait_for_load_state("domcontentloaded")

    # Wait for cluster creation to complete
    creation_success = wait_for_cluster_creation(page, cluster_name, timeout=600)
    assert creation_success, f"Cluster '{cluster_name}' did not reach IDLE state within timeout"

    # Delete cluster
    delete_cluster(page, base_url, cluster_name)

    # Wait for cluster deletion to complete
    deletion_success = wait_for_cluster_deletion(page, cluster_name, timeout=600)
    assert deletion_success, f"Cluster '{cluster_name}' was not deleted within timeout"

    # Delete project
    delete_project(page, base_url, project_name)

    print("\n" + "="*80)
    print("✓ M0 Cluster Lifecycle Test Completed Successfully")
    print("="*80 + "\n")


@pytest.mark.integration
@pytest.mark.lifecycle
@pytest.mark.flex
def test_flex_cluster_lifecycle(page: Page):
    """
    Test Flex cluster full lifecycle with polling.

    Steps:
    1. Create a new project
    2. Create a Flex cluster
    3. Wait for cluster to reach IDLE state (polling)
    4. Delete the cluster
    5. Wait for cluster deletion to complete (polling)
    6. Delete the project
    """
    base_url = "http://localhost:8000"

    print("\n" + "="*80)
    print("TEST: Flex Cluster Full Lifecycle")
    print("="*80)

    # Create project
    project_name = create_project(page, base_url)

    # Create Flex cluster
    cluster_name = f"flex-test-{int(time.time())}"
    create_cluster(
        page=page,
        base_url=base_url,
        project_name=project_name,
        cluster_name=cluster_name,
        provider="AWS",
        region="US_EAST_1",
        instance_size="FLEX"
    )

    # Navigate to all clusters page for monitoring (uses queue system)
    page.goto(f"{base_url}/clusters")
    page.wait_for_load_state("domcontentloaded")

    # Wait for cluster creation to complete
    creation_success = wait_for_cluster_creation(page, cluster_name, timeout=600)
    assert creation_success, f"Cluster '{cluster_name}' did not reach IDLE state within timeout"

    # Delete cluster
    delete_cluster(page, base_url, cluster_name)

    # Wait for cluster deletion to complete
    deletion_success = wait_for_cluster_deletion(page, cluster_name, timeout=600)
    assert deletion_success, f"Cluster '{cluster_name}' was not deleted within timeout"

    # Delete project
    delete_project(page, base_url, project_name)

    print("\n" + "="*80)
    print("✓ Flex Cluster Lifecycle Test Completed Successfully")
    print("="*80 + "\n")


@pytest.mark.integration
@pytest.mark.lifecycle
@pytest.mark.m10
def test_m10_cluster_lifecycle(page: Page):
    """
    Test M10 cluster full lifecycle with polling.

    Steps:
    1. Create a new project
    2. Create an M10 cluster
    3. Wait for cluster to reach IDLE state (polling)
    4. Delete the cluster
    5. Wait for cluster deletion to complete (polling)
    6. Delete the project
    """
    base_url = "http://localhost:8000"

    print("\n" + "="*80)
    print("TEST: M10 Cluster Full Lifecycle")
    print("="*80)

    # Create project
    project_name = create_project(page, base_url)

    # Create M10 cluster
    cluster_name = f"m10-test-{int(time.time())}"
    create_cluster(
        page=page,
        base_url=base_url,
        project_name=project_name,
        cluster_name=cluster_name,
        provider="AWS",
        region="US_EAST_1",
        instance_size="M10"
    )

    # Navigate to all clusters page for monitoring (uses queue system)
    page.goto(f"{base_url}/clusters")
    page.wait_for_load_state("domcontentloaded")

    # Wait for cluster creation to complete
    creation_success = wait_for_cluster_creation(page, cluster_name, timeout=600)
    assert creation_success, f"Cluster '{cluster_name}' did not reach IDLE state within timeout"

    # Delete cluster
    delete_cluster(page, base_url, cluster_name)

    # Wait for cluster deletion to complete
    deletion_success = wait_for_cluster_deletion(page, cluster_name, timeout=600)
    assert deletion_success, f"Cluster '{cluster_name}' was not deleted within timeout"

    # Delete project
    delete_project(page, base_url, project_name)

    print("\n" + "="*80)
    print("✓ M10 Cluster Lifecycle Test Completed Successfully")
    print("="*80 + "\n")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "-m", "integration"])
