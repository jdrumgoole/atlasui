"""
Playwright test for cluster creation UI.

This test automates the cluster creation process and captures detailed error information.
"""
import pytest
from playwright.sync_api import Page, expect
import json


@pytest.mark.browser
def test_create_cluster(page: Page, atlasui_server):
    """
    Test cluster creation through the UI.

    This test will:
    1. Navigate to a project's clusters page
    2. Click the Create Cluster button
    3. Fill out the form with valid data
    4. Capture console logs and network errors
    5. Submit the form
    6. Report any errors
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

    # Listen to network responses
    page.on("response", lambda response: request_responses.append({
        "url": response.url,
        "status": response.status,
        "method": response.request.method
    }) if "/api/clusters/" in response.url else None)

    print("\n" + "="*80)
    print("Starting Cluster Creation Test")
    print("="*80)

    # Navigate to the application
    base_url = "http://localhost:8100"
    print(f"\n1. Navigating to {base_url}")
    page.goto(base_url)

    # Wait for the page to load
    page.wait_for_load_state("load")

    # Navigate to the global clusters page
    print("2. Navigating to global clusters page")
    page.goto(f"{base_url}/clusters")
    page.wait_for_load_state("load")

    # Wait for the Create Cluster button to be visible
    print("3. Waiting for Create Cluster button")
    create_button = page.locator("#createClusterBtn")
    create_button.wait_for(state="visible", timeout=10000)

    # Click the Create Cluster button
    print("4. Clicking Create Cluster button")
    create_button.click()

    # Wait for the modal to appear
    print("5. Waiting for Create Cluster modal")
    modal = page.locator("#createClusterModal")
    modal.wait_for(state="visible", timeout=5000)

    # Fill out the form
    print("6. Filling out cluster creation form")

    # Cluster name
    cluster_name = "test-cluster-playwright"
    page.fill("#clusterNameInput", cluster_name)
    print(f"   - Cluster name: {cluster_name}")

    # Select cloud provider (AWS)
    page.select_option("#providerName", "AWS")
    print("   - Provider: AWS")

    # Wait a moment for regions to populate
    page.wait_for_timeout(1000)

    # Select region
    page.select_option("#regionName", "US_EAST_1")
    print("   - Region: US_EAST_1")

    # Select instance size (M10)
    page.select_option("#instanceSize", "M10")
    print("   - Instance size: M10")

    # Select cluster type
    page.select_option("#clusterType", "REPLICASET")
    print("   - Cluster type: REPLICASET")

    # MongoDB version (leave default)
    print("   - MongoDB version: Latest (default)")

    # Enable backup (uncheck for M10 to keep it simple)
    backup_checkbox = page.locator("#enableBackup")
    if backup_checkbox.is_checked():
        backup_checkbox.uncheck()
    print("   - Backup: Disabled")

    print("\n7. Submitting cluster creation form")

    # Clear previous console messages
    console_messages.clear()
    request_responses.clear()
    network_errors.clear()

    # Click the create button
    submit_button = page.locator("#submitCreateClusterBtn")
    submit_button.click()

    # Wait for response (either success or error)
    print("8. Waiting for response...")
    page.wait_for_timeout(3000)

    # Print all captured information
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

    # Check for error message in the UI
    error_div = page.locator("#createClusterError")
    if error_div.is_visible():
        error_text = error_div.text_content()
        print("\n--- UI Error Message ---")
        print(error_text)

    # Check for success message
    success_div = page.locator("#createClusterSuccess")
    if success_div.is_visible():
        print("\n--- SUCCESS ---")
        print("Cluster creation initiated successfully!")

    print("\n" + "="*80)
    print("Test Complete")
    print("="*80 + "\n")

    # Keep browser open for inspection
    # page.pause()  # Uncomment this to pause and inspect manually


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
