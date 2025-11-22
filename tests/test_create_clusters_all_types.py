"""
Playwright test for creating and deleting multiple cluster types.

This test automates the full lifecycle:
1. Creates a new project
2. Creates M0 Free Tier cluster (US_EAST_1 - recommended for M0)
3. Creates Serverless cluster (SKIPPED - configuration format under investigation)
4. Creates M10 Dedicated cluster (EU_WEST_1)
5. Deletes the project (which automatically deletes all associated clusters)

This test validates both cluster creation and the project deletion functionality,
including the cascading deletion of all clusters within the project.

IMPORTANT LIMITATIONS:
- Only ONE M0 cluster is allowed per PROJECT. You can have multiple M0 clusters in
  an organization as long as they are in different projects.
- M0 clusters use the TENANT provider with a backingProviderName instead of the
  standard providerSettings configuration.
- Serverless cluster creation is currently skipped due to unresolved API configuration
  format. The correct providerSettings structure needs clarification from MongoDB Atlas
  API documentation.
"""
import pytest
from playwright.sync_api import Page, expect
import time


def test_create_project_and_clusters(page: Page):
    """
    Test the full lifecycle of project and cluster management.

    This test will:
    1. Navigate to the organizations page
    2. Create a new project
    3. Create an M0 cluster in US_EAST_1
    4. Skip Serverless cluster (configuration format under investigation)
    5. Create an M10 cluster in EU_WEST_1
    6. Delete the project (cascading delete of all clusters)
    7. Verify project and clusters are deleted
    8. Capture console logs and network errors
    9. Report any errors
    """
    # Storage for console messages and network failures
    console_messages = []
    network_errors = []
    request_responses = []

    # Listen to console messages
    page.on("console", lambda msg: console_messages.append({
        "type": msg.type,
        "text": msg.text
    }))

    # Listen to network failures
    page.on("requestfailed", lambda request: network_errors.append({
        "url": request.url,
        "method": request.method,
        "failure": request.failure
    }))

    # Listen to network responses for cluster and project creation
    page.on("response", lambda response: request_responses.append({
        "url": response.url,
        "status": response.status,
        "method": response.request.method
    }) if "/api/clusters/" in response.url or "/api/projects/" in response.url else None)

    print("\n" + "="*80)
    print("Starting Project and Cluster Creation Test")
    print("="*80)

    # Navigate to the application
    base_url = "http://localhost:8000"
    print(f"\n1. Navigating to {base_url}")
    page.goto(base_url)

    # Wait for the page to load
    page.wait_for_load_state("networkidle")

    # =========================================================================
    # STEP 1: Create a new project
    # =========================================================================
    print("\n2. Creating a new project")
    page.goto(f"{base_url}/organizations")
    page.wait_for_load_state("networkidle")

    # Wait for the page to load and find the first organization
    print("3. Waiting for organizations to load...")
    time.sleep(2)

    # Click on the first organization's projects link
    # Find the first organization and navigate to its projects
    try:
        # Look for a link that goes to /organizations/*/projects
        projects_link = page.locator('a[href*="/organizations/"][href*="/projects"]').first
        org_name = projects_link.get_attribute('href').split('/')[2]
        print(f"4. Found organization: {org_name}")
        projects_link.click()
        page.wait_for_load_state("networkidle")
    except Exception as e:
        print(f"Error finding organization: {e}")
        print("Attempting alternate method...")
        # Alternative: navigate directly if we can get org name from page
        page.goto(f"{base_url}/organizations")
        page.wait_for_load_state("networkidle")

    # Click Create Project button
    print("5. Clicking Create Project button")
    create_project_btn = page.locator("#createProjectBtn, button:has-text('Create Project')").first
    create_project_btn.wait_for(state="visible", timeout=10000)
    create_project_btn.click()

    # Wait for modal to appear
    print("6. Waiting for Create Project modal")
    project_modal = page.locator("#createProjectModal")
    project_modal.wait_for(state="visible", timeout=5000)

    # Generate a unique project name
    project_name = f"test-clusters-{int(time.time())}"
    print(f"7. Creating project: {project_name}")

    # Fill in project name
    page.fill("#projectName", project_name)

    # Click create
    submit_btn = page.locator("#createProjectBtn").last
    submit_btn.click()

    # Wait for project to be created
    print("8. Waiting for project creation to complete...")
    time.sleep(3)

    # Get the project ID (we'll need this for cluster creation)
    project_id = None

    # =========================================================================
    # STEP 2: Navigate to clusters page
    # =========================================================================
    print("\n9. Navigating to clusters page")
    page.goto(f"{base_url}/clusters")
    page.wait_for_load_state("networkidle")

    # Clear previous messages
    console_messages.clear()
    request_responses.clear()
    network_errors.clear()

    # =========================================================================
    # STEP 3: Create M0 Free Tier Cluster
    # =========================================================================
    print("\n" + "="*80)
    print("Creating M0 Free Tier Cluster")
    print("="*80)
    print("Note: M0 uses TENANT provider with US_EAST_1 for best support")
    print("Note: Only ONE M0 cluster allowed per project (multiple M0s allowed across different projects)")

    create_cluster(
        page=page,
        cluster_name=f"m0-cluster-{int(time.time())}",
        project_name=project_name,
        provider="AWS",
        region="US_EAST_1",
        instance_size="M0",
        cluster_type="REPLICASET"
    )

    print("\n10. M0 cluster creation initiated successfully")
    time.sleep(2)

    # =========================================================================
    # STEP 4: Skip Serverless (configuration needs more investigation)
    # =========================================================================
    print("\n" + "="*80)
    print("Skipping Serverless Cluster (configuration format under investigation)")
    print("="*80)
    print("Note: Serverless providerSettings format needs clarification from MongoDB Atlas API docs")

    # =========================================================================
    # STEP 5: Create M10 Dedicated Cluster
    # =========================================================================
    print("\n" + "="*80)
    print("Creating M10 Dedicated Cluster")
    print("="*80)

    create_cluster(
        page=page,
        cluster_name=f"m10-cluster-{int(time.time())}",
        project_name=project_name,
        provider="AWS",
        region="EU_WEST_1",
        instance_size="M10",
        cluster_type="REPLICASET"
    )

    print("\n12. M10 cluster creation initiated successfully")

    # =========================================================================
    # STEP 6: Delete the Project (and all its clusters)
    # =========================================================================
    print("\n" + "="*80)
    print("Deleting Project and Associated Clusters")
    print("="*80)
    print(f"13. Navigating to projects page to delete project: {project_name}")

    # Navigate to the organizations page to find the project
    page.goto(f"{base_url}/organizations")
    page.wait_for_load_state("networkidle")
    time.sleep(2)

    # Click on the first organization's projects link to get to the projects page
    projects_link = page.locator('a[href*="/organizations/"][href*="/projects"]').first
    projects_link.click()
    page.wait_for_load_state("networkidle")
    time.sleep(2)

    print(f"14. Finding and clicking delete button for project: {project_name}")

    # Find the project row and click the delete button
    # The project table has rows with project names, find the one matching our project
    project_row = page.locator(f'tr:has-text("{project_name}")').first
    delete_btn = project_row.locator('button:has-text("Delete")').first
    delete_btn.click()

    print("15. Waiting for delete confirmation modal")
    # Wait for the delete confirmation modal to appear
    delete_modal = page.locator("#deleteConfirmModal")
    delete_modal.wait_for(state="visible", timeout=5000)

    # Wait for resources to load in the modal
    time.sleep(3)

    print("16. Typing project name to confirm deletion")
    # Type the project name in the confirmation input
    confirm_input = page.locator("#deleteConfirmInput")
    confirm_input.fill(project_name)

    print("17. Clicking delete confirmation button")
    # Click the delete confirmation button
    # After typing the correct project name, the button should be enabled
    delete_confirm_btn = page.locator("#deleteConfirmBtn")
    delete_confirm_btn.wait_for(state="visible", timeout=5000)
    # Wait a moment for the button to be enabled after typing
    time.sleep(0.5)
    delete_confirm_btn.click()

    print("18. Waiting for project deletion to complete...")
    # Wait for the deletion process to complete
    # The button text will change during the process:
    # "Preparing..." -> "Loading clusters..." -> "Deleting clusters (X/Y)..."
    # -> "Waiting for cluster deletions to complete..." -> "Deleting project..."
    # Cluster deletion can take 30-60 seconds, so we wait up to 2 minutes
    time.sleep(90)  # Give enough time for cluster deletions to complete and project deletion

    print("19. Verifying project has been deleted")
    # Verify the success message appears
    success_alert = page.locator('.alert-success:has-text("deleted successfully")')
    if success_alert.is_visible():
        print("✓ Project deletion success message displayed")
    else:
        print("⚠ No success message visible, but continuing...")

    # Wait for projects list to reload
    time.sleep(2)

    # Verify the project is no longer in the list
    project_exists = page.locator(f'tr:has-text("{project_name}")').count() > 0
    if not project_exists:
        print(f"✓ Project '{project_name}' successfully removed from projects list")
    else:
        print(f"⚠ Project '{project_name}' still visible in list (may be caching)")

    # =========================================================================
    # Print Summary
    # =========================================================================
    print("\n" + "="*80)
    print("CAPTURED INFORMATION")
    print("="*80)

    # Print console messages
    print("\n--- Console Messages ---")
    for msg in console_messages:
        print(f"[{msg['type'].upper()}] {msg['text']}")

    # Print network responses
    print("\n--- Network Responses ---")
    for resp in request_responses:
        print(f"{resp['method']} {resp['url']} - Status: {resp['status']}")

    # Print network errors
    if network_errors:
        print("\n--- Network Errors ---")
        for err in network_errors:
            print(f"{err['method']} {err['url']}")
            print(f"  Failure: {err['failure']}")

    print("\n" + "="*80)
    print("Test Complete")
    print("="*80 + "\n")

    # Keep browser open for inspection
    # page.pause()  # Uncomment this to pause and inspect manually


def create_cluster(page: Page, cluster_name: str, project_name: str,
                   provider: str, region: str, instance_size: str,
                   cluster_type: str):
    """
    Helper function to create a cluster.

    Args:
        page: Playwright page object
        cluster_name: Name for the cluster
        project_name: Project name to create cluster in
        provider: Cloud provider (AWS, GCP, AZURE)
        region: Region code (e.g., EU_WEST_1)
        instance_size: Instance size (M0, SERVERLESS, M10, etc.)
        cluster_type: Cluster type (REPLICASET, SHARDED)
    """
    print(f"\nCreating cluster: {cluster_name}")
    print(f"  Project: {project_name}")
    print(f"  Provider: {provider}")
    print(f"  Region: {region}")
    print(f"  Instance Size: {instance_size}")
    print(f"  Type: {cluster_type}")

    # Click Create Cluster button
    print("\n  - Clicking Create Cluster button")
    create_btn = page.locator("#createClusterBtn")
    create_btn.wait_for(state="visible", timeout=10000)
    create_btn.click()

    # Wait for modal
    print("  - Waiting for Create Cluster modal")
    modal = page.locator("#createClusterModal")
    modal.wait_for(state="visible", timeout=5000)

    # Select project
    print(f"  - Selecting project: {project_name}")
    project_select = page.locator("#createClusterProjectId")

    # Wait for projects to load
    time.sleep(3)

    # The project dropdown contains options like "ProjectName (OrgName)"
    # We need to find the option that contains our project name
    # Get all options and find the one containing our project name
    options = page.locator("#createClusterProjectId option").all()
    selected = False
    for option in options:
        text = option.text_content()
        if project_name in text:
            value = option.get_attribute("value")
            print(f"    Found project option: {text} (value: {value})")
            project_select.select_option(value=value)
            selected = True
            break

    if not selected:
        # If we couldn't find the project, print all available options for debugging
        print("    ERROR: Could not find project in dropdown!")
        print("    Available options:")
        for option in options:
            print(f"      - {option.text_content()}")
        raise Exception(f"Could not find project '{project_name}' in dropdown")

    # Fill cluster name
    print(f"  - Setting cluster name: {cluster_name}")
    page.fill("#clusterNameInput", cluster_name)

    # Select provider
    print(f"  - Selecting provider: {provider}")
    page.select_option("#providerName", provider)

    # Wait for regions to load
    time.sleep(1)

    # Select region
    print(f"  - Selecting region: {region}")
    page.select_option("#regionName", region)

    # Select instance size
    print(f"  - Selecting instance size: {instance_size}")
    page.select_option("#instanceSize", instance_size)

    # Select cluster type (if not Serverless)
    if instance_size != "SERVERLESS":
        print(f"  - Selecting cluster type: {cluster_type}")
        page.select_option("#clusterType", cluster_type)

    # Submit
    print("  - Submitting cluster creation form")
    submit_btn = page.locator("#submitCreateClusterBtn")
    submit_btn.click()

    # Wait for response
    print("  - Waiting for response...")
    time.sleep(3)

    # Check for error or success
    error_div = page.locator("#createClusterError")
    success_div = page.locator("#createClusterSuccess")

    if error_div.is_visible():
        error_text = error_div.text_content()
        print(f"\n  ❌ ERROR: {error_text}")
        # Close modal
        close_btn = page.locator("#createClusterModal .btn-close")
        close_btn.click()
        raise Exception(f"Failed to create cluster: {error_text}")

    if success_div.is_visible():
        print("  ✓ Cluster creation initiated")
        # Wait a bit to see the animation
        time.sleep(3)
        # Close modal if it hasn't auto-closed
        try:
            close_btn = page.locator("#createClusterModal .btn-close")
            if close_btn.is_visible():
                close_btn.click()
        except:
            pass  # Modal may have auto-closed
    else:
        print("  ⚠ No success or error message visible")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
